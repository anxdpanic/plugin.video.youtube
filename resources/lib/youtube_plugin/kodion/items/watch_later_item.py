# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .directory_item import DirectoryItem
from .. import constants


class WatchLaterItem(DirectoryItem):
    def __init__(self, context, alt_name=None, image=None, fanart=None):
        name = alt_name
        if not name:
            name = context.localize('watch_later')

        if image is None:
            image = context.create_resource_path('media/watch_later.png')

        super(WatchLaterItem, self).__init__(name, context.create_uri([constants.paths.WATCH_LATER, 'list']), image=image)
        if fanart:
            self.set_fanart(fanart)
        else:
            self.set_fanart(context.get_fanart())
