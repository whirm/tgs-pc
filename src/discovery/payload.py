from dispersy.payload import Payload

class HotsPayload(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, suggestions):
            """
            Implement hots message.

            SUGGESTIONS is a list containing (weight, community-id, member-id, global-time) quadruples.
            """
            super(HotsPayload.Implementation, self).__init__(meta)
            self._suggestions = suggestions

        @property
        def suggestions(self):
            return self._suggestions

class SearchRequestPayload(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, identifier, terms, squares, threshold):
            """
            Implement search request.

            IDENTIFIER is a 2 byte number.
            TERMS is a list containing (weight, string) pairs.
            SQUARES is a list containing (weight, community-id) pairs.
            THRESHOLD is the minimal value for a hit to qualify.
            """
            assert isinstance(terms, list) and 0 < len(terms) < 256
            assert all(isinstance(x, tuple) and len(x) == 2 for x in terms)
            assert all(isinstance(x[0], int) and -128 <= x[0] < 128 for x in terms)
            assert all(isinstance(x[1], unicode) and len(x[1].encode("UTF-8")) < 256 for x in terms)
            assert isinstance(squares, list) and len(squares) < 256
            assert all(isinstance(x, tuple) and len(x) == 2 for x in squares)
            assert all(isinstance(x[0], int) and -128 <= x[0] < 128 for x in squares)
            assert all(isinstance(x[1], unicode) and len(x[1]) == 20 for x in squares)
            assert isinstance(threshold, int) and 0 < threshold < 256
            super(SearchRequestPayload.Implementation, self).__init__(meta)
            self.identifier = identifier
            self.terms = terms
            self.squares = squares
            self.threshold = threshold

class SearchMemberRequestPayload(SearchRequestPayload):
    pass

class SearchSquareRequestPayload(SearchRequestPayload):
    pass

class SearchTextRequestPayload(SearchRequestPayload):
    pass

class SearchResponsePayload(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, identifier, suggestions):
            """
            Implement search response.

            IDENTIFIER is a 2 byte number.
            SUGGESTIONS is a list containing (weight, community-id, member-id, global-time) quadruples.
            """
            super(SearchResponsePayload.Implementation, self).__init__(meta)
            self.identifier = identifier
            self.suggestions = suggestions

class SearchMemberResponsePayload(SearchResponsePayload):
    pass

class SearchSquareResponsePayload(SearchResponsePayload):
    pass

class SearchTextResponsePayload(SearchResponsePayload):
    pass
