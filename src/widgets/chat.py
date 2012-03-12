#!/usr/bin/env python
# -*- coding: utf-8 -*-

#QT
from PyQt4.QtGui import QWidget, QPixmap, QListWidgetItem
from PyQt4.QtCore import QSize

#Python builtin
from time import strftime, localtime

#Local
from ui.chatmessage import Ui_ChatMessage

__all__ = ['ChatMessageWidget', 'ChatMessageListItem']


class ChatMessageListItem(QListWidgetItem):
    def __init__(self, parent, message):
        super(ChatMessageListItem, self).__init__(type=QListWidgetItem.UserType)

        self.message = message
        nick = message.payload.member_info.payload.alias
        body = message.payload.text
        timestamp = message.payload.utc_timestamp

        #TODO: Obtain media associated with message.media_hash and put it in the message.
        #TODO: Obtain media associated with message.member_info.thumbnail_hash and update the avatar.
        self.widget = ChatMessageWidget(nick, body, timestamp)

        self.setSizeHint(self.widget.minimumSizeHint())

        #First check if we should be appended at the end to avoid iterating over
        #the whole list for each new message we receive
        count = parent.count()
        if (count == 0) or (parent.item(count-1).message.payload.utc_timestamp <= timestamp):
            parent.addItem(self)
            parent.setItemWidget(self, self.widget)
        else:
            #Insert ourselves in the appropiate place in the timeline.
            for row in xrange(0,count):
                list_item = parent.item(row)
                if list_item.message.payload.utc_timestamp > timestamp:
                    row = parent.row(list_item)
                    parent.insertItem(row, self)
                    parent.setItemWidget(self, self.widget)
                    #We are done here.
                    break


class ChatMessageWidget(QWidget, Ui_ChatMessage):
    def __init__(self, nick='', body='', timestamp=None, avatar=None, media=None):
        super(ChatMessageWidget, self).__init__()
        self.setupUi(self)

        if nick:
            self.action_lbl.setText('%s says:' % nick)
        else:
            self.action_lbl.clear()

        if body:
            self.body_lbl.setText(body)
        else:
            self.body_lbl.clear()

        if timestamp:
            self.timestamp_lbl.setText(strftime('%H:%M:%S',localtime(timestamp)))
        else:
            self.timestamp_lbl.setText(strftime('%H:%M:%S'))

        if avatar:
            self.avatar_lbl.setPixmap(QPixmap(avatar))

        if media:
            self.media_lbl.setText("This message has media, but the coder is lazy.")
        else:
            self.media_lbl.hide()
