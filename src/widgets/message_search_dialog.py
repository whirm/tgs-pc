#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from ui.message_search import Ui_MessageSearchDialog
except (ImportError):
    print "\n>>> MessageSearch: Run build_resources.sh (you need pyqt4-dev-tools) <<<\n"
    import sys
    sys.exit()

from PyQt4 import QtGui, QtCore

#Local
from widgets import ChatMessageWidget

__all__=['MessageSearchDialog',]

class MessageSearchDialog(QtGui.QDialog, Ui_MessageSearchDialog):
    onSearchRequested = QtCore.pyqtSignal(unicode)
    def __init__(self, *argv, **kwargs):
        super(MessageSearchDialog, self).__init__(*argv, **kwargs)
        self.setupUi(self)

        #Connect the joinSquare button to its callback
        self.joinSquare_btn.clicked.connect(self.onJoinSquareClicked)
        self.followMessageAuthor_btn.clicked.connect(self.onJoinSquareClicked)

        self.search_line.returnPressed.connect(self.onSearchReady)
        self.search_btn.clicked.connect(self.onSearchReady)

    def onJoinSquareClicked(self):
        #TODO
        msgBox = QtGui.QMessageBox()
        msgBox.setText("You wish!")
        self.close()
        msgBox.exec_()

    def onFollowMessageAuthorClicked(self):
        #TODO:
        msgBox = QtGui.QMessageBox()
        msgBox.setText("You wish!")
        self.close()
        msgBox.exec_()

    def onSearchReady(self):
        self.onSearchRequested.emit(self.search_line.text())

