# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .storage import Storage
from ..utils.methods import generate_hash


class SearchHistory(Storage):
    _table_name = 'storage_v2'
    _table_updated = False
    _sql = {}

    def __init__(self, filepath, max_item_count=10, migrate=False):
        super(SearchHistory, self).__init__(filepath,
                                            max_item_count=max_item_count,
                                            migrate=migrate)

    def get_items(self, process=None):
        result = self._get_by_ids(oldest_first=False,
                                  limit=self._max_item_count,
                                  process=process)
        return result

    def add_item(self, query):
        if isinstance(query, dict):
            params = query
            query = params['q']
        else:
            params = {'q': query}
        self._set(generate_hash(query), params)

    def del_item(self, query):
        if isinstance(query, dict):
            query = query['q']
        self._remove(generate_hash(query))

    def update_item(self, query, timestamp=None):
        if isinstance(query, dict):
            params = query
            query = params['q']
        else:
            params = {'q': query}
        self._update(generate_hash(query), params, timestamp)
