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
from atexit import register as atexit_register
from threading import RLock, Timer

from .. import logging
from ..compatibility import pickle, to_str
from ..utils.datetime import fromtimestamp, since_epoch
from ..utils.file_system import make_dirs
from ..utils.system_version import current_system_version


class StorageLock(object):
    def __init__(self):
        self._lock = RLock()
        self._num_accessing = 0
        self._num_waiting = 0

    if current_system_version.compatible(19):
        def __enter__(self):
            self._num_waiting += 1
            locked = not self._lock.acquire(timeout=3)
            self._num_waiting -= 1
            return locked
    else:
        def __enter__(self):
            self._num_waiting += 1
            locked = not self._lock.acquire(blocking=False)
            self._num_waiting -= 1
            return locked

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._lock.release()
        except RuntimeError:
            pass

    def accessing(self, start=False, done=False):
        num = self._num_accessing
        if start:
            num += 1
        elif done and num > 0:
            num -= 1
        self._num_accessing = num
        return num > 0

    def waiting(self):
        return self._num_waiting > 0


class ExistingDBConnection(object):
    def __init__(self, db):
        self._db = db

    def __enter__(self):
        db = self._db
        return db, db.cursor() if db else None

    def __exit__(self, *excinfo):
        pass


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
        'prune_invalid': (
            'DELETE'
            ' FROM {table}'
            ' WHERE key IS NULL;'
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
        self._lock = StorageLock()
        self._memory_store = getattr(self.__class__, '_memory_store', None)
        self._close_timer = None
        self._close_actions = False
        self._max_item_count = -1 if migrate else max_item_count
        self._max_file_size_kb = -1 if migrate else max_file_size_kb
        atexit_register(self._close, event='shutdown')

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

    def __del__(self):
        self._close(event='deleted')

    def __enter__(self):
        self._lock.accessing(start=True)

        close_timer = self._close_timer
        if close_timer:
            close_timer.cancel()

        db = self._db or self._open()
        try:
            cursor = db.cursor()
        except (AttributeError, sqlite3.ProgrammingError):
            db = self._open()
            cursor = db.cursor()
        cursor.arraysize = 100
        return db, cursor

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        close_timer = self._close_timer
        if close_timer:
            close_timer.cancel()

        if self._lock.accessing(done=True) or self._lock.waiting():
            return

        with self._lock as locked:
            if locked or self._close_timer:
                return
            close_timer = Timer(5, self._close)
            close_timer.start()
            self._close_timer = close_timer

    def _open(self):
        table_queries = []
        if not os.path.exists(self._filepath):
            make_dirs(os.path.dirname(self._filepath))
            table_queries.extend((
                self._sql['create_table'],
            ))
            self._base._table_updated = True

        for attempt in range(1, 4):
            try:
                db = sqlite3.connect(self._filepath,
                                     cached_statements=0,
                                     check_same_thread=False,
                                     isolation_level=None)
                break
            except (sqlite3.Error, sqlite3.OperationalError) as exc:
                if attempt < 3 and isinstance(exc, sqlite3.OperationalError):
                    self.log.warning('Attempt %d of 3',
                                     attempt,
                                     exc_info=True)
                    time.sleep(0.1)
                else:
                    self.log.exception('Failed')
                    return None
        else:
            return None

        cursor = db.cursor()

        queries = [
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
                    table_queries.extend((
                        'PRAGMA writable_schema = 1;',
                        self._sql['drop_old_table'],
                        'PRAGMA writable_schema = 0;',
                    ))
                break

        if table_queries:
            transaction_begin = len(queries) + 1
            queries.extend(('BEGIN IMMEDIATE;', 'COMMIT;', 'VACUUM;'))
            queries[transaction_begin:transaction_begin] = table_queries
        self._execute(cursor, queries)

        self._base._table_updated = True
        self._db = db
        return db

    def _close(self, commit=False, event=None):
        close_timer = self._close_timer
        if close_timer:
            close_timer.cancel()

        if self._lock.accessing() or self._lock.waiting():
            return False

        db = self._db
        if not db:
            if self._close_actions:
                db = self._open()
            else:
                return None

        if event or self._close_actions:
            if not event:
                queries = (
                    'BEGIN IMMEDIATE;',
                    self._set_many(items=None, defer=True, flush=True),
                    'COMMIT;',
                    'BEGIN IMMEDIATE;',
                    self._optimize_item_count(defer=True),
                    self._optimize_file_size(defer=True, db=db),
                    'COMMIT;',
                    'VACUUM;',
                )
            elif self._close_actions:
                queries = (
                    'BEGIN IMMEDIATE;',
                    self._set_many(items=None, defer=True, flush=True),
                    'COMMIT;',
                    'BEGIN IMMEDIATE;',
                    self._sql['prune_invalid'],
                    self._optimize_item_count(defer=True),
                    self._optimize_file_size(defer=True, db=db),
                    'COMMIT;',
                    'VACUUM;',
                    'PRAGMA optimize;',
                )
            else:
                queries = (
                    'BEGIN IMMEDIATE;',
                    self._sql['prune_invalid'],
                    'COMMIT;',
                    'VACUUM;',
                    'PRAGMA optimize;',
                )
            self._execute(db.cursor(), queries)

        # Not needed if using db as a context manager
        if commit:
            db.commit()

        if event:
            db.close()
            self._db = None
        self._close_actions = False
        self._close_timer = None
        return True

    def _execute(self, cursor, queries, values=(), many=False, script=False):
        result = []
        if not cursor:
            self.log.error_trace('Database not available')
            return result

        if isinstance(queries, (list, tuple)):
            if script:
                queries = ('\n'.join(queries),)
        else:
            queries = (queries,)

        for query in queries:
            if not query:
                continue
            if isinstance(query, tuple):
                query, _values, _many = query
            else:
                _many = many
                _values = values

            # Retry DB operation 3 times in case DB is locked or busy
            abort = False
            for attempt in range(1, 4):
                try:
                    if _many:
                        result = cursor.executemany(query, _values)
                    elif script:
                        result = cursor.executescript(query)
                    else:
                        result = cursor.execute(query, _values)
                    break
                except (sqlite3.Error, sqlite3.OperationalError) as exc:
                    if attempt >= 3:
                        abort = True
                    elif isinstance(exc, sqlite3.OperationalError):
                        time.sleep(0.1)
                    elif isinstance(exc, sqlite3.InterfaceError):
                        cursor = self._db.cursor()
                    else:
                        abort = True
                    if abort:
                        self.log.exception(('Failed',
                                            'Query:  {query!r}',
                                            'Values: {values!r}'),
                                           attempt=attempt,
                                           query=query,
                                           values=values)
                        break
                    self.log.warning_trace(('Attempt {attempt} of 3',
                                            'Query:  {query!r}',
                                            'Values: {values!r}'),
                                           attempt=attempt,
                                           query=query,
                                           values=values,
                                           exc_info=True)
            if abort:
                break
        return result

    def _optimize_file_size(self, defer=False, db=None):
        # do nothing - optimize only if max size limit has been set
        if self._max_file_size_kb <= 0:
            return False

        with ExistingDBConnection(db) if db else self as (db, cursor):
            result = self._execute(cursor, self._sql['get_total_data_size'])
            result = result.fetchone() if result else None
            result = result[0] if result else None
        if result is not None:
            size_kb = result // 1024
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
        with self as (db, cursor):
            self._execute(
                cursor,
                (
                    'BEGIN IMMEDIATE;',
                    query,
                    'COMMIT;',
                    'VACUUM;',
                ),
            )
        return None

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
        with self as (db, cursor):
            self._execute(
                cursor,
                (
                    'BEGIN IMMEDIATE;',
                    query,
                    'COMMIT;',
                    'VACUUM;',
                ),
            )
        return None

    def _set(self, item_id, item, defer=False, flush=False):
        memory_store = self._memory_store
        if memory_store is not None:
            key = to_str(item_id)
            if defer:
                memory_store[key] = (
                    item_id,
                    since_epoch(),
                    item,
                )
                self._close_actions = True
                return None
            if flush:
                memory_store.clear()
                return False
            if memory_store:
                memory_store[key] = (
                    item_id,
                    since_epoch(),
                    item,
                )
                return self._set_many(items=None)

        with self as (db, cursor), db:
            self._execute(
                cursor,
                self._sql['set'],
                self._encode(item_id, item),
            )
        return True

    def _set_many(self, items, flatten=False, defer=False, flush=False):
        memory_store = self._memory_store
        if memory_store is not None:
            if defer and not flush:
                now = since_epoch()
                memory_store.update({
                    to_str(item_id): (
                        item_id,
                        now,
                        item,
                    )
                    for item_id, item in items.items()
                })
                self._close_actions = True
                return None
            if flush and not defer:
                memory_store.clear()
                return False
            if memory_store:
                flush = True

        now = since_epoch()
        values = []

        if flatten:
            num_item = 0
            if items:
                values.extend([
                    part
                    for item_id, item in items.items()
                    for part in self._encode(item_id, item, now)
                ])
                num_item += len(items)
            if memory_store:
                values.extend([
                    part
                    for item_id, timestamp, item in memory_store.values()
                    for part in self._encode(item_id, item, timestamp)
                ])
                num_item += len(memory_store)
            query = self._sql['set_flat'].format(
                '(?,?,?,?),' * (num_item - 1) + '(?,?,?,?)'
            )
            many = False
        else:
            if items:
                values.extend([
                    self._encode(item_id, item, now)
                    for item_id, item in items.items()
                ])
            if memory_store:
                values.extend([
                    self._encode(item_id, item, timestamp)
                    for item_id, timestamp, item in memory_store.values()
                ])
            query = self._sql['set']
            many = True

        if flush and memory_store:
            memory_store.clear()

        if values:
            if defer:
                return query, values, many

            with self as (db, cursor):
                self._execute(
                    cursor,
                    (
                        'BEGIN IMMEDIATE;',
                        (query, values, many),
                        'COMMIT;',
                    ),
                )
                self._close_actions = True
        return None

    def _refresh(self, item_id, timestamp=None, defer=False):
        key = to_str(item_id)
        if not timestamp:
            timestamp = since_epoch()

        memory_store = self._memory_store
        if memory_store and key in memory_store:
            if defer:
                item = memory_store[key]
                memory_store[key] = (
                    item_id,
                    timestamp,
                    item[2],
                )
                self._close_actions = True
                return None
            del memory_store[key]

        values = (timestamp, key)
        with self as (db, cursor):
            self._execute(
                cursor,
                (
                    'BEGIN IMMEDIATE;',
                    (self._sql['refresh'], values, False),
                    'COMMIT;',
                ),
            )
        return True

    def _update(self, item_id, item, timestamp=None, defer=False):
        key = to_str(item_id)
        if not timestamp:
            timestamp = since_epoch()

        memory_store = self._memory_store
        if memory_store and key in memory_store:
            if defer:
                memory_store[key] = (
                    item_id,
                    timestamp,
                    item,
                )
                self._close_actions = True
                return None
            del memory_store[key]

        values = self._encode(item_id, item, timestamp, for_update=True)
        with self as (db, cursor):
            self._execute(
                cursor,
                (
                    'BEGIN IMMEDIATE;',
                    (self._sql['update'], values, False),
                    'COMMIT;',
                ),
            )
        return True

    def clear(self, defer=False):
        memory_store = self._memory_store
        if memory_store:
            memory_store.clear()

        query = self._sql['clear']
        if defer:
            return query

        with self as (db, cursor), db:
            self._execute(
                cursor,
                query,
            )
            self._close_actions = True
        return None

    def is_empty(self):
        with self as (db, cursor):
            result = self._execute(cursor, self._sql['is_empty'])
            for item in result:
                is_empty = item[0] == 0
                break
            else:
                is_empty = True
        return is_empty

    @staticmethod
    def _decode(obj, process=None, item=None):
        if item and item[3] is None:
            decoded_obj = obj
        else:
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
        key = to_str(item_id)
        memory_store = self._memory_store
        if memory_store and key in memory_store:
            item = memory_store[key]
            item = (
                item_id,
                item[1],  # timestamp from memory store item
                item[2],  # object from memory store item
                None,
            )
        else:
            with self as (db, cursor):
                result = self._execute(
                    cursor,
                    self._sql['get'],
                    (key,),
                )
                item = result.fetchone() if result else None
                if not item or not all(item):
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

    def _get_by_ids(self, item_ids=(), oldest_first=True, limit=-1,
                    wildcard=False, seconds=None, process=None,
                    as_dict=False, values_only=True, excluding=None):
        in_memory_result = None
        result = None

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
                memory_store = self._memory_store
                if memory_store:
                    in_memory_result = []
                    _item_ids = []
                    for item_id in item_ids:
                        key = to_str(item_id)
                        if key in memory_store:
                            item = memory_store[key]
                            in_memory_result.append((
                                item_id,
                                item[1],  # timestamp from memory store item
                                item[2],  # object from memory store item
                                None,
                            ))
                        else:
                            _item_ids.append(item_id)
                    item_ids = _item_ids

                if item_ids:
                    query = self._sql['get_by_key'].format(
                        '?,' * (len(item_ids) - 1) + '?'
                    )
                    item_ids = tuple(map(to_str, item_ids))
                else:
                    query = None

        if query:
            with self as (db, cursor):
                result = self._execute(cursor, query, item_ids)
                if result:
                    result = result.fetchall()

        if in_memory_result:
            if result:
                in_memory_result.extend(result)
            result = in_memory_result

        now = since_epoch()
        cut_off = now - seconds if seconds else 0

        if as_dict:
            if values_only:
                result = {
                    item[0]: self._decode(item[2], process, item)
                    for item in result if not cut_off or item[1] >= cut_off
                }
            else:
                result = {
                    item[0]: {
                        'age': now - item[1],
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
        key = to_str(item_id)
        memory_store = self._memory_store
        if memory_store and key in memory_store:
            del memory_store[key]

        with self as (db, cursor):
            self._execute(
                cursor,
                (
                    'BEGIN IMMEDIATE;',
                    (self._sql['remove'], (key,), False),
                    'COMMIT;',
                ),
            )
            self._close_actions = True
        return True

    def _remove_many(self, item_ids):
        memory_store = self._memory_store
        if memory_store:
            _item_ids = []
            for item_id in item_ids:
                key = to_str(item_id)
                if key in memory_store:
                    del memory_store[key]
                else:
                    _item_ids.append(item_id)
            item_ids = _item_ids

        num_ids = len(item_ids)
        query = self._sql['remove_by_key'].format('?,' * (num_ids - 1) + '?')
        with self as (db, cursor):
            self._execute(
                cursor,
                (
                    'BEGIN IMMEDIATE;',
                    (query, tuple(map(to_str, item_ids)), False),
                    'COMMIT;',
                ),
            )
            self._close_actions = True
        return True
