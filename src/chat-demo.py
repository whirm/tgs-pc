#!/usr/bin/python
# -*- conding: utf8 -*-
# tar cvjf chat-demo.tar.bz2 chat-demo --exclude ".svn" --exclude "*pyc" --exclude "*~" --exclude ".backup"

#Disable QString compatibility
import sip
sip.setapi('QString', 2)

import time
import sys

from discovery.community import DiscoveryCommunity
from square.community import PreviewCommunity, SquareCommunity
import events

from dispersy.endpoint import StandaloneEndpoint
from dispersy.callback import Callback
from dispersy.dispersy import Dispersy
from dispersy.member import Member
from dispersy.dprint import dprint
from dispersy.crypto import (ec_generate_key,
        ec_to_public_bin, ec_to_private_bin)

try:
    from ui.main import Ui_TheGlobalSquare
except (ImportError):
    print "\n>>> Run build_resources.sh (you need pyqt4-dev-tools) <<<\n"
    sys.exit()

#from PySide import QtGui, QtCore
from PyQt4 import QtGui, QtCore

#Python
from threading import Lock

#Local
from widgets import ChatMessageListItem, MainWin, SquareOverviewListItem, SquareEditDialog, SquareSearchDialog

#Set up QT as event broker
events.setEventBrokerFactory(events.qt.createEventBroker)
global_events = events.qt.createEventBroker(None)

#Die with ^C
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

#TODO: Implement the hot communities list:
#214648     +eviy  whirm: ok.  when you are at that point, look in the discovery community.  thats what gossips the 'hot' messages around
#214701    +whirm  ok, noted
#214728     +eviy  whirm: a signal at the end of _collect_top_hots will tell you when the most recent hots have been chosen

class ChatCore:
    def __init__(self):
        self.nick = u"Anon"
        self.message_references = []
        self._communities = {}
        self._communities_listwidgets = {}
        self._square_search_dialog = None

    def dispersy(self, callback):
        # start Dispersy
        dispersy = Dispersy.get_instance(callback, u".")
        dispersy.endpoint = StandaloneEndpoint(dispersy, 12345)
        dispersy.endpoint.start()

        # load/join discovery community
        public_key = "3081a7301006072a8648ce3d020106052b81040027038192000406b34f060c416e452fd31fb1770c2f475e928effce751f2f82565bec35c46a97fb8b375cca4ac5dc7d93df1ba594db335350297f003a423e207b53709e6163b7688c0f60a9cf6599037829098d5fbbfe786e0cb95194292f241ff6ae4d27c6414f94de7ed1aa62f0eb6ef70d2f5af97c9aade8266eb85b14296ed2004646838c056d1d9ad8a509b69f81fbc726201b57".decode("HEX")
        if False:
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

        def response_func(message):
            if message:
                if message.name == "search-member-response":
                    dprint("received ", len(message.payload.members), " members")
                if message.name == "search-square-response":
                    dprint("received ", len(message.payload.squares), " squares")
                if message.name == "search-text-response":
                    dprint("received ", len(message.payload.texts), " texts")
            else:
                dprint("received timeout, will occur for each search unless 999 responses are received")

        for index in xrange(999999):
            # user clicked the 'search' button
            self._discovery.simple_member_search(u"member test %d" % index, response_func)
            self._discovery.simple_square_search(u"square test %d" % index, response_func)
            self._discovery.simple_text_search(u"text test %d" % index, response_func)
            yield 1.0

    def onTextMessageReceived(self, message):
        #Put the message in the overview list
        ChatMessageListItem(parent=self.mainwin.message_list, message=message)

        while self.mainwin.message_list.count() > 250:
            print "Deleting A chat message"
            self.mainwin.message_list.takeItem(0)

        #Put the message in the square specific list
        square_list_widget = self._communities_listwidgets[message.square.cid]
        ChatMessageListItem(parent=square_list_widget, message=message)

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
            current_item = self.mainwin.squares_list.selectedItems()[0]
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
        # self.callback.register(square.set_my_member_info, (self.nick,''))

        list_item = SquareOverviewListItem(parent=self.mainwin.squares_list, square=square)
        item_index = self.mainwin.squares_list.row(list_item)
        #Create this square's messages list
        list_widget = QtGui.QListWidget()

        #Setup widget properties
        list_widget.setFrameShape(QtGui.QFrame.NoFrame)
        list_widget.setFrameShadow(QtGui.QFrame.Plain)
        list_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        list_widget.setAutoScroll(True)
        list_widget.setAutoScrollMargin(2)
        list_widget.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        list_widget.setProperty("showDropIndicator", False)
        list_widget.setDragDropMode(QtGui.QAbstractItemView.NoDragDrop)
        list_widget.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        list_widget.setVerticalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        list_widget.setHorizontalScrollMode(QtGui.QAbstractItemView.ScrollPerPixel)
        list_widget.setMovement(QtGui.QListView.Snap)
        list_widget.setProperty("isWrapping", False)
        list_widget.setSpacing(2)
        list_widget.setWordWrap(True)

        #Scroll to bottom at each new message insertion
        message_model = list_widget.model()
        message_model.rowsInserted.connect(list_widget.scrollToBottom)

        self.mainwin.messages_stack.insertWidget(item_index, list_widget)
        self.mainwin.messages_stack.setCurrentIndex(item_index)

        list_item.setSelected(True)

        self._communities_listwidgets[square.cid]=list_widget

        self._communities[square.cid]=square

        #TODO: Put this on the widget constructor, and remove it from here and onNewPreviewCommunityCreated
        square.events.connect(square.events, QtCore.SIGNAL('squareInfoUpdated'), list_item.onInfoUpdated)
        square.events.connect(square.events, QtCore.SIGNAL('messageReceived'), self.onTextMessageReceived)

    def onNewPreviewCommunityCreated(self, square):
        print "New suggested square created", square
        if self._square_search_dialog:
            list_item = SquareOverviewListItem(parent=self._square_search_dialog.results_list, square=square)

            #TODO: Put this on the widget constructor and remove it from here and onNewCommunityCreated
            square.events.connect(square.events, QtCore.SIGNAL('squareInfoUpdated'), list_item.onInfoUpdated)
            square.events.connect(square.events, QtCore.SIGNAL('messageReceived'), self.onTextMessageReceived)
        else:
            print "But the search window doesn't exist, dropping it..."

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

    def onSearchSquareClicked(self):
        self.mainwin.search_square_btn.setEnabled(False)
        self._square_search_dialog = SquareSearchDialog()
        self._square_search_dialog.rejected.connect(self.onSquareSearchDialogClosed)
        self._square_search_dialog.onSearchRequested.connect(self.startNewSearch)
        self._square_search_dialog.show()

    def onSquareSearchDialogClosed(self):
        self.mainwin.search_square_btn.setEnabled(True)

    def startNewSearch(self, search_terms):
        print "Searching for:", search_terms
        self.callback.register(self._discovery.keyword_search, (search_terms, self._dispersy_onSearchResult))

    def _dispersy_onSearchResult(self, result):
        print "OnSearchResult", result

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
        self.mainwin.message_send_btn.clicked.connect(
                                                self.onMessageReadyToSend)
        self.mainwin.join_square_btn.clicked.connect(self.onJoinPreviewCommunity)
        self.mainwin.leave_square_btn.clicked.connect(self.onLeaveCommunity)
        self.mainwin.createSquare_btn.clicked.connect(self.onCreateSquareBtnPushed)

        self.mainwin.search_square_btn.clicked.connect(self.onSearchSquareClicked)

        #Connect global events
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
