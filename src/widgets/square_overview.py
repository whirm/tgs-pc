#!/usr/bin/env python
# -*- coding: utf-8 -*-

#QT
from PyQt4.QtGui import QWidget, QPixmap, QListWidgetItem
from PyQt4.QtCore import QSize

#Python builtin
from time import strftime, localtime

#Local
from ui.squareoverview import Ui_SquareOverview

__all__ = ['SquareOverviewWidget', 'SquareOverviewListItem']


class SquareOverviewListItem(QListWidgetItem):
    def __init__(self, parent, *argv, **kwargs):
        super(SquareOverviewListItem, self).__init__(type=QListWidgetItem.UserType)

        self.widget = SquareOverviewWidget(*argv, **kwargs)
        self.setSizeHint(self.widget.minimumSizeHint())
        parent.addItem(self)
        parent.setItemWidget(self, self.widget)


class SquareOverviewWidget(QWidget, Ui_SquareOverview):
    def __init__(self, name, description='', timestamp=None, avatar=None):
        super(SquareOverviewWidget, self).__init__()
        self.setupUi(self)

        self.name_lbl.setText(name)

        if description:
            self.avatar_lbl.setToolTip(description)

        if timestamp:
            self.timestamp_lbl.setText(strftime('%H:%M:%S',localtime(timestamp)))
        else:
            self.timestamp_lbl.setText(strftime('%H:%M:%S'))

        if avatar:
            self.avatar_lbl.setPixmap(QPixmap(avatar))

