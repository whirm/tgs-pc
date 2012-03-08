#!/usr/bin/python
# -*- conding: utf8 -*-
# tar cvjf chat-demo.tar.bz2 chat-demo --exclude ".svn" --exclude "*pyc" --exclude "*~" --exclude ".backup"

#Disable QString compatibility
import sip
sip.setapi('QString', 2)

import communication
import time
import sys

from discovery.community import DiscoveryCommunity
from square.community import PreviewCommunity, SquareCommunity
import events

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
from widgets import ChatMessageListItem, MainWin, SquareOverviewListItem

#Set up QT as event broker
events.setEventBrokerFactory(events.qt.createEventBroker)
global_events = events.qt.createEventBroker(None)

#Die with ^C
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


class ChatCore:
    def __init__(self):
        self.nick = "Anon"
        self.message_references = []
        self._communities = {}

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

        # load squares
        for master in SquareCommunity.get_master_members():
            yield 1.0
            community = dispersy.get_community(master.mid)

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

    def onTextMessageReceived(self, message):
        ChatMessageListItem(parent=self.mainwin.message_list, nick=message.payload.member_info.payload.alias, body=message.payload.text)
        #TODO: Obtain member_info data.
        #TODO: Obtain media associated with message.media_hash and put it in the message.
        #TODO: Obtain media associated with message.member_info.thumbnail_hash and update the avatar.

        while self.mainwin.message_list.count() > 250:
            print "Deleting A chat message"
            self.mainwin.message_list.takeItem(0)

    def onNickChanged(self, *argv, **kwargs):
        nick = self.mainwin.nick_line.text()
        print "Nick changed to:", nick
        if nick and nick != self.nick:
            for community in self._communities.itervalues():
                #TODO: Set thumbnail info (setting an empty string ATM)
                self.callback.register(community.set_my_member_info, (nick,''))
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

    def onNewCommunityCreated(self, square):
        #TODO: We need to update the squares list here.
        print "New square created", square
        #TODO: We will switch to an MVC widget soon, so we can sort, filter, update, etc easily.
        list_item=SquareOverviewListItem(parent=self.mainwin.squares_list, square=square)
        self._communities[square.cid]=square
        square.events.connect(square.events, QtCore.SIGNAL('squareInfoUpdated'), list_item.onInfoUpdated)
        square.events.connect(square.events, QtCore.SIGNAL('messageReceived'), self.onTextMessageReceived)

    def onNewPreviewCommunityCreated(self, square):
        #TODO: We need to update the squares list here.
        print "New suggested square created", square
        SquareOverviewListItem(parent=self.mainwin.suggested_squares_list, square=square)

    def _setupThreads(self):

        # start threads
        callback = Callback()
        callback.start(name="Dispersy")

        callback.register(self.dispersy, (callback,))
        callback.register(self.DEBUG_SIMULATION)
        self.callback = callback

        #pyside:
        #community.textMessageReceived.connect(self.onTextMessageReceived, QtCore.Qt.ConnectionType.DirectConnection)

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
        global_events.qt.newCommunityCreated.connect(self.onNewCommunityCreated)
        global_events.qt.newPreviewCommunityCreated.connect(self.onNewPreviewCommunityCreated)

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
