# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2019 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .storage import Storage


class DataCache(Storage):
    _table_name = 'storage_v2'
    _table_created = False
    _table_updated = False
    _sql = {}

    def __init__(self, filepath, max_file_size_mb=5):
        max_file_size_kb = max_file_size_mb * 1024
        super(DataCache, self).__init__(filepath,
                                        max_file_size_kb=max_file_size_kb)

    def get_items(self, content_ids, seconds):
        result = self._get_by_ids(content_ids, seconds=seconds, as_dict=True)
        return result

    def get_item(self, content_id, seconds):
        result = self._get(content_id, seconds=seconds)
        return result

    def set_item(self, content_id, item):
        self._set(content_id, item)

    def set_items(self, items):
        self._set_many(items)

    def remove(self, content_id):
        self._remove(content_id)

    def update(self, content_id, item):
        self._set(str(content_id), item)

    def _optimize_item_count(self, limit=-1, defer=False):
        return False
