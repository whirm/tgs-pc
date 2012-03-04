from time import time

from conversion import Conversion
from payload import HotsPayload
from hot import Hot, HotCache

from square.community import PreviewSquare

from dispersy.cache import CacheDict
from dispersy.authentication import MemberAuthentication
from dispersy.community import Community
from dispersy.conversion import DefaultConversion
from dispersy.destination import CommunityDestination
from dispersy.distribution import DirectDistribution
from dispersy.message import Message
from dispersy.resolution import PublicResolution

if __debug__:
    from dispersy.dprint import dprint

class Discovery(Community):
    def __init__(self, *args):
        super(Discovery, self).__init__(*args)
        self._explicitly_hot_messages = []
        self._implicitly_hot_messages = []
        self._top_squares = []
        self._top_messages = []
        self._hots = CacheDict(max_caches=1024)
        self._pending_callbacks.append(self._dispersy.callback.register(self._select_and_announce_hot))
        self._pending_callbacks.append(self._dispersy.callback.register(self._collect_top_hots))
        self._pending_callbacks.append(self._dispersy.callback.register(self._hot_cleanup))

    def initiate_meta_messages(self):
        return [Message(self, u"hots", MemberAuthentication(encoding="sha1"), PublicResolution(), DirectDistribution(), CommunityDestination(node_count=5), HotsPayload(), self._dispersy._generic_timeline_check, self.on_hots)]

    def initiate_conversions(self):
        return [DefaultConversion(self), Conversion(self)]

    @property
    def top_squares(self):
        return self._top_squares

    @property
    def top_messages(self):
        return self._top_messages

    def add_explicitly_hot_message(self, message):
        self._explicitly_hot_messages.append(message)
        del self._explicitly_hot_messages[20:]

    def add_implicitly_hot_messages(self, messages):
        self._implicitly_hot_messages.extend(messages)
        del self._implicitly_hot_messages[20:]

    def _hot_cleanup(self):
        while True:
            yield 300.0
            for _ in self._hots.cleanup():
                pass

    def _select_and_announce_hot(self):
        meta = self._meta_messages[u"favorite-square"]
        while True:
            yield 60.0
            # what is hot?
            # explicit: a message the user marked as 'hot'
            # implicit: a newly received message
            messages = sample(self._explicitly_hot_messages, max(15, len(self._explicitly_hot_messages)))
            messages.extend(sample(self._implicitly_hot_messages, max(20-len(messages)), len(self._implicitly_hot_messages)))

            hots = [Hot(message.community.cid, message.authentication.member.mid, message.distribution.global_time) for message in messages]
            message = meta.impl(authentication=(self._my_member,), distribution=(self.global_time,), payload=(hots))
            self._dispersy.store_update_forward([message], False, False, True)

    def _collect_top_hots(self):
        while True:
            yield 30.0
            now = time()
            self._top_squares = []
            self._top_messages = []

            for index, hot in enumerate(self._hots):
                if not hot.square:
                    try:
                        hot.square = self._dispersy.get_community(hot.cid, load=True)
                    except KeyError:
                        hot.square = PreviewSquare.join_community(hot.cid, self._my_member)

                if index < 10:
                    if not hot.message and hot.last_requested < now - 10.0:
                        hot.message = hot.square.fetch_hot_message(hot)

                    if hot.message:
                        self._top_messages.append(hot.message)

                if not hot.square in self._top_squares:
                    self._top_squares.append(hot.square)
                    if len(self._top_squares) == 10:
                        break

    def on_hots(self, messages):
        for message in messages:
            for hot in message.payload.hots:

                # 'upgrade' Hot to HotCache, also modifies importance counters in CacheDict
                if hot in self._hots:
                    self._hots[hot] = hot = HotCache(hot)
                else:
                    hot = self._hots[hot]

                hot.add_source(message.candidate)

    def on_missing_hot(self, messages):
        for message in messages:
            # 'upgrade' Hot to HotCache, also modifies importance counters in CacheDict
            hot = self._hots.get(message.payload.hot)
            if hot and hot.is_available:
                self._dispersy._send([message.candidate], [hot.square, hot.message], u"-missing-hot-")
