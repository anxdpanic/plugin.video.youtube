# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .base_item import BaseItem
from ..compatibility import unescape, urlencode


class DirectoryItem(BaseItem):
    def __init__(self,
                 name,
                 uri,
                 image='DefaultFolder.png',
                 fanart=None,
                 plot=None,
                 action=False,
                 category_label=None,
                 channel_id=None,
                 playlist_id=None,
                 subscription_id=None):
        super(DirectoryItem, self).__init__(name, uri, image, fanart)
        name = self.get_name()
        self._category_label = None
        self.set_category_label(category_label or name)
        self._plot = plot or name
        self._is_action = action
        self._channel_id = channel_id
        self._playlist_id = playlist_id
        self._subscription_id = subscription_id
        self._next_page = False

    def set_name(self, name, category_label=None):
        name = super(DirectoryItem, self).set_name(name)
        if hasattr(self, '_category_label'):
            self.set_category_label(category_label or name)
        self.set_plot(name)
        return name

    def set_category_label(self, label):
        if label == '__inherit__':
            self._category_label = None
            return

        current_label = self._category_label
        if current_label:
            if current_label != label:
                uri = self.get_uri()
                self.set_uri(uri.replace(
                    urlencode({'category_label': current_label}),
                    urlencode({'category_label': label}) if label else '',
                ))
        elif label:
            uri = self.get_uri()
            self.set_uri(('&' if '?' in uri else '?').join((
                uri,
                urlencode({'category_label': label}),
            )))
        self._category_label = label

    def get_category_label(self):
        return self._category_label

    def set_plot(self, plot):
        try:
            plot = unescape(plot)
        except Exception:
            pass
        self._plot = plot

    def get_plot(self):
        return self._plot

    def is_action(self):
        return self._is_action

    def set_action(self, value):
        if isinstance(value, bool):
            self._is_action = value

    @property
    def subscription_id(self):
        return self._subscription_id

    @subscription_id.setter
    def subscription_id(self, value):
        self._subscription_id = value

    @property
    def channel_id(self):
        return self._channel_id

    @channel_id.setter
    def channel_id(self, value):
        self._channel_id = value

    @property
    def playlist_id(self):
        return self._playlist_id

    @playlist_id.setter
    def playlist_id(self, value):
        self._playlist_id = value

    @property
    def next_page(self):
        return self._next_page

    @next_page.setter
    def next_page(self, value):
        self._next_page = value
