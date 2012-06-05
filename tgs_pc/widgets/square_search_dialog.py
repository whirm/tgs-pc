#!/usr/bin/env python
# -*- coding: utf-8 -*-


from ..ui.square_search import Ui_SquareSearchDialog

from PyQt4 import QtGui, QtCore

#Local

#TODO: Set item delegate (already designed, need to refactor it from the old item-based code)

__all__=['SquareSearchDialog',]

#Row name constants
COLUMNS=4
TITLE, DESCRIPTION, LOCATION, SQUARE = range(COLUMNS)

#TODO: Refactor this into a generic search dialog class and then make the Search dialogs inherit from it

class SquareSearchDialog(QtGui.QDialog, Ui_SquareSearchDialog):
    onSearchRequested = QtCore.pyqtSignal(unicode)
    onJoinSquareRequested = QtCore.pyqtSignal(object)

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
        self._model = QtGui.QStandardItemModel(0, COLUMNS, self.results_list)
        self._model.setHeaderData(TITLE, QtCore.Qt.Horizontal, "Title")
        self._model.setHeaderData(DESCRIPTION, QtCore.Qt.Horizontal, "Description")
        self._model.setHeaderData(LOCATION, QtCore.Qt.Horizontal, "Location")
        self._model.setHeaderData(SQUARE, QtCore.Qt.Horizontal, "Square")
        self.results_list.setModel(self._model)

        #Clear the square list
        self._squares = []

    def onJoinSquareClicked(self):
        index = self.results_list.currentIndex()
        #TODO: This should be simpler but it segfaults
        #square = index.sibling(index.row(), SQUARE).internalPointer()
        #TODO: this is hackier and it returns None...
        #square = self._model.item(index.row(), SQUARE).data().toPyObject()
        #TODO: That's not pretty, figure out what's wrong with this ^^^ and use only the model....
        square = self._squares[index.row()]
        self.onJoinSquareRequested.emit(square)

        msgBox = QtGui.QMessageBox()
        msgBox.setText("You wish!")
        self.close()
        msgBox.exec_()

    def onSearchReady(self):
        if self.search_line.text():
            self.search_btn.setDisabled(True)
            self.search_line.setDisabled(True)
            self.onSearchRequested.emit(self.search_line.text())

    def addResult(self, square):
        self._model.insertRow(0)
        self._model.setData(self._model.index(0, TITLE), square.title)
        self._model.setData(self._model.index(0, DESCRIPTION), square.description)
        self._model.setData(self._model.index(0, LOCATION), square.location)
        self._model.setData(self._model.index(0, SQUARE), square)
        self._squares.insert(0, square)

    def clearResultsList(self):
        self._resetModel()

    def onSearchFinished(self):
        self.search_btn.setDisabled(False)
        self.search_line.setDisabled(False)
