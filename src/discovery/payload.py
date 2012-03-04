from dispersy.payload import Payload

class HotSPayload(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, hots):
            super(HotSPayload.Implementation, self).__init__(meta)
            self._hots = hots

        @property
        def hots(self):
            return self._hots

class MissingHot(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, hot):
            super(MissingHotPayload.Implementation, self).__init__(meta)
            self._hot = hot

        @property
        def hot(self):
            return self._hot
