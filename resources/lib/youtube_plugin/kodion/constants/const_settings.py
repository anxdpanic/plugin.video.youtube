# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

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
MPD_STREAM_FEATURES = 'kodion.mpd.stream.features'  # (list[str])
VIDEO_STREAM_SELECT = 'kodion.video.stream.select'  # (int)
VIDEO_QUALITY_ASK = 'kodion.video.quality.ask'  # (bool)
VIDEO_QUALITY = 'kodion.video.quality'  # (int)
AUDIO_ONLY = 'kodion.audio_only'  # (bool)

SUBTITLE_SELECTION = 'kodion.subtitle.languages.num'  # (int)
SUBTITLE_DOWNLOAD = 'kodion.subtitle.download'  # (bool)

ITEMS_PER_PAGE = 'kodion.content.max_per_page'  # (int)
HIDE_VIDEOS = 'youtube.view.hide_videos'  # (list[str])
SHORTS_DURATION = 'youtube.view.shorts.duration'  # (int)
FILTER_LIST = 'youtube.view.filter.list'  # (str)

SUBSCRIPTIONS_FILTER_ENABLED = 'youtube.folder.my_subscriptions_filtered.show'  # (bool)
SUBSCRIPTIONS_FILTER_BLACKLIST = 'youtube.filter.my_subscriptions_filtered.blacklist'  # (bool)
SUBSCRIPTIONS_FILTER_LIST = 'youtube.filter.my_subscriptions_filtered.list'  # (str)

SAFE_SEARCH = 'kodion.safe.search'  # (int)
AGE_GATE = 'kodion.age.gate'  # (bool)

API_CONFIG_PAGE = 'youtube.api.config.page'  # (bool)
API_KEY = 'youtube.api.key'  # (str)
API_ID = 'youtube.api.id'  # (str)
API_SECRET = 'youtube.api.secret'  # (str)
ALLOW_DEV_KEYS = 'youtube.allow.dev.keys'  # (bool)

SHOW_SIGN_IN = 'youtube.folder.sign.in.show'  # (bool)
SHOW_MY_SUBSCRIPTIONS = 'youtube.folder.my_subscriptions.show'  # (bool)
SHOW_MY_SUBSCRIPTIONS_FILTERED = 'youtube.folder.my_subscriptions_filtered.show'  # (bool)
SHOW_RECOMMENDATIONS = 'youtube.folder.recommendations.show'  # (bool)
SHOW_RELATED = 'youtube.folder.related.show'  # (bool)
SHOW_TRENDING = 'youtube.folder.popular_right_now.show'  # (bool)
SHOW_SEARCH = 'youtube.folder.search.show'  # (bool)
SHOW_QUICK_SEARCH = 'youtube.folder.quick_search.show'  # (bool)
SHOW_INCOGNITO_SEARCH = 'youtube.folder.quick_search_incognito.show'  # (bool)
SHOW_MY_LOCATION = 'youtube.folder.my_location.show'  # (bool)
SHOW_MY_CHANNEL = 'youtube.folder.my_channel.show'  # (bool)
SHOW_WATCH_LATER = 'youtube.folder.watch_later.show'  # (bool)
SHOW_LIKED = 'youtube.folder.liked_videos.show'  # (bool)
SHOW_DISLIKED = 'youtube.folder.disliked_videos.show'  # (bool)
SHOW_HISTORY = 'youtube.folder.history.show'  # (bool)
SHOW_PLAYLISTS = 'youtube.folder.playlists.show'  # (bool)
SHOW_SAVED_PLAYLISTS = 'youtube.folder.saved.playlists.show'  # (bool)
SHOW_SUBSCRIPTIONS = 'youtube.folder.subscriptions.show'  # (bool)
SHOW_BOOKMARKS = 'youtube.folder.bookmarks.show'  # (bool)
SHOW_BROWSE_CHANNELS = 'youtube.folder.browse_channels.show'  # (bool)
SHOW_COMPlETED_LIVE = 'youtube.folder.completed.live.show'  # (bool)
SHOW_UPCOMING_LIVE = 'youtube.folder.upcoming.live.show'  # (bool)
SHOW_LIVE = 'youtube.folder.live.show'  # (bool)
SHOW_SWITCH_USER = 'youtube.folder.switch.user.show'  # (bool)
SHOW_SIGN_OUT = 'youtube.folder.sign.out.show'  # (bool)
SHOW_SETUP_WIZARD = 'youtube.folder.settings.show'  # (bool)
SHOW_SETTINGS = 'youtube.folder.settings.advanced.show'  # (bool)

WATCH_LATER_PLAYLIST = 'youtube.folder.watch_later.playlist'  # (str)
HISTORY_PLAYLIST = 'youtube.folder.history.playlist'  # (str)

SUPPORT_ALTERNATIVE_PLAYER = 'kodion.support.alternative_player'  # (bool)
DEFAULT_PLAYER_WEB_URLS = 'kodion.default_player.web_urls'  # (bool)
ALTERNATIVE_PLAYER_WEB_URLS = 'kodion.alternative_player.web_urls'  # (bool)
ALTERNATIVE_PLAYER_MPD = 'kodion.alternative_player.mpd'  # (bool)

USE_ISA = 'kodion.video.quality.isa'  # (bool)
LIVE_STREAMS = 'kodion.live_stream.selection'  # (int)

USE_LOCAL_HISTORY = 'kodion.history.local'  # (bool)
USE_REMOTE_HISTORY = 'kodion.history.remote'  # (bool)

SEARCH_SIZE = 'kodion.search.size'  # (int)
CACHE_SIZE = 'kodion.cache.size'  # (int)

CHANNEL_NAME_ALIASES = 'youtube.view.channel_name.aliases'  # (list[str])
DETAILED_DESCRIPTION = 'youtube.view.description.details'  # (bool)
DETAILED_LABELS = 'youtube.view.label.details'  # (bool)
LABEL_COLOR = 'youtube.view.label.color'  # (str)

THUMB_SIZE = 'kodion.thumbnail.size'  # (int)
THUMB_SIZE_BEST = 2
FANART_SELECTION = 'kodion.fanart.selection'  # (int)
FANART_CHANNEL = 2
FANART_THUMBNAIL = 3

LANGUAGE = 'youtube.language'  # (str)
REGION = 'youtube.region'  # (str)
LOCATION = 'youtube.location'  # (str)
LOCATION_RADIUS = 'youtube.location.radius'  # (int)

PLAY_SUGGESTED = 'youtube.suggested_videos'  # (bool)

PLAY_COUNT_MIN_PERCENT = 'kodion.play_count.percent'  # (int)

RATE_VIDEOS = 'youtube.post.play.rate'  # (bool)
RATE_PLAYLISTS = 'youtube.post.play.rate.playlists'  # (bool)
PLAY_REFRESH = 'youtube.post.play.refresh'  # (bool)

WATCH_LATER_REMOVE = 'youtube.playlist.watchlater.autoremove'  # (bool)

VERIFY_SSL = 'requests.ssl.verify'  # (bool)
CONNECT_TIMEOUT = 'requests.timeout.connect'  # (int)
READ_TIMEOUT = 'requests.timeout.read'  # (int)
REQUESTS_CACHE_SIZE = 'requests.cache.size'  # (int)

PROXY_SOURCE = 'requests.proxy.source'  # (int)
PROXY_ENABLED = 'requests.proxy.enabled'  # (bool)
PROXY_TYPE = 'requests.proxy.type'  # (int)
PROXY_SERVER = 'requests.proxy.server'  # (str)
PROXY_PORT = 'requests.proxy.port'  # (int)
PROXY_USERNAME = 'requests.proxy.username'  # (str)
PROXY_PASSWORD = 'requests.proxy.password'  # (str)

HTTPD_PORT = 'kodion.http.port'  # (int)
HTTPD_LISTEN = 'kodion.http.listen'  # (str)
HTTPD_WHITELIST = 'kodion.http.ip.whitelist'  # (str)
HTTPD_IDLE_SLEEP = 'youtube.http.idle_sleep'  # (bool)
HTTPD_STREAM_REDIRECT = 'youtube.http.stream_redirect'  # (bool)

LOG_LEVEL = 'kodion.debug.log.level'  # (int)
EXEC_LIMIT = 'kodion.debug.exec.limit'  # (int)
