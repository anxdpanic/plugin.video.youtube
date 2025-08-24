# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

INTERNAL = '/kodion'
BOOKMARKS = INTERNAL + '/bookmarks'
COMMAND = INTERNAL + '/command'
EXTERNAL_SEARCH = '/search'
GOTO_PAGE = INTERNAL + '/goto_page'
ROUTE = INTERNAL + '/route'
SEARCH = INTERNAL + '/search'
WATCH_LATER = INTERNAL + '/watch_later'
HISTORY = INTERNAL + '/playback_history'

CHANNEL = '/channel'
MY_CHANNEL = CHANNEL + '/mine'
LIKED_VIDEOS = CHANNEL + '/mine/playlist/LL'
MY_PLAYLIST = CHANNEL + '/mine/playlist'
MY_PLAYLISTS = CHANNEL + '/mine/playlists'

HOME = '/home'
MAINTENANCE = '/maintenance'
PLAY = '/play'
PLAYLIST = '/playlist'
SUBSCRIPTIONS = '/subscriptions'
VIDEO = '/video'

SPECIAL = '/special'
DESCRIPTION_LINKS = SPECIAL + '/description_links'
DISLIKED_VIDEOS = SPECIAL + '/disliked_videos'
LIVE_VIDEOS = SPECIAL + '/live'
LIVE_VIDEOS_COMPLETED = SPECIAL + '/completed_live'
LIVE_VIDEOS_UPCOMING = SPECIAL + '/upcoming_live'
MY_SUBSCRIPTIONS = SPECIAL + '/my_subscriptions'
MY_SUBSCRIPTIONS_FILTERED = SPECIAL + '/my_subscriptions_filtered'
RECOMMENDATIONS = SPECIAL + '/recommendations'
RELATED_VIDEOS = SPECIAL + '/related_videos'
SAVED_PLAYLISTS = SPECIAL + '/saved_playlists'
TRENDING = SPECIAL + '/popular_right_now'
VIDEO_COMMENTS = SPECIAL + '/parent_comments'
VIDEO_COMMENTS_THREAD = SPECIAL + '/child_comments'
VIRTUAL_PLAYLIST = SPECIAL + '/playlist'

HTTP_SERVER = '/youtube'
API = HTTP_SERVER + '/api'
API_SUBMIT = HTTP_SERVER + '/api/submit'
DRM = HTTP_SERVER + '/widevine'
IP = HTTP_SERVER + '/client_ip'
MPD = HTTP_SERVER + '/manifest/dash'
PING = HTTP_SERVER + '/ping'
REDIRECT = HTTP_SERVER + '/redirect'
STREAM_PROXY = HTTP_SERVER + '/stream'
