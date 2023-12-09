# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2019 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
from datetime import datetime

from .storage import Storage


class DataCache(Storage):
    def __init__(self, filename, max_file_size_mb=5):
        max_file_size_kb = max_file_size_mb * 1024
        super(DataCache, self).__init__(filename,
                                        max_file_size_kb=max_file_size_kb)

    def is_empty(self):
        return self._is_empty()

    def get_items(self, content_ids, seconds):
        query_result = self._get_by_ids(content_ids, process=json.loads)
        if not query_result:
            return {}

        current_time = datetime.now()
        result = {
            item[0]: item[2]
            for item in query_result
            if self.get_seconds_diff(item[1] or current_time) <= seconds
        }
        return result

    def get_item(self, content_id, seconds):
        content_id = str(content_id)
        query_result = self._get(content_id)
        if not query_result:
            return None

        current_time = datetime.now()
        if self.get_seconds_diff(query_result[1] or current_time) > seconds:
            return None

        return json.loads(query_result[0])

    def set_item(self, content_id, item):
        self._set(content_id, item)

    def set_items(self, items):
        self._set_all(items)

    def clear(self):
        self._clear()

    def remove(self, content_id):
        self._remove(content_id)

    def update(self, content_id, item):
        self._set(str(content_id), json.dumps(item))

    def _optimize_item_count(self):
        pass
