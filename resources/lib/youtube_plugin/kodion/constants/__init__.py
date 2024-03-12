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

WAIT_FLAG = 'builtin_running'

__all__ = (
    'ADDON_ID',
    'ADDON_PATH',
    'DATA_PATH',
    'MEDIA_PATH',
    'RESOURCE_PATH',
    'TEMP_PATH',
    'WAIT_FLAG',
    'content',
    'paths',
    'settings',
    'sort',
)
