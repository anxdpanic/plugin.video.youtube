# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2019 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from functools import partial
from hashlib import md5

from .storage import Storage


class FunctionCache(Storage):
    _table_name = 'storage_v2'
    _table_created = False
    _table_updated = False
    _sql = {}

    def __init__(self, filepath, max_file_size_mb=5):
        max_file_size_kb = max_file_size_mb * 1024
        super(FunctionCache, self).__init__(filepath,
                                            max_file_size_kb=max_file_size_kb)

        self._enabled = True

    def enabled(self):
        """
        Enables the caching
        :return:
        """
        self._enabled = True

    def disable(self):
        """
        Disable caching e.g. for tests
        :return:
        """
        self._enabled = False

    @staticmethod
    def _create_id_from_func(partial_func):
        """
        Creats an id from the given function
        :param partial_func:
        :return: id for the given function
        """
        md5_hash = md5()
        md5_hash.update(partial_func.func.__module__.encode('utf-8'))
        md5_hash.update(partial_func.func.__name__.encode('utf-8'))
        md5_hash.update(str(partial_func.args).encode('utf-8'))
        md5_hash.update(str(partial_func.keywords).encode('utf-8'))
        return md5_hash.hexdigest()

    def get_result(self, func, *args, **kwargs):
        partial_func = partial(func, *args, **kwargs)

        # if caching is disabled call the function
        if not self._enabled:
            return partial_func()

        # only return before cached data
        cache_id = self._create_id_from_func(partial_func)
        return self._get(cache_id)

    def run(self, func, seconds, *args, **kwargs):
        """
        Returns the cached data of the given function.
        :param func, function to cache
        :param seconds: time to live in
        :param _refresh: bool, updates cache with new func result
        :return:
        """
        refresh = kwargs.pop('_refresh', False)
        partial_func = partial(func, *args, **kwargs)

        # if caching is disabled call the function
        if not self._enabled:
            return partial_func()

        cache_id = self._create_id_from_func(partial_func)
        data = None if refresh else self._get(cache_id, seconds=seconds)
        if data is None:
            data = partial_func()
            self._set(cache_id, data)

        return data

    def _optimize_item_count(self, limit=-1, defer=False):
        # override method Storage._optimize_item_count
        # for function cache do not optimize by item count, use database size.
        return False
