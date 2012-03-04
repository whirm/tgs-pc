#!/usr/bin/python
# -*- conding: utf8 -*-
# tar cvjf chat-demo.tar.bz2 chat-demo --exclude ".svn" --exclude "*pyc" --exclude "*~" --exclude ".backup"

import communication
import time
import sys

from discovery.community import DiscoveryCommunity
from square.community import PreviewCommunity, SquareCommunity

from dispersy.callback import Callback
from dispersy.dispersy import Dispersy
from dispersy.member import Member
from dispersy.dprint import dprint
from dispersy.crypto import (ec_generate_key,
        ec_to_public_bin, ec_to_private_bin)

try:
    from ui.main import Ui_TheGlobalSquare
    from ui.square import Ui_SquareDialog
except (ImportError):
    print "\n>>> Run build_resources.sh (you need pyqt4-dev-tools) <<<\n"
    sys.exit()

#from PySide import QtGui, QtCore
from PyQt4 import QtGui, QtCore

#Python
from threading import Lock

#Local
from widgets import ChatMessageListItem, MainWin

class ChatCore:
    def __init__(self):
        self.nick = "Anon"
        self.message_references=[]

        self.setup_lock=Lock()

    def dispersy(self, callback):
        # start Dispersy
        dispersy = Dispersy.get_instance(callback, u".")
        dispersy.socket = communication.get_socket(callback, dispersy)

        # load/join discovery community
        public_key = "3081a7301006072a8648ce3d020106052b81040027038192000406b34f060c416e452fd31fb1770c2f475e928effce751f2f82565bec35c46a97fb8b375cca4ac5dc7d93df1ba594db335350297f003a423e207b53709e6163b7688c0f60a9cf6599037829098d5fbbfe786e0cb95194292f241ff6ae4d27c6414f94de7ed1aa62f0eb6ef70d2f5af97c9aade8266eb85b14296ed2004646838c056d1d9ad8a509b69f81fbc726201b57".decode("HEX")
        if True:
            # when crypto.py is disabled a public key is slightly
            # different...
            public_key = ";".join(("60", public_key[:60].encode("HEX"), ""))
        master = Member(public_key)
        try:
            self._discovery = DiscoveryCommunity.load_community(master)
        except ValueError:
            ec = ec_generate_key(u"low")
            self._my_member = Member(ec_to_public_bin(ec), ec_to_private_bin(ec))
            self._discovery = DiscoveryCommunity.join_community(master, self._my_member)
        else:
            self._my_member = self._discovery.my_member

        dispersy.define_auto_load(PreviewCommunity, (self._discovery,))
        dispersy.define_auto_load(SquareCommunity, (self._discovery,))

        self.community = community
        self.setup_lock.release()

        # load squares
        for master in SquareCommunity.get_master_members():
            yield 1.0
            dispersy.get_community(master.mid)

    def DEBUG_SIMULATION(self):
        yield 5.0

        # user clicked the 'create new square' button
        community = SquareCommunity.create_community(self._my_member, self._discovery)
        yield 1.0

        # user clicked the 'update my member info' button
        community.set_my_member_info(u"SIM nickname", "")
        yield 1.0

        # user clicked the 'update square info' button
        community.set_square_info(u"SIM title", u"SIM description", "", (0, 0), 0)
        yield 1.0

        for index in xrange(5):
            # user clicked the 'post message' button
            community.post_text(u"SIM message %d" % index, "")
            yield 1.0

        for index in xrange(5):
            # user clicked the 'search' button
            self._discovery.keyword_search([u"SIM", u"%d" % index])

    def onTextMessageReceived(self, text):
        #TODO: Temporary hack until we use the new chat message:
        try:
            nick, body = text.split(' writes ', 1)
        except ValueError:
            try:
                nick, body = text.split(': ', 1)
            except ValueError:
                nick = 'NONICK'
                body = text

        ChatMessageListItem(parent=self.mainwin.message_list, nick=nick, body=body)
        while self.mainwin.message_list.count() > 250:
            print "Deleting A chat message"
            self.mainwin.message_list.takeItem(0)

    def onNickChanged(self, *argv, **kwargs):
        nick = self.mainwin.nick_line.text()
        print "Nick changed to:", nick
        if nick and nick != self.nick:
            self.callback.register(self.community.setNick, (nick,))
            self.nick = nick
        else:
            print "Same or empty nick, doing nothing"

    def onMessageReadyToSend(self):
        message = unicode(self.mainwin.message_line.text())
        if message:
            print "Sending message: ", message
            self.callback.register(self.community.sendMessage, (message,))
            self.mainwin.message_line.clear()
        else:
            print "Not sending empty message."

    def _setupThreads(self):
        self.setup_lock.acquire()

        # start threads
        callback = Callback()
        callback.start(name="Dispersy")

        callback.register(self.dispersy, (callback,))
        callback.register(self.DEBUG_SIMULATION)
        self.callback = callback

        #pyside:
        #community.textMessageReceived.connect(self.onTextMessageReceived, QtCore.Qt.ConnectionType.DirectConnection)

        #Wait for the Dispersy thread to instance the Community class so we can connect to its signals
        self.setup_lock.acquire()
        self.community.textMessageReceived.connect(self.onTextMessageReceived)
        self.setup_lock.release()
        #It won't be used again:
        del self.setup_lock

    def _stopThreads(self):
        self.callback.stop()

        if self.callback.exception:
            global exit_exception
            exit_exception = self.callback.exception

    def run(self):

        #while not callback.is_finished:
        #    print "X", app.processEvents()
        #    time.sleep(0.01)

        #Setup QT main window
        self.app = QtGui.QApplication(sys.argv)
        self.mainwin = MainWin()
        self.mainwin.show()
        #ui.nick_line.returnPressed.connect(on_nick_changed)
        self.mainwin.nick_line.editingFinished.connect(self.onNickChanged)
        self.mainwin.message_line.returnPressed.connect(
                                                self.onMessageReadyToSend)

        #Setup dispersy threads
        self._setupThreads()

        #Start QT's event loop
        self.app.exec_()

        #Destroy dispersy threads
        self._stopThreads()

if __name__ == "__main__":
    exit_exception = None
    chat = ChatCore()
    chat.run()
    if exit_exception:
        raise exit_exception
