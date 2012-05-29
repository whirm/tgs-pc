#!/usr/bin/python
# -*- coding: utf-8 -*-
# tar cvjf chat-demo.tar.bz2 chat-demo --exclude ".svn" --exclude "*pyc" --exclude "*~" --exclude ".backup"

#Disable QString compatibility
import sip
sip.setapi('QString', 2)

import time
import sys
import os

from tgscore.discovery.community import DiscoveryCommunity, SearchCache
from tgscore.square.community import PreviewCommunity, SquareCommunity
from tgscore import events

from tgscore.dispersy.endpoint import StandaloneEndpoint
from tgscore.dispersy.callback import Callback
from tgscore.dispersy.dispersy import Dispersy
from tgscore.dispersy.member import Member
from tgscore.dispersy.dprint import dprint
from tgscore.dispersy.crypto import (ec_generate_key,
        ec_to_public_bin, ec_to_private_bin)


from configobj import ConfigObj

#from PySide import QtGui, QtCore
from PyQt4 import QtGui, QtCore

#Local
from widgets import (ChatMessageListItem, MainWin, SquareOverviewListItem,
        SquareEditDialog, SquareSearchDialog, MessageSearchDialog, MemberSearchDialog)

#Set up QT as event broker
events.setEventBrokerFactory(events.qt.createEventBroker)
global_events = events.qt.createEventBroker(None)

#Die with ^C
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

CONFIG_FILE_NAME='tgs.conf'

#TODO: Implement the hot communities list:
#214648     +eviy  whirm: ok.  when you are at that point, look in the discovery community.  thats what gossips the 'hot' messages around
#214701    +whirm  ok, noted
#214728     +eviy  whirm: a signal at the end of _collect_top_hots will tell you when the most recent hots have been chosen

#TODO: Separate the TGS stuff (dispersy threads setup et al, internal callbacks...) from the pure UI code and put it in this class:
class TGS(QtCore.QObject):
    ##################################
    #Signals:
    ##################################
    memberSearchUpdate = QtCore.pyqtSignal(SearchCache, 'QString')
    squareSearchUpdate = QtCore.pyqtSignal(SearchCache, 'QString')
    textSearchUpdate = QtCore.pyqtSignal(SearchCache, 'QString')

    def __init__(self):
        super(TGS, self).__init__()
        self.callback = None
        self._discovery = None
        self._my_member = None

    ##################################
    #Slots:
    ##################################
    #TODO: Add an arg to add the result list widget/model to support multiple search windows.
    def startNewMemberSearch(self, search_terms):
        print "Searching members for:", search_terms
        self._discovery.simple_member_search(search_terms, self.memberSearchUpdate.emit)

    def startNewSquareSearch(self, search_terms):
        print "Searching squares for:", search_terms
        self._discovery.simple_square_search(search_terms, self.squareSearchUpdate.emit)

    def startNewTextSearch(self, search_terms):
        print "Searching text messages for:", search_terms
        self._discovery.simple_text_search(search_terms, self.textSearchUpdate.emit)

    def joinSquare(self, square):
        self.callback.register(square.join_square)

    def leaveSquare(self, square):
        self.callback.register(square.leave_square)

    ##################################
    #Public methods:
    ##################################
    def setupThreads(self):
        # start threads
        callback = Callback()
        callback.start(name="Dispersy")

        callback.register(self._dispersy, (callback,))
        if "--simulate" in sys.argv:
            callback.register(self._DEBUG_SIMULATION)
        if "--simulate-qt" in sys.argv:
            callback.register(self._DEBUG_QT_SIMULATION)
        self.callback = callback

    def stopThreads(self):
        self.callback.stop()

        if self.callback.exception:
            global exit_exception
            exit_exception = self.callback.exception

    def createNewSquare(self, square_info):
        self.callback.register(self._dispersyCreateCommunity, square_info)

    def sendText(self, community, message, media_hash=''):
        self.callback.register(community.post_text, (message, media_hash))

    def setMemberInfo(self, community, alias, thumbnail_hash=''):
        self.callback.register(community.set_my_member_info, (alias,thumbnail_hash))

    ##################################
    #Private methods:
    ##################################
    def _dispersy(self, callback):
        if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
            workdir = unicode(sys.argv[1])
        else:
            workdir = u"."

        # start Dispersy
        dispersy = Dispersy.get_instance(callback, workdir)
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

        dispersy.define_auto_load(PreviewCommunity, (self._discovery, False))
        dispersy.define_auto_load(SquareCommunity, (self._discovery,))

        # load squares
        for master in SquareCommunity.get_master_members():
            yield 0.1
            dispersy.get_community(master.mid)


    def _dispersy_onSearchResult(self, result):
        print "OnSearchResult", result

    def _dispersyCreateCommunity(self, title, description, avatar, lat, lon, radius):
        community = SquareCommunity.create_community(self._my_member, self._discovery)

        #TODO: Publish the avatar via swift and set the avatar's hash here
        community.set_square_info(title, description, '', (int(lat*10**6), int(lon*10**6)), radius)

    def _DEBUG_SIMULATION(self):
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

        def response_func(cache, event, request_timestamp):
            if cache:
                dprint(round(time.time() - request_timestamp, 2), "s ", event, "! received ", len(cache.suggestions), " suggestions; retrieved ", sum(1 if suggestion.hit else 0 for suggestion in cache.suggestions), " hits", force=1)

        yield 3.0

        for index in xrange(999999):
            # user clicked the 'search' button
            dprint("NEW SEARCH", line=1, force=1)
            now = time.time()
            self._discovery.simple_member_search(u"member test %d" % index, response_func, (now,))
            self._discovery.simple_square_search(u"square test %d" % index, response_func, (now,))
            self._discovery.simple_text_search(u"text test %d" % index, response_func, (now,))
            yield 30.0

    def _DEBUG_QT_SIMULATION(self):
        yield 5.0

        for index in xrange(999999):
            # user clicked the 'search' button
            dprint("NEW QT SEARCH", line=1, force=1)
            self.onSearchSquareClicked()
            yield 1
            self._tgs.startNewSearch("member test $d" % index)
            #now = time.time()
            #self._discovery.simple_member_search(u"member test %d" % index, self._tgs.memberSearchUpdate.emit, (now,))
            #self._discovery.simple_square_search(u"square test %d" % index, response_func, (now,))
            #self._discovery.simple_text_search(u"text test %d" % index, response_func, (now,))
            yield 30.0


class ChatCore:
    def __init__(self):
        self.message_references = []
        self._communities = {}
        self._communities_listwidgets = {}
        self._square_search_dialog = None
        self._message_attachment = None

        self._tgs = TGS()

        self._tgs.memberSearchUpdate.connect(self.onMemberSearchUpdate)
        self._tgs.squareSearchUpdate.connect(self.onSquareSearchUpdate)
        self._tgs.textSearchUpdate.connect(self.onTextSearchUpdate)


    #Slots:
    ##################################

    #TODO: Refactor the 3 search functions to 3 small ones an a generic one as they are basically the same.
    def onMemberSearchUpdate(self, cache, event):
        #TODO:
        print "Received member search update"
        #TODO: Deal with status changes and notify user when search is done.
        if self._member_search_dialog:
            self._member_search_dialog.clearResultsList()
            for suggestion in cache.suggestions:
                member = suggestion.hit
                if suggestion.state == 'done':
                    self._member_search_dialog.addResult(member.alias, member.thumbnail_hash)
            if event == "finished":
                self._member_search_dialog.onSearchFinished()
        else:
            print "But the search window doesn't exist, dropping it..."

    def onSquareSearchUpdate(self, cache, event):
        #TODO:
        print "Received Square search update"
        #TODO: Deal with status changes and notify user when search is done.
        if self._square_search_dialog:
            self._square_search_dialog.clearResultsList()
            for suggestion in cache.suggestions:
                square = suggestion.hit
                if suggestion.state == 'done':
                    self._square_search_dialog.addResult(square)
            if event == "finished":
                self._square_search_dialog.onSearchFinished()
        else:
            print "But the search window doesn't exist, dropping it..."

    def onTextSearchUpdate(self, cache, event):
        #TODO:
        print "Received text search update"
        #TODO: Deal with status changes and notify user when search is done.
        if self._message_search_dialog:
            self._message_search_dialog.clearResultsList()
            for suggestion in cache.suggestions:
                text = suggestion.hit
                if suggestion.state == 'done':
                    self._message_search_dialog.addResult(text.text, text.member, text.square)
            if event == "finished":
                self._message_search_dialog.onSearchFinished()
        else:
            print "But the search window doesn't exist, dropping it..."

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
        alias = self.mainwin.nick_line.text()
        print "Alias changed to:", alias
        if alias and alias != self._config['Member']['Alias']:
            self._config['Member']['Alias'] = alias
            self._propagateMemberInfoToAll()
            self._config.write()
        else:
            print "Same or empty nick, doing nothing"

    def onMessageReadyToSend(self):
        message = self.mainwin.message_line.text()
        #TODO: Check if the community where we are sending the message has our member info up to date!!
        if message:
            print "Sending message: ", message
            #Get currently selected community
            current_item = self.mainwin.squares_list.selectedItems()[0]
            if type(current_item) is SquareOverviewListItem:
                square = current_item.square
                #TODO: Add media_hash support, empty string ATM.
                media_hash = ''
                self._tgs.sendText(square, message, media_hash)
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

        self._communities[square.cid] = square

        #Set member info for this square
        self._setMemberInfo(square)

        #TODO: Put this on the widget constructor, and remove it from here and onNewPreviewCommunityCreated
        square.events.connect(square.events, QtCore.SIGNAL('squareInfoUpdated'), list_item.onInfoUpdated)
        square.events.connect(square.events, QtCore.SIGNAL('messageReceived'), self.onTextMessageReceived)

    def onJoinPreviewCommunity(self, community):
        #TODO: disable the leave/join buttons if no square is selected
        print "Joining a new community!"
        self._tgs.joinSquare(community)

    def onLeaveCommunity(self):
        print "leaving community!"
        #Get currently selected community
        current_item = self.mainwin.squares_list.currentItem()
        if type(current_item) is SquareOverviewListItem:
            square = current_item.square
            self._tgs.leaveSquare(square)
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

        self._tgs.createNewSquare(square_info)

        self._square_edit_dialog = None
        self.mainwin.createSquare_btn.setEnabled(True)

    def onSearchSquareClicked(self):
        self.mainwin.search_square_btn.setEnabled(False)
        self._square_search_dialog = SquareSearchDialog()
        self._square_search_dialog.rejected.connect(self.onSquareSearchDialogClosed)
        self._square_search_dialog.onSearchRequested.connect(self._tgs.startNewSquareSearch)
        self._square_search_dialog.onJoinSquareRequested.connect(self._tgs.joinSquare)
        self._square_search_dialog.show()

    def onSquareSearchDialogClosed(self):
        self.mainwin.search_square_btn.setEnabled(True)

    def onSearchMessageClicked(self):
        self.mainwin.search_message_btn.setEnabled(False)
        self._message_search_dialog = MessageSearchDialog()
        self._message_search_dialog.rejected.connect(self.onMessageSearchDialogClosed)
        self._message_search_dialog.onSearchRequested.connect(self._tgs.startNewTextSearch)
        self._message_search_dialog.show()

    def onMessageSearchDialogClosed(self):
        self.mainwin.search_message_btn.setEnabled(True)

    def onSearchMemberClicked(self):
        self.mainwin.search_member_btn.setEnabled(False)
        self._member_search_dialog = MemberSearchDialog()
        self._member_search_dialog.rejected.connect(self.onMemberSearchDialogClosed)
        self._member_search_dialog.onSearchRequested.connect(self._tgs.startNewMemberSearch)
        self._member_search_dialog.show()

    def onMemberSearchDialogClosed(self):
        self.mainwin.search_member_btn.setEnabled(True)

    def onThumbnailButtonPressed(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self.mainwin,
                    "Select your avatar", "", "Image Files (*.png *.jpg *.bmp *.gif)"
        )
        image = QtGui.QPixmap(fileName)
        if image.width() > image.height():
            image = image.scaledToWidth(64)
        else:
            image = image.scaledToHeight(64)

        self.mainwin.avatar_btn.setIcon(QtGui.QIcon(image))
        thumb_data = QtCore.QBuffer()
        thumb_data.open(thumb_data.ReadWrite)
        image.save(thumb_data, 'PNG')

        self._config['Member']['Thumbnail'] = thumb_data.buffer().toBase64()
        self._config.write()

    def onAttachButtonToggled(self, status):
        if status:
            self._message_attachment = QtGui.QFileDialog.getOpenFileName(self.mainwin,
                                                    "Attach file to message", "", "")
            self.mainwin.attach_btn.setToolTip(self._message_attachment)
        else:
            self._message_attachment = None
            self.mainwin.attach_btn.setToolTip('')

    ##################################
    #Public Methods
    ##################################
    def run(self):
        #Read config file
        self._config = self._getConfig()

        #Setup QT main window
        self.app = QtGui.QApplication(sys.argv)
        self.mainwin = MainWin()

        #Set configurable values
        self.mainwin.nick_line.setText(self._config['Member']['Alias'])
        thumb_data = QtCore.QBuffer()
        thumb_data.open(thumb_data.ReadWrite)
        thumb_bytes = QtCore.QByteArray.fromBase64(self._config['Member']['Thumbnail'])
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(thumb_bytes, 'PNG')
        self.mainwin.avatar_btn.setIcon(QtGui.QIcon(pixmap))

        #Connect main window signals
        self.mainwin.nick_line.editingFinished.connect(self.onNickChanged)
        self.mainwin.avatar_btn.clicked.connect(self.onThumbnailButtonPressed)
        self.mainwin.message_line.returnPressed.connect(
                                                self.onMessageReadyToSend)
        self.mainwin.message_send_btn.clicked.connect(
                                                self.onMessageReadyToSend)
        self.mainwin.attach_btn.toggled.connect(self.onAttachButtonToggled)
        self.mainwin.join_square_btn.clicked.connect(self.onJoinPreviewCommunity)
        self.mainwin.leave_square_btn.clicked.connect(self.onLeaveCommunity)
        self.mainwin.createSquare_btn.clicked.connect(self.onCreateSquareBtnPushed)

        self.mainwin.search_square_btn.clicked.connect(self.onSearchSquareClicked)
        self.mainwin.search_message_btn.clicked.connect(self.onSearchMessageClicked)
        self.mainwin.search_member_btn.clicked.connect(self.onSearchMemberClicked)

        #Hide the tools panel
        self.mainwin.tools_grp.hide()

        #TODO: Refactor this to put it in TGS class
        #Connect global events
        global_events.qt.newCommunityCreated.connect(self.onNewCommunityCreated)
        #global_events.qt.newPreviewCommunityCreated.connect(
        #                                        self.onNewPreviewCommunityCreated)

        #Setup dispersy threads
        self._tgs.setupThreads()

        #Show the main window
        self.mainwin.show()
        #Start QT's event loop
        self.app.exec_()

        #Destroy dispersy threads before exiting
        self._tgs.stopThreads()

    ##################################
    #Private Methods
    ##################################
    def _getConfig(self):
        current_os = sys.platform
        if current_os in ('win32','cygwin'):
            config_path = os.path.join(os.environ['AppData'], 'TheGlobalSquare')
        elif current_os.startswith('linux'):
            config_path = os.path.join(os.environ['HOME'], '.config', 'TheGlobalSquare')
        elif current_os == 'darwin':
            config_path = os.path.join('Users', os.environ['USER'], 'Library', 'Preferences', 'TheGlobalSquare')
        else:
            print "I don't know where to store my config in this operating system! (%s)\nExiting..." % current_os
            sys.exit(10)

        #Create app data dir if it doesn't exist
        if not os.path.exists(config_path):
            os.makedirs(config_path)

        config_file_path = os.path.join(config_path, CONFIG_FILE_NAME)

        config = ConfigObj(config_file_path, encoding='utf-8')

        if not os.path.exists(config_file_path):
            #Set default values
            config['Member'] = {
                'Alias': 'Anon',
                'Thumbnail': ''
                }
            config.write()

        return config

    def _propagateMemberInfoToAll(self):
        #TODO: Check if the community has up to date info before sending unnecessary updates
        for community in self._communities.itervalues():
            self._setMemberInfo(community)

    def _setMemberInfo(self, community):
        alias = self._config['Member']['Alias']
        thumbnail = '' #str(self._config['Member']['Thumbnail']) #TODO: Setup this correctly when swift gets integrated
        self._tgs.setMemberInfo(community, alias, thumbnail)


if __name__ == "__main__":
    exit_exception = None
    chat = ChatCore()
    chat.run()
    if exit_exception:
        raise exit_exception
