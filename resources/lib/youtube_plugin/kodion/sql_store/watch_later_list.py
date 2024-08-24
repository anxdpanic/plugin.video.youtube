# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .storage import Storage
from ..items import from_json


class WatchLaterList(Storage):
    _table_name = 'storage_v2'
    _table_updated = False
    _sql = {}

    def __init__(self, filepath):
        super(WatchLaterList, self).__init__(filepath)

    def get_items(self):
        result = self._get_by_ids(process=from_json, as_dict=True)
        return result

    def add_item(self, video_id, item):
        self._set(video_id, item)

    def del_item(self, video_id):
        self._remove(video_id)
