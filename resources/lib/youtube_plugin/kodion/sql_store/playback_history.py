# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .storage import Storage, fromtimestamp


class PlaybackHistory(Storage):
    _table_name = 'storage_v2'
    _table_created = False
    _table_updated = False
    _sql = {}

    def __init__(self, filepath, migrate=False):
        super(PlaybackHistory, self).__init__(filepath, migrate=migrate)

    @staticmethod
    def _add_last_played(value, item):
        value['last_played'] = fromtimestamp(item[1])
        return value

    def get_items(self, keys=None, limit=-1, process=None):
        if process is None:
            process = self._add_last_played
        result = self._get_by_ids(keys,
                                  oldest_first=False,
                                  process=process,
                                  as_dict=True,
                                  limit=limit)
        return result

    def get_item(self, key):
        result = self._get(key, process=self._add_last_played)
        return result

    def remove(self, video_id):
        self._remove(video_id)

    def update(self, video_id, play_data, timestamp=None):
        self._set(video_id, play_data, timestamp)

    def _optimize_item_count(self, limit=-1, defer=False):
        return False

    def _optimize_file_size(self, limit=-1, defer=False):
        return False
