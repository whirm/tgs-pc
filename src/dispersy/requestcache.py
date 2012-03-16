from random import random

class Cache(object):
    def __init__(self, identifier):
        self._identifier = identifier

    @property
    def identifier(self):
        return self._identifier

class RequestCache(object):
    def __init__(self, callback):
        self._callback_register = callback.register
        self._identifiers = dict()

    def claim(self, duration, cls, *args, **kargs):
        assert isinstance(duration, float)
        assert issubclass(cls, Cache)
        while True:
            identifier = int(random() * 2**16)
            if not identifier in self._identifiers:
                self._identifiers[identifier] = cache = cls(identifier, *args, **kargs)
                self._callback_register(self._identifiers.pop, (cache,), delay=duration)
                return cache

    def get(self, identifier, default=None):
        return self._identifiers.get(identifier, default)
