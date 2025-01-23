# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2019 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os
import pickle
import sqlite3
import time
from threading import Lock
from traceback import format_stack

from ..compatibility import to_str
from ..logger import Logger
from ..utils.datetime_parser import fromtimestamp, since_epoch
from ..utils.methods import make_dirs


class Storage(object):
    ONE_MINUTE = 60
    ONE_HOUR = 60 * ONE_MINUTE
    ONE_DAY = 24 * ONE_HOUR
    ONE_WEEK = 7 * ONE_DAY
    ONE_MONTH = 4 * ONE_WEEK

    _base = None
    _table_name = 'storage_v2'
    _table_updated = False

    _sql = {
        'clear': (
            'DELETE'
            ' FROM {table};'
        ),
        'create_table': (
            'CREATE TABLE'
            ' IF NOT EXISTS {table} ('
            '  key TEXT PRIMARY KEY,'
            '  timestamp REAL,'
            '  value BLOB,'
            '  size INTEGER'
            ' );'
        ),
        'drop_old_table': (
            'DELETE'
            ' FROM sqlite_master'
            ' WHERE type = "table"'
            ' and name IS NOT "{table}";'
        ),
        'get': (
            'SELECT *'
            ' FROM {table}'
            ' WHERE key = ?;'
        ),
        'get_by_key': (
            'SELECT *'
            ' FROM {table}'
            ' WHERE key in ({{0}});'
        ),
        'get_by_key_like': (
            'SELECT *'
            ' FROM {table}'
            ' WHERE key like ?'
            ' ORDER BY {order_col}'
            ' LIMIT {{0}};'
        ),
        'get_by_key_like_desc': (
            'SELECT *'
            ' FROM {table}'
            ' WHERE key like ?'
            ' ORDER BY {order_col} DESC'
            ' LIMIT {{0}};'
        ),
        'get_many': (
            'SELECT *'
            ' FROM {table}'
            ' ORDER BY {order_col}'
            ' LIMIT {{0}};'
        ),
        'get_many_desc': (
            'SELECT *'
            ' FROM {table}'
            ' ORDER BY {order_col} DESC'
            ' LIMIT {{0}};'
        ),
        'has_old_table': (
            'SELECT EXISTS ('
            ' SELECT 1'
            ' FROM sqlite_master'
            ' WHERE type = "table"'
            ' and name IS NOT "{table}"'
            ');'
        ),
        'is_empty': (
            'SELECT EXISTS ('
            ' SELECT 1'
            ' FROM {table}'
            ');'
        ),
        'prune_by_count': (
            'DELETE'
            ' FROM {table}'
            ' WHERE rowid IN ('
            '  SELECT rowid'
            '  FROM {table}'
            '  ORDER BY timestamp DESC'
            '  LIMIT {{0}}'
            '  OFFSET {{1}}'
            ' );'
        ),
        'prune_by_size': (
            'DELETE'
            ' FROM {table}'
            ' WHERE rowid IN ('
            '  SELECT rowid'
            '  FROM {table}'
            '  WHERE ('
            '   SELECT SUM(size)'
            '   FROM {table} AS _'
            '   WHERE timestamp<={table}.timestamp'
            '  ) <= {{0}}'
            ' );'
        ),
        'remove': (
            'DELETE'
            ' FROM {table}'
            ' WHERE key = ?;'
        ),
        'remove_by_key': (
            'DELETE'
            ' FROM {table}'
            ' WHERE key in ({{0}});'
        ),
        'set': (
            'REPLACE'
            ' INTO {table}'
            ' (key, timestamp, value, size)'
            ' VALUES (?,?,?,?);'
        ),
        'set_flat': (
            'REPLACE'
            ' INTO {table}'
            ' (key, timestamp, value, size)'
            ' VALUES {{0}};'
        ),
        'update': (
            'UPDATE'
            ' {table}'
            ' SET timestamp = ?, value = ?, size = ?'
            ' WHERE key = ?;'
        ),
    }

    def __init__(self,
                 filepath,
                 max_item_count=-1,
                 max_file_size_kb=-1,
                 migrate=False):
        self.uuid = filepath[1]
        self._filepath = os.path.join(*filepath)
        self._db = None
        self._cursor = None
        self._lock = Lock()
        self._max_item_count = -1 if migrate else max_item_count
        self._max_file_size_kb = -1 if migrate else max_file_size_kb

        if migrate:
            self._base = self
            self._sql = {}
            self._table_name = migrate
            self._table_updated = True
        else:
            self._base = self.__class__

        if migrate or not self._sql:
            statements = {
                name: sql.format(table=self._table_name,
                                 order_col='time' if migrate else 'timestamp')
                for name, sql in Storage._sql.items()
            }
            self._base._sql.update(statements)
        elif self._sql and '_partial' in self._sql:
            statements = {
                name: sql.format(table=self._table_name,
                                 order_col='timestamp')
                for name, sql in Storage._sql.items()
            }
            partial_statements = {
                name: sql.format(table=self._table_name,
                                 order_col='timestamp')
                for name, sql in self._base._sql.items()
                if not name.startswith('_')
            }
            statements.update(partial_statements)
            self._base._sql = statements

    def set_max_item_count(self, max_item_count):
        self._max_item_count = max_item_count

    def set_max_file_size_kb(self, max_file_size_kb):
        self._max_file_size_kb = max_file_size_kb

    def __enter__(self):
        self._lock.acquire()
        if not self._db or not self._cursor:
            self._open()
        return self._db, self._cursor

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self._close()
        self._lock.release()

    def _open(self):
        statements = []
        if not os.path.exists(self._filepath):
            make_dirs(os.path.dirname(self._filepath))
            statements.append(
                self._sql['create_table']
            )
            self._base._table_updated = True

        for _ in range(3):
            try:
                db = sqlite3.connect(self._filepath,
                                     check_same_thread=False,
                                     isolation_level=None)
                break
            except (sqlite3.Error, sqlite3.OperationalError) as exc:
                msg = ('SQLStorage._open - Error'
                       '\n\tException: {exc!r}'
                       '\n\tStack trace (most recent call last):\n{stack}'
                       .format(exc=exc,
                               stack=''.join(format_stack())))
                if isinstance(exc, sqlite3.OperationalError):
                    Logger.log_warning(msg)
                    time.sleep(0.1)
                else:
                    Logger.log_error(msg)
                    return False

        else:
            return False

        cursor = db.cursor()
        cursor.arraysize = 100

        sql_script = [
            'PRAGMA busy_timeout = 1000;',
            'PRAGMA read_uncommitted = TRUE;',
            'PRAGMA secure_delete = FALSE;',
            'PRAGMA synchronous = OFF;',
            'PRAGMA locking_mode = EXCLUSIVE;'
            'PRAGMA temp_store = MEMORY;',
            'PRAGMA mmap_size = 4096000;',
            'PRAGMA page_size = 4096;',
            'PRAGMA cache_size = 1000;',
            'PRAGMA journal_mode = PERSIST;',
        ]

        if not self._table_updated:
            for result in self._execute(cursor, self._sql['has_old_table']):
                if result[0] == 1:
                    statements.extend((
                        'PRAGMA writable_schema = 1;',
                        self._sql['drop_old_table'],
                        'PRAGMA writable_schema = 0;',
                    ))
                break

        if statements:
            transaction_begin = len(sql_script) + 1
            sql_script.extend(('BEGIN;', 'COMMIT;', 'VACUUM;'))
            sql_script[transaction_begin:transaction_begin] = statements
        self._execute(cursor, '\n'.join(sql_script), script=True)

        self._base._table_updated = True
        self._db = db
        self._cursor = cursor

    def _close(self):
        if self._cursor:
            self._execute(self._cursor, 'PRAGMA optimize')
            self._cursor.close()
            self._cursor = None
        if self._db:
            # Not needed if using self._db as a context manager
            # self._db.commit()
            self._db.close()
            self._db = None

    @staticmethod
    def _execute(cursor, query, values=None, many=False, script=False):
        if values is None:
            values = ()
        """
        Tests revealed that sqlite has problems to release the database in time
        This happens no so often, but just to be sure, we try at least 3 times
        to execute our statement.
        """
        for _ in range(3):
            try:
                if many:
                    return cursor.executemany(query, values)
                if script:
                    return cursor.executescript(query)
                return cursor.execute(query, values)
            except (sqlite3.Error, sqlite3.OperationalError) as exc:
                msg = ('SQLStorage._execute - Error'
                       '\n\tException: {exc!r}'
                       '\n\tStack trace (most recent call last):\n{stack}'
                       .format(exc=exc,
                               stack=''.join(format_stack())))
                if isinstance(exc, sqlite3.OperationalError):
                    Logger.log_warning(msg)
                    time.sleep(0.1)
                else:
                    Logger.log_error(msg)
                    return []
        return []

    def _optimize_file_size(self, defer=False):
        # do nothing - optimize only if max size limit has been set
        if self._max_file_size_kb <= 0:
            return False

        try:
            file_size_kb = (os.path.getsize(self._filepath) // 1024)
            if file_size_kb <= self._max_file_size_kb:
                return False
        except OSError:
            return False

        prune_size = 1024 * int(file_size_kb - self._max_file_size_kb / 2)
        query = self._sql['prune_by_size'].format(prune_size)
        if defer:
            return query
        with self as (db, cursor), db:
            self._execute(cursor, query)
            self._execute(cursor, 'VACUUM')
        return True

    def _optimize_item_count(self, limit=-1, defer=False):
        # do nothing - optimize only if max item limit has been set
        if self._max_item_count < 0:
            return False

        # clear db if max item count has been set to 0
        if not self._max_item_count:
            if not self.is_empty():
                return self.clear(defer)
            return False

        query = self._sql['prune_by_count'].format(
            limit, self._max_item_count
        )
        if defer:
            return query
        with self as (db, cursor), db:
            self._execute(cursor, query)
            self._execute(cursor, 'VACUUM')
        return True

    def _set(self, item_id, item, timestamp=None):
        values = self._encode(item_id, item, timestamp)
        optimize_query = self._optimize_item_count(1, defer=True)
        with self as (db, cursor), db:
            if optimize_query:
                self._execute(cursor, 'BEGIN')
                self._execute(cursor, optimize_query)
            self._execute(cursor, self._sql['set'], values=values)

    def _set_many(self, items, flatten=False):
        now = since_epoch()
        num_items = len(items)

        if flatten:
            values = [enc_part
                      for item in items.items()
                      for enc_part in self._encode(*item, timestamp=now)]
            query = self._sql['set_flat'].format(
                '(?,?,?,?),' * (num_items - 1) + '(?,?,?,?)'
            )
        else:
            values = [self._encode(*item, timestamp=now)
                      for item in items.items()]
            query = self._sql['set']

        optimize_query = self._optimize_item_count(num_items, defer=True)
        with self as (db, cursor), db:
            self._execute(cursor, 'BEGIN')
            if optimize_query:
                self._execute(cursor, optimize_query)
            self._execute(cursor, query, many=(not flatten), values=values)
        self._optimize_file_size()

    def _update(self, item_id, item, timestamp=None):
        values = self._encode(item_id, item, timestamp, for_update=True)
        with self as (db, cursor), db:
            self._execute(cursor, self._sql['update'], values=values)

    def clear(self, defer=False):
        query = self._sql['clear']
        if defer:
            return query
        with self as (db, cursor), db:
            self._execute(cursor, query)
            self._execute(cursor, 'VACUUM')
        return True

    def is_empty(self):
        with self as (db, cursor), db:
            result = self._execute(cursor, self._sql['is_empty'])
            for item in result:
                is_empty = item[0] == 0
                break
            else:
                is_empty = True
        return is_empty

    @staticmethod
    def _decode(obj, process=None, item=None):
        decoded_obj = pickle.loads(obj)
        if process:
            return process(decoded_obj, item)
        return decoded_obj

    @staticmethod
    def _encode(key, obj, timestamp=None, for_update=False):
        timestamp = timestamp or since_epoch()
        blob = sqlite3.Binary(pickle.dumps(
            obj, protocol=pickle.HIGHEST_PROTOCOL
        ))
        size = getattr(blob, 'nbytes', None)
        if not size:
            size = int(memoryview(blob).itemsize) * len(blob)
        if key:
            if for_update:
                return timestamp, blob, size, to_str(key)
            return to_str(key), timestamp, blob, size
        return timestamp, blob, size

    def _get(self, item_id, process=None, seconds=None, as_dict=False):
        with self as (db, cursor), db:
            result = self._execute(cursor, self._sql['get'], [to_str(item_id)])
            item = result.fetchone() if result else None
            if not item:
                return None
        cut_off = since_epoch() - seconds if seconds else 0
        if not cut_off or item[1] >= cut_off:
            if as_dict:
                return {
                    'item_id': item_id,
                    'age': since_epoch() - item[1],
                    'value': self._decode(item[2], process, item),
                }
            return self._decode(item[2], process, item)
        return None

    def _get_by_ids(self, item_ids=None, oldest_first=True, limit=-1,
                    wildcard=False, seconds=None, process=None,
                    as_dict=False, values_only=True):
        if not item_ids:
            if oldest_first:
                query = self._sql['get_many']
            else:
                query = self._sql['get_many_desc']
            query = query.format(limit)
        elif wildcard:
            if oldest_first:
                query = self._sql['get_by_key_like']
            else:
                query = self._sql['get_by_key_like_desc']
            query = query.format(limit)
        else:
            num_ids = len(item_ids)
            query = self._sql['get_by_key'].format('?,' * (num_ids - 1) + '?')
            item_ids = tuple(item_ids)

        epoch = since_epoch()
        cut_off = epoch - seconds if seconds else 0
        with self as (db, cursor), db:
            result = self._execute(cursor, query, item_ids)
            if as_dict:
                if values_only:
                    result = {
                        item[0]: self._decode(item[2], process, item)
                        for item in result if not cut_off or item[1] >= cut_off
                    }
                else:
                    result = {
                        item[0]: {
                            'age': epoch - item[1],
                            'value': self._decode(item[2], process, item),
                        }
                        for item in result if not cut_off or item[1] >= cut_off
                    }
            elif values_only:
                result = [
                    self._decode(item[2], process, item)
                    for item in result if not cut_off or item[1] >= cut_off
                ]
            else:
                result = [
                    (item[0],
                     fromtimestamp(item[1]),
                     self._decode(item[2], process, item))
                    for item in result if not cut_off or item[1] >= cut_off
                ]
        return result

    def _remove(self, item_id):
        with self as (db, cursor), db:
            self._execute(cursor, self._sql['remove'], [item_id])

    def _remove_many(self, item_ids):
        num_ids = len(item_ids)
        query = self._sql['remove_by_key'].format('?,' * (num_ids - 1) + '?')
        with self as (db, cursor), db:
            self._execute(cursor, query, tuple(item_ids))
            self._execute(cursor, 'VACUUM')
