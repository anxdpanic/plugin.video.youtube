# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .directory_item import DirectoryItem
from ..constants.const_paths import SEARCH


class SearchHistoryItem(DirectoryItem):
    def __init__(self, context, query, image=None, fanart=None, location=False):
        if image is None:
            image = context.create_resource_path('media/search.png')

        params = {'q': query}
        if location:
            params['location'] = location

        super(SearchHistoryItem, self).__init__(query, context.create_uri([SEARCH, 'query'], params=params), image=image)
        if fanart:
            self.set_fanart(fanart)
        else:
            self.set_fanart(context.get_fanart())

        context_menu = [(context.localize('search.remove'),
                         'RunPlugin(%s)' % context.create_uri([SEARCH, 'remove'], params={'q': query})),
                        (context.localize('search.rename'),
                         'RunPlugin(%s)' % context.create_uri([SEARCH, 'rename'], params={'q': query})),
                        (context.localize('search.clear'),
                         'RunPlugin(%s)' % context.create_uri([SEARCH, 'clear']))]
        self.set_context_menu(context_menu)
