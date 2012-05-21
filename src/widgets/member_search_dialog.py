#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from ui.member_search import Ui_MemberSearchDialog
except (ImportError):
    print "\n>>> Run build_resources.sh (you need pyqt4-dev-tools) <<<\n"
    import sys
    sys.exit()

from PyQt4 import QtGui, QtCore

#Local
from member_overview_widget import MemberOverviewWidget

__all__=['MemberSearchDialog',]

#Row name constants
ALIAS, THUMBNAIL_HASH = range(2)

class MemberSearchDialog(QtGui.QDialog, Ui_MemberSearchDialog):
    onSearchRequested = QtCore.pyqtSignal(unicode)
    def __init__(self, *argv, **kwargs):
        super(MemberSearchDialog, self).__init__(*argv, **kwargs)
        self.setupUi(self)

        self._resetModel()

        #Connect the followUser button to its callback
        self.followUser_btn.clicked.connect(self.onFollowUserClicked)

        self.search_line.returnPressed.connect(self.onSearchReady)
        self.search_btn.clicked.connect(self.onSearchReady)

    def _resetModel(self):
        #Set up the square list data model
        self._model = QtGui.QStandardItemModel(0, 3, self.results_list)
        self._model.setHeaderData(ALIAS, QtCore.Qt.Horizontal, "Title")
        self._model.setHeaderData(THUMBNAIL_HASH, QtCore.Qt.Horizontal, "Thumbnail hash")
        self.results_list.setModel(self._model)

    def onFollowUserClicked(self):
		#TODO:
        msgBox = QtGui.QMessageBox()
        msgBox.setText("You wish!")
        self.close()
        msgBox.exec_()

    def onSearchReady(self):
        if self.search_line.text():
            self.search_btn.setDisabled(True)
            self.search_line.setDisabled(True)
            self.onSearchRequested.emit(self.search_line.text())

    def addResult(self, alias, thumbnail_hash):
        self._model.insertRow(0)
        self._model.setData(self._model.index(0, ALIAS), alias)
        self._model.setData(self._model.index(0, THUMBNAIL_HASH), thumbnail_hash)

    def clearResultsList(self):
        self._resetModel()

    def onSearchFinished(self):
        self.search_btn.setDisabled(False)
        self.search_line.setDisabled(False)
