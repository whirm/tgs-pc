#!/usr/bin/env python
# -*- conding: utf8 -*-


try:
    from ui.square import Ui_SquareDialog
except (ImportError):
    print "\n>>> Run build_resources.sh (you need pyqt4-dev-tools) <<<\n"
    import sys
    sys.exit()

from PyQt4 import QtGui

#Local
from widgets import ChatMessageWidget

__all__=['SquareDialog',]

class SquareDialog(QtGui.QDialog, Ui_SquareDialog):
    def __init__(self, *argv, **kwargs):
        super(SquareDialog, self).__init__(*argv, **kwargs)
        self.setupUi(self)

        #Connect the joinSquare button to its callback
        self.joinSquare_btn.clicked.connect(self.onJoinSquareClicked)

    def onJoinSquareClicked(self):
        msgBox = QtGui.QMessageBox()
        msgBox.setText("You wish!")
        self.close()
        msgBox.exec_()

