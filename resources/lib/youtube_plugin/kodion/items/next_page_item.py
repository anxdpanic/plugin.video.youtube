# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .directory_item import DirectoryItem


class NextPageItem(DirectoryItem):
    def __init__(self, context, params, image=None, fanart=None):
        if 'refresh' in params:
            del params['refresh']

        super(NextPageItem, self).__init__(
            context.localize('next_page') % params.get('page', 2),
            context.create_uri(context.get_path(), params),
            image=image,
            category_label='__inherit__',
        )

        if fanart:
            self.set_fanart(fanart)

        self.next_page = True
