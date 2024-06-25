# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

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
