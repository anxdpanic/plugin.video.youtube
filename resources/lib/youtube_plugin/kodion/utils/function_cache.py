from functools import partial
import hashlib
import datetime

from storage import Storage


class FunctionCache(Storage):
    ONE_MINUTE = 60
    ONE_HOUR = 60 * ONE_MINUTE
    ONE_DAY = 24 * ONE_HOUR
    ONE_WEEK = 7 * ONE_DAY
    ONE_MONTH = 4 * ONE_WEEK

    def __init__(self, filename, max_file_size_kb=-1):
        Storage.__init__(self, filename, max_file_size_kb=max_file_size_kb)

        self._enabled = True
        pass

    def clear(self):
        self._clear()
        pass

    def enabled(self):
        """
        Enables the caching
        :return:
        """
        self._enabled = True
        pass

    def disable(self):
        """
        Disable caching e.g. for tests
        :return:
        """
        self._enabled = False
        pass

    def _create_id_from_func(self, partial_func):
        """
        Creats an id from the given function
        :param partial_func:
        :return: id for the given function
        """
        m = hashlib.md5()
        m.update(partial_func.func.__module__)
        m.update(partial_func.func.__name__)
        m.update(str(partial_func.args))
        m.update(str(partial_func.keywords))
        return m.hexdigest()

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
        if data is not None:
            return data[0]

        return None

    def get(self, seconds, func, *args, **keywords):
        def _seconds_difference(_first, _last):
            _delta = _last - _first
            return 24*60*60*_delta.days + _delta.seconds + _delta.microseconds/1000000.

        """
        Returns the cached data of the given function.
        :param partial_func: function to cache
        :param seconds: time to live in seconds
        :param return_cached_only: return only cached data and don't call the function
        :return:
        """

        partial_func = partial(func, *args, **keywords)

        # if caching is disabled call the function
        if not self._enabled:
            return partial_func()

        cached_data = None
        cached_time = None
        data, cache_id = self._get_cached_data(partial_func)
        if data is not None:
            cached_data = data[0]
            cached_time = data[1]
            pass

        diff_seconds = 0
        now = datetime.datetime.now()
        if cached_time is not None:
            # this is so stupid, but we have the function 'total_seconds' only starting with python 2.7
            diff_seconds = _seconds_difference(cached_time, now)
            pass

        if cached_data is None or diff_seconds > seconds:
            cached_data = partial_func()
            self._set(cache_id, cached_data)
            pass

        return cached_data

    pass
