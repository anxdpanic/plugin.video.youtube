# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from . import menu_items
from .directory_item import DirectoryItem
from ..constants import PATHS


class SearchItem(DirectoryItem):
    def __init__(self,
                 context,
                 name=None,
                 image=None,
                 fanart=None,
                 location=False):
        if not name:
            name = context.localize('search')

        if image is None:
            image = '{media}/search.png'

        params = {}
        if location:
            params['location'] = location

        super(SearchItem, self).__init__(name,
                                         context.create_uri(
                                             (PATHS.SEARCH, 'list',),
                                             params=params,
                                         ),
                                         image=image,
                                         fanart=fanart)

        context_menu = [
            menu_items.search_clear(context),
            menu_items.separator(),
            menu_items.goto_quick_search(context, params),
            menu_items.goto_quick_search(context, params, incognito=True)
        ]
        self.add_context_menu(context_menu)


class SearchHistoryItem(DirectoryItem):
    def __init__(self, context, query, image=None, fanart=None, location=False):
        if image is None:
            image = '{media}/search.png'

        if isinstance(query, dict):
            params = query
            query = params['q']
        else:
            params = {'q': query}
        if location:
            params['location'] = location

        super(SearchHistoryItem, self).__init__(query,
                                                context.create_uri(
                                                    (PATHS.SEARCH, 'query',),
                                                    params=params,
                                                ),
                                                image=image,
                                                fanart=fanart)

        context_menu = [
            menu_items.search_remove(context, query),
            menu_items.search_rename(context, query),
            menu_items.search_clear(context),
            menu_items.separator(),
            menu_items.search_sort_by(context, params, 'relevance'),
            menu_items.search_sort_by(context, params, 'date'),
            menu_items.search_sort_by(context, params, 'viewCount'),
            menu_items.search_sort_by(context, params, 'rating'),
            menu_items.search_sort_by(context, params, 'title'),
        ]
        self.add_context_menu(context_menu)


class NewSearchItem(DirectoryItem):
    def __init__(self,
                 context,
                 name=None,
                 image=None,
                 fanart=None,
                 incognito=False,
                 channel_id='',
                 addon_id='',
                 location=False):
        if not name:
            name = context.get_ui().bold(context.localize('search.new'))

        if image is None:
            image = '{media}/new_search.png'

        params = {}
        if addon_id:
            params['addon_id'] = addon_id
        if incognito:
            params['incognito'] = incognito
        if channel_id:
            params['channel_id'] = channel_id
        if location:
            params['location'] = location

        super(NewSearchItem, self).__init__(name,
                                            context.create_uri(
                                                (PATHS.SEARCH, 'input',),
                                                params=params,
                                            ),
                                            image=image,
                                            fanart=fanart)

        if context.is_plugin_path(context.get_uri(), ((PATHS.SEARCH, 'list'),)):
            context_menu = [
                menu_items.search_clear(context),
                menu_items.separator(),
                menu_items.goto_quick_search(context, params, not incognito)
            ]
        else:
            context_menu = [
                menu_items.goto_quick_search(context, params, not incognito)
            ]
        self.add_context_menu(context_menu)
