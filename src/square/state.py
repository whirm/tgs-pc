if __debug__:
    from dispersy import dprint

class State(object):
    def __init__(self, previous_state):
        if __debug__: dprint("state ", previous_state, " -> ", self)

class DummyState(State):
    def __init__(self):
        pass

class UnknownState(State):
    pass

class SquareState(State):
    pass

class TaskGroupState(State):
    pass
