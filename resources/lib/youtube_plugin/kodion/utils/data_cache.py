# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2019 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from six import PY2
# noinspection PyPep8Naming
from six.moves import cPickle as pickle

import json
import sqlite3

from datetime import datetime, timedelta

from .storage import Storage
from .. import logger


class DataCache(Storage):
    ONE_MINUTE = 60
    ONE_HOUR = 60 * ONE_MINUTE
    ONE_DAY = 24 * ONE_HOUR
    ONE_WEEK = 7 * ONE_DAY
    ONE_MONTH = 4 * ONE_WEEK

    def __init__(self, filename, max_file_size_mb=5):
        max_file_size_kb = max_file_size_mb * 1024
        Storage.__init__(self, filename, max_file_size_kb=max_file_size_kb)

    def is_empty(self):
        return self._is_empty()

    def get_items(self, seconds, content_ids):
        def _decode(obj):
            if PY2:
                obj = str(obj)
            return pickle.loads(obj)

        current_time = datetime.now()
        placeholders = ','.join(['?' for _ in content_ids])
        keys = [str(item) for item in content_ids]
        query = 'SELECT * FROM %s WHERE key IN (%s)' % (self._table_name, placeholders)

        self._open()

        query_result = self._execute(False, query, keys)
        result = {}
        if query_result:
            for item in query_result:
                cached_time = item[1]
                if cached_time is None:
                    logger.log_error('Data Cache [get_items]: cached_time is None while getting {content_id}'.format(content_id=str(item[0])))
                    cached_time = current_time
                # this is so stupid, but we have the function 'total_seconds' only starting with python 2.7
                diff_seconds = self.get_seconds_diff(cached_time)
                if diff_seconds <= seconds:
                    result[str(item[0])] = json.loads(_decode(item[2]))

        self._close()
        return result

    def get_item(self, seconds, content_id):
        content_id = str(content_id)
        query_result = self._get(content_id)
        result = {}
        if query_result:
            current_time = datetime.now()
            cached_time = query_result[1]
            if cached_time is None:
                logger.log_error('Data Cache [get]: cached_time is None while getting {content_id}'.format(content_id=content_id))
                cached_time = current_time
            # this is so stupid, but we have the function 'total_seconds' only starting with python 2.7
            diff_seconds = self.get_seconds_diff(cached_time)
            if diff_seconds <= seconds:
                result[content_id] = json.loads(query_result[0])

        return result

    def set(self, content_id, item):
        self._set(content_id, item)

    def set_all(self, items):
        self._set_all(items)

    def clear(self):
        self._clear()

    def remove(self, content_id):
        self._remove(content_id)

    def update(self, content_id, item):
        self._set(str(content_id), json.dumps(item))

    def _optimize_item_count(self):
        pass

    def _set(self, content_id, item):
        def _encode(obj):
            return sqlite3.Binary(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))

        current_time = datetime.now() + timedelta(microseconds=1)
        query = 'REPLACE INTO %s (key,time,value) VALUES(?,?,?)' % self._table_name

        self._open()
        self._execute(True, query, values=[content_id, current_time, _encode(item)])
        self._close()

    def _set_all(self, items):
        def _encode(obj):
            return sqlite3.Binary(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))

        needs_commit = True
        current_time = datetime.now() + timedelta(microseconds=1)

        query = 'REPLACE INTO %s (key,time,value) VALUES(?,?,?)' % self._table_name

        self._open()

        for key in list(items.keys()):
            item = items[key]
            self._execute(needs_commit, query, values=[key, current_time, _encode(json.dumps(item))])
            needs_commit = False

        self._close()
