# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import datetime
import pickle
import sqlite3

from .storage import Storage


class PlaybackHistory(Storage):
    def __init__(self, filename):
        Storage.__init__(self, filename)

    def is_empty(self):
        return self._is_empty()

    def get_items(self, keys):
        def _decode(obj):
            return pickle.loads(obj)

        self._open()
        placeholders = ','.join(['?' for _ in keys])
        keys = [str(item) for item in keys]
        query = 'SELECT * FROM %s WHERE key IN (%s)' % (self._table_name, placeholders)
        query_result = self._execute(False, query, keys)
        result = {}
        if query_result:
            for item in query_result:
                values = _decode(item[2]).split(',')
                result[str(item[0])] = {'play_count': values[0], 'total_time': values[1],
                                        'played_time': values[2], 'played_percent': values[3],
                                        'last_played': item[1]}

        self._close()
        return result

    def get_item(self, key):
        key = str(key)
        query_result = self._get(key)
        result = {}
        if query_result:
            values = query_result[0].split(',')
            result[key] = {'play_count': values[0], 'total_time': values[1],
                           'played_time': values[2], 'played_percent': values[3],
                           'last_played': query_result[1]}
        return result

    def clear(self):
        self._clear()

    def remove(self, video_id):
        self._remove(video_id)

    def update(self, video_id, play_count, total_time, played_time, played_percent):
        item = ','.join([str(play_count), str(total_time), str(played_time), str(played_percent)])
        self._set(str(video_id), item)

    def _set(self, item_id, item):
        def _encode(obj):
            return sqlite3.Binary(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))

        self._open()
        now = datetime.datetime.now() + datetime.timedelta(microseconds=1)  # add 1 microsecond, required for dbapi2
        query = 'REPLACE INTO %s (key,time,value) VALUES(?,?,?)' % self._table_name
        self._execute(True, query, values=[item_id, now, _encode(item)])
        self._close()

    def _optimize_item_count(self):
        pass

    def _optimize_file_size(self):
        pass
