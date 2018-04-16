from six.moves import urllib

import os

from .. import constants
from ..logging import log
from ..utils import *


class AbstractContext(object):
    def __init__(self, path=u'/', params=None, plugin_name=u'', plugin_id=u''):
        if not params:
            params = {}

        self._cache_path = None

        self._function_cache = None
        self._search_history = None
        self._favorite_list = None
        self._watch_later_list = None
        self._access_manager = None

        self._plugin_name = str(plugin_name)
        self._version = 'UNKNOWN'
        self._plugin_id = plugin_id
        self._path = create_path(path)
        self._params = params
        self._utils = None
        self._view_mode = None

        # create valid uri
        self._uri = self.create_uri(self._path, self._params)

    def format_date_short(self, date_obj):
        raise NotImplementedError()

    def format_time(self, time_obj):
        raise NotImplementedError()

    def get_language(self):
        raise NotImplementedError()

    def get_region(self):
        raise NotImplementedError()

    def _get_cache_path(self):
        if not self._cache_path:
            self._cache_path = os.path.join(self.get_data_path(), 'kodion')
        return self._cache_path

    def get_function_cache(self):
        if not self._function_cache:
            max_cache_size_mb = self.get_settings().get_int(constants.setting.CACHE_SIZE, 5)
            self._function_cache = FunctionCache(os.path.join(self._get_cache_path(), 'cache'),
                                                 max_file_size_mb=max_cache_size_mb)
        return self._function_cache

    def get_search_history(self):
        if not self._search_history:
            max_search_history_items = self.get_settings().get_int(constants.setting.SEARCH_SIZE, 50)
            self._search_history = SearchHistory(os.path.join(self._get_cache_path(), 'search'),
                                                 max_search_history_items)
        return self._search_history

    def get_favorite_list(self):
        if not self._favorite_list:
            self._favorite_list = FavoriteList(os.path.join(self._get_cache_path(), 'favorites'))
        return self._favorite_list

    def get_watch_later_list(self):
        if not self._watch_later_list:
            self._watch_later_list = WatchLaterList(os.path.join(self._get_cache_path(), 'watch_later'))
        return self._watch_later_list

    def get_access_manager(self):
        if not self._access_manager:
            self._access_manager = AccessManager(self)
        return self._access_manager

    def get_video_playlist(self):
        raise NotImplementedError()

    def get_audio_playlist(self):
        raise NotImplementedError()

    def get_video_player(self):
        raise NotImplementedError()

    def get_audio_player(self):
        raise NotImplementedError()

    def get_ui(self):
        raise NotImplementedError()

    def get_system_version(self):
        raise NotImplementedError()

    def create_uri(self, path=u'/', params=None):
        if not params:
            params = {}

        uri = create_uri_path(path)
        if uri:
            uri = "%s://%s%s" % ('plugin', str(self._plugin_id), uri)
        else:
            uri = "%s://%s/" % ('plugin', str(self._plugin_id))

        if len(params) > 0:
            # make a copy of the map
            uri_params = {}
            uri_params.update(params)

            # encode in utf-8
            for param in uri_params:
                if isinstance(params[param], int):
                    params[param] = str(params[param])

                uri_params[param] = to_utf8(params[param])
            uri += '?' + urllib.parse.urlencode(uri_params)

        return uri

    def get_path(self):
        return self._path

    def set_path(self, value):
        self._path = value

    def get_params(self):
        return self._params

    def get_param(self, name, default=None):
        return self.get_params().get(name, default)

    def set_param(self, name, value):
        self._params[name] = value

    def get_data_path(self):
        """
        Returns the path for read/write access of files
        :return:
        """
        raise NotImplementedError()

    def get_native_path(self):
        raise NotImplementedError()

    def get_icon(self):
        return os.path.join(self.get_native_path(), 'icon.png')

    def get_fanart(self):
        return os.path.join(self.get_native_path(), 'fanart.jpg')

    def create_resource_path(self, *args):
        path_comps = []
        for arg in args:
            path_comps.extend(arg.split('/'))
        path = os.path.join(self.get_native_path(), 'resources', *path_comps)
        return path

    def get_uri(self):
        return self._uri

    def get_name(self):
        return self._plugin_name

    def get_version(self):
        return self._version

    def get_id(self):
        return self._plugin_id

    def get_handle(self):
        raise NotImplementedError()

    def get_settings(self):
        raise NotImplementedError()

    def localize(self, text_id, default_text=u''):
        raise NotImplementedError()

    def set_content_type(self, content_type):
        raise NotImplementedError()

    def add_sort_method(self, *sort_methods):
        raise NotImplementedError()

    def log(self, text, log_level=constants.log.NOTICE):
        log_line = '[%s] %s' % (self.get_id(), text)
        log(log_line, log_level)

    def log_warning(self, text):
        self.log(text, constants.log.WARNING)

    def log_error(self, text):
        self.log(text, constants.log.ERROR)

    def log_notice(self, text):
        self.log(text, constants.log.NOTICE)

    def log_debug(self, text):
        self.log(text, constants.log.DEBUG)

    def log_info(self, text):
        self.log(text, constants.log.INFO)

    def clone(self, new_path=None, new_params=None):
        raise NotImplementedError()

    def execute(self, command):
        raise NotImplementedError()

    def sleep(self, milli_seconds):
        raise NotImplementedError()
