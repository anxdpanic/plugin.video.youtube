# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .directory_item import DirectoryItem
from ..constants import paths


class FavoritesItem(DirectoryItem):
    def __init__(self, context, name=None, image=None, fanart=None):
        if not name:
            name = context.localize('favorites')

        if image is None:
            image = '{media}/favorites.png'

        super(FavoritesItem, self).__init__(name,
                                            context.create_uri(
                                                (paths.FAVORITES, 'list',),
                                            ),
                                            image=image)

        if fanart:
            self.set_fanart(fanart)
