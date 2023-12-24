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

__all__ = (
    'ADDON_ID',
    'content',
    'paths',
    'settings',
    'sort',
)
