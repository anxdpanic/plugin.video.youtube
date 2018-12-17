# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from .directory_item import DirectoryItem
from .. import constants


class SearchHistoryItem(DirectoryItem):
    def __init__(self, context, query, image=None, fanart=None, location=False):
        if image is None:
            image = context.create_resource_path('media/search.png')

        params = {'q': query}
        if location:
            params['location'] = location

        DirectoryItem.__init__(self, query, context.create_uri([constants.paths.SEARCH, 'query'], params=params), image=image)
        if fanart:
            self.set_fanart(fanart)
        else:
            self.set_fanart(context.get_fanart())

        context_menu = [(context.localize(constants.localize.SEARCH_REMOVE),
                         'RunPlugin(%s)' % context.create_uri([constants.paths.SEARCH, 'remove'], params={'q': query})),
                        (context.localize(constants.localize.SEARCH_RENAME),
                         'RunPlugin(%s)' % context.create_uri([constants.paths.SEARCH, 'rename'], params={'q': query})),
                        (context.localize(constants.localize.SEARCH_CLEAR),
                         'RunPlugin(%s)' % context.create_uri([constants.paths.SEARCH, 'clear']))]
        self.set_context_menu(context_menu)
