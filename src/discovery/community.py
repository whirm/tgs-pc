from itertools import islice, groupby
from os import path, makedirs
from random import sample, random

from conversion import Conversion
from payload import HotsPayload, SearchMemberRequestPayload, SearchSquareRequestPayload, SearchTextRequestPayload, SearchMemberResponsePayload, SearchSquareResponsePayload, SearchTextResponsePayload

from square.community import PreviewCommunity
from square.database import SquareDatabase

from dispersy.authentication import NoAuthentication
from dispersy.community import Community
from dispersy.conversion import DefaultConversion
from dispersy.destination import CommunityDestination, CandidateDestination
from dispersy.distribution import DirectDistribution
from dispersy.member import DummyMember
from dispersy.message import Message, DropMessage
from dispersy.requestcache import Cache
from dispersy.resolution import PublicResolution

if __debug__:
    from dispersy.dprint import dprint

class Suggestion(object):
    def __init__(self, cid, mid, global_time):
        self.cid = cid
        self.mid = mid
        self.global_time = global_time
        self.attempt = 0
        self.sources = []
        self.state = "waiting"
        self.weight = 0
        self.square = None
        self.hit = None

    def __str__(self):
        return "<Suggestion %s weight:%d attempt:%d>" % (self.state, self.weight, self.attempt)

    def _result(self, message, repository):
        if message and message.name == self.message_name:
            self.state = "done"
            self.hit = self.message_to_hit(message)
            self.square.dec_dependencies()
            if __debug__: dprint("hit! ", self, " (attempt #", self.attempt, ")")
            repository.on_hit()
            return True

        else:
            return False

    def _fetch_retry(self, response, repository):
        if not self._result(response, repository):
            if self.attempt < 10:
                self.attempt += 1

                # retry
                self.fetch(repository)

            else:
                self.state = "give-up"
                self.square.dec_dependencies()

    def fetch(self, repository):
        assert isinstance(repository, SuggestionRepository), type(repository)
        if self.state in ("waiting", "fetching"):
            if self.sources:
                assert self.hit is None

                if self.square is None:
                    # get square
                    try:
                        self.square = repository.discovery.dispersy.get_community(self.cid, load=True)
                    except KeyError:
                        self.square = PreviewCommunity.join_community(DummyMember(self.cid), repository.discovery.my_member, repository.discovery, repository.enable_walker)

                    if isinstance(self.square, PreviewCommunity) and repository.enable_walker and not self.square.dispersy_enable_candidate_walker:
                        # we must enable the walker
                        self.square.start_candidate_walker()

                    self.state = "fetching"
                    self.square.inc_dependencies()

                # get message
                source = self.sources[int(random() * len(self.sources))]
                if __debug__: dprint("fetch ", self, " from ", source, " (attempt #", self.attempt, ")")
                message = self.square.fetch_message(self.mid, self.global_time, source, self._fetch_retry, (repository,), 5.0 if __debug__ else 1.0)

                self._result(message, repository)

            else:
                self.state = "waiting"
                self.square.dec_dependencies()

    @property
    def message_name(self):
        raise NotImplementedError()

    @property
    def message_to_hit(self):
        raise NotImplementedError()

class MemberSuggestion(Suggestion):
    @property
    def message_name(self):
        return  u"member-info"

    @property
    def message_to_hit(self):
        return self.square.message_to_member

class SquareSuggestion(Suggestion):
    @property
    def message_name(self):
        return  u"square-info"

    @property
    def message_to_hit(self):
        return lambda _: self.square

class TextSuggestion(Suggestion):
    @property
    def message_name(self):
        return  u"text"

    @property
    def message_to_hit(self):
        return self.square.message_to_text

class SuggestionRepository(object):
    def __init__(self, discovery):
        self.discovery = discovery
        self.unordered_suggestions = {}
        self.suggestions = []

    @property
    def enable_walker(self):
        raise NotImplementedError()

    def add_suggestions(self, source, suggestions, suggestion_cls):
        if __debug__: dprint(len(suggestions), " suggestions from ", source)

        for weight, cid, mid, global_time in suggestions:
            response = self.unordered_suggestions.get((cid, mid, global_time))
            if response is None:
                self.unordered_suggestions[(cid, mid, global_time)] = response = suggestion_cls(cid, mid, global_time)

            response.sources.append(source)
            response.weight += weight

        return len(self.unordered_suggestions) > len(self.suggestions)

    def order_and_fetch_suggestions(self, fetch_count):
        previous_suggestions_count = len(self.suggestions)

        # order by weight
        self.suggestions = sorted(self.unordered_suggestions.itervalues(), key=lambda response: response.weight, reverse=True)

        # download the top N hits
        for response in islice(self.suggestions, fetch_count):
            if response.state == "waiting":
                response.fetch(self)

        return len(self.suggestions) > previous_suggestions_count

class HotCollector(SuggestionRepository):
    def __init__(self, discovery):
        super(HotCollector, self).__init__(discovery)
        self.top_squares = []
        self.top_texts = []

    @property
    def enable_walker(self):
        return True

    def on_hots(self, messages):
        for message in messages:
            self.add_suggestions(message.candidate, message.payload.suggestions, TextSuggestion)

        old_top = self.suggestions[:10]
        self.order_and_fetch_suggestions(10)

        for i, suggestion in enumerate(self.suggestions[:10]):
            suggestion.square.inc_dependencies()

        for suggestion in old_top:
            suggestion.square.dec_dependencies()

    def on_hit(self):
        self.top_texts = []
        self.top_squares = []

        for suggestion in self.suggestions:
            if suggestion.state == "done":
                if len(self.top_texts) < 10:
                    self.top_texts.append(suggestion.hit)

                if len(self.top_squares) < 10:
                    if not suggestion.square in self.top_squares:
                        self.top_squares.append(suggestion.square)
                else:
                    break

        if __debug__:
            for index, text in enumerate(self.top_texts):
                dprint("#", index, " - ", text)
            for index, square in enumerate(self.top_squares):
                dprint("#", index, " - ", square)

        # TODO notify GUI that there are new top squares and texts

class SearchCache(SuggestionRepository, Cache):
    cleanup_delay = 180.0

    def __init__(self, discovery, terms, squares, threshold, response_func, response_args, timeout):
        super(SearchCache, self).__init__(discovery)

        # the original search request
        self.discovery = discovery
        self.terms = terms
        self.squares = squares
        self.threshold = threshold
        self.response_func = response_func
        self.response_args = response_args
        self.timeout_delay = timeout

        if __debug__: dprint("searching for ", terms)

    @property
    def enable_walker(self):
        return False

    def on_response(self, messages, suggestion_cls):
        for message in messages:
            self.add_suggestions(message.candidate, message.payload.suggestions, suggestion_cls)

        if self.order_and_fetch_suggestions(10):
            # inform that there are suggestions
            self.response_func(self, "suggestion", *self.response_args)

    def on_hit(self):
        # inform that there are suggestions
        self.response_func(self, "hit", *self.response_args)

    def on_timeout(self):
        # inform that there will be no more suggestions or hits
        self.response_func(self, "finished", *self.response_args)

class DiscoveryCommunity(Community):
    def __init__(self, *args):
        self._explicitly_hot_text = []
        self._implicitly_hot_text = []
        self._hot_collector = HotCollector(self)

        super(DiscoveryCommunity, self).__init__(*args)

        self._database = SquareDatabase.has_instance()
        if not self._database:
            # our data storage
            sqlite_directory = path.join(self._dispersy.working_directory, u"sqlite")
            if not path.isdir(sqlite_directory):
                makedirs(sqlite_directory)

            self._database = SquareDatabase.get_instance(sqlite_directory)
            self._dispersy.database.attach_commit_callback(self._database.commit)

        self._pending_callbacks.append(self._dispersy.callback.register(self._select_and_announce_hot))

    def initiate_meta_messages(self):
        return [Message(self, u"hots", NoAuthentication(), PublicResolution(), DirectDistribution(), CommunityDestination(node_count=5), HotsPayload(), self._dispersy._generic_timeline_check, self._hot_collector.on_hots),
                Message(self, u"search-member-request", NoAuthentication(), PublicResolution(), DirectDistribution(), CommunityDestination(node_count=20), SearchMemberRequestPayload(), self._dispersy._generic_timeline_check, self.on_search_member_request),
                Message(self, u"search-square-request", NoAuthentication(), PublicResolution(), DirectDistribution(), CommunityDestination(node_count=20), SearchSquareRequestPayload(), self._dispersy._generic_timeline_check, self.on_search_square_request),
                Message(self, u"search-text-request", NoAuthentication(), PublicResolution(), DirectDistribution(), CommunityDestination(node_count=20), SearchTextRequestPayload(), self._dispersy._generic_timeline_check, self.on_search_text_request),
                Message(self, u"search-member-response", NoAuthentication(), PublicResolution(), DirectDistribution(), CandidateDestination(), SearchMemberResponsePayload(), self.check_search_response, self.on_search_member_response),
                Message(self, u"search-square-response", NoAuthentication(), PublicResolution(), DirectDistribution(), CandidateDestination(), SearchSquareResponsePayload(), self.check_search_response, self.on_search_square_response),
                Message(self, u"search-text-response", NoAuthentication(), PublicResolution(), DirectDistribution(), CandidateDestination(), SearchTextResponsePayload(), self.check_search_response, self.on_search_text_response)]

    def initiate_conversions(self):
        return [DefaultConversion(self), Conversion(self)]

    @property
    def top_squares(self):
        return self._hot_collector.top_squares

    @property
    def top_texts(self):
        return self._hot_collector.top_texts

    def add_explicitly_hot_text(self, message):
        # TODO all messages should be unique
        self._explicitly_hot_text.append(message)
        del self._explicitly_hot_text[20:]

    def add_implicitly_hot_text(self, messages):
        # TODO all messages should be unique
        self._implicitly_hot_text.extend(messages)
        del self._implicitly_hot_text[20:]

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
                suggestions = [(0, message.community.cid, message.authentication.member.mid, message.distribution.global_time) for message in messages]
                message = meta.impl(distribution=(self.global_time,), payload=(suggestions,))
                # hots = [Hot(message.community.cid, message.authentication.member.mid, message.distribution.global_time) for message in messages]
                # message = meta.impl(distribution=(self.global_time,), payload=(hots,))
                self._dispersy.store_update_forward([message], False, False, True)

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
        cache = SearchCache(self, terms, squares, threshold, response_func, response_args, timeout)
        identifier = self._dispersy.request_cache.claim(cache)

        meta = self._meta_messages[u"search-member-request"]
        request = meta.impl(distribution=(self.global_time,), payload=(identifier, terms, squares, threshold))
        if not self._dispersy.store_update_forward([request], False, False, True):
            if __debug__: dprint("unable to search.  most likely there are no candidates", level="warning")
            self._dispersy.request_cache.pop(identifier, SearchCache)
            cache.on_timeout()

        return cache

    def square_search(self, terms, squares, threshold, response_func, response_args=(), timeout=10.0):
        cache = SearchCache(self, terms, squares, threshold, response_func, response_args, timeout)
        identifier = self._dispersy.request_cache.claim(cache)

        meta = self._meta_messages[u"search-square-request"]
        request = meta.impl(distribution=(self.global_time,), payload=(identifier, terms, squares, threshold))
        if not self._dispersy.store_update_forward([request], False, False, True):
            if __debug__: dprint("unable to search.  most likely there are no candidates", level="warning")
            self._dispersy.request_cache.pop(identifier, SearchCache)
            cache.on_timeout()

        return cache

    def text_search(self, terms, squares, threshold, response_func, response_args=(), timeout=10.0):
        cache = SearchCache(self, terms, squares, threshold, response_func, response_args, timeout)
        identifier = self._dispersy.request_cache.claim(cache)

        meta = self._meta_messages[u"search-text-request"]
        request = meta.impl(distribution=(self.global_time,), payload=(identifier, terms, squares, threshold))
        if not self._dispersy.store_update_forward([request], False, False, True):
            if __debug__: dprint("unable to search.  most likely there are no candidates", level="warning")
            self._dispersy.request_cache.pop(identifier, SearchCache)
            cache.on_timeout()

        return cache

    def check_search_response(self, messages):
        for message in messages:
            if not self._dispersy.request_cache.has(message.payload.identifier, SearchCache):
                yield DropMessage(message, "invalid response identifier")
                continue

            yield message

    def on_search_member_response(self, messages):
        key = lambda message: message.payload.identifier
        for identifier, iterator in groupby(sorted(messages, key=key), key=key):
            cache = self._dispersy.request_cache.get(identifier, SearchCache)
            cache.on_response(list(iterator), MemberSuggestion)

    def on_search_square_response(self, messages):
        key = lambda message: message.payload.identifier
        for identifier, iterator in groupby(sorted(messages, key=key), key=key):
            cache = self._dispersy.request_cache.get(identifier, SearchCache)
            cache.on_response(list(iterator), SquareSuggestion)

    def on_search_text_response(self, messages):
        key = lambda message: message.payload.identifier
        for identifier, iterator in groupby(sorted(messages, key=key), key=key):
            cache = self._dispersy.request_cache.get(identifier, SearchCache)
            cache.on_response(list(iterator), TextSuggestion)

    def on_search_member_request(self, messages):
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
            suggestions = list(islice(self._sync_id_to_search_response(results), 21))
            if suggestions:
                responses.append(meta.impl(distribution=(self.global_time,), destination=(message.candidate,), payload=(payload.identifier, suggestions)))

        if responses:
            self._dispersy.store_update_forward(responses, False, False, True)

    def on_search_square_request(self, messages):
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
            suggestions = list(islice(self._sync_id_to_search_response(results), 21))
            if suggestions:
                responses.append(meta.impl(distribution=(self.global_time,), destination=(message.candidate,), payload=(payload.identifier, suggestions)))

        self._dispersy.store_update_forward(responses, False, False, True)

    def on_search_text_request(self, messages):
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
            suggestions = list(islice(self._sync_id_to_search_response(results), 20))
            if suggestions:
                responses.append(meta.impl(distribution=(self.global_time,), destination=(message.candidate,), payload=(payload.identifier, suggestions,)))

        if responses:
            self._dispersy.store_update_forward(responses, False, False, True)

    def _sync_id_to_search_response(self, results):
        dispersy_execute = self._dispersy.database.execute
        for docid, weight in results:
            try:
                cid, mid, global_time = dispersy_execute(u"SELECT master.mid, member.mid, sync.global_time FROM sync JOIN community ON community.id = sync.community JOIN member AS master ON master.id = community.master JOIN member ON member.id = sync.member WHERE sync.id = ?", (docid,)).next()
            except StopIteration:
                if __debug__: dprint("unable to determine results for docid ", docid, level="error")
                continue
            else:
                yield weight, str(cid), str(mid), global_time

