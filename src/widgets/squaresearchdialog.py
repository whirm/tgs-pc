#!/usr/bin/env python
# -*- conding: utf8 -*-


try:
    from ui.square import Ui_SquareSearchDialog
except (ImportError):
    print "\n>>> Run build_resources.sh (you need pyqt4-dev-tools) <<<\n"
    import sys
    sys.exit()

from PyQt4 import QtGui, QtCore

#Local
from widgets import ChatMessageWidget

__all__=['SquareSearchDialog',]

class SquareSearchDialog(QtGui.QDialog, Ui_SquareSearchDialog):
    onSearchRequested = QtCore.pyqtSignal(list)
    def __init__(self, *argv, **kwargs):
        super(SquareSearchDialog, self).__init__(*argv, **kwargs)
        self.setupUi(self)

        #Connect the joinSquare button to its callback
        self.joinSquare_btn.clicked.connect(self.onJoinSquareClicked)

        self.search_line.returnPressed.connect(self.onSearchReady)
        self.search_btn.clicked.connect(self.onSearchReady)

    def onJoinSquareClicked(self):
        msgBox = QtGui.QMessageBox()
        msgBox.setText("You wish!")
        self.close()
        msgBox.exec_()

    def onSearchReady(self):
        search_terms = self.search_line.text().split()
        self.onSearchRequested.emit(search_terms)

