# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os
import sqlite3
import time
from threading import RLock, Timer

from .. import logging
from ..compatibility import pickle, to_str
from ..utils.datetime_parser import fromtimestamp, since_epoch
from ..utils.file_system import make_dirs


class StorageLock(object):
    def __init__(self):
        self._lock = RLock()
        self._num_waiting = 0

    def __enter__(self):
        self._num_waiting += 1
        self._lock.acquire()
        self._num_waiting -= 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()

    def waiting(self):
        return self._num_waiting > 0


class Storage(object):
    log = logging.getLogger(__name__)

    ONE_MINUTE = 60
    ONE_HOUR = 60 * ONE_MINUTE
    ONE_DAY = 24 * ONE_HOUR
    ONE_WEEK = 7 * ONE_DAY
    ONE_MONTH = 30 * ONE_DAY

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
        'get_by_key_excluding': (
            'SELECT *'
            ' FROM {table}'
            ' WHERE key in ({{0}})'
            ' AND key not in ({{1}});'
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
        'get_total_data_size': (
            'SELECT SUM(size)'
            'FROM {table}'
        ),
        'get_database_size': (
            'SELECT page_size * page_count'
            ' FROM ('
            '  pragma_page_count(),'
            '  pragma_page_size()'
            ');'
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
        'refresh': (
            'UPDATE'
            ' {table}'
            ' SET timestamp = ?'
            ' WHERE key = ?;'
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
        self._lock = StorageLock()
        self._close_timer = None
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
            statements = [
                (name, sql.format(table=self._table_name,
                                  order_col='time' if migrate else 'timestamp'))
                for name, sql in Storage._sql.items()
            ]
            self._base._sql.update(statements)
        elif self._sql and '_partial' in self._sql:
            statements = {
                name: sql.format(table=self._table_name,
                                 order_col='timestamp')
                for name, sql in Storage._sql.items()
            }
            partial_statements = [
                (name, sql.format(table=self._table_name,
                                  order_col='timestamp'))
                for name, sql in self._base._sql.items()
                if not name.startswith('_')
            ]
            statements.update(partial_statements)
            self._base._sql = statements

    def set_max_item_count(self, max_item_count):
        self._max_item_count = max_item_count

    def set_max_file_size_kb(self, max_file_size_kb):
        self._max_file_size_kb = max_file_size_kb

    def __enter__(self):
        close_timer = self._close_timer
        if close_timer:
            close_timer.cancel()
            self._close_timer = None
        if self._db and self._cursor:
            return self._db, self._cursor
        return self._open()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        close_timer = self._close_timer
        if close_timer:
            close_timer.cancel()
        if self._lock.waiting():
            self._close_timer = None
            return
        close_timer = Timer(5, self._close)
        close_timer.daemon = True
        close_timer.start()
        self._close_timer = close_timer

    def _open(self):
        statements = []
        if not os.path.exists(self._filepath):
            make_dirs(os.path.dirname(self._filepath))
            statements.extend((
                self._sql['create_table'],
            ))
            self._base._table_updated = True

        for attempt in range(1, 4):
            try:
                db = sqlite3.connect(self._filepath,
                                     check_same_thread=False,
                                     isolation_level=None)
                break
            except (sqlite3.Error, sqlite3.OperationalError) as exc:
                if attempt < 3 and isinstance(exc, sqlite3.OperationalError):
                    self.log.warning('Retry, attempt %d of 3',
                                     attempt,
                                     exc_info=True)
                    time.sleep(0.1)
                else:
                    self.log.exception('Failed')
                    return None, None

        else:
            return None, None

        cursor = db.cursor()
        cursor.arraysize = 100

        sql_script = [
            'PRAGMA busy_timeout = 1000;',
            'PRAGMA read_uncommitted = TRUE;',
            'PRAGMA secure_delete = FALSE;',
            # 'PRAGMA synchronous = OFF;',
            'PRAGMA synchronous = NORMAL;',
            # 'PRAGMA locking_mode = EXCLUSIVE;'
            'PRAGMA temp_store = MEMORY;',
            'PRAGMA mmap_size = -1;',
            'PRAGMA page_size = 4096;',
            'PRAGMA cache_size = -2000;',
            # 'PRAGMA journal_mode = TRUNCATE;',
            # 'PRAGMA journal_mode = PERSIST;',
            # 'PRAGMA journal_mode = MEMORY;',
            'PRAGMA journal_mode = WAL;',
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
        return db, cursor

    def _close(self):
        cursor = self._cursor
        if cursor:
            self._execute(cursor, 'PRAGMA optimize')
            cursor.close()
            self._cursor = None
        db = self._db
        if db:
            # Not needed if using db as a context manager
            # db.commit()
            db.close()
            self._db = None

    def _execute(self, cursor, query, values=None, many=False, script=False):
        if not cursor:
            self.log.error_trace('Database not available')
            return []
        if values is None:
            values = ()
        """
        Tests revealed that sqlite has problems to release the database in time
        This happens no so often, but just to be sure, we try at least 3 times
        to execute our statement.
        """
        for attempt in range(1, 4):
            try:
                if many:
                    return cursor.executemany(query, values)
                if script:
                    return cursor.executescript(query)
                return cursor.execute(query, values)
            except (sqlite3.Error, sqlite3.OperationalError) as exc:
                if attempt < 3 and isinstance(exc, sqlite3.OperationalError):
                    self.log.warning('Retry, attempt %d of 3',
                                     attempt,
                                     exc_info=True)
                    time.sleep(0.1)
                else:
                    self.log.exception('Failed')
                    return []
        return []

    def _optimize_file_size(self, defer=False):
        # do nothing - optimize only if max size limit has been set
        if self._max_file_size_kb <= 0:
            return False

        with self._lock, self as (db, cursor), db:
            result = self._execute(cursor, self._sql['get_total_data_size'])

        if result:
            size_kb = result.fetchone()[0] // 1024
        else:
            try:
                size_kb = (os.path.getsize(self._filepath) // 1024)
            except OSError:
                return False

        if size_kb <= self._max_file_size_kb:
            return False

        prune_size = 1024 * int(size_kb - self._max_file_size_kb / 2)
        query = self._sql['prune_by_size'].format(prune_size)
        if defer:
            return query
        with self._lock, self as (db, cursor), db:
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
        with self._lock, self as (db, cursor), db:
            self._execute(cursor, query)
            self._execute(cursor, 'VACUUM')
        return True

    def _set(self, item_id, item, timestamp=None):
        values = self._encode(item_id, item, timestamp)
        optimize_query = self._optimize_item_count(1, defer=True)
        with self._lock, self as (db, cursor), db:
            self._execute(cursor, 'BEGIN')
            if optimize_query:
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
        with self._lock, self as (db, cursor), db:
            self._execute(cursor, 'BEGIN')
            if optimize_query:
                self._execute(cursor, optimize_query)
            self._execute(cursor, query, many=(not flatten), values=values)
            self._execute(cursor, 'COMMIT')
        self._optimize_file_size()

    def _refresh(self, item_id, timestamp=None):
        values = (timestamp or since_epoch(), to_str(item_id))
        with self._lock, self as (db, cursor), db:
            self._execute(cursor, self._sql['refresh'], values=values)

    def _update(self, item_id, item, timestamp=None):
        values = self._encode(item_id, item, timestamp, for_update=True)
        with self._lock, self as (db, cursor), db:
            self._execute(cursor, self._sql['update'], values=values)

    def clear(self, defer=False):
        query = self._sql['clear']
        if defer:
            return query
        with self._lock, self as (db, cursor), db:
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
            obj, protocol=-1
        ))
        size = getattr(blob, 'nbytes', None)
        if not size:
            size = int(memoryview(blob).itemsize) * len(blob)
        if key:
            if for_update:
                return timestamp, blob, size, to_str(key)
            return to_str(key), timestamp, blob, size
        return timestamp, blob, size

    def _get(self,
             item_id,
             process=None,
             seconds=None,
             as_dict=False,
             with_timestamp=False):
        with self._lock, self as (db, cursor), db:
            result = self._execute(cursor, self._sql['get'], [to_str(item_id)])
            item = result.fetchone() if result else None
            if not item:
                return None
        cut_off = since_epoch() - seconds if seconds else 0
        if not cut_off or item[1] >= cut_off:
            if as_dict:
                output = {
                    'item_id': item_id,
                    'age': since_epoch() - item[1],
                    'value': self._decode(item[2], process, item),
                }
                if with_timestamp:
                    output['timestamp'] = item[1]
                return output
            return self._decode(item[2], process, item)
        return None

    def _get_by_ids(self, item_ids=None, oldest_first=True, limit=-1,
                    wildcard=False, seconds=None, process=None,
                    as_dict=False, values_only=True, excluding=None):
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
            if excluding:
                query = self._sql['get_by_key_excluding'].format(
                    '?,' * (len(item_ids) - 1) + '?',
                    '?,' * (len(excluding) - 1) + '?',
                )
                item_ids = tuple(item_ids) + tuple(excluding)
            else:
                query = self._sql['get_by_key'].format(
                    '?,' * (len(item_ids) - 1) + '?'
                )
                item_ids = tuple(item_ids)

        epoch = since_epoch()
        cut_off = epoch - seconds if seconds else 0
        with self._lock, self as (db, cursor), db:
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
        with self._lock, self as (db, cursor), db:
            self._execute(cursor, self._sql['remove'], [item_id])

    def _remove_many(self, item_ids):
        num_ids = len(item_ids)
        query = self._sql['remove_by_key'].format('?,' * (num_ids - 1) + '?')
        with self._lock, self as (db, cursor), db:
            self._execute(cursor, query, tuple(item_ids))
            self._execute(cursor, 'VACUUM')
