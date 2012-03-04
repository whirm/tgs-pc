#!/usr/bin/python
# -*- conding: utf8 -*-
# tar cvjf chat-demo.tar.bz2 chat-demo --exclude ".svn" --exclude "*pyc" --exclude "*~" --exclude ".backup"

import communication
import time
import sys

from community.community import ChatCommunity

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

#Local
from widgets import ChatMessageWidget, MainWin

# generated: Sun Feb 26 16:54:45 2012
# curve: high <<< NID_sect571r1 >>>
# len: 571 bits ~ 144 bytes signature
# pub: 170 3081a7301006072a8648ce3d020106052b81040027038192000400686f2843cd96ff5f3ff399af8e4a97af3ca716d4e84855285b9cdf054a11b5ec3e4076f75ab2c36d2d508dd7cbc1180378a39c35998b6fb4c80b384cdcadd643471df7da6d4a41008a33f0a5b29009fffeca8b20b65d1313b6759ee20149c5c8b2838b78b9f25b445dfcc1dec68b423c41f7abd8104a481ff86c5e638b13ed5bd95059b743cbbc25c9b2b06e271e4f
# prv: 241 3081ee0201010448034952e07f3f71d422949cc6c55eb96e3b0072b1ad389e23f6b20709d9d26b869813e8289381a03c3348763a715f914323c89c164aa5f859f15efd3eb52304750f3ed7df43e0bf79a00706052b81040027a18195038192000400686f2843cd96ff5f3ff399af8e4a97af3ca716d4e84855285b9cdf054a11b5ec3e4076f75ab2c36d2d508dd7cbc1180378a39c35998b6fb4c80b384cdcadd643471df7da6d4a41008a33f0a5b29009fffeca8b20b65d1313b6759ee20149c5c8b2838b78b9f25b445dfcc1dec68b423c41f7abd8104a481ff86c5e638b13ed5bd95059b743cbbc25c9b2b06e271e4f
# pub-sha1 fbd87c6fb50b8ffa880d8fecdc26034794ec4e46
# prv-sha1 13796c396c6895b53ad2c205dbba40d73eb99c2f
# -----BEGIN PUBLIC KEY-----
# MIGnMBAGByqGSM49AgEGBSuBBAAnA4GSAAQAaG8oQ82W/18/85mvjkqXrzynFtTo
# SFUoW5zfBUoRtew+QHb3WrLDbS1QjdfLwRgDeKOcNZmLb7TICzhM3K3WQ0cd99pt
# SkEAijPwpbKQCf/+yosgtl0TE7Z1nuIBScXIsoOLeLnyW0Rd/MHexotCPEH3q9gQ
# Skgf+GxeY4sT7VvZUFm3Q8u8JcmysG4nHk8=
# -----END PUBLIC KEY-----
# -----BEGIN EC PRIVATE KEY-----
# MIHuAgEBBEgDSVLgfz9x1CKUnMbFXrluOwBysa04niP2sgcJ2dJrhpgT6CiTgaA8
# M0h2OnFfkUMjyJwWSqX4WfFe/T61IwR1Dz7X30Pgv3mgBwYFK4EEACehgZUDgZIA
# BABobyhDzZb/Xz/zma+OSpevPKcW1OhIVShbnN8FShG17D5AdvdassNtLVCN18vB
# GAN4o5w1mYtvtMgLOEzcrdZDRx332m1KQQCKM/ClspAJ//7KiyC2XRMTtnWe4gFJ
# xciyg4t4ufJbRF38wd7Gi0I8Qfer2BBKSB/4bF5jixPtW9lQWbdDy7wlybKwbice
# Tw==
# -----END EC PRIVATE KEY-----
master_public_key = "3081a7301006072a8648ce3d020106052b810400270381920004006\
86f2843cd96ff5f3ff399af8e4a97af3ca716d4e84855285b9cdf054a11b5ec3e4076f75ab2c\
36d2d508dd7cbc1180378a39c35998b6fb4c80b384cdcadd643471df7da6d4a41008a33f0a5b\
29009fffeca8b20b65d1313b6759ee20149c5c8b2838b78b9f25b445dfcc1dec68b423c41f7a\
bd8104a481ff86c5e638b13ed5bd95059b743cbbc25c9b2b06e271e4f".decode("HEX")
if True:
    # when crypto.py is disabled a public key is slightly
    # different...
    master_public_key = ";".join(("60", master_public_key[:60].encode("HEX"),
                                                                         ""))

from threading import current_thread, Lock

class ChatCore:
    def __init__(self):
        self.nick = "Anon"
        self.message_references=[]

        self.setup_lock=Lock()

        print "THREAD init:",  current_thread().name

    def demo(self, callback):
        dispersy = Dispersy.get_instance()
        master = Member(master_public_key)

        try:
            community = ChatCommunity.load_community(master)
        except ValueError:
            ec = ec_generate_key(u"low")
            my_member = Member(ec_to_public_bin(ec), ec_to_private_bin(ec))
            community = ChatCommunity.join_community(master, my_member)

        self.community = community
        self.setup_lock.release()

    def dispersy(self, callback):
        # start Dispersy
        dispersy = Dispersy.get_instance(callback, u".")
        dispersy.socket = communication.get_socket(callback, dispersy)
        return dispersy

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

        #print ">>>>Z", nick, ";;;;;;", body
        self.mainwin.message_list.addItem(text)
        row = self.mainwin.message_list.currentRow()
        print "XXXXXXXXXX", row
        print "THREAD onmessagereceived",  current_thread().name
        current_item = self.mainwin.message_list.item(row)
        widget = ChatMessageWidget(nick=nick, body=body)
        self.mainwin.message_list.setItemWidget(current_item, widget)
        #That's a temporary hack too as with the new message format we will switch to
        #A model based chat message list widget
        self.message_references.append(widget)


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
        callback.register(self.demo, (callback,))
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
