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


class NextPageItem(DirectoryItem):
    def __init__(self, context, params, image=None, fanart=None):
        if 'refresh' in params:
            del params['refresh']

        path = context.get_path()
        page = params.get('page', 2)
        items_per_page = params.get('items_per_page', 50)
        can_jump = ('next_page_token' not in params
                    and not path.startswith(('/channel',
                                             PATHS.RECOMMENDATIONS,
                                             PATHS.RELATED_VIDEOS)))
        can_search = not path.startswith(PATHS.SEARCH)
        if 'page_token' not in params and can_jump:
            params['page_token'] = self.create_page_token(page, items_per_page)

        name = context.localize('page.next') % page
        if page != context.get_param('page', 1) + 1:
            name = ''.join((name, ' (', context.localize('filtered'), ')'))

        super(NextPageItem, self).__init__(
            name,
            context.create_uri(path, params),
            image=image,
            fanart=fanart,
            category_label='__inherit__',
        )

        self.next_page = page
        self.items_per_page = items_per_page

        context_menu = [
            menu_items.refresh(context),
            menu_items.goto_page(context, params) if can_jump else None,
            menu_items.goto_home(context),
            menu_items.goto_quick_search(context) if can_search else None,
        ]
        self.add_context_menu(context_menu)

    @classmethod
    def create_page_token(cls, page, items_per_page=50):
        low = 'AEIMQUYcgkosw048'
        high = 'ABCDEFGHIJKLMNOP'
        len_low = len(low)
        len_high = len(high)

        position = (page - 1) * items_per_page

        overflow_token = 'Q'
        if position >= 128:
            overflow_token_iteration = position // 128
            overflow_token = '%sE' % high[overflow_token_iteration]
        low_iteration = position % len_low

        # at this position the iteration starts with 'I' again (after 'P')
        if position >= 256:
            multiplier = (position // 128) - 1
            position -= 128 * multiplier
        high_iteration = (position // len_low) % len_high

        return 'C{high_token}{low_token}{overflow_token}AA'.format(
            high_token=high[high_iteration],
            low_token=low[low_iteration],
            overflow_token=overflow_token
        )
