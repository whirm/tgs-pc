#!/usr/bin/env python
# -*- conding: utf8 -*-

import communication
import time
import sys

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

from PyQt4 import QtGui, QtCore

from widgets import SquareDialog

__all__=['MainWin',]

class MainWin(QtGui.QMainWindow, Ui_TheGlobalSquare):
    def __init__(self, *argv, **kwargs):
        super(MainWin, self).__init__(*argv, **kwargs)
        #super(Ui_MainWindow, self).__init__(*argv, **kwargs)
        self.setupUi(self)

        #We want the message list to scroll to the bottom every time we send or receive a new message.
        message_model = self.message_list.model()
        message_model.rowsInserted.connect(self.message_list.scrollToBottom)

        #Debug/demo stuff we will remove as functionality is implemented:
        self.showSquare_btn.clicked.connect(self.onDemoShowSquare)

    def onDemoShowSquare(self):
        #Keep a reference to it so it doesn't get destroyed
        self.square_dialog = SquareDialog()
        self.square_dialog.show()

