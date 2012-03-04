from random import sample
from time import time

from conversion import Conversion
from payload import HotsPayload, SearchPayload
from hot import Hot, HotCache

from square.community import PreviewCommunity

from dispersy.member import DummyMember
from dispersy.cache import CacheDict
from dispersy.authentication import NoAuthentication
from dispersy.community import Community
from dispersy.conversion import DefaultConversion
from dispersy.destination import CommunityDestination
from dispersy.distribution import DirectDistribution
from dispersy.message import Message
from dispersy.resolution import PublicResolution

if __debug__:
    from dispersy.dprint import dprint

class DiscoveryCommunity(Community):
    def __init__(self, *args):
        super(DiscoveryCommunity, self).__init__(*args)
        self._explicitly_hot_text = []
        self._implicitly_hot_text = []
        self._top_squares = []
        self._top_text = []
        self._hots = CacheDict(max_caches=1024)
        self._pending_callbacks.append(self._dispersy.callback.register(self._select_and_announce_hot))
        self._pending_callbacks.append(self._dispersy.callback.register(self._periodically_collect_top_hots))
        self._pending_callbacks.append(self._dispersy.callback.register(self._hot_cleanup))

    def initiate_meta_messages(self):
        return [Message(self, u"hots", NoAuthentication(), PublicResolution(), DirectDistribution(), CommunityDestination(node_count=5), HotsPayload(), self._dispersy._generic_timeline_check, self.on_hots),
                Message(self, u"search", NoAuthentication(), PublicResolution(), DirectDistribution(), CommunityDestination(node_count=20), SearchPayload(), self._dispersy._generic_timeline_check, self.on_search)]

    def initiate_conversions(self):
        return [DefaultConversion(self), Conversion(self)]

    @property
    def top_squares(self):
        return self._top_squares

    @property
    def top_text(self):
        return self._top_text

    def add_explicitly_hot_text(self, message):
        # TODO all messages should be unique
        self._explicitly_hot_text.append(message)
        del self._explicitly_hot_text[20:]

    def add_implicitly_hot_text(self, messages):
        # TODO all messages should be unique
        self._implicitly_hot_text.extend(messages)
        del self._implicitly_hot_text[20:]

    def _hot_cleanup(self):
        while True:
            yield 300.0
            for _ in self._hots.cleanup():
                pass

    def _select_and_announce_hot(self):
        meta = self._meta_messages[u"hots"]
        while True:
            # TODO yield 60.0, lowered for debugging
            yield 10.0
            # what is hot?
            # explicit: a message the user marked as 'hot'
            # implicit: a newly received message
            messages = sample(self._explicitly_hot_text, min(15, len(self._explicitly_hot_text)))
            messages.extend(sample(self._implicitly_hot_text, min(20-len(messages), len(self._implicitly_hot_text))))
            # TODO all messages should be unique

            if messages:
                if __debug__: dprint(len(messages), "x text")
                hots = [Hot(message.community.cid, message.authentication.member.mid, message.distribution.global_time) for message in messages]
                message = meta.impl(distribution=(self.global_time,), payload=(hots,))
                self._dispersy.store_update_forward([message], False, False, True)

    def _collect_top_hots(self):
        now = time()
        self._top_squares = []
        self._top_text = []

        for index, key in enumerate(self._hots):
            hot = self._hots[key]
            assert isinstance(hot, HotCache), hot
            if not hot.square:
                try:
                    hot.square = self._dispersy.get_community(hot.cid, load=True)
                except KeyError:
                    master = DummyMember(hot.cid)
                    hot.square = PreviewCommunity.join_community(master, self._my_member, self)

            if index < 10:
                if not hot.message and hot.last_requested < now - 10.0 and hot.sources:
                    hot.message = hot.square.fetch_hot_text(hot)

                if hot.message:
                    self._top_text.append(hot.message)

            if not hot.square in self._top_squares:
                self._top_squares.append(hot.square)
                if len(self._top_squares) == 10:
                    break

        if __debug__:
            for index, square in enumerate(self._top_squares):
                dprint(index, "] SQUARE ", square.cid.encode("HEX"), " - ", square.title)
            for index, message in enumerate(self._top_text):
                dprint(index, "]   TEXT ", message.community.cid.encode("HEX"), " - ", message.payload.text)

    def _periodically_collect_top_hots(self):
        while True:
            # TODO yield 30.0, lowered for debugging
            yield 10.0
            self._collect_top_hots()

    def on_hots(self, messages):
        for message in messages:
            for hot in message.payload.hots:
                key = hot.key

                # 'upgrade' Hot to HotCache, also modifies importance counters in CacheDict
                if key in self._hots:
                    hot = self._hots[key]
                else:
                    self._hots[key] = hot = HotCache(hot)
                assert isinstance(hot, HotCache), hot
                assert isinstance(self._hots[key], HotCache), self._hots[key]

                hot.add_source(message.candidate)

        if len(self._top_squares) + len(self._top_text) < 10:
            self._collect_top_hots()

    def keyword_search(self, keywords):
        return self.expression_search(u"|".join(keywords))
            
    def expression_search(self, expression):
        meta = self._meta_messages[u"search"]
        message = meta.impl(distribution=(self.global_time,), payload=(expression,))
        self._dispersy.store_update_forward([message], False, False, True)
        return message

    def on_search(self, messages):
        for message in messages:
            if __debug__: dprint("searching for \\", message.payload.expression, "\\")
            # TODO
