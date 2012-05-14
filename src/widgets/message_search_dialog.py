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

#Row name constants
TEXT, MEMBER, SQUARE = range(3)

class MessageSearchDialog(QtGui.QDialog, Ui_MessageSearchDialog):
    onSearchRequested = QtCore.pyqtSignal(unicode)
    def __init__(self, *argv, **kwargs):
        super(MessageSearchDialog, self).__init__(*argv, **kwargs)
        self.setupUi(self)

        self._resetModel()        
		#Connect the joinSquare button to its callback
        self.joinSquare_btn.clicked.connect(self.onJoinSquareClicked)
        self.followMessageAuthor_btn.clicked.connect(self.onJoinSquareClicked)

        self.search_line.returnPressed.connect(self.onSearchReady)
        self.search_btn.clicked.connect(self.onSearchReady)

    def _resetModel(self):
        #Set up the square list data model
        self._model = QtGui.QStandardItemModel(0, 3, self.results_list)
        self._model.setHeaderData(TEXT, QtCore.Qt.Horizontal, "Title")
        self._model.setHeaderData(MEMBER, QtCore.Qt.Horizontal, "Member")
        self._model.setHeaderData(SQUARE, QtCore.Qt.Horizontal, "Square")
        self.results_list.setModel(self._model)

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
        if self.search_line.text():
            self.onSearchRequested.emit(self.search_line.text())
            self.search_btn.setDisabled(True)
            self.search_line.setDisabled(True)

    def addResult(self, text, member, square):
        self._model.insertRow(0)
        self._model.setData(self._model.index(0, TEXT), text)
        self._model.setData(self._model.index(0, MEMBER), member)
        self._model.setData(self._model.index(0, SQUARE), square)

    def clearResultsList(self):
        self._resetModel()

    def onSearchFinished(self):
        self.search_btn.setDisabled(False)
        self.search_line.setDisabled(False)
