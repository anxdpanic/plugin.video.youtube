# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from .base_item import BaseItem


class DirectoryItem(BaseItem):
    def __init__(self, name, uri, image=u'', fanart=u''):
        BaseItem.__init__(self, name, uri, image, fanart)
        self._plot = name
        self._is_action = False

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
