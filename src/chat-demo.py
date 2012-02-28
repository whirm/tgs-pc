#!/usr/bin/python

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


from ui.main import Ui_MainWindow
from PySide import QtGui

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


class ChatCore:
    def demo(self, callback):
        dispersy = Dispersy.get_instance()
        master = Member.get_instance(master_public_key)

        try:
            community = ChatCommunity.load_community(master)
        except ValueError:
            ec = ec_generate_key(u"low")
            my_member = Member.get_instance(ec_to_public_bin(ec),
                                            ec_to_private_bin(ec),
                                            sync_with_database=True)
            community = ChatCommunity.join_community(master, my_member)

        community.textMessageReceived.connect(self.onTextMessageReceived)
        self.community = community

    def dispersy(self, callback):
        # start Dispersy
        dispersy = Dispersy.get_instance(callback, u".")
        dispersy.socket = communication.get_socket(callback, dispersy)
        return dispersy

    def onTextMessageReceived(self, text):
        self.mainwin.message_list.addItem(text)
        print text

    def onNickChanged(self, *argv, **kwargs):
        nick = self.mainwin.nick_line.text()
        print "Nick changed to:", nick
        self.callback.register(self.community.setNick, (nick,))

    def onMessageReadyToSend(self):
        message = self.mainwin.message_line.text()
        print "Sending message: ", message
        self.callback.register(self.community.sendMessage, (message,))
        self.mainwin.message_line.clear()

    def _setupThreads(self):
        # start threads
        callback = Callback()
        callback.start(name="Dispersy")

        callback.register(self.dispersy, (callback,))
        callback.register(self.demo, (callback,))
        self.callback = callback

    def _stopThreads():
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


class MainWin(QtGui.QMainWindow, Ui_MainWindow):
    def __init__(self, *argv, **kwargs):
        super(MainWin, self).__init__(*argv, **kwargs)
        #super(Ui_MainWindow, self).__init__(*argv, **kwargs)
        self.setupUi(self)


if __name__ == "__main__":
    exit_exception = None
    chat = ChatCore()
    chat.run()
    if exit_exception:
        raise exit_exception
