# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os

from .. import logging
from ..compatibility import (
    parse_qsl,
    quote,
    string_type,
    to_str,
    unquote,
    urlencode,
    urlsplit,
)
from ..constants import (
    ACTION,
    ADDON_ID_PARAM,
    BOOL_FROM_STR,
    CHANNEL_ID,
    CHANNEL_IDS,
    CLIP,
    CONTEXT_MENU,
    END,
    FANART_TYPE,
    HIDE_CHANNELS,
    HIDE_FOLDERS,
    HIDE_LIVE,
    HIDE_MEMBERS,
    HIDE_NEXT_PAGE,
    HIDE_PLAYLISTS,
    HIDE_PROGRESS,
    HIDE_SEARCH,
    HIDE_SHORTS,
    HIDE_VIDEOS,
    INCOGNITO,
    ITEMS_PER_PAGE,
    ITEM_FILTER,
    KEYMAP,
    LIVE,
    ORDER,
    PAGE,
    PATHS,
    PLAYLIST_ID,
    PLAYLIST_IDS,
    PLAYLIST_ITEM_ID,
    PLAY_FORCE_AUDIO,
    PLAY_PROMPT_QUALITY,
    PLAY_PROMPT_SUBTITLES,
    PLAY_STRM,
    PLAY_TIMESHIFT,
    PLAY_USING,
    SCREENSAVER,
    SEEK,
    START,
    SUBSCRIPTION_ID,
    VIDEO_ID,
    VIDEO_IDS,
    WINDOW_CACHE,
    WINDOW_FALLBACK,
    WINDOW_REPLACE,
    WINDOW_RETURN,
)
from ..sql_store import (
    BookmarksList,
    DataCache,
    FeedHistory,
    FunctionCache,
    PlaybackHistory,
    RequestCache,
    SearchHistory,
    WatchLaterList,
)
from ..utils.system_version import current_system_version


class AbstractContext(object):
    log = logging.getLogger(__name__)

    _initialized = False
    _addon = None
    _settings = None

    _BOOL_PARAMS = frozenset((
        CONTEXT_MENU,
        KEYMAP,
        PLAY_FORCE_AUDIO,
        PLAY_PROMPT_SUBTITLES,
        PLAY_PROMPT_QUALITY,
        PLAY_STRM,
        PLAY_TIMESHIFT,
        PLAY_USING,
        'confirmed',
        CLIP,
        'enable',
        HIDE_CHANNELS,
        HIDE_FOLDERS,
        HIDE_LIVE,
        HIDE_MEMBERS,
        HIDE_NEXT_PAGE,
        HIDE_PLAYLISTS,
        HIDE_PROGRESS,
        HIDE_SEARCH,
        HIDE_SHORTS,
        HIDE_VIDEOS,
        INCOGNITO,
        'location',
        'logged_in',
        'resume',
        SCREENSAVER,
        WINDOW_CACHE,
        WINDOW_FALLBACK,
        WINDOW_REPLACE,
        WINDOW_RETURN,
    ))
    _INT_PARAMS = frozenset((
        FANART_TYPE,
        'filtered',
        ITEMS_PER_PAGE,
        LIVE,
        'next_page_token',
        PAGE,
        'refresh',
    ))
    _INT_BOOL_PARAMS = frozenset((
        'refresh',
    ))
    _FLOAT_PARAMS = frozenset((
        END,
        'recent_days',
        SEEK,
        START,
    ))
    _LIST_PARAMS = frozenset((
        CHANNEL_IDS,
        'exclude',
        ITEM_FILTER,
        PLAYLIST_IDS,
        VIDEO_IDS,
    ))
    _STRING_PARAMS = frozenset((
        'api_key',
        ACTION,
        ADDON_ID_PARAM,
        'category_label',
        CHANNEL_ID,
        'client_id',
        'client_secret',
        'click_tracking',
        'event_type',
        'item',
        'item_id',
        'item_name',
        ORDER,
        'page_token',
        'parent_id',
        'playlist',  # deprecated
        PLAYLIST_ITEM_ID,
        PLAYLIST_ID,
        'q',
        'rating',
        'reload_path',
        'search_type',
        SUBSCRIPTION_ID,
        'uri',
        'videoid',  # deprecated
        VIDEO_ID,
        'visitor',
    ))
    _STRING_BOOL_PARAMS = frozenset((
        'logged_in',
        'reload_path',
    ))
    _STRING_INT_PARAMS = frozenset((
    ))
    _NON_EMPTY_STRING_PARAMS = set()

    def __init__(self, path='/', params=None, plugin_id=''):
        self._access_manager = None
        self._uuid = None
        self._api_store = None

        self._bookmarks_list = None
        self._data_cache = None
        self._feed_history = None
        self._function_cache = None
        self._playback_history = None
        self._requests_cache = None
        self._search_history = None
        self._watch_later_list = None

        self._plugin_handle = -1
        self._plugin_id = plugin_id
        self._plugin_name = None
        self._plugin_icon = None
        self._version = 'UNKNOWN'

        self._param_string = ''
        self._params = params or {}
        if params:
            self.parse_params(params)

        self._uri = None
        self._path = None
        self._path_parts = []
        self.set_path(path, force=True)

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

    def get_player_language(self):
        raise NotImplementedError()

    def get_subtitle_language(self):
        raise NotImplementedError()

    def get_region(self):
        raise NotImplementedError()

    def get_playback_history(self):
        uuid = self.get_uuid()
        playback_history = self._playback_history
        if not playback_history or playback_history.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'history.sqlite')
            playback_history = PlaybackHistory(filepath)
            self._playback_history = playback_history
        return playback_history

    def get_feed_history(self):
        uuid = self.get_uuid()
        feed_history = self._feed_history
        if not feed_history or feed_history.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'feeds.sqlite')
            feed_history = FeedHistory(filepath)
            self._feed_history = feed_history
        return feed_history

    def get_data_cache(self):
        uuid = self.get_uuid()
        data_cache = self._data_cache
        if not data_cache or data_cache.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'data_cache.sqlite')
            data_cache = DataCache(
                filepath,
                max_file_size_mb=self.get_settings().cache_size() / 2,
            )
            self._data_cache = data_cache
        return data_cache

    def get_function_cache(self):
        uuid = self.get_uuid()
        function_cache = self._function_cache
        if not function_cache or function_cache.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'cache.sqlite')
            function_cache = FunctionCache(
                filepath,
                max_file_size_mb=self.get_settings().cache_size() / 2,
            )
            self._function_cache = function_cache
        return function_cache

    def get_requests_cache(self):
        uuid = self.get_uuid()
        requests_cache = self._requests_cache
        if not requests_cache or requests_cache.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'requests_cache.sqlite')
            requests_cache = RequestCache(
                filepath,
                max_file_size_mb=self.get_settings().requests_cache_size(),
            )
            self._requests_cache = requests_cache
        return requests_cache

    def get_search_history(self):
        uuid = self.get_uuid()
        search_history = self._search_history
        if not search_history or search_history.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'search.sqlite')
            search_history = SearchHistory(
                filepath,
                max_item_count=self.get_settings().get_search_history_size(),
            )
            self._search_history = search_history
        return search_history

    def get_bookmarks_list(self):
        uuid = self.get_uuid()
        bookmarks_list = self._bookmarks_list
        if not bookmarks_list or bookmarks_list.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'bookmarks.sqlite')
            bookmarks_list = BookmarksList(filepath)
            self._bookmarks_list = bookmarks_list
        return bookmarks_list

    def get_watch_later_list(self):
        uuid = self.get_uuid()
        watch_later_list = self._watch_later_list
        if not watch_later_list or watch_later_list.uuid != uuid:
            filepath = (self.get_data_path(), uuid, 'watch_later.sqlite')
            watch_later_list = WatchLaterList(filepath)
            self._watch_later_list = watch_later_list
        return watch_later_list

    def get_uuid(self):
        uuid = self._uuid
        if not uuid:
            uuid = self.get_access_manager().get_current_user_id()
            self._uuid = uuid
        return uuid

    def get_access_manager(self):
        access_manager = self._access_manager
        if access_manager:
            return access_manager
        return self.reload_access_manager()

    def reload_access_manager(self):
        raise NotImplementedError()

    def get_api_store(self):
        api_store = self._api_store
        if api_store:
            return api_store
        return self.reload_api_store()

    def reload_api_store(self):
        raise NotImplementedError()

    def get_playlist_player(self, playlist_type=None):
        raise NotImplementedError()

    def get_ui(self):
        raise NotImplementedError()

    @staticmethod
    def get_system_version():
        return current_system_version

    def create_uri(self,
                   path=None,
                   params=None,
                   parse_params=False,
                   run=False,
                   play=None,
                   window=None,
                   command=False):
        if isinstance(path, (list, tuple)):
            uri = self.create_path(*path, is_uri=True)
        elif path:
            uri = path
        else:
            uri = '/'

        if not uri.startswith('plugin://'):
            uri = self._plugin_id.join(('plugin://', uri))

        if params:
            if isinstance(params, string_type):
                if parse_params:
                    params = dict(parse_qsl(params, keep_blank_values=True))
            else:
                parse_params = True
            if parse_params:
                if isinstance(params, dict):
                    params = params.items()
                params = urlencode([
                    (
                        ('%' + param,
                         ','.join([quote(item) for item in value]))
                        if len(value) > 1 else
                        (param, value[0])
                    )
                    if value and isinstance(value, (list, tuple)) else
                    (param, value)
                    for param, value in params
                ])
            uri = '?'.join((uri, params))

        command = 'command://' if command else ''
        if run:
            return ''.join((command,
                            'RunAddon('
                            if run == 'addon' else
                            'RunScript('
                            if run == 'script' else
                            'RunPlugin(',
                            uri,
                            ')'))
        if play is not None:
            return ''.join((
                command,
                'PlayMedia(',
                uri,
                ',playlist_type_hint=', str(play), ')',
            ))
        if window:
            if not isinstance(window, dict):
                window = {}
            if window.setdefault('refresh', False):
                method = 'Container.Refresh('
                if not window.setdefault('replace', False):
                    uri = ''
                history_replace = False
                window_return = False
            elif window.setdefault('update', False):
                method = 'Container.Update('
                history_replace = window.setdefault('replace', False)
                window_return = False
            else:
                history_replace = False
                window_name = window.setdefault('name', 'Videos')
                if window.setdefault('replace', False):
                    method = 'ReplaceWindow(%s,' % window_name
                    window_return = window.setdefault('return', False)
                else:
                    method = 'ActivateWindow(%s,' % window_name
                    window_return = window.setdefault('return', True)
            return ''.join((
                command,
                method,
                uri,
                ',return' if window_return else '',
                ',replace' if history_replace else '',
                ')'
            ))
        return uri

    def get_parent_uri(self, **kwargs):
        return self.create_uri(self._path_parts[:-1], **kwargs)

    @staticmethod
    def create_path(*args, **kwargs):
        include_parts = kwargs.get('parts')
        parser = kwargs.get('parser')
        parts = [
            parser(part[6:-1])
            if parser and part.startswith('$INFO[') else
            part
            for part in [
                to_str(arg).strip('/').replace('\\', '/').replace('//', '/')
                for arg in args
            ]
            if part
        ]
        if parts:
            path = '/'.join(parts).join(('/', '/'))
            if path.startswith(PATHS.ROUTE):
                parts = parts[2:]
            elif path.startswith(PATHS.COMMAND):
                parts = []
            elif path.startswith(PATHS.GOTO_PAGE):
                parts = parts[2:]
                if parts:
                    try:
                        int(parts[0])
                    except (TypeError, ValueError):
                        pass
                    else:
                        parts = parts[1:]
        else:
            return ('/', parts) if include_parts else '/'

        if kwargs.get('is_uri'):
            path = quote(path)
        return (path, parts) if include_parts else path

    def get_path(self):
        return self._path

    def set_path(self, *path, **kwargs):
        if kwargs.get('force'):
            parts = kwargs.get('parts')
            path = unquote(path[0])
            if parts is None:
                path = path.split('/')
                path, parts = self.create_path(
                    *path,
                    parts=True,
                    parser=kwargs.get('parser')
                )
        else:
            path, parts = self.create_path(*path, parts=True)

        self._path = path
        self._path_parts = parts
        if kwargs.get('update_uri', True):
            self.update_uri()

    def get_original_params(self):
        return self._param_string

    def get_params(self):
        return self._params

    def get_param(self, name, default=None):
        return self._params.get(name, default)

    def pop_param(self, name, default=None):
        return self._params.pop(name, default)

    def parse_uri(self, uri, parse_params=True, update=False):
        uri = urlsplit(uri)
        path = uri.path
        if parse_params:
            params = self.parse_params(
                dict(parse_qsl(uri.query, keep_blank_values=True)),
                update=False,
            )
            if update:
                self._params = params
                self.set_path(path)
        else:
            params = uri.query
        return path, params

    def parse_params(self, params, update=True, parser=None):
        to_delete = []
        output = self._params if update else {}

        for param, value in params.items():
            if param.startswith('%'):
                param = param[1:]
                value = unquote(value)
            try:
                if param in self._BOOL_PARAMS:
                    parsed_value = BOOL_FROM_STR.get(
                        str(value),
                        bool(value)
                        if param in self._STRING_BOOL_PARAMS else
                        False
                    )
                elif param in self._INT_PARAMS:
                    parsed_value = int(
                        (BOOL_FROM_STR.get(str(value), value) or 0)
                        if param in self._INT_BOOL_PARAMS else
                        value
                    )
                elif param in self._FLOAT_PARAMS:
                    parsed_value = float(value)
                elif param in self._LIST_PARAMS:
                    parsed_value = (
                        list(value)
                        if isinstance(value, (list, tuple)) else
                        [unquote(val) for val in value.split(',') if val]
                    )
                elif param in self._STRING_PARAMS:
                    if parser and value.startswith('$INFO['):
                        parsed_value = parser(value[6:-1])
                    else:
                        parsed_value = value
                    if param in self._STRING_BOOL_PARAMS:
                        parsed_value = BOOL_FROM_STR.get(
                            parsed_value, parsed_value
                        )
                    elif param in self._STRING_INT_PARAMS:
                        try:
                            parsed_value = int(parsed_value)
                        except (TypeError, ValueError):
                            pass
                    # process and translate deprecated parameters
                    elif param == 'action':
                        if parsed_value in {'play_all', 'play_video'}:
                            to_delete.append(param)
                            self.set_path(PATHS.PLAY, update_uri=False)
                            continue
                    elif param == 'videoid':
                        to_delete.append(param)
                        param = VIDEO_ID
                    elif params == 'playlist':
                        to_delete.append(param)
                        param = PLAYLIST_ID
                elif param in self._NON_EMPTY_STRING_PARAMS:
                    parsed_value = BOOL_FROM_STR.get(value, value)
                    if not parsed_value:
                        raise ValueError
                else:
                    self.log.debug('Unknown parameter {param!r}: {value!r}',
                                   param=param,
                                   value=value)
                    to_delete.append(param)
                    continue
            except (TypeError, ValueError):
                self.log.exception('Invalid value for {param!r}: {value!r}',
                                   param=param,
                                   value=value)
                to_delete.append(param)
                continue

            output[param] = parsed_value

        for param in to_delete:
            del params[param]

        return output

    def set_params(self, **kwargs):
        self.parse_params(kwargs)

    def get_data_path(self):
        """
        Returns the path for read/write access of files
        :return:
        """
        raise NotImplementedError()

    def get_addon_path(self):
        raise NotImplementedError()

    def get_icon(self):
        return self._plugin_icon

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

    def update_uri(self):
        self._uri = self.create_uri(self._path, self._params)

    def get_name(self):
        return self._plugin_name

    def get_version(self):
        return self._version

    def get_id(self):
        return self._plugin_id

    def get_handle(self):
        return self._plugin_handle

    def get_settings(self, refresh=False):
        raise NotImplementedError()

    def localize(self, text_id, args=None, default_text=None):
        raise NotImplementedError()

    def apply_content(self,
                      content_type=None,
                      sub_type=None,
                      category_label=None):
        raise NotImplementedError()

    def add_sort_method(self, *sort_methods):
        raise NotImplementedError()

    def clone(self, new_path=None, new_params=None):
        raise NotImplementedError()

    def execute(self,
                command,
                wait=False,
                wait_for=None,
                wait_for_set=True,
                block_ui=None):
        raise NotImplementedError()

    @staticmethod
    def sleep(timeout=None):
        raise NotImplementedError()

    def tear_down(self):
        pass

    def ipc_exec(self, target, timeout=None, payload=None, raise_exc=False):
        raise NotImplementedError()

    @staticmethod
    def is_plugin_folder(folder_name=None):
        raise NotImplementedError()

    def refresh_requested(self, force=False, on=False, off=False, params=None):
        raise NotImplementedError

    def parse_item_ids(self,
                       uri=None,
                       from_listitem=True):
        raise NotImplementedError()
