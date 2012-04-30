from itertools import islice
from os import path, makedirs
from random import sample
from time import time

from conversion import Conversion
from payload import HotsPayload, SearchMemberRequestPayload, SearchSquareRequestPayload, SearchTextRequestPayload, SearchMemberResponsePayload, SearchSquareResponsePayload, SearchTextResponsePayload
from hot import Hot, HotCache

from square.community import PreviewCommunity
from square.database import SquareDatabase

from dispersy.member import DummyMember
from dispersy.cache import CacheDict
from dispersy.authentication import NoAuthentication
from dispersy.community import Community
from dispersy.conversion import DefaultConversion
from dispersy.destination import CommunityDestination, CandidateDestination
from dispersy.distribution import DirectDistribution
from dispersy.message import Message
from dispersy.resolution import PublicResolution

if __debug__:
    from dispersy.dprint import dprint

class DiscoveryCommunity(Community):
    def __init__(self, *args):
        super(DiscoveryCommunity, self).__init__(*args)

        self._database = SquareDatabase.has_instance()
        if not self._database:
            # our data storage
            sqlite_directory = path.join(self._dispersy.working_directory, u"sqlite")
            if not path.isdir(sqlite_directory):
                makedirs(sqlite_directory)

            self._database = SquareDatabase.get_instance(sqlite_directory)
            self._dispersy.database.attach_commit_callback(self._database.commit)

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
                Message(self, u"search-member-request", NoAuthentication(), PublicResolution(), DirectDistribution(), CommunityDestination(node_count=20), SearchMemberRequestPayload(), self._dispersy._generic_timeline_check, self.on_search_member_request),
                Message(self, u"search-square-request", NoAuthentication(), PublicResolution(), DirectDistribution(), CommunityDestination(node_count=20), SearchSquareRequestPayload(), self._dispersy._generic_timeline_check, self.on_search_square_request),
                Message(self, u"search-text-request", NoAuthentication(), PublicResolution(), DirectDistribution(), CommunityDestination(node_count=20), SearchTextRequestPayload(), self._dispersy._generic_timeline_check, self.on_search_text_request),
                Message(self, u"search-member-response", NoAuthentication(), PublicResolution(), DirectDistribution(), CandidateDestination(), SearchMemberResponsePayload(), self._dispersy._generic_timeline_check, self.on_search_member_response),
                Message(self, u"search-square-response", NoAuthentication(), PublicResolution(), DirectDistribution(), CandidateDestination(), SearchSquareResponsePayload(), self._dispersy._generic_timeline_check, self.on_search_square_response),
                Message(self, u"search-text-response", NoAuthentication(), PublicResolution(), DirectDistribution(), CandidateDestination(), SearchTextResponsePayload(), self._dispersy._generic_timeline_check, self.on_search_text_response)]

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

    def simple_member_search(self, string, response_func, response_args=(), timeout=10.0):
        pairs = [(min(len(keyword), 127), keyword) for keyword in string.split()]
        return self.member_search(pairs, [], 1, response_func, response_args, timeout)

    def simple_square_search(self, string, response_func, response_args=(), timeout=10.0):
        pairs = [(min(len(keyword), 127), keyword) for keyword in string.split()]
        return self.square_search(pairs, [], 1, response_func, response_args, timeout)

    def simple_text_search(self, string, response_func, response_args=(), timeout=10.0):
        pairs = [(min(len(keyword), 127), keyword) for keyword in string.split()]
        return self.text_search(pairs, [], 1, response_func, response_args, timeout)

    def member_search(self, terms, squares, threshold, response_func, response_args=(), timeout=10.0):
        meta = self._meta_messages[u"search-member-request"]
        message = meta.impl(distribution=(self.global_time,), payload=(0, terms, squares, threshold))
        if self._dispersy.store_update_forward([message], False, False, True):
            meta = self._meta_messages[u"search-member-response"]
            self._dispersy.await_message(meta.generate_footprint(), response_func, response_args=response_args, timeout=timeout, max_responses=1)
        else:
            if __debug__: dprint("unable to search.  most likely there are no candidates", level="warning")
            response_func(None, *response_args)

        return message

    def square_search(self, terms, squares, threshold, response_func, response_args=(), timeout=10.0):
        meta = self._meta_messages[u"search-square-request"]
        message = meta.impl(distribution=(self.global_time,), payload=(0, terms, squares, threshold))
        if self._dispersy.store_update_forward([message], False, False, True):
            meta = self._meta_messages[u"search-square-response"]
            self._dispersy.await_message(meta.generate_footprint(), response_func, response_args=response_args, timeout=timeout, max_responses=1)
        else:
            if __debug__: dprint("unable to search.  most likely there are no candidates", level="warning")
            response_func(None, *response_args)

        return message

    def text_search(self, terms, squares, threshold, response_func, response_args=(), timeout=10.0):
        meta = self._meta_messages[u"search-text-request"]
        message = meta.impl(distribution=(self.global_time,), payload=(0, terms, squares, threshold))
        if self._dispersy.store_update_forward([message], False, False, True):
            meta = self._meta_messages[u"search-text-response"]
            self._dispersy.await_message(meta.generate_footprint(), response_func, response_args=response_args, timeout=timeout, max_responses=1)
        else:
            if __debug__: dprint("unable to search.  most likely there are no candidates", level="warning")
            response_func(None, *response_args)

        return message

    def on_search_member_request(self, messages):
        dispersy_execute = self._dispersy.database.execute
        execute = self._database.execute
        meta = self._meta_messages[u"search-member-response"]
        responses = []

        for message in messages:
            payload = message.payload
            if __debug__: dprint("searching ", " + ".join("%d:%s" % (weight, term) for weight, term in payload.terms), " for ", message.candidate)

            results = dict()
            for weight, term in payload.terms:
                for docid, in execute(u"SELECT docid FROM member_fts WHERE alias MATCH ?", (term,)):
                    if docid in results:
                        results[docid] += weight
                    else:
                        results[docid] = weight

            results = sorted(results.iteritems(), key=lambda tup:tup[1], reverse=True)
            members = []
            for docid, weight in islice(results, 24):
                try:
                    member_id, community_id = execute(u"SELECT dispersy_id, square FROM member WHERE id = ?", (docid,)).next()
                    cid, = dispersy_execute(u"SELECT master.mid FROM community JOIN member AS master ON master.id = community.master WHERE community.id = ?", (community_id,)).next()
                    mid, = dispersy_execute(u"SELECT mid FROM member WHERE id = ?", (member_id,)).next()
                except StopIteration:
                    if __debug__: dprint("unable to determine results for docid ", docid, level="error", exception=1)
                    continue
                else:
                    members.append((weight, str(cid), str(mid)))

            if members:
                responses.append(meta.impl(distribution=(self.global_time,), destination=(message.candidate,), payload=(payload.identifier, members)))

        if responses:
            self._dispersy.store_update_forward(responses, False, False, True)

    def on_search_square_request(self, messages):
        dispersy_execute = self._dispersy.database.execute
        execute = self._database.execute
        meta = self._meta_messages[u"search-square-response"]
        responses = []

        for message in messages:
            payload = message.payload
            if __debug__: dprint("searching ", " + ".join("%d:%s" % (weight, term) for weight, term in payload.terms), " for ", message.candidate)

            results = dict()
            for weight, term in payload.terms:
                for docid, in execute(u"SELECT docid FROM square_fts WHERE title MATCH ?", (term,)):
                    if docid in results:
                        results[docid] += weight
                    else:
                        results[docid] = weight

                for docid, in execute(u"SELECT docid FROM square_fts WHERE description MATCH ?", (term,)):
                    if docid in results:
                        results[docid] += weight
                    else:
                        results[docid] = weight

            results = sorted(results.iteritems(), key=lambda tup:tup[1], reverse=True)
            squares = []
            for docid, weight in islice(results, 48):
                try:
                    cid, = dispersy_execute(u"SELECT master.mid FROM community JOIN member AS master ON master.id = community.master WHERE community.id = ?", (docid,)).next()
                except StopIteration:
                    if __debug__: dprint("unable to determine results for docid ", docid, level="error")
                    continue
                else:
                    squares.append((weight, str(cid)))

            if squares:
                responses.append(meta.impl(distribution=(self.global_time,), destination=(message.candidate,), payload=(payload.identifier, squares,)))

        if responses:
            self._dispersy.store_update_forward(responses, False, False, True)

    def on_search_text_request(self, messages):
        dispersy_execute = self._dispersy.database.execute
        execute = self._database.execute
        meta = self._meta_messages[u"search-text-response"]
        responses = []

        for message in messages:
            payload = message.payload
            if __debug__: dprint("searching ", " + ".join("%d:%s" % (weight, term) for weight, term in payload.terms), " for ", message.candidate)

            results = dict()
            for weight, term in payload.terms:
                for docid, in execute(u"SELECT docid FROM text_fts WHERE text MATCH ?", (term,)):
                    if docid in results:
                        results[docid] += weight
                    else:
                        results[docid] = weight

            results = sorted(results.iteritems(), key=lambda tup:tup[1], reverse=True)
            texts = []
            for docid, weight in islice(results, 20):
                try:
                    cid, mid, global_time = dispersy_execute(u"SELECT master.mid, member.mid, sync.global_time FROM sync JOIN community ON community.id = sync.community JOIN member AS master ON master.id = community.master JOIN member ON member.id = sync.member WHERE sync.id = ?", (docid,)).next()
                except StopIteration:
                    if __debug__: dprint("unable to determine results for docid ", docid, level="error")
                    continue
                else:
                    texts.append((weight, str(cid), str(mid), global_time))

            if texts:
                responses.append(meta.impl(distribution=(self.global_time,), destination=(message.candidate,), payload=(payload.identifier, texts,)))

        if responses:
            self._dispersy.store_update_forward(responses, False, False, True)

    def on_search_member_response(self, messages):
        pass

    def on_search_square_response(self, messages):
        pass

    def on_search_text_response(self, messages):
        pass
