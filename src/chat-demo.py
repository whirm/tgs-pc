#!/usr/bin/python

# tar cvjf chat-demo.tar.bz2 chat-demo --exclude ".svn" --exclude "*pyc" --exclude "*~" --exclude ".backup"

import communication
import time
import sys

from discovery.community import DiscoveryCommunity
from square.community import SquareCommunity

from dispersy.callback import Callback
from dispersy.dispersy import Dispersy
from dispersy.member import Member
from dispersy.dprint import dprint
from dispersy.crypto import (ec_generate_key,
        ec_to_public_bin, ec_to_private_bin)


from ui.main import Ui_MainWindow
#from PySide import QtGui, QtCore
from PyQt4 import QtGui, QtCore

class ChatCore:
    def __init__(self):
        self.nick = "Anon"

    def dispersy(self, callback):
        # start Dispersy
        dispersy = Dispersy.get_instance(callback, u".")
        dispersy.socket = communication.get_socket(callback, dispersy)
        dispersy.define_auto_load(SquareCommunity)

        # load/join discovery community
        public_key = "3081a7301006072a8648ce3d020106052b81040027038192000406b34f060c416e452fd31fb1770c2f475e928effce751f2f82565bec35c46a97fb8b375cca4ac5dc7d93df1ba594db335350297f003a423e207b53709e6163b7688c0f60a9cf6599037829098d5fbbfe786e0cb95194292f241ff6ae4d27c6414f94de7ed1aa62f0eb6ef70d2f5af97c9aade8266eb85b14296ed2004646838c056d1d9ad8a509b69f81fbc726201b57".decode("HEX")
        if True:
            # when crypto.py is disabled a public key is slightly
            # different...
            public_key = ";".join(("60", public_key[:60].encode("HEX"), ""))
        master = Member.get_instance(public_key)
        try:
            community = DiscoveryCommunity.load_community(master)
        except ValueError:
            ec = ec_generate_key(u"low")
            my_member = Member.get_instance(ec_to_public_bin(ec),
                                            ec_to_private_bin(ec),
                                            sync_with_database=True)
            community = DiscoveryCommunity.join_community(master, my_member)
        else:
            my_member = community.my_member

        # load squares
        for master in SquareCommunity.get_master_members():
            yield 1.0
            dispersy.get_community(master.mid)

    def onTextMessageReceived(self, text):
        self.mainwin.message_list.addItem(text)

    def onNickChanged(self, *argv, **kwargs):
        nick = self.mainwin.nick_line.text()
        print "Nick changed to:", nick
        if nick and nick != self.nick:
            self.callback.register(self.community.setNick, (nick,))
            self.nick = nick
        else:
            print "Same or empty nick, doing nothing"

    def onMessageReadyToSend(self):
        message = self.mainwin.message_line.text()
        if message:
            print "Sending message: ", message
            self.callback.register(self.community.sendMessage, (message,))
            self.mainwin.message_line.clear()
        else:
            print "Not sending empty message."

    def _setupThreads(self):
        # start threads
        callback = Callback()
        callback.start(name="Dispersy")

        callback.register(self.dispersy, (callback,))
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

        #We want the message list to scroll to the bottom every time we send or receive a new message.
        message_model = self.message_list.model()
        message_model.rowsInserted.connect(self.message_list.scrollToBottom)


if __name__ == "__main__":
    exit_exception = None
    chat = ChatCore()
    chat.run()
    if exit_exception:
        raise exit_exception
