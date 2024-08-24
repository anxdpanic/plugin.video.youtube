# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2019 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from hashlib import md5

from .storage import Storage


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

    @staticmethod
    def _make_id(search_text):
        return md5(search_text.encode('utf-8')).hexdigest()

    def add_item(self, search_text):
        self._set(self._make_id(search_text), search_text)

    def del_item(self, search_text):
        self._remove(self._make_id(search_text))

    def update_item(self, search_text, timestamp=None):
        self._update(self._make_id(search_text), search_text, timestamp)
