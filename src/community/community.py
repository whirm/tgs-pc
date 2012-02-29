
from conversion import Conversion
from payload import TextPayload

from dispersy.callback import Callback
from dispersy.authentication import MemberAuthentication
from dispersy.community import Community
from dispersy.conversion import DefaultConversion
from dispersy.destination import CommunityDestination
from dispersy.distribution import FullSyncDistribution
from dispersy.message import BatchConfiguration, Message, DelayMessageByProof
from dispersy.resolution import PublicResolution

#Looks like pyside is crashing more than what's confortable, let's try with ol' pyqt
#from PySide.QtCore import Signal, QObject
from PyQt4.QtCore import pyqtSignal, QObject
Signal = pyqtSignal

#Python:
from time import time

if __debug__:
    from dispersy.dprint import dprint

class ChatCommunity(Community,QObject):
    textMessageReceived = Signal(str)
    def __init__(self, *args):
        super(ChatCommunity, self).__init__(*args)
        QObject.__init__(self)


        #self._ui_callback = Callback()
        #self._ui_callback.start("GUI")
        #self._ui_callback.register(self._gui_thread)

        self.nick="Anon"

    def initiate_meta_messages(self):
        return [Message(self, u"text", MemberAuthentication(encoding="sha1"), PublicResolution(), FullSyncDistribution(enable_sequence_number=False, synchronization_direction=u"ASC", priority=128), CommunityDestination(node_count=10), TextPayload(), self.check_text, self.on_text, batch=BatchConfiguration(max_window=1.0))]

    def initiate_conversions(self):
        return [DefaultConversion(self), Conversion(self)]

    def _gui_thread(self):
        callback = self._dispersy.callback
        while True:
            #TODO: Get the message from the user
            text = "Hello World! Its party time! %s" % time()
            if not text:
                break
            callback.register(self.create_text, (self.nick + u" says " + text,))
            yield 5.0

        dprint("Shutting down", force=1)
        callback.stop(wait=False)
        self._ui_callback.stop(wait=False)

    def setNick(self, nick):
        self.sendMessage(u' changed nick to: ' + nick)
        self.nick = nick

    def sendMessage(self, message):
        self._dispersy.callback.register(self.create_text, (u'%s: %s' % (self.nick, message), ))

    def create_text(self, text, store=True, update=True, forward=True):
        assert isinstance(text, unicode)
        meta = self._meta_messages[u"text"]
        message = meta.impl(authentication=(self._my_member,), distribution=(self.claim_global_time(),), payload=(text,))
        self._dispersy.store_update_forward([message], store, update, forward)
        if __debug__: dprint(message, force=1)

    def check_text(self, messages):
        for message in messages:
            allowed, _ = self._timeline.check(message)
            if allowed:
                yield message
            else:
                yield DelayMessageByProof(message)

    def on_text(self, messages):
        for message in messages:
            if __debug__: dprint(message.payload.text, force=1)
            print "Message:", message.payload.text
            self.textMessageReceived.emit(message.payload.text)
