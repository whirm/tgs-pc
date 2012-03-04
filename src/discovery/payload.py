from dispersy.payload import Payload

class HotsPayload(Payload):
    class Implementation(Payload.Implementation):
        def __init__(self, meta, hots):
            super(HotsPayload.Implementation, self).__init__(meta)
            self._hots = hots

        @property
        def hots(self):
            return self._hots
