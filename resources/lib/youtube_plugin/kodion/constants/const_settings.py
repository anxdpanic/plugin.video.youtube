# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals


THUMB_SIZE = 'kodion.thumbnail.size'  # (int)
SHOW_FANART = 'kodion.fanart.show'  # (bool)
SAFE_SEARCH = 'kodion.safe.search'  # (int)
ITEMS_PER_PAGE = 'kodion.content.max_per_page'  # (int)
SEARCH_SIZE = 'kodion.search.size'  # (int)
CACHE_SIZE = 'kodion.cache.size'  # (int)
AUDIO_ONLY = 'kodion.audio_only'  # (bool)
AGE_GATE = 'kodion.age.gate'  # (bool)
SUBTITLE_LANGUAGE = 'kodion.subtitle.languages.num'  # (int)
SUBTITLE_DOWNLOAD = 'kodion.subtitle.download'  # (bool)
SETUP_WIZARD = 'kodion.setup_wizard'  # (bool)
LANGUAGE = 'youtube.language'  # (str)
LOCATION = 'youtube.location'  # (str)
LOCATION_RADIUS = 'youtube.location.radius'  # (int)
PLAY_COUNT_MIN_PERCENT = 'kodion.play_count.percent'  # (int)
USE_LOCAL_HISTORY = 'kodion.history.local'  # (bool)
USE_REMOTE_HISTORY = 'kodion.history.remote'  # (bool)
HIDE_SHORT_VIDEOS = 'youtube.hide_shorts'  # (bool)
DETAILED_DESCRIPTION = 'youtube.view.description.details'  # (bool)
DETAILED_LABELS = 'youtube.view.label.details'  # (bool)

SUPPORT_ALTERNATIVE_PLAYER = 'kodion.support.alternative_player'  # (bool)
ALTERNATIVE_PLAYER_WEB_URLS = 'kodion.alternative_player.web.urls'  # (bool)

ALLOW_DEV_KEYS = 'youtube.allow.dev.keys'  # (bool)

VIDEO_QUALITY = 'kodion.video.quality'  # (int)
VIDEO_QUALITY_ASK = 'kodion.video.quality.ask'  # (bool)
USE_ISA = 'kodion.video.quality.isa'  # (bool)
LIVE_STREAMS = 'kodion.live_stream.selection'  # (int)
MPD_VIDEOS = 'kodion.mpd.videos'  # (bool)
MPD_QUALITY_SELECTION = 'kodion.mpd.quality.selection'  # (int)
MPD_STREAM_FEATURES = 'kodion.mpd.stream.features'  # (list[string])
MPD_STREAM_SELECT = 'kodion.mpd.stream.select'  # (int)

VERIFY_SSL = 'requests.ssl.verify'  # (bool)
CONNECT_TIMEOUT = 'requests.timeout.connect'  # (int)
READ_TIMEOUT = 'requests.timeout.read'  # (int)

HTTPD_PORT = 'kodion.http.port'  # (number)
HTTPD_LISTEN = 'kodion.http.listen'  # (string)
HTTPD_WHITELIST = 'kodion.http.ip.whitelist'  # (string)

API_CONFIG_PAGE = 'youtube.api.config.page'  # (bool)
API_KEY = 'youtube.api.key'  # (string)
API_ID = 'youtube.api.id'  # (string)
API_SECRET = 'youtube.api.secret'  # (string)

CLIENT_SELECTION = 'youtube.client.selection'  # (int)

WATCH_LATER_PLAYLIST = 'youtube.folder.watch_later.playlist'  # (str)
HISTORY_PLAYLIST = 'youtube.folder.history.playlist'  # (str)
