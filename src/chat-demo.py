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
from widgets import ChatMessageListItem, MainWin, SquareOverviewListItem, SquareEditDialog

#Set up QT as event broker
events.setEventBrokerFactory(events.qt.createEventBroker)
global_events = events.qt.createEventBroker(None)

#Die with ^C
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


class ChatCore:
    def __init__(self):
        self.nick = u"Anon"
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
        #community = SquareCommunity.create_community(self._my_member, self._discovery)
        #yield 1.0

        # user clicked the 'update my member info' button
        #community.set_my_member_info(u"SIM nickname", "")
        #yield 1.0

        # user clicked the 'update square info' button
        #community.set_square_info(u"SIM title", u"SIM description", "", (0, 0), 0)
        #yield 1.0

        #for index in xrange(5):
        #    # user clicked the 'post message' button
        #    community.post_text(u"SIM message %d" % index, "")
        #    yield 1.0

        for index in xrange(5):
            # user clicked the 'search' button
            self._discovery.keyword_search([u"SIM", u"%d" % index])

    def onTextMessageReceived(self, message):
        ChatMessageListItem(parent=self.mainwin.message_list, nick=message.payload.member_info.payload.alias, body=message.payload.text)
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
        message = self.mainwin.message_line.text()
        if message:
            print "Sending message: ", message
            #Get currently selected community
            current_item = self.mainwin.squares_list.currentItem()
            if type(current_item) is SquareOverviewListItem:
                square = current_item.square
                #TODO: Add media_hash support, empty string ATM.
                self.callback.register(square.post_text, (message, ''))
                self.mainwin.message_line.clear()
            else:
                msg_box = QtGui.QMessageBox()
                msg_box.setText("Please, select to which square you want to send the message from the the top-left list first.")
                msg_box.exec_()
        else:
            print "I categorically refuse to send an empty message."

    def onNewCommunityCreated(self, square):
        #TODO: We need to update the squares list here.
        print "New square created", square
        #TODO: We will switch to an MVC widget soon, so we can sort, filter, update, etc easily.

        #Set the member info stuff for this community
        #TODO: Set thumbnail info (setting an empty string ATM)
        self.callback.register(square.set_my_member_info, (self.nick,''))

        list_item = SquareOverviewListItem(parent=self.mainwin.squares_list, square=square)
        self._communities[square.cid]=square

        square.events.connect(square.events, QtCore.SIGNAL('squareInfoUpdated'), list_item.onInfoUpdated)
        square.events.connect(square.events, QtCore.SIGNAL('messageReceived'), self.onTextMessageReceived)

    def onNewPreviewCommunityCreated(self, square):
        #TODO: We need to update the squares list here.
        print "New suggested square created", square
        list_item = SquareOverviewListItem(parent=self.mainwin.suggested_squares_list, square=square)

        #TODO: refactor this to have a common method for new squares
        square.events.connect(square.events, QtCore.SIGNAL('squareInfoUpdated'), list_item.onInfoUpdated)
        square.events.connect(square.events, QtCore.SIGNAL('messageReceived'), self.onTextMessageReceived)
        #TODO: put the hot communities here instead when the search squares dialog is in a working condition:
        #214648     +eviy  whirm: ok.  when you are at that point, look in the discovery community.  thats what gossips the 'hot' messages around
        #214701    +whirm  ok, noted
        #214728     +eviy  whirm: a signal at the end of _collect_top_hots will tell you when the most recent hots have been chosen

    def onJoinPreviewCommunity(self):
        #TODO: disable the leave/join buttons if no square is selected
        print "Joining a new community!"
        #Get currently selected community
        current_item = self.mainwin.suggested_squares_list.currentItem()
        if type(current_item) is SquareOverviewListItem:
            square = current_item.square
            self.callback.register(square.join_square)
            row = self.mainwin.suggested_squares_list.currentRow()
            self.mainwin.suggested_squares_list.takeItem(row)
        else:
            msg_box = QtGui.QMessageBox()
            msg_box.setText("Please, select which square you want to join from the bottom-left list first.")
            msg_box.exec_()

    def onLeaveCommunity(self):
        print "leaving community!"
        #Get currently selected community
        current_item = self.mainwin.squares_list.currentItem()
        if type(current_item) is SquareOverviewListItem:
            square = current_item.square
            self.callback.register(square.leave_square)
            row = self.mainwin.squares_list.currentRow()
            self.mainwin.squares_list.takeItem(row)
            #Remove the square reference from the squares list
            self._communities.pop(current_item.square.cid)
        else:
            msg_box = QtGui.QMessageBox()
            msg_box.setText("Please, select which square you want to leave from the top-left list first.")
            msg_box.exec_()

    def onCreateSquareBtnPushed(self):
        self.mainwin.createSquare_btn.setEnabled(False)
        self._square_edit_dialog = SquareEditDialog()
        self._square_edit_dialog.squareInfoReady.connect(self.onSquareCreateDialogFinished)
        self._square_edit_dialog.show()

    def onSquareCreateDialogFinished(self):

        square_info = self._square_edit_dialog.getSquareInfo()

        self.callback.register(self._dispersyCreateCommunity, square_info)

        self._square_edit_dialog = None
        self.mainwin.createSquare_btn.setEnabled(True)

    def _dispersyCreateCommunity(self, title, description, avatar, lat, lon, radius):
        community = SquareCommunity.create_community(self._my_member, self._discovery)

        #TODO: Publish the avatar via swift and set the avatar's hash here
        community.set_square_info(title, description, '', (int(lat*10**6), int(lon*10**6)), radius)

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

        #Connect main window signals
        self.mainwin.nick_line.editingFinished.connect(self.onNickChanged)
        self.mainwin.message_line.returnPressed.connect(
                                                self.onMessageReadyToSend)
        self.mainwin.join_square_btn.clicked.connect(self.onJoinPreviewCommunity)
        self.mainwin.leave_square_btn.clicked.connect(self.onLeaveCommunity)
        self.mainwin.createSquare_btn.clicked.connect(self.onCreateSquareBtnPushed)

        global_events.qt.newCommunityCreated.connect(self.onNewCommunityCreated)
        global_events.qt.newPreviewCommunityCreated.connect(
                                                self.onNewPreviewCommunityCreated)

        #Setup dispersy threads
        self._setupThreads()

        #Show the main window
        self.mainwin.show()
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
