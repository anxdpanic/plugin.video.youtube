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

BUSY_FLAG = 'busy'
SWITCH_PLAYER_FLAG = 'switch_player'
PLAYLIST_POSITION = 'playlist_position'
WAIT_FLAG = 'builtin_running'

__all__ = (
    'ADDON_ID',
    'ADDON_PATH',
    'BUSY_FLAG',
    'DATA_PATH',
    'MEDIA_PATH',
    'PLAYLIST_POSITION',
    'RESOURCE_PATH',
    'SWITCH_PLAYER_FLAG',
    'TEMP_PATH',
    'VALUE_FROM_STR',
    'WAIT_FLAG',
    'content',
    'paths',
    'settings',
    'sort',
)
