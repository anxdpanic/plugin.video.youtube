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
                                                (paths.SEARCH, 'input',),
                                                params=params,
                                            ), image=image)

        if fanart:
            self.set_fanart(fanart)
