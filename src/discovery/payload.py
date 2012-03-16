from dispersy.payload import Payload

class HotsPayload(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, hots):
            super(HotsPayload.Implementation, self).__init__(meta)
            self._hots = hots

        @property
        def hots(self):
            return self._hots

class SearchPayload(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, identifier, expression):
            assert isinstance(identifier, int)
            assert isinstance(expression, unicode)
            assert len(expression) < 1024
            super(SearchPayload.Implementation, self).__init__(meta)
            self._identifier = identifier
            self._expression = expression

        @property
        def identifier(self):
            return self._identifier

        @property
        def expression(self):
            return self._expression

class SearchResponsePayload(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, identifier, hots):
            assert isinstance(identifier, int)
            super(SearchResponsePayload.Implementation, self).__init__(meta)
            self._hots = hots

        @property
        def identifier(self):
            return self._identifier

        @property
        def hots(self):
            return self._hots
