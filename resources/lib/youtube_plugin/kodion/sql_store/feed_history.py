# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .storage import Storage


class FeedHistory(Storage):
    _table_name = 'storage_v2'
    _table_updated = False
    _sql = {}

    def __init__(self, filepath):
        super(FeedHistory, self).__init__(filepath)

    def get_items(self, content_ids, seconds=None):
        result = self._get_by_ids(content_ids,
                                  seconds=seconds,
                                  as_dict=True,
                                  values_only=False)
        return result

    def get_item(self, content_id, seconds=None):
        result = self._get(content_id, seconds=seconds, as_dict=True)
        return result

    def set_items(self, items):
        self._set_many(items)

    def _optimize_item_count(self, limit=-1, defer=False):
        return False

    def _optimize_file_size(self, limit=-1, defer=False):
        return False
