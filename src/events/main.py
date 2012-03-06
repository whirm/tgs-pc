
from dummy import getDummyEventBroker

__all__=('setEventBrokerFactory', 'getEventBroker')

EVENT_BROKER_FACTORY=getDummyEventBroker

def setEventBrokerFactory(factory):
    global EVENT_BROKER_FACTORY
    EVENT_BROKER_FACTORY=factory

def getEventBroker(obj):
    return EVENT_BROKER_FACTORY(obj)

