#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from ui.square_search import Ui_SquareSearchDialog
except (ImportError):
    print "\n>>> Run build_resources.sh (you need pyqt4-dev-tools) <<<\n"
    import sys
    sys.exit()

from PyQt4 import QtGui, QtCore

#Local

#TODO: Set item delegate (already designed, need to refactor it from the old item-based code)

__all__=['SquareSearchDialog',]

#Row name constants
TITLE, DESCRIPTION, LOCATION = range(3)

#TODO: Refactor this into a generic search dialog class and then make the Search dialogs inherit from it

class SquareSearchDialog(QtGui.QDialog, Ui_SquareSearchDialog):
    onSearchRequested = QtCore.pyqtSignal(unicode)
    def __init__(self, *argv, **kwargs):
        super(SquareSearchDialog, self).__init__(*argv, **kwargs)
        self.setupUi(self)

        self._resetModel()

        #Connect the joinSquare button to its callback
        self.joinSquare_btn.clicked.connect(self.onJoinSquareClicked)

        self.search_line.returnPressed.connect(self.onSearchReady)
        self.search_btn.clicked.connect(self.onSearchReady)

    def _resetModel(self):
        #Set up the square list data model
        self._model = QtGui.QStandardItemModel(0, 3, self.results_list)
        self._model.setHeaderData(TITLE, QtCore.Qt.Horizontal, "Title")
        self._model.setHeaderData(DESCRIPTION, QtCore.Qt.Horizontal, "Description")
        self._model.setHeaderData(LOCATION, QtCore.Qt.Horizontal, "Location")
        self.results_list.setModel(self._model)

    def onJoinSquareClicked(self):
        msgBox = QtGui.QMessageBox()
        msgBox.setText("You wish!")
        self.close()
        msgBox.exec_()

    def onSearchReady(self):
        if self.search_line.text():
            self.onSearchRequested.emit(self.search_line.text())
            self.search_btn.setDisabled(True)
            self.search_line.setDisabled(True)

    def addResult(self, title, description, location):
        self._model.insertRow(0)
        self._model.setData(self._model.index(0, TITLE), title)
        self._model.setData(self._model.index(0, DESCRIPTION), description)
        self._model.setData(self._model.index(0, LOCATION), location)

    def clearResultsList(self):
        self._resetModel()

    def onSearchFinished(self):
        self.search_btn.setDisabled(False)
        self.search_line.setDisabled(False)
