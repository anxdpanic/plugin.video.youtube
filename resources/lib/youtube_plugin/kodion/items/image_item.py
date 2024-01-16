# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .base_item import BaseItem


class ImageItem(BaseItem):
    def __init__(self, name, uri, image='', fanart=''):
        super(ImageItem, self).__init__(name, uri, image, fanart)
        self._title = None

    def set_title(self, title):
        self._title = title

    def get_title(self):
        return self._title
