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
    def __init__(self, filename, max_file_size_mb=5):
        max_file_size_kb = max_file_size_mb * 1024
        super(FunctionCache, self).__init__(filename,
                                            max_file_size_kb=max_file_size_kb)

        self._enabled = True

    def clear(self):
        self._clear()

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

    def _get_cached_data(self, partial_func):
        cache_id = self._create_id_from_func(partial_func)
        return self._get(cache_id), cache_id

    def get_cached_only(self, func, *args, **keywords):
        partial_func = partial(func, *args, **keywords)

        # if caching is disabled call the function
        if not self._enabled:
            return partial_func()

        # only return before cached data
        data, cache_id = self._get_cached_data(partial_func)
        if data is None:
            return None
        return data[1]

    def get(self, func, seconds, *args, **keywords):
        """
        Returns the cached data of the given function.
        :param func, function to cache
        :param seconds: time to live in seconds
        :return:
        """

        partial_func = partial(func, *args, **keywords)

        # if caching is disabled call the function
        if not self._enabled:
            return partial_func()

        data, cache_id = self._get_cached_data(partial_func)
        if data is not None:
            cached_time, cached_data = data

        if data is None or self.get_seconds_diff(cached_time) > seconds:
            data = partial_func()
            self._set(cache_id, data)
            return data
        return cached_data

    def _optimize_item_count(self):
        # override method Storage._optimize_item_count
        # for function cache do not optimize by item count, use database size.
        pass
