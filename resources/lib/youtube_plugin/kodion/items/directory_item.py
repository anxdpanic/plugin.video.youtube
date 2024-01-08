# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .base_item import BaseItem
from ..compatibility import urlencode


class DirectoryItem(BaseItem):
    def __init__(self,
                 name,
                 uri,
                 image='',
                 fanart='',
                 action=False,
                 category_label=None):
        if category_label is None:
            category_label = name
        if category_label:
            uri = ('&' if '?' in uri else '?').join((
                uri,
                urlencode({'category_label': category_label}),
            ))
        super(DirectoryItem, self).__init__(name, uri, image, fanart)
        self._plot = self.get_name()
        self._is_action = action
        self._channel_subscription_id = None
        self._channel_id = None

    def set_name(self, name):
        self._name = name

    def set_plot(self, plot):
        self._plot = plot

    def get_plot(self):
        return self._plot

    def is_action(self):
        return self._is_action

    def set_action(self, value):
        if isinstance(value, bool):
            self._is_action = value

    def get_channel_subscription_id(self):
        return self._channel_subscription_id

    def set_channel_subscription_id(self, value):
        self._channel_subscription_id = value

    def set_channel_id(self, value):
        self._channel_id = value

    def get_channel_id(self):
        return self._channel_id
