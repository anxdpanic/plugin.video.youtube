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

    def _add_last_played(self, value, item):
        value['last_played'] = self._convert_timestamp(item[1])
        return value

    def get_items(self, keys=None):
        result = self._get_by_ids(keys,
                                  oldest_first=False,
                                  process=self._add_last_played,
                                  as_dict=True)
        return result

    def get_item(self, key):
        result = self._get(key, process=self._add_last_played)
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
