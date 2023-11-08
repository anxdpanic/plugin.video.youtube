# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from .storage import Storage


class PlaybackHistory(Storage):
    def __init__(self, filename):
        super(PlaybackHistory, self).__init__(filename)

    def is_empty(self):
        return self._is_empty()

    @staticmethod
    def _process_item(item):
        return item.split(',')

    def get_items(self, keys):
        query_result = self._get_by_ids(keys, process=self._process_item)
        if not query_result:
            return {}

        result = {
            item[0]: {
                'play_count': int(item[2][0]),
                'total_time': float(item[2][1]),
                'played_time': float(item[2][2]),
                'played_percent': int(item[2][3]),
                'last_played': str(item[1]),
            } for item in query_result
        }
        return result

    def get_item(self, key):
        query_result = self._get(key)
        if not query_result:
            return {}

        values = query_result[0].split(',')
        result = {key: {
            'play_count': int(values[0]),
            'total_time': float(values[1]),
            'played_time': float(values[2]),
            'played_percent': int(values[3]),
            'last_played': str(query_result[1]),
        }}
        return result

    def clear(self):
        self._clear()

    def remove(self, video_id):
        self._remove(video_id)

    def update(self, video_id, play_count, total_time, played_time, played_percent):
        item = ','.join([str(play_count), str(total_time), str(played_time), str(played_percent)])
        self._set(str(video_id), item)

    def _optimize_item_count(self):
        pass

    def _optimize_file_size(self):
        pass
