# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2019 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import os
import pickle
import sqlite3
import time
from datetime import datetime
from traceback import print_exc

from ..logger import log_error
from ..utils.datetime_parser import since_epoch


class Storage(object):
    ONE_MINUTE = 60
    ONE_HOUR = 60 * ONE_MINUTE
    ONE_DAY = 24 * ONE_HOUR
    ONE_WEEK = 7 * ONE_DAY
    ONE_MONTH = 4 * ONE_WEEK

    _key = str('key')
    _time = str('time')
    _value = str('value')
    _timestamp = str('timestamp')

    _table_name = 'storage'
    _clear_query = 'DELETE FROM %s' % _table_name
    _create_table_query = 'CREATE TABLE IF NOT EXISTS %s (key TEXT PRIMARY KEY, time TIMESTAMP, value BLOB)' % _table_name
    _get_query = 'SELECT * FROM %s WHERE key = ?' % _table_name
    _get_by_query = 'SELECT * FROM %s WHERE key in ({0})' % _table_name
    _get_all_asc_query = 'SELECT * FROM %s ORDER BY time ASC LIMIT {0}' % _table_name
    _get_all_desc_query = 'SELECT * FROM %s ORDER BY time DESC LIMIT {0}' % _table_name
    _is_empty_query = 'SELECT EXISTS(SELECT 1 FROM %s LIMIT 1)' % _table_name
    _optimize_item_query = 'SELECT key FROM %s ORDER BY time DESC LIMIT -1 OFFSET {0}' % _table_name
    _remove_query = 'DELETE FROM %s WHERE key = ?' % _table_name
    _remove_all_query = 'DELETE FROM %s WHERE key in ({0})' % _table_name
    _set_query = 'REPLACE INTO %s (key, time, value) VALUES(?, ?, ?)' % _table_name

    def __init__(self, filename, max_item_count=-1, max_file_size_kb=-1):
        self._filename = filename
        if not self._filename.endswith('.sqlite'):
            self._filename = ''.join([self._filename, '.sqlite'])
        self._db = None
        self._cursor = None
        self._max_item_count = max_item_count
        self._max_file_size_kb = max_file_size_kb

        self._table_created = False
        self._needs_commit = False

        sqlite3.register_converter(self._timestamp, self._convert_timestamp)

    def set_max_item_count(self, max_item_count):
        self._max_item_count = max_item_count

    def set_max_file_size_kb(self, max_file_size_kb):
        self._max_file_size_kb = max_file_size_kb

    def __del__(self):
        self._close()

    def _open(self):
        if self._db:
            return

        self._optimize_file_size()

        path = os.path.dirname(self._filename)
        if not os.path.exists(path):
            os.makedirs(path)

        db = sqlite3.connect(self._filename, check_same_thread=False,
                             detect_types=sqlite3.PARSE_DECLTYPES,
                             timeout=1, isolation_level=None)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        # cursor.execute('PRAGMA journal_mode=MEMORY')
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA busy_timeout=20000')
        cursor.execute('PRAGMA read_uncommitted=TRUE')
        cursor.execute('PRAGMA temp_store=MEMORY')
        # cursor.execute('PRAGMA synchronous=OFF')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.arraysize = 100
        self._db = db
        self._cursor = cursor
        self._create_table()

    def _execute(self, needs_commit, query, values=None, many=False):
        if values is None:
            values = ()
        if not self._needs_commit and needs_commit:
            self._needs_commit = True
            self._cursor.execute('BEGIN')

        """
        Tests revealed that sqlite has problems to release the database in time
        This happens no so often, but just to be sure, we try at least 3 times
        to execute our statement.
        """
        for _ in range(3):
            try:
                if many:
                    return self._cursor.executemany(query, values)
                return self._cursor.execute(query, values)
            except TypeError:
                return []
            except:
                time.sleep(0.1)
        return []

    def _close(self):
        if self._db:
            self._sync()
            self._db.commit()
            self._cursor.close()
            self._cursor = None
            self._db.close()
            self._db = None

    def _optimize_file_size(self):
        # do nothing - only we have given a size
        if self._max_file_size_kb <= 0:
            return

        # do nothing - only if this folder exists
        path = os.path.dirname(self._filename)
        if not os.path.exists(path):
            return

        if not os.path.exists(self._filename):
            return

        try:
            file_size_kb = (os.path.getsize(self._filename) // 1024)
            if file_size_kb >= self._max_file_size_kb:
                os.remove(self._filename)
        except OSError:
            pass

    def _create_table(self):
        if self._table_created:
            return
        self._execute(True, self._create_table_query)
        self._table_created = True

    def _sync(self):
        if not self._needs_commit:
            return None
        self._needs_commit = False
        return self._execute(False, 'COMMIT')

    def _set(self, item_id, item):
        # add 1 microsecond, required for dbapi2
        now = since_epoch(datetime.now()) + 0.000001
        self._open()
        self._execute(True, self._set_query, values=[str(item_id),
                                                     now,
                                                     self._encode(item)])
        self._close()
        self._optimize_item_count()

    def _set_all(self, items):
        # add 1 microsecond, required for dbapi2
        now = since_epoch(datetime.now()) + 0.000001
        self._open()
        self._execute(True, self._set_query,
                      values=[(str(key), now, self._encode(item))
                              for key, item in items.items()],
                      many=True)
        self._close()
        self._optimize_item_count()

    def _optimize_item_count(self):
        if not self._max_item_count:
            if not self._is_empty():
                self._clear()
            return
        if self._max_item_count < 0:
            return
        query = self._optimize_item_query.format(self._max_item_count)
        self._open()
        item_ids = self._execute(False, query)
        key = self._key
        item_ids = [item_id[key] for item_id in item_ids]
        if item_ids:
            self._remove_all(item_ids)
        self._close()

    def _clear(self):
        self._open()
        self._execute(True, self._clear_query)
        self._create_table()
        self._sync()
        self._execute(False, 'VACUUM')
        self._close()

    def _is_empty(self):
        self._open()
        result = self._execute(False, self._is_empty_query)
        for item in result:
            is_empty = item[0] == 0
            break
        else:
            is_empty = True
        self._close()
        return is_empty

    @staticmethod
    def _decode(obj, process=None):
        decoded_obj = pickle.loads(obj)
        if process:
            return process(decoded_obj)
        return json.loads(decoded_obj)

    @staticmethod
    def _encode(obj):
        return sqlite3.Binary(pickle.dumps(
            json.dumps(obj, ensure_ascii=False),
            protocol=pickle.HIGHEST_PROTOCOL
        ))

    def _get(self, item_id):
        self._open()
        result = self._execute(False, self._get_query, [item_id])
        if result:
            result = result.fetchone()
        self._close()
        if result:
            return self._decode(result[self._value]), result[self._time]
        return None

    def _get_by_ids(self, item_ids=None, oldest_first=True, limit=-1,
                    process=None):
        if not item_ids:
            if oldest_first:
                query = self._get_all_asc_query
            else:
                query = self._get_all_desc_query
            query = query.format(limit)
        else:
            num_ids = len(item_ids)
            query = self._get_by_query.format(('?,' * (num_ids - 1)) + '?')
            item_ids = tuple(item_ids)

        self._open()
        result = self._execute(False, query, item_ids)
        key = self._key
        time = self._time
        value = self._value
        result = [
            (item[key], item[time], self._decode(item[value], process))
            for item in result
        ]
        self._close()
        return result

    def _remove(self, item_id):
        self._open()
        self._execute(True, self._remove_query, [item_id])

    def _remove_all(self, item_ids):
        num_ids = len(item_ids)
        query = self._remove_all_query.format(('?,' * (num_ids - 1)) + '?')
        self._open()
        self._execute(True, query, tuple(item_ids))

    @staticmethod
    def strptime(stamp, stamp_fmt):
        # noinspection PyUnresolvedReferences
        import _strptime
        try:
            time.strptime('01 01 2012', '%d %m %Y')  # dummy call
        except:
            pass
        return time.strptime(stamp, stamp_fmt)

    @classmethod
    def _convert_timestamp(cls, val):
        val = val.decode('utf-8')
        if '-' in val or ':' in val:
            return cls._parse_datetime_string(val)
        return datetime.fromtimestamp(float(val))

    @classmethod
    def _parse_datetime_string(cls, current_stamp):
        for stamp_format in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S']:
            try:
                stamp_datetime = datetime(
                    *(cls.strptime(current_stamp, stamp_format)[0:6])
                )
                break
            except ValueError:  # current_stamp has no microseconds
                continue
            except TypeError:
                log_error('Exception while parsing timestamp:\n'
                          'current_stamp |{cs}|{cst}|\n'
                          'stamp_format |{sf}|{sft}|\n{tb}'
                          .format(cs=current_stamp,
                                  cst=type(current_stamp),
                                  sf=stamp_format,
                                  sft=type(stamp_format),
                                  tb=print_exc()))
        else:
            return None
        return stamp_datetime

    def get_seconds_diff(self, current_stamp):
        if not current_stamp:
            return 86400  # 24 hrs

        current_datetime = datetime.now()
        if isinstance(current_stamp, datetime):
            time_delta = current_datetime - current_stamp
            return time_delta.total_seconds()

        if isinstance(current_stamp, (float, int)):
            return since_epoch(current_datetime) - current_stamp

        stamp_datetime = self._parse_datetime_string(current_stamp)
        if not stamp_datetime:
            return 604800  # one week
        time_delta = current_datetime - stamp_datetime
        return time_delta.total_seconds()
