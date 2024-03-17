# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from . import datetime_parser
from .methods import (
    create_path,
    duration_to_seconds,
    find_best_fit,
    find_video_id,
    friendly_number,
    get_kodi_setting_bool,
    get_kodi_setting_value,
    loose_version,
    make_dirs,
    merge_dicts,
    rm_dir,
    seconds_to_duration,
    select_stream,
    strip_html_from_text,
    to_unicode,
    validate_ip_address,
)
from .system_version import current_system_version


__all__ = (
    'create_path',
    'current_system_version',
    'datetime_parser',
    'duration_to_seconds',
    'find_best_fit',
    'find_video_id',
    'friendly_number',
    'get_kodi_setting_bool',
    'get_kodi_setting_value',
    'loose_version',
    'make_dirs',
    'merge_dicts',
    'rm_dir',
    'seconds_to_duration',
    'select_stream',
    'strip_html_from_text',
    'to_unicode',
    'validate_ip_address',
)
