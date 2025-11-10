# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .storage import Storage


class RequestCache(Storage):
    _table_name = 'storage_v2'
    _table_updated = False
    _sql = {}

    _memory_store = {}

    def __init__(self, filepath, max_file_size_mb=20):
        max_file_size_kb = max_file_size_mb * 1024
        super(RequestCache, self).__init__(filepath,
                                           max_file_size_kb=max_file_size_kb)

    def get(self, request_id, seconds=None, as_dict=True, with_timestamp=True):
        result = self._get(request_id,
                           seconds=seconds,
                           as_dict=as_dict,
                           with_timestamp=with_timestamp)
        return result

    def set(self, request_id, response=None, etag=None, timestamp=None):
        if response:
            item = (etag, response)
            if timestamp:
                self._update(request_id, item, timestamp, defer=True)
            else:
                self._set(request_id, item, defer=True)
        else:
            self._refresh(request_id, timestamp, defer=True)

    def _optimize_item_count(self, limit=-1, defer=False):
        return False
