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
from itertools import chain

from .storage import Storage


class FunctionCache(Storage):
    _table_name = 'storage_v2'
    _table_updated = False
    _sql = {}

    _BUILTIN = str.__module__
    SCOPE_NONE = 0
    SCOPE_BUILTINS = 1
    SCOPE_ALL = 2

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

    @classmethod
    def _create_id_from_func(cls, partial_func, scope=SCOPE_ALL):
        """
        Creates an id from the given function
        :param partial_func:
        :return: id for the given function
        """
        signature = (
            partial_func.func.__module__,
            partial_func.func.__name__,
        )
        if scope == cls.SCOPE_BUILTINS:
            signature = chain(
                signature,
                ((
                    arg
                    if type(arg).__module__ == cls._BUILTIN else
                    type(arg)
                ) for arg in partial_func.args),
                ((
                    (key, arg)
                    if type(arg).__module__ == cls._BUILTIN else
                    (key, type(arg))
                ) for key, arg in partial_func.keywords.items()),
            )
        elif scope == cls.SCOPE_ALL:
            signature = chain(
                signature,
                partial_func.args,
                partial_func.keywords.items(),
            )
        return md5(','.join(map(str, signature)).encode('utf-8')).hexdigest()

    def get_result(self, func, *args, **kwargs):
        partial_func = partial(func, *args, **kwargs)

        # if caching is disabled call the function
        if not self._enabled:
            return partial_func()

        # only return previously cached data
        cache_id = self._create_id_from_func(partial_func)
        return self._get(cache_id)

    def run(self, func, seconds=None, *args, **kwargs):
        """
        Returns the cached data of the given function.
        :param function func: function to call and cache if not already cached
        :param int|None seconds: max allowable age of cached result
        :param tuple args: positional arguments passed to the function
        :param dict kwargs: keyword arguments passed to the function
        :keyword _scope: (int) cache result if matching:
                         0: function only,
                         1: function + value of builtin type parameters
                         2: function + value of all parameters, default 2
        :keyword _ignore_value: (Any) don't cache func return value if equal to
                                _ignored_value, default None
        :keyword _oneshot: (bool) remove previously cached result, default False
        :keyword _refresh: (bool) updates cache with new result, default False
        :keyword _retry_value: (Any) re-evaluate func if cached value is equal
                               _retry_value, default None
        :return:
        """
        scope = kwargs.pop('_scope', self.SCOPE_ALL)
        ignore_value = kwargs.pop('_ignore_value', None)
        oneshot = kwargs.pop('_oneshot', False)
        refresh = kwargs.pop('_refresh', False)
        retry_value = kwargs.pop('_retry_value', None)
        partial_func = partial(func, *args, **kwargs)

        # if caching is disabled call the function
        if not self._enabled:
            return partial_func()

        cache_id = self._create_id_from_func(partial_func, scope)
        data = retry_value if refresh else self._get(cache_id, seconds=seconds)
        if data == retry_value:
            data = partial_func()
        if data != ignore_value:
            self._set(cache_id, data)
        elif oneshot:
            self._remove(cache_id)

        return data

    def _optimize_item_count(self, limit=-1, defer=False):
        # override method Storage._optimize_item_count
        # for function cache do not optimize by item count, use database size.
        return False
