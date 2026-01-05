# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from . import (
    const_content_types as CONTENT,
    const_paths as PATHS,
    const_settings as SETTINGS,
    const_sort_methods as SORT,
)
from .const_lang_region import (
    DEFAULT_LANGUAGES,
    DEFAULT_REGIONS,
    TRANSLATION_LANGUAGES,
)


# Addon paths
ADDON_ID = 'plugin.video.youtube'
ADDON_PATH = 'special://home/addons/' + ADDON_ID
DATA_PATH = 'special://profile/addon_data/' + ADDON_ID
MEDIA_PATH = ADDON_PATH + '/resources/media'
RESOURCE_PATH = ADDON_PATH + '/resources'
TEMP_PATH = 'special://temp/' + ADDON_ID

# Const values
BOOL_FROM_STR = {
    '0': False,
    '1': True,
    'false': False,
    'False': False,
    'true': True,
    'True': True,
    'None': None,
    'null': None,
    '': None,
}

VALUE_TO_STR = {
    False: 'false',
    True: 'true',
    None: '',
    -1: '',
    0: 'false',
    1: 'true',
}

YOUTUBE_HOSTNAMES = frozenset((
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'www.youtubekids.com',
    'music.youtube.com',
))

# Flags
ABORT_FLAG = 'abort_requested'
BUSY_FLAG = 'busy'
SERVICE_RUNNING_FLAG = 'service_monitor_running'
WAIT_END_FLAG = 'builtin_completed'
TRAKT_PAUSE_FLAG = 'script.trakt.paused'

# Container Info
CURRENT_CONTAINER_INFO = 'Container.%s'
PLUGIN_CONTAINER_INFO = 'Container(%s).%s'
CURRENT_ITEM = 'CurrentItem'
FOLDER_NAME = 'FolderName'
FOLDER_URI = 'FolderPath'
HAS_FILES = 'HasFiles'
HAS_FOLDERS = 'HasFolders'
HAS_PARENT = 'HasParent'
NUM_ALL_ITEMS = 'NumAllItems'
SCROLLING = 'Scrolling'
UPDATING = 'IsUpdating'

# ListItem Info
CONTAINER_LISTITEM_INFO = 'Container(%s).ListItem(0).%s'
LISTITEM_INFO = 'ListItem.%s'
ARTIST = 'Artist'
LABEL = 'Label'
PLAY_COUNT = 'PlayCount'
RESUMABLE = 'IsResumable'
TITLE = 'Title'
URI = 'FileNameAndPath'

# ListItem Properties
CONTAINER_LISTITEM_PROP = 'Container(%s).ListItem(0).Property(%s)'
LISTITEM_PROP = 'ListItem.Property(%s)'
BOOKMARK_ID = 'bookmark_id'
CHANNEL_ID = 'channel_id'
PLAY_COUNT_PROP = 'video_play_count'
PLAYLIST_ID = 'playlist_id'
PLAYLIST_ITEM_ID = 'playlist_item_id'
SUBSCRIPTION_ID = 'subscription_id'
VIDEO_ID = 'video_id'

# Events
CHECK_SETTINGS = 'check_settings'
CONTEXT_MENU = 'cxm_action'
FILE_READ = 'file_read'
FILE_WRITE = 'file_write'
KEYMAP = 'key_action'
PLAYBACK_INIT = 'playback_init'
PLAYBACK_FAILED = 'playback_failed'
PLAYBACK_STARTED = 'playback_started'
PLAYBACK_STOPPED = 'playback_stopped'
REFRESH_CONTAINER = 'refresh_container'
RELOAD_ACCESS_MANAGER = 'reload_access_manager'
SERVICE_IPC = 'service_ipc'
SYNC_LISTITEM = 'sync_listitem'

# Sleep/wakeup states
PLUGIN_WAKEUP = 'plugin_wakeup'
PLUGIN_SLEEPING = 'plugin_sleeping'
SERVER_WAKEUP = 'server_wakeup'

# Play options
PLAY_CANCELLED = 'play_cancelled'
PLAY_FORCE_AUDIO = 'audio_only'
PLAY_FORCED = 'play_forced'
PLAY_PROMPT_QUALITY = 'ask_for_quality'
PLAY_PROMPT_SUBTITLES = 'prompt_for_subtitles'
PLAY_STRM = 'strm'
PLAY_TIMESHIFT = 'timeshift'
PLAY_USING = 'play_using'
FORCE_PLAY_PARAMS = frozenset((
    PLAY_FORCE_AUDIO,
    PLAY_TIMESHIFT,
    PLAY_PROMPT_QUALITY,
    PLAY_PROMPT_SUBTITLES,
    PLAY_USING,
))

# Stored data
PROPERTY = 'Window(home).Property(%s-%%s)' % ADDON_ID
PROPERTY_AS_LABEL = '$INFO[Window(home).Property(%s-%%s)]' % ADDON_ID
CONTAINER_ID = 'container_id'
CONTAINER_FOCUS = 'container_focus'
CONTAINER_POSITION = 'container_position'
DEVELOPER_CONFIGS = 'configs'
LICENSE_TOKEN = 'license_token'
LICENSE_URL = 'license_url'
MARK_AS_LABEL = 'mark_as_label'
PLAYER_DATA = 'player_json'
PLAYER_VIDEO_ID = 'player_video_id'
PLAYLIST_PATH = 'playlist_path'
PLAYLIST_POSITION = 'playlist_position'
REROUTE_PATH = 'reroute_path'

# Routing parameters
WINDOW_CACHE = 'window_cache'
WINDOW_FALLBACK = 'window_fallback'
WINDOW_REPLACE = 'window_replace'
WINDOW_RETURN = 'window_return'

# Plugin url query parameters
ACTION = 'action'
ADDON_ID_PARAM = 'addon_id'
CHANNEL_IDS = 'channel_ids'
CLIP = 'clip'
END = 'end'
FANART_TYPE = 'fanart_type'
HIDE_CHANNELS = 'hide_channels'
HIDE_FOLDERS = 'hide_folders'
HIDE_LIVE = 'hide_live'
HIDE_MEMBERS = 'hide_members'
HIDE_NEXT_PAGE = 'hide_next_page'
HIDE_PLAYLISTS = 'hide_playlists'
HIDE_PROGRESS = 'hide_progress'
HIDE_SEARCH = 'hide_search'
HIDE_SHORTS = 'hide_shorts'
HIDE_VIDEOS = 'hide_videos'
INCOGNITO = 'incognito'
ITEM_FILTER = 'item_filter'
ITEMS_PER_PAGE = 'items_per_page'
LIVE = 'live'
ORDER = 'order'
PAGE = 'page'
PLAYLIST_IDS = 'playlist_ids'
SCREENSAVER = 'screensaver'
SEEK = 'seek'
START = 'start'
VIDEO_IDS = 'video_ids'

INHERITED_PARAMS = frozenset((
    ADDON_ID_PARAM,
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
    ITEM_FILTER,
    ITEMS_PER_PAGE,
    PLAY_FORCE_AUDIO,
    PLAY_TIMESHIFT,
    PLAY_PROMPT_QUALITY,
    PLAY_PROMPT_SUBTITLES,
    PLAY_USING,
))


__all__ = (
    # Addon paths
    'ADDON_ID',
    'ADDON_PATH',
    'DATA_PATH',
    'MEDIA_PATH',
    'RESOURCE_PATH',
    'TEMP_PATH',

    # Const values
    'BOOL_FROM_STR',
    'VALUE_TO_STR',
    'YOUTUBE_HOSTNAMES',

    # Flags
    'ABORT_FLAG',
    'BUSY_FLAG',
    'SERVICE_RUNNING_FLAG',
    'TRAKT_PAUSE_FLAG',
    'WAIT_END_FLAG',

    # Container Info
    'CURRENT_CONTAINER_INFO',
    'PLUGIN_CONTAINER_INFO',
    'CURRENT_ITEM',
    'FOLDER_NAME',
    'FOLDER_URI',
    'HAS_FILES',
    'HAS_FOLDERS',
    'HAS_PARENT',
    'NUM_ALL_ITEMS',
    'SCROLLING',
    'UPDATING',

    # ListItem Info
    'CONTAINER_LISTITEM_INFO',
    'LISTITEM_INFO',
    'ARTIST',
    'LABEL',
    'PLAY_COUNT',
    'RESUMABLE',
    'TITLE',
    'URI',

    # ListItem Properties
    'CONTAINER_LISTITEM_PROP',
    'LISTITEM_PROP',
    'BOOKMARK_ID',
    'CHANNEL_ID',
    'PLAY_COUNT_PROP',
    'PLAYLIST_ID',
    'PLAYLIST_ITEM_ID',
    'SUBSCRIPTION_ID',
    'VIDEO_ID',

    # Events
    'CHECK_SETTINGS',
    'CONTEXT_MENU',
    'FILE_READ',
    'FILE_WRITE',
    'KEYMAP',
    'PLAYBACK_INIT',
    'PLAYBACK_FAILED',
    'PLAYBACK_STARTED',
    'PLAYBACK_STOPPED',
    'REFRESH_CONTAINER',
    'RELOAD_ACCESS_MANAGER',
    'SERVICE_IPC',
    'SYNC_LISTITEM',

    # Sleep/wakeup states
    'PLUGIN_SLEEPING',
    'PLUGIN_WAKEUP',
    'SERVER_WAKEUP',

    # Play options
    'PLAY_CANCELLED',
    'PLAY_FORCE_AUDIO',
    'PLAY_FORCED',
    'PLAY_PROMPT_QUALITY',
    'PLAY_PROMPT_SUBTITLES',
    'PLAY_STRM',
    'PLAY_TIMESHIFT',
    'PLAY_USING',
    'FORCE_PLAY_PARAMS',

    # Stored data
    'PROPERTY',
    'PROPERTY_AS_LABEL',
    'CONTAINER_ID',
    'CONTAINER_FOCUS',
    'CONTAINER_POSITION',
    'DEVELOPER_CONFIGS',
    'LICENSE_TOKEN',
    'LICENSE_URL',
    'MARK_AS_LABEL',
    'PLAYER_DATA',
    'PLAYER_VIDEO_ID',
    'PLAYLIST_PATH',
    'PLAYLIST_POSITION',
    'REROUTE_PATH',

    # Routing parameters
    'WINDOW_CACHE',
    'WINDOW_FALLBACK',
    'WINDOW_REPLACE',
    'WINDOW_RETURN',

    # Plugin url query parameters
    'ACTION',
    'ADDON_ID_PARAM',
    'CHANNEL_IDS',
    'CLIP',
    'END',
    'FANART_TYPE',
    'HIDE_CHANNELS',
    'HIDE_FOLDERS',
    'HIDE_LIVE',
    'HIDE_MEMBERS',
    'HIDE_NEXT_PAGE',
    'HIDE_PLAYLISTS',
    'HIDE_PROGRESS',
    'HIDE_SEARCH',
    'HIDE_SHORTS',
    'HIDE_VIDEOS',
    'INCOGNITO',
    'ITEM_FILTER',
    'ITEMS_PER_PAGE',
    'LIVE',
    'ORDER',
    'PAGE',
    'PLAYLIST_IDS',
    'SCREENSAVER',
    'SEEK',
    'START',
    'VIDEO_IDS',

    'INHERITED_PARAMS',

    # Other constants
    'CONTENT',
    'PATHS',
    'SETTINGS',
    'SORT',

    # Languages and Regions
    'DEFAULT_LANGUAGES',
    'DEFAULT_REGIONS',
    'TRANSLATION_LANGUAGES',
)
