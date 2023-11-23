# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from .directory_item import DirectoryItem
from ..constants.const_paths import SEARCH


class SearchItem(DirectoryItem):
    def __init__(self, context, alt_name=None, image=None, fanart=None, location=False):
        name = alt_name
        if not name:
            name = context.localize('search')

        if image is None:
            image = context.create_resource_path('media/search.png')

        params = {'location': location} if location else {}

        super(SearchItem, self).__init__(name, context.create_uri([SEARCH, 'list'], params=params), image=image)
        if fanart:
            self.set_fanart(fanart)
        else:
            self.set_fanart(context.get_fanart())
