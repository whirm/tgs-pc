#!/usr/bin/env python
# -*- coding: utf-8 -*-

#import communication
import time
import sys


try:
    from ui.main import Ui_TheGlobalSquare
except (ImportError):
    print "\n>>> Run build_resources.sh (you need pyqt4-dev-tools) <<<\n"
    sys.exit()

from PyQt4 import QtGui, QtCore

__all__=['MainWin',]

class MainWin(QtGui.QMainWindow, Ui_TheGlobalSquare):
    def __init__(self, *argv, **kwargs):
        super(MainWin, self).__init__(*argv, **kwargs)
        #super(Ui_MainWindow, self).__init__(*argv, **kwargs)
        self.setupUi(self)

        #We want the overview message list to scroll to the bottom every time we send or receive a new message.
        message_model = self.message_list.model()
        message_model.rowsInserted.connect(self.message_list.scrollToBottom)


