#!/usr/bin/env python
# -*- coding: utf-8 -*-

#QT
from PyQt4.QtGui import QWidget, QPixmap, QListWidgetItem
from PyQt4.QtCore import QSize, Qt

#Python builtin
from time import strftime, localtime

#Local
from ui.squareoverview import Ui_SquareOverview

__all__ = ['SquareOverviewWidget', 'SquareOverviewListItem']


class SquareOverviewListItem(QListWidgetItem):
    def __init__(self, parent, square, *argv, **kwargs):
        super(SquareOverviewListItem, self).__init__(type=QListWidgetItem.UserType)

        self.square = square
        self.widget = SquareOverviewWidget(title=square.title, *argv, **kwargs)
        self.setSizeHint(self.widget.minimumSizeHint())

        self.setFlags(Qt.ItemFlags(Qt.ItemIsSelectable + Qt.ItemIsEnabled))

        parent.addItem(self)
        parent.setItemWidget(self, self.widget)

    def onInfoUpdated(self):
        #TODO: update all the fields (timestamp, thumbnail...)
        self.widget.update(title=self.square.title, description=self.square.description)


class SquareOverviewWidget(QWidget, Ui_SquareOverview):
    def __init__(self, title, description='', timestamp=None, avatar=None):
        super(SquareOverviewWidget, self).__init__()
        self.setupUi(self)

        self.update(title, description, timestamp, avatar)

    def update(self, title=None, description='', timestamp=None, avatar=None):
        if title:
            self.name_lbl.setText(title)

        if description:
            self.avatar_lbl.setToolTip(description)

        if timestamp:
            self.timestamp_lbl.setText(strftime('%H:%M:%S',localtime(timestamp)))
        else:
            self.timestamp_lbl.setText(strftime('%H:%M:%S'))

        if avatar:
            self.avatar_lbl.setPixmap(QPixmap(avatar))
