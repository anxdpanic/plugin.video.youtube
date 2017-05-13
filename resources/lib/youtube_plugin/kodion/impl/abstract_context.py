import os
import urllib

from .. import constants
from ..logging import *
from ..utils import *


class AbstractContext(object):
    def __init__(self, path=u'/', params=None, plugin_name=u'', plugin_id=u''):
        if not params:
            params = {}
            pass

        self._cache_path = None

        self._function_cache = None
        self._search_history = None
        self._favorite_list = None
        self._watch_later_list = None
        self._access_manager = None

        self._plugin_name = unicode(plugin_name)
        self._version = 'UNKNOWN'
        self._plugin_id = plugin_id
        self._path = create_path(path)
        self._params = params
        self._utils = None
        self._view_mode = None

        # create valid uri
        self._uri = self.create_uri(self._path, self._params)
        pass

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
            pass
        return self._cache_path

    def get_function_cache(self):
        if not self._function_cache:
            max_cache_size_mb = self.get_settings().get_int(constants.setting.CACHE_SIZE, 5)
            self._function_cache = FunctionCache(os.path.join(self._get_cache_path(), 'cache'),
                                                 max_file_size_kb=max_cache_size_mb * 1024)
            pass
        return self._function_cache

    def get_search_history(self):
        if not self._search_history:
            max_search_history_items = self.get_settings().get_int(constants.setting.SEARCH_SIZE, 50)
            self._search_history = SearchHistory(os.path.join(self._get_cache_path(), 'search'),
                                                 max_search_history_items)
            pass
        return self._search_history

    def get_favorite_list(self):
        if not self._favorite_list:
            self._favorite_list = FavoriteList(os.path.join(self._get_cache_path(), 'favorites'))
            pass
        return self._favorite_list

    def get_watch_later_list(self):
        if not self._watch_later_list:
            self._watch_later_list = WatchLaterList(os.path.join(self._get_cache_path(), 'watch_later'))
            pass
        return self._watch_later_list

    def get_access_manager(self):
        if not self._access_manager:
            self._access_manager = AccessManager(self.get_settings())
            pass
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
            pass

        uri = create_uri_path(path)
        if uri:
            uri = "%s://%s%s" % ('plugin', self._plugin_id.encode('utf-8'), uri)
        else:
            uri = "%s://%s/" % ('plugin', self._plugin_id.encode('utf-8'))
            pass

        if len(params) > 0:
            # make a copy of the map
            uri_params = {}
            uri_params.update(params)

            # encode in utf-8
            for param in uri_params:
                if isinstance(params[param], int):
                    params[param] = str(params[param])
                    pass

                uri_params[param] = to_utf8(params[param])
                pass
            uri += '?' + urllib.urlencode(uri_params)
            pass

        return uri

    def get_path(self):
        return self._path

    def get_params(self):
        return self._params

    def get_param(self, name, default=None):
        return self.get_params().get(name, default)

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
            pass
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
        pass

    def log_warning(self, text):
        self.log(text, constants.log.WARNING)
        pass

    def log_error(self, text):
        self.log(text, constants.log.ERROR)
        pass

    def log_notice(self, text):
        self.log(text, constants.log.NOTICE)
        pass

    def log_debug(self, text):
        self.log(text, constants.log.DEBUG)
        pass

    def log_info(self, text):
        self.log(text, constants.log.INFO)
        pass

    def clone(self, new_path=None, new_params=None):
        raise NotImplementedError()

    def execute(self, command):
        raise NotImplementedError()

    def sleep(self, milli_seconds):
        raise NotImplementedError()
