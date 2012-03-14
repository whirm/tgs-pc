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
        def __init__(self, meta, expression):
            assert isinstance(expression, unicode)
            assert len(expression) < 1024
            super(SearchPayload.Implementation, self).__init__(meta)
            self._expression = expression

        @property
        def expression(self):
            return self._expression

class SearchResponsePayload(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, hots):
            super(HotsPayload.Implementation, self).__init__(meta)
            self._hots = hots

        @property
        def hots(self):
            return self._hots
