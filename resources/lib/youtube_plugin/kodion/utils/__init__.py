# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from . import datetime_parser
from .methods import loose_version
from .methods import *
from .search_history import SearchHistory
from .favorite_list import FavoriteList
from .watch_later_list import WatchLaterList
from .function_cache import FunctionCache
from .access_manager import AccessManager
from .http_server import get_http_server, is_httpd_live, get_client_ip_address
from .monitor import YouTubeMonitor
from .player import YouTubePlayer
from .playback_history import PlaybackHistory
from .data_cache import DataCache
from .system_version import SystemVersion
from . import ip_api


__all__ = ['SearchHistory', 'FavoriteList', 'WatchLaterList', 'FunctionCache', 'AccessManager',
           'strip_html_from_text', 'create_path', 'create_uri_path', 'find_best_fit', 'to_unicode', 'to_utf8',
           'datetime_parser', 'select_stream', 'get_http_server', 'is_httpd_live', 'YouTubeMonitor',
           'make_dirs', 'loose_version', 'ip_api', 'PlaybackHistory', 'DataCache', 'get_client_ip_address',
           'SystemVersion', 'find_video_id', 'YouTubePlayer']
