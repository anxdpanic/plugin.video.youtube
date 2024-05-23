# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals


SETUP_WIZARD = 'kodion.setup_wizard'  # (bool)
SETUP_WIZARD_RUNS = 'kodion.setup_wizard.forced_runs'  # (int)
SETTINGS_END = '|end_settings_marker|'  # (bool)

MPD_VIDEOS = 'kodion.mpd.videos'  # (bool)
MPD_STREAM_SELECT = 'kodion.mpd.stream.select'  # (int)
MPD_QUALITY_SELECTION = 'kodion.mpd.quality.selection'  # (int)
MPD_STREAM_FEATURES = 'kodion.mpd.stream.features'  # (list[string])
VIDEO_QUALITY_ASK = 'kodion.video.quality.ask'  # (bool)
VIDEO_QUALITY = 'kodion.video.quality'  # (int)
AUDIO_ONLY = 'kodion.audio_only'  # (bool)

SUBTITLE_SELECTION = 'kodion.subtitle.languages.num'  # (int)
SUBTITLE_DOWNLOAD = 'kodion.subtitle.download'  # (bool)

ITEMS_PER_PAGE = 'kodion.content.max_per_page'  # (int)
HIDE_VIDEOS = 'youtube.view.hide_videos'  # (list[string])

SAFE_SEARCH = 'kodion.safe.search'  # (int)
AGE_GATE = 'kodion.age.gate'  # (bool)

API_CONFIG_PAGE = 'youtube.api.config.page'  # (bool)
API_KEY = 'youtube.api.key'  # (string)
API_ID = 'youtube.api.id'  # (string)
API_SECRET = 'youtube.api.secret'  # (string)
ALLOW_DEV_KEYS = 'youtube.allow.dev.keys'  # (bool)

WATCH_LATER_PLAYLIST = 'youtube.folder.watch_later.playlist'  # (str)
HISTORY_PLAYLIST = 'youtube.folder.history.playlist'  # (str)

CLIENT_SELECTION = 'youtube.client.selection'  # (int)
SUPPORT_ALTERNATIVE_PLAYER = 'kodion.support.alternative_player'  # (bool)
DEFAULT_PLAYER_WEB_URLS = 'kodion.default_player.web_urls'  # (bool)
ALTERNATIVE_PLAYER_WEB_URLS = 'kodion.alternative_player.web_urls'  # (bool)
ALTERNATIVE_PLAYER_ADAPTIVE = 'kodion.alternative_player.adaptive'  # (bool)

USE_ISA = 'kodion.video.quality.isa'  # (bool)
LIVE_STREAMS = 'kodion.live_stream.selection'  # (int)

USE_LOCAL_HISTORY = 'kodion.history.local'  # (bool)
USE_REMOTE_HISTORY = 'kodion.history.remote'  # (bool)

SEARCH_SIZE = 'kodion.search.size'  # (int)
CACHE_SIZE = 'kodion.cache.size'  # (int)

CHANNEL_NAME_ALIASES = 'youtube.view.channel_name.aliases'  # (list[string])
DETAILED_DESCRIPTION = 'youtube.view.description.details'  # (bool)
DETAILED_LABELS = 'youtube.view.label.details'  # (bool)
LABEL_COLOR = 'youtube.view.label.color'  # (string)

THUMB_SIZE = 'kodion.thumbnail.size'  # (int)
THUMB_SIZE_BEST = 2
FANART_SELECTION = 'kodion.fanart.selection'  # (int)
FANART_CHANNEL = 2
FANART_THUMBNAIL = 3

LANGUAGE = 'youtube.language'  # (str)
REGION = 'youtube.region'  # (str)
LOCATION = 'youtube.location'  # (str)
LOCATION_RADIUS = 'youtube.location.radius'  # (int)

PLAY_COUNT_MIN_PERCENT = 'kodion.play_count.percent'  # (int)

VERIFY_SSL = 'requests.ssl.verify'  # (bool)
CONNECT_TIMEOUT = 'requests.timeout.connect'  # (int)
READ_TIMEOUT = 'requests.timeout.read'  # (int)

HTTPD_PORT = 'kodion.http.port'  # (number)
HTTPD_LISTEN = 'kodion.http.listen'  # (string)
HTTPD_WHITELIST = 'kodion.http.ip.whitelist'  # (string)
