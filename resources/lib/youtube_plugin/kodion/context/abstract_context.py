# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os

from .. import logger
from ..compatibility import to_str, urlencode
from ..json_store import AccessManager
from ..sql_store import (
    DataCache,
    FavoriteList,
    FunctionCache,
    PlaybackHistory,
    SearchHistory,
    WatchLaterList,
)
from ..utils import create_path, current_system_version


class AbstractContext(object):
    _BOOL_PARAMS = {
        'ask_for_quality',
        'audio_only',
        'confirmed',
        'clip',
        'enable',
        'hide_folders',
        'hide_live',
        'hide_playlists',
        'hide_search',
        'incognito',
        'location',
        'logged_in',
        'play',
        'prompt_for_subtitles',
        'refresh',
        'resume',
        'screensaver',
        'strm',
    }
    _INT_PARAMS = {
        'live',
        'offset',
        'page',
    }
    _FLOAT_PARAMS = {
        'seek',
        'start',
        'end'
    }
    _LIST_PARAMS = {
        'channel_ids',
        'playlist_ids',
    }
    _STRING_PARAMS = {
        'api_key',
        'action',
        'addon_id',
        'category_label',
        'channel_id',
        'channel_name',
        'client_id',
        'client_secret',
        'click_tracking',
        'event_type',
        'item',
        'item_id',
        'next_page_token',
        'order',
        'page_token',
        'parent_id',
        'playlist',  # deprecated
        'playlist_id',
        'playlist_name',
        'q',
        'rating',
        'reload_path',
        'search_type',
        'subscription_id',
        'uri',
        'videoid',  # deprecated
        'video_id',
        'video_name',
        'visitor',
    }

    def __init__(self, path='/', params=None, plugin_name='', plugin_id=''):
        if not params:
            params = {}

        self._cache_path = None
        self._debug_path = None

        self._function_cache = None
        self._data_cache = None
        self._search_history = None
        self._playback_history = None
        self._favorite_list = None
        self._watch_later_list = None
        self._access_manager = None

        self._plugin_name = str(plugin_name)
        self._version = 'UNKNOWN'
        self._plugin_id = plugin_id
        self._path = create_path(path)
        self._params = params
        self._utils = None

        # create valid uri
        self.parse_params()
        self._uri = self.create_uri(self._path, self._params)

    @staticmethod
    def format_date_short(date_obj, str_format=None):
        raise NotImplementedError()

    @staticmethod
    def format_time(time_obj, str_format=None):
        raise NotImplementedError()

    @staticmethod
    def get_language():
        raise NotImplementedError()

    def get_language_name(self, lang_id=None):
        raise NotImplementedError()

    def get_subtitle_language(self):
        raise NotImplementedError()

    def get_region(self):
        raise NotImplementedError()

    def get_playback_history(self):
        if not self._playback_history:
            uuid = self.get_access_manager().get_current_user_id()
            filename = 'history.sqlite'
            filepath = os.path.join(self.get_data_path(), uuid, filename)
            self._playback_history = PlaybackHistory(filepath)
        return self._playback_history

    def get_data_cache(self):
        if not self._data_cache:
            settings = self.get_settings()
            cache_size = settings.cache_size() / 2
            uuid = self.get_access_manager().get_current_user_id()
            filename = 'data_cache.sqlite'
            filepath = os.path.join(self.get_data_path(), uuid, filename)
            self._data_cache = DataCache(filepath, max_file_size_mb=cache_size)
        return self._data_cache

    def get_function_cache(self):
        if not self._function_cache:
            settings = self.get_settings()
            cache_size = settings.cache_size() / 2
            uuid = self.get_access_manager().get_current_user_id()
            filename = 'cache.sqlite'
            filepath = os.path.join(self.get_data_path(), uuid, filename)
            self._function_cache = FunctionCache(filepath,
                                                 max_file_size_mb=cache_size)
        return self._function_cache

    def get_search_history(self):
        if not self._search_history:
            settings = self.get_settings()
            search_size = settings.get_int(settings.SEARCH_SIZE, 50)
            uuid = self.get_access_manager().get_current_user_id()
            filename = 'search.sqlite'
            filepath = os.path.join(self.get_data_path(), uuid, filename)
            self._search_history = SearchHistory(filepath,
                                                 max_item_count=search_size)
        return self._search_history

    def get_favorite_list(self):
        if not self._favorite_list:
            uuid = self.get_access_manager().get_current_user_id()
            filename = 'favorites.sqlite'
            filepath = os.path.join(self.get_data_path(), uuid, filename)
            self._favorite_list = FavoriteList(filepath)
        return self._favorite_list

    def get_watch_later_list(self):
        if not self._watch_later_list:
            uuid = self.get_access_manager().get_current_user_id()
            filename = 'watch_later.sqlite'
            filepath = os.path.join(self.get_data_path(), uuid, filename)
            self._watch_later_list = WatchLaterList(filepath)
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

    @staticmethod
    def get_system_version():
        return current_system_version

    def create_uri(self, path=None, params=None):
        if isinstance(path, (list, tuple)):
            uri = create_path(*path, is_uri=True)
        elif path:
            uri = path
        else:
            uri = '/'

        uri = self._plugin_id.join(('plugin://', uri))

        if params:
            uri = '?'.join((uri, urlencode(params)))

        return uri

    def get_path(self):
        return self._path

    def set_path(self, *path):
        self._path = create_path(*path)

    def get_params(self):
        return self._params

    def get_param(self, name, default=None):
        return self._params.get(name, default)

    def parse_params(self, params=None):
        if not params:
            params = self._params
        to_delete = []

        for param, value in params.items():
            try:
                if param in self._BOOL_PARAMS:
                    parsed_value = str(value).lower() in ('true', '1')
                elif param in self._INT_PARAMS:
                    parsed_value = int(value)
                elif param in self._FLOAT_PARAMS:
                    parsed_value = float(value)
                elif param in self._LIST_PARAMS:
                    parsed_value = [
                        val for val in value.split(',') if val
                    ]
                elif param in self._STRING_PARAMS:
                    parsed_value = to_str(value)
                    # process and translate deprecated parameters
                    if param == 'action':
                        if parsed_value in ('play_all', 'play_video'):
                            to_delete.append(param)
                            self.set_path('play')
                            continue
                    elif param == 'videoid':
                        to_delete.append(param)
                        param = 'video_id'
                    elif params == 'playlist':
                        to_delete.append(param)
                        param = 'playlist_id'
                else:
                    self.log_debug('Unknown parameter - |{0}: {1}|'.format(
                        param, value
                    ))
                    to_delete.append(param)
                    continue
            except (TypeError, ValueError):
                self.log_error('Invalid parameter value - |{0}: {1}|'.format(
                    param, value
                ))
                to_delete.append(param)
                continue

            self._params[param] = parsed_value

        for param in to_delete:
            del params[param]

    def set_param(self, name, value):
        self.parse_params({name: value})

    def get_data_path(self):
        """
        Returns the path for read/write access of files
        :return:
        """
        raise NotImplementedError()

    def get_addon_path(self):
        raise NotImplementedError()

    def get_icon(self):
        return self.create_resource_path('media/icon.png')

    def get_fanart(self):
        return self.create_resource_path('media/fanart.jpg')

    def create_resource_path(self, *args):
        path_comps = []
        for arg in args:
            path_comps.extend(arg.split('/'))
        path = os.path.join(self.get_addon_path(), 'resources', *path_comps)
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

    def localize(self, text_id, default_text=None):
        raise NotImplementedError()

    def set_content(self, content_type, sub_type=None, category_label=None):
        raise NotImplementedError()

    def add_sort_method(self, *sort_methods):
        raise NotImplementedError()

    def log(self, text, log_level=logger.NOTICE):
        logger.log(text, log_level, self.get_id())

    def log_warning(self, text):
        self.log(text, logger.WARNING)

    def log_error(self, text):
        self.log(text, logger.ERROR)

    def log_notice(self, text):
        self.log(text, logger.NOTICE)

    def log_debug(self, text):
        self.log(text, logger.DEBUG)

    def log_info(self, text):
        self.log(text, logger.INFO)

    def clone(self, new_path=None, new_params=None):
        raise NotImplementedError()

    @staticmethod
    def execute(command):
        raise NotImplementedError()

    @staticmethod
    def sleep(timeout=None):
        raise NotImplementedError()

    @staticmethod
    def get_infolabel(name):
        raise NotImplementedError()

    @staticmethod
    def get_listitem_detail(detail_name, attr=False):
        raise NotImplementedError()

    def tear_down(self):
        pass
