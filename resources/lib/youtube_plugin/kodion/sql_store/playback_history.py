# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .storage import Storage


class PlaybackHistory(Storage):
    def __init__(self, filename):
        super(PlaybackHistory, self).__init__(filename)

    def is_empty(self):
        return self._is_empty()

    def get_items(self, keys):
        query_result = self._get_by_ids(keys)
        if not query_result:
            return {}

        result = {
            item[0]: dict(item[2], last_played=item[1])
            for item in query_result
        }
        return result

    def get_item(self, key):
        query_result = self._get(key)
        if not query_result:
            return {}

        result = {key: dict(query_result[1], last_played=query_result[0])}
        return result

    def clear(self):
        self._clear()

    def remove(self, video_id):
        self._remove(video_id)

    def update(self, video_id, play_data):
        self._set(video_id, play_data)

    def _optimize_item_count(self):
        pass

    def _optimize_file_size(self):
        pass
