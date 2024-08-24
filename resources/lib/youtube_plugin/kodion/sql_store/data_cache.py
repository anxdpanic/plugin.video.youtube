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
    _table_updated = False
    _sql = {}

    def __init__(self, filepath, max_file_size_mb=5):
        max_file_size_kb = max_file_size_mb * 1024
        super(DataCache, self).__init__(filepath,
                                        max_file_size_kb=max_file_size_kb)

    def get_items(self,
                  content_ids,
                  seconds=None,
                  as_dict=True,
                  values_only=True):
        result = self._get_by_ids(content_ids,
                                  seconds=seconds,
                                  as_dict=as_dict,
                                  values_only=values_only)
        return result

    def get_items_like(self, content_id, seconds=None):
        result = self._get_by_ids((content_id,),
                                  seconds=seconds,
                                  wildcard=True,
                                  as_dict=True,
                                  values_only=False)
        return result

    def get_item_like(self, content_id, seconds=None, first=False):
        result = self._get_by_ids((content_id,),
                                  seconds=seconds,
                                  wildcard=True,
                                  as_dict=False,
                                  values_only=False,
                                  oldest_first=first,
                                  limit=1)
        return result

    def get_item(self, content_id, seconds=None, as_dict=False):
        result = self._get(content_id, seconds=seconds, as_dict=as_dict)
        return result

    def set_item(self, content_id, item):
        self._set(content_id, item)

    def set_items(self, items):
        self._set_many(items)

    def del_item(self, content_id):
        self._remove(content_id)

    def update_item(self, content_id, item, timestamp=None):
        self._update(content_id, item, timestamp)

    def _optimize_item_count(self, limit=-1, defer=False):
        return False
