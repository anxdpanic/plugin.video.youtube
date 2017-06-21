__author__ = 'bromix'

import datetime
import os
import sqlite3
import time

try:
    import cPickle as pickle
except ImportError:
    import pickle


class Storage(object):
    def __init__(self, filename, max_item_count=1000, max_file_size_kb=-1):
        self._table_name = 'storage'
        self._filename = filename
        if not self._filename.endswith('.sqlite'):
            self._filename += '.sqlite'
        self._file = None
        self._cursor = None
        self._max_item_count = max_item_count
        self._max_file_size_kb = max_file_size_kb

        self._table_created = False
        self._needs_commit = False

    def set_max_item_count(self, max_item_count):
        self._max_item_count = max_item_count

    def set_max_file_size_kb(self, max_file_size_kb):
        self._max_file_size_kb = max_file_size_kb

    def __del__(self):
        self._close()

    def _open(self):
        if self._file is None:
            self._optimize_file_size()

            path = os.path.dirname(self._filename)
            if not os.path.exists(path):
                os.makedirs(path)

            self._file = sqlite3.connect(self._filename, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES,
                                         timeout=1)
            self._file.isolation_level = None
            self._cursor = self._file.cursor()
            self._cursor.execute('PRAGMA journal_mode=MEMORY')
            self._cursor.execute('PRAGMA busy_timeout=20000')
            # self._cursor.execute('PRAGMA synchronous=OFF')
            self._create_table()

    def _execute(self, needs_commit, query, values=[]):
        if not self._needs_commit and needs_commit:
            self._needs_commit = True
            self._cursor.execute('BEGIN')

        """
        Tests revealed that sqlite has problems to release the database in time. This happens no so often, but just to
        be sure, we try at least 5 times to execute out statement.
        """
        for tries in range(5):
            try:
                return self._cursor.execute(query, values)
            except TypeError:
                return None
            except:
                time.sleep(2)
        else:
            return None

    def _close(self):
        if self._file is not None:
            self.sync()
            self._file.commit()
            self._cursor.close()
            self._cursor = None
            self._file.close()
            self._file = None

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

        file_size_kb = os.path.getsize(self._filename) / 1024
        if file_size_kb >= self._max_file_size_kb:
            os.remove(self._filename)

    def _create_table(self):
        self._open()
        if not self._table_created:
            query = 'CREATE TABLE IF NOT EXISTS %s (key TEXT PRIMARY KEY, time TIMESTAMP, value BLOB)' % self._table_name
            self._execute(True, query)
            self._table_created = True

    def sync(self):
        if self._cursor is not None and self._needs_commit:
            self._needs_commit = False
            return self._execute(False, 'COMMIT')

    def _set(self, item_id, item):
        def _encode(obj):
            return sqlite3.Binary(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))

        self._open()
        now = datetime.datetime.now()
        if not now.microsecond:  # now is to the second
            now += datetime.timedelta(microseconds=1)  # add 1 microsecond, required for dbapi2
        query = 'REPLACE INTO %s (key,time,value) VALUES(?,?,?)' % self._table_name
        self._execute(True, query, values=[item_id, now, _encode(item)])
        self._optimize_item_count()
        self._close()

    def _optimize_item_count(self):
        self._open()
        query = 'SELECT key FROM %s ORDER BY time DESC LIMIT -1 OFFSET %d' % (self._table_name, self._max_item_count)
        result = self._execute(False, query)
        if result is not None:
            for item in result:
                self._remove(item[0])
        self._close()

    def _clear(self):
        self._open()
        query = 'DELETE FROM %s' % self._table_name
        self._execute(True, query)
        self._create_table()
        self._close()

    def _is_empty(self):
        self._open()
        query = 'SELECT exists(SELECT 1 FROM %s LIMIT 1);' % self._table_name
        result = self._execute(False, query)
        is_empty = True
        if result is not None:
            for item in result:
                is_empty = item[0] == 0
                break
        self._close()
        return is_empty

    def _get_ids(self, oldest_first=True):
        self._open()
        # self.sync()
        query = 'SELECT key FROM %s' % self._table_name
        if oldest_first:
            query = '%s ORDER BY time ASC' % query
        else:
            query = '%s ORDER BY time DESC' % query

        query_result = self._execute(False, query)

        result = []
        if query_result:
            for item in query_result:
                result.append(item[0])

        self._close()
        return result

    def _get(self, item_id):
        def _decode(obj):
            return pickle.loads(bytes(obj))

        self._open()
        query = 'SELECT time, value FROM %s WHERE key=?' % self._table_name
        result = self._execute(False, query, [item_id])
        if result is None:
            self._close()
            return None

        item = result.fetchone()
        if item is None:
            self._close()
            return None

        self._close()
        return _decode(item[1]), item[0]

    def _remove(self, item_id):
        self._open()
        query = 'DELETE FROM %s WHERE key = ?' % self._table_name
        self._execute(True, query, [item_id])
