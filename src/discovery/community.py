from random import sample
from time import time

from conversion import Conversion
from payload import HotsPayload, SearchPayload, SearchResponsePayload
from hot import Hot, HotCache

from square.community import SquareBase, PreviewCommunity

from dispersy.member import DummyMember
from dispersy.cache import CacheDict
from dispersy.authentication import NoAuthentication
from dispersy.community import Community
from dispersy.conversion import DefaultConversion
from dispersy.destination import CommunityDestination, CandidateDestination
from dispersy.distribution import DirectDistribution
from dispersy.message import Message
from dispersy.resolution import PublicResolution
from dispersy.requestcache import Cache

if __debug__:
    from dispersy.dprint import dprint

class SearchCache(Cache):
    class Hit(object):
        def __init__(self):
            self.count = 0
            self.sources = []
            self.last_requested = 0.0
            self.square = None
            self.message = None

    def __init__(self, identifier, expression, response_func, response_args):
        super(SearchCache, self).__init__(identifier)
        self._expression = expression
        self._response_func = response_func
        self._response_args = response_args
        self._responses_received = 0
        self._hits = {}

    @property
    def hits(self):
        return self._hits

    def add_hit(self, cid, mid, global_time, candidate):
        key = (cid, mid, global_time)
        hit = self._hits.get(key)
        if not hit:
            self._hits[key] = hit = self.Hit()
        hit.count += 1
        hit.sources.append(candidate)
        self._responses_received += 1

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
                Message(self, u"search", NoAuthentication(), PublicResolution(), DirectDistribution(), CommunityDestination(node_count=20), SearchPayload(), self._dispersy._generic_timeline_check, self.on_search),
                Message(self, u"search-response", NoAuthentication(), PublicResolution(), DirectDistribution(), CandidateDestination(), SearchResponsePayload(), self._dispersy._generic_timeline_check, self.on_search_response)]

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
                    if not isinstance(hot.square, SquareBase):
                        # TODO do this better
                        if __debug__: dprint("hit in invalid community")
                        hot.square = None
                        continue
                except KeyError:
                    master = DummyMember(hot.cid)
                    hot.square = PreviewCommunity.join_community(master, self._my_member, self)

            if index < 10:
                if not hot.message and hot.last_requested < now - 10.0 and hot.sources:
                    hot.message = hot.square.fetch_text(hot.mid, hot.global_time, hot.sources)

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
        pass
        # for message in messages:
        #     for hot in message.payload.hots:
        #         key = hot.key

        #         # 'upgrade' Hot to HotCache, also modifies importance counters in CacheDict
        #         if key in self._hots:
        #             hot = self._hots[key]
        #         else:
        #             self._hots[key] = hot = HotCache(hot)
        #         assert isinstance(hot, HotCache), hot
        #         assert isinstance(self._hots[key], HotCache), self._hots[key]

        #         hot.add_source(message.candidate)

        # if len(self._top_squares) + len(self._top_text) < 10:
        #     self._collect_top_hots()

    def keyword_search(self, keywords, response_func, response_args=(), timeout=10.0):
        return self.expression_search(u"|".join(keywords), response_func, response_args, timeout)

    def expression_search(self, expression, response_func, response_args=(), timeout=10.0):
        cache = self._dispersy._request_cache.claim(timeout, SearchCache, expression, response_func, response_args)

        meta = self._meta_messages[u"search"]
        message = meta.impl(distribution=(self.global_time,), payload=(cache.identifier, expression))
        if not self._dispersy.store_update_forward([message], False, False, True):
            if __debug__: dprint("unable to search.  most likely there are no candidates", level="warning")
            response_func(None, *response_args)

        return message

    def on_search(self, messages):
        meta = self._meta_messages[u"search-response"]
        for message in messages:
            if __debug__: dprint("searching \\", message.payload.expression, "\\ for ", message.candidate)

            # TODO currently always responding with whats hot
            if self._implicitly_hot_text:
                hots = [Hot(msg.community.cid, msg.authentication.member.mid, msg.distribution.global_time) for msg in self._implicitly_hot_text[:10]]

                response = meta.impl(distribution=(self.global_time,), destination=(message.candidate,), payload=(message.payload.identifier, hots))
                self._dispersy.store_update_forward([response], False, False, True)
                if __debug__: dprint("responding with ", len(hots), " hot messages")

    def on_search_response(self, messages):
        updated_caches = set()
        for message in messages:
            cache = self._dispersy._request_cache.get(message.payload.identifier)
            if cache:
                updated_caches.add(cache)
                for hot in message.payload.hots:
                    cache.add_hit(hot.cid, hot.mid, hot.global_time, message.candidate)

        # auto-join squares to retrieve results
        now = time()
        for cache in updated_caches:
            for (cid, mid, global_time), hit in cache.hits.iteritems():
                if not hit.square:
                    try:
                        hit.square = self._dispersy.get_community(cid, load=True)
                        if not isinstance(hit.square, SquareBase):
                            # TODO do this better
                            if __debug__: dprint("hit in invalid community: ", hit.square)
                            hit.square = None
                            continue
                    except KeyError:
                        master = DummyMember(cid)
                        hit.square = PreviewCommunity.join_community(master, self._my_member, self)

                if not hit.message and hit.last_requested < now - 10.0 and hit.sources:
                    hit.message = hit.square.fetch_text(hit.mid, hit.global_time, hit.sources)

                    if hit.message:
                        if __debug__: dprint("received and verified \"", hit.message.payload.text, "\"")
                        # TODO notify the GUI
