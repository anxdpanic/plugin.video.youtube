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


class WatchLaterItem(DirectoryItem):
    def __init__(self, context, name=None, image=None, fanart=None):
        if not name:
            name = context.localize('watch_later')

        if image is None:
            image = '{media}/watch_later.png'

        super(WatchLaterItem, self).__init__(name,
                                             context.create_uri(
                                                 (paths.WATCH_LATER, 'list',),
                                             ),
                                             image=image)

        if fanart:
            self.set_fanart(fanart)
