#!/usr/bin/env python
# -*- coding: utf-8 -*-

#Pyqt
from PyQt4.QtCore import pyqtSignal

try:
    from ui.squareeditdialog import Ui_SquareEditDialog
except (ImportError):
    print "\n>>> Run build_resources.sh (you need pyqt4-dev-tools) <<<\n"
    import sys
    sys.exit()

from PyQt4 import QtGui

__all__=['SquareEditDialog',]

class SquareEditDialog(QtGui.QDialog, Ui_SquareEditDialog):
    squareInfoReady = pyqtSignal()
    #TODO: Put a char counter to both the title and the description
    #The description sould be less than 1024 bytes when encoded in utf-8
    #The title should be less than 256 when idem

    def __init__(self, *argv, **kwargs):
        super(SquareEditDialog, self).__init__(*argv, **kwargs)
        self.setupUi(self)

        #Connect the joinSquare button to its callback
        self.saveSquare_btn.clicked.connect(self.onSaveSquareClicked)

    def onSaveSquareClicked(self):
        #TODO:Check for the info in the form to be correct.
        self.squareInfoReady.emit()
        self.close()

    def getSquareInfo(self):
        """
        Obtains all the square info from the widgets and returns it in a nice tuple.
        """
        title = self.title_line.text()
        description = self.description_txt.toPlainText()
        avatar = self.avatar_btn.icon()
        lat = self.lat_spin.value()
        lon = self.lon_spin.value()
        radius = self.radius_spin.value()
        return (title, description, avatar, lat, lon, radius)

    #TODO: Implement setSquareInfo, will be used to edit currently existing Squares.

