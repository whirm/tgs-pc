#
# -*- coding: utf-8 -*-

from PyQt4.QtCore import QObject, SIGNAL, pyqtSignal

from tgscore.square.community import SquareCommunity, PreviewCommunity

_global_broker = None

def createEventBroker(obj):
    if obj == None:
        global _global_broker
        if not _global_broker:
            _global_broker = QtGlobalEventBroker()
        return _global_broker
    else:
        return QtEventBroker(obj)

class QtEventBroker(QObject):
    def __init__(self, obj):
        super(QtEventBroker, self).__init__()
        self._obj = obj

    class QtEmitter:
        def __init__(self, broker, event):
            self._broker=broker
            self._event_name=event

        def __call__(self, *argv):
            #print "EventQT: %s fired with %s" % (self._event_name, argv)
            if argv:
                self._broker.emit(SIGNAL(self._event_name), *argv)
            else:
                self._broker.emit(SIGNAL(self._event_name))

    def __getattr__(self, attr):
        #TODO: Cache instances so we don't create objects for the same signals more than once.
        return self.QtEmitter(self, attr)

class QtGlobalEventBroker:
    def __init__(self):
        self.qt = QtGlobalEventBrokerWrapped()

    #TODO: use __gettattr__ for this.
    def newCommunityCreated(self, square):
        self.qt.newCommunityCreated.emit(square)
    def newPreviewCommunityCreated(self, square):
        self.qt.newPreviewCommunityCreated.emit(square)

class QtGlobalEventBrokerWrapped(QObject):
    newCommunityCreated = pyqtSignal(SquareCommunity)
    newPreviewCommunityCreated = pyqtSignal(PreviewCommunity)
