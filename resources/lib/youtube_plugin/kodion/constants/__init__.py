# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from . import (
    const_content_types as content,
    const_paths as paths,
    const_settings as settings,
    const_sort_methods as sort,
)


ADDON_ID = 'plugin.video.youtube'
ADDON_PATH = 'special://home/addons/{id}'.format(id=ADDON_ID)
DATA_PATH = 'special://profile/addon_data/{id}'.format(id=ADDON_ID)
MEDIA_PATH = ADDON_PATH + '/resources/media'
RESOURCE_PATH = ADDON_PATH + '/resources'
TEMP_PATH = 'special://temp/{id}'.format(id=ADDON_ID)

VALUE_FROM_STR = {
    '0': False,
    '1': True,
    'false': False,
    'true': True,
}

ABORT_FLAG = 'abort_requested'
BUSY_FLAG = 'busy'
CHANNEL_ID = 'channel_id'
CHECK_SETTINGS = 'check_settings'
DEVELOPER_CONFIGS = 'configs'
CONTENT_TYPE = 'content_type'
LICENSE_TOKEN = 'license_token'
LICENSE_URL = 'license_url'
PLAY_COUNT = 'video_play_count'
PLAY_FORCE_AUDIO = 'audio_only'
PLAY_PROMPT_QUALITY = 'ask_for_quality'
PLAY_PROMPT_SUBTITLES = 'prompt_for_subtitles'
PLAYER_DATA = 'player_json'
PLAYLIST_ID = 'playlist_id'
PLAYLISTITEM_ID = 'playlistitem_id'
PLAYLIST_PATH = 'playlist_path'
PLAYLIST_POSITION = 'playlist_position'
REFRESH_CONTAINER = 'refresh_container'
RELOAD_ACCESS_MANAGER = 'reload_access_manager'
REROUTE = 'reroute'
SLEEPING = 'sleeping'
SUBSCRIPTION_ID = 'subscription_id'
SWITCH_PLAYER_FLAG = 'switch_player'
VIDEO_ID = 'video_id'
WAIT_FLAG = 'builtin_running'
WAKEUP = 'wakeup'

__all__ = (
    'ABORT_FLAG',
    'ADDON_ID',
    'ADDON_PATH',
    'BUSY_FLAG',
    'CHANNEL_ID',
    'CHECK_SETTINGS',
    'CONTENT_TYPE',
    'DATA_PATH',
    'DEVELOPER_CONFIGS',
    'LICENSE_TOKEN',
    'LICENSE_URL',
    'MEDIA_PATH',
    'PLAY_COUNT',
    'PLAY_FORCE_AUDIO',
    'PLAY_PROMPT_QUALITY',
    'PLAY_PROMPT_SUBTITLES',
    'PLAYER_DATA',
    'PLAYLIST_ID',
    'PLAYLISTITEM_ID',
    'PLAYLIST_PATH',
    'PLAYLIST_POSITION',
    'REFRESH_CONTAINER',
    'RELOAD_ACCESS_MANAGER',
    'RESOURCE_PATH',
    'REROUTE',
    'SLEEPING',
    'SUBSCRIPTION_ID',
    'SWITCH_PLAYER_FLAG',
    'TEMP_PATH',
    'VALUE_FROM_STR',
    'VIDEO_ID',
    'WAIT_FLAG',
    'WAKEUP',
    'content',
    'paths',
    'settings',
    'sort',
)
