class Hot(object):
    def __init__(self, cid, mid, global_time):
        self._cid = cid
        self._mid = mid
        self._global_time = global_time

    @property
    def key(self):
        return (self._cid, self._mid, self._global_time)

    @property
    def cid(self):
        return self._cid

    @property
    def mid(self):
        return self._mid

    @property
    def global_time(self):
        return self._global_time

class HotCache(Hot):
    def __init__(self, hot):
        assert isinstance(hot, Hot)
        super(HotCache, self).__init__(hot.cid, hot.mid, hot.global_time)
        self._sources = []
        self._last_requested = 0.0
        self._square = None
        self._message = None

    @property
    def sources(self):
        return self._sources

    @property
    def square(self):
        return self._square

    @square.setter
    def square(self, square):
        self._square = square

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, message):
        self._message = message

    @property
    def last_requested(self):
        return self._last_requested

    @last_requested.setter
    def last_requested(self, last_requested):
        self._last_requested = last_requested

    def add_source(self, candidate):
        try:
            self._sources.remove(candidate)
        except ValueError:
            pass
        else:
            if len(self._sources) > 10:
                self._sources.pop()
        self._sources.insert(0, candidate)
