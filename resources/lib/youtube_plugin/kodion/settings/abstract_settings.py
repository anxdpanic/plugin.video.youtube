# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import sys

from ..constants import settings
from ..utils import current_system_version, validate_ip_address


class AbstractSettings(object):
    _vars = vars()
    for name, value in settings.__dict__.items():
        _vars[name] = value
    del _vars

    VALUE_FROM_STR = {
        'false': False,
        'true': True,
    }

    _echo = False
    _cache = {}
    _check_set = True
    _instance = None

    @classmethod
    def flush(cls, xbmc_addon):
        raise NotImplementedError()

    def get_bool(self, setting, default=None, echo=None):
        raise NotImplementedError()

    def set_bool(self, setting, value, echo=None):
        raise NotImplementedError()

    def get_int(self, setting, default=-1, converter=None, echo=None):
        raise NotImplementedError()

    def set_int(self, setting, value, echo=None):
        raise NotImplementedError()

    def get_string(self, setting, default='', echo=None):
        raise NotImplementedError()

    def set_string(self, setting, value, echo=None):
        raise NotImplementedError()

    def get_string_list(self, setting, default=None, echo=None):
        raise NotImplementedError()

    def set_string_list(self, setting, value, echo=None):
        raise NotImplementedError()

    def open_settings(self):
        raise NotImplementedError()

    def items_per_page(self, value=None):
        if value is not None:
            return self.set_int(settings.ITEMS_PER_PAGE, value)
        return self.get_int(settings.ITEMS_PER_PAGE, 50)

    _VIDEO_QUALITY_MAP = {
        0: 240,
        1: 360,
        2: 480,  # 576 seems not to work well
        3: 720,
        4: 1080,
    }

    def get_video_quality(self, quality_map_override=None):
        if quality_map_override is not None:
            video_quality_map = quality_map_override
        else:
            video_quality_map = self._VIDEO_QUALITY_MAP
        value = self.get_int(settings.VIDEO_QUALITY, 3)
        return video_quality_map[value]

    def ask_for_video_quality(self):
        return (self.get_bool(settings.VIDEO_QUALITY_ASK, False)
                or self.get_int(settings.MPD_STREAM_SELECT) == 4)

    def show_fanart(self):
        return self.get_bool(settings.SHOW_FANART, True)

    def cache_size(self, value=None):
        if value is not None:
            return self.set_int(settings.CACHE_SIZE, value)
        return self.get_int(settings.CACHE_SIZE, 20)

    def get_search_history_size(self):
        return self.get_int(settings.SEARCH_SIZE, 10)

    def is_setup_wizard_enabled(self):
        # Increment min_required on new release to enable oneshot on first run
        min_required = 2
        forced_runs = self.get_int(settings.SETUP_WIZARD_RUNS, min_required - 1)
        if forced_runs < min_required:
            self.set_int(settings.SETUP_WIZARD_RUNS, min_required)
            return True
        return self.get_bool(settings.SETUP_WIZARD, False)

    def support_alternative_player(self, value=None):
        if value is not None:
            return self.set_bool(settings.SUPPORT_ALTERNATIVE_PLAYER, value)
        return self.get_bool(settings.SUPPORT_ALTERNATIVE_PLAYER, False)

    def alternative_player_web_urls(self, value=None):
        if value is not None:
            return self.set_bool(settings.ALTERNATIVE_PLAYER_WEB_URLS, value)
        return self.get_bool(settings.ALTERNATIVE_PLAYER_WEB_URLS, False)

    def use_isa(self, value=None):
        if value is not None:
            return self.set_bool(settings.USE_ISA, value)
        return self.get_bool(settings.USE_ISA, False)

    def subtitle_download(self):
        return self.get_bool(settings.SUBTITLE_DOWNLOAD, False)

    def audio_only(self):
        return self.get_bool(settings.AUDIO_ONLY, False)

    def get_subtitle_selection(self):
        return self.get_int(settings.SUBTITLE_SELECTION, 0)

    def set_subtitle_selection(self, value):
        return self.set_int(settings.SUBTITLE_SELECTION, value)

    def set_subtitle_download(self, value):
        return self.set_bool(settings.SUBTITLE_DOWNLOAD, value)

    def use_thumbnail_size(self):
        size = self.get_int(settings.THUMB_SIZE, 0)
        sizes = {0: 'medium', 1: 'high'}
        return sizes[size]

    def safe_search(self):
        index = self.get_int(settings.SAFE_SEARCH, 0)
        values = {0: 'moderate', 1: 'none', 2: 'strict'}
        return values[index]

    def age_gate(self):
        return self.get_bool(settings.AGE_GATE, True)

    def verify_ssl(self):
        verify = self.get_bool(settings.VERIFY_SSL, False)
        if sys.version_info <= (2, 7, 9):
            verify = False
        return verify

    def get_timeout(self):
        connect_timeout = self.get_int(settings.CONNECT_TIMEOUT, 9) + 0.5
        read_timout = self.get_int(settings.READ_TIMEOUT, 27)
        return connect_timeout, read_timout

    def allow_dev_keys(self):
        return self.get_bool(settings.ALLOW_DEV_KEYS, False)

    def use_mpd_videos(self, value=None):
        if self.use_isa():
            if value is not None:
                return self.set_bool(settings.MPD_VIDEOS, value)
            return self.get_bool(settings.MPD_VIDEOS, True)
        return False

    _LIVE_STREAM_TYPES = {
        0: 'mpegts',
        1: 'hls',
        2: 'isa_hls',
        3: 'isa_mpd',
    }

    def live_stream_type(self, value=None):
        if self.use_isa():
            default = 2
            setting = settings.LIVE_STREAMS + '.1'
        else:
            default = 0
            setting = settings.LIVE_STREAMS + '.2'
        if value is not None:
            return self.set_int(setting, value)
        value = self.get_int(setting, default)
        if value in self._LIVE_STREAM_TYPES:
            return self._LIVE_STREAM_TYPES[value]
        return self._LIVE_STREAM_TYPES[default]

    def use_isa_live_streams(self):
        if self.use_isa():
            return self.get_int(settings.LIVE_STREAMS + '.1', 2) > 1
        return False

    def use_mpd_live_streams(self):
        if self.use_isa():
            return self.get_int(settings.LIVE_STREAMS + '.1', 2) == 3
        return False

    def httpd_port(self, value=None):
        default = 50152

        if value is None:
            port = self.get_int(settings.HTTPD_PORT, default)
        else:
            port = value

        try:
            port = int(port)
        except ValueError:
            port = default

        if value is not None:
            return self.set_int(settings.HTTPD_PORT, port)
        return port

    def httpd_listen(self, value=None):
        default = '0.0.0.0'

        if value is None:
            ip_address = self.get_string(settings.HTTPD_LISTEN, default)
        else:
            ip_address = value

        octets = validate_ip_address(ip_address)
        ip_address = '.'.join(map(str, octets))

        if value is not None:
            return self.set_string(settings.HTTPD_LISTEN, ip_address)
        return ip_address

    def httpd_whitelist(self):
        whitelist = self.get_string(settings.HTTPD_WHITELIST, '')
        whitelist = ''.join(whitelist.split()).split(',')
        allow_list = []
        for ip_address in whitelist:
            octets = validate_ip_address(ip_address)
            if not any(octets):
                continue
            allow_list.append('.'.join(map(str, octets)))
        return allow_list

    def api_config_page(self):
        return self.get_bool(settings.API_CONFIG_PAGE, False)

    def api_id(self, new_id=None):
        if new_id is not None:
            self.set_string(settings.API_ID, new_id)
            return new_id
        return self.get_string(settings.API_ID)

    def api_key(self, new_key=None):
        if new_key is not None:
            self.set_string(settings.API_KEY, new_key)
            return new_key
        return self.get_string(settings.API_KEY)

    def api_secret(self, new_secret=None):
        if new_secret is not None:
            self.set_string(settings.API_SECRET, new_secret)
            return new_secret
        return self.get_string(settings.API_SECRET)

    def get_location(self):
        location = self.get_string(settings.LOCATION, '').replace(' ', '').strip()
        coords = location.split(',')
        latitude = longitude = None
        if len(coords) == 2:
            try:
                latitude = float(coords[0])
                longitude = float(coords[1])
                if latitude > 90.0 or latitude < -90.0:
                    latitude = None
                if longitude > 180.0 or longitude < -180.0:
                    longitude = None
            except ValueError:
                latitude = longitude = None
        if latitude and longitude:
            return '{lat},{long}'.format(lat=latitude, long=longitude)
        return ''

    def set_location(self, value):
        self.set_string(settings.LOCATION, value)

    def get_location_radius(self):
        return ''.join((self.get_int(settings.LOCATION_RADIUS, 500, str), 'km'))

    def get_play_count_min_percent(self):
        return self.get_int(settings.PLAY_COUNT_MIN_PERCENT, 0)

    def use_local_history(self):
        return self.get_bool(settings.USE_LOCAL_HISTORY, False)

    def use_remote_history(self):
        return self.get_bool(settings.USE_REMOTE_HISTORY, False)

    # Selections based on max width and min height at common (utra-)wide aspect ratios
    _QUALITY_SELECTIONS = {                                                 # Setting | Resolution
        7:   {'width': 7680, 'height': 3148, 'label': '4320p{0} (8K){1}'},  #   7     |   4320p 8K
        6:   {'width': 3840, 'height': 1080, 'label': '2160p{0} (4K){1}'},  #   6     |   2160p 4K
        5:   {'width': 2560, 'height': 984, 'label': '1440p{0} (QHD){1}'},  #   5     |   1440p 2.5K / QHD
        4.1: {'width': 2048, 'height': 858, 'label': '1152p{0} (2K){1}'},   #   N/A   |   1152p 2K / QWXGA
        4:   {'width': 1920, 'height': 787, 'label': '1080p{0} (FHD){1}'},  #   4     |   1080p FHD
        3:   {'width': 1280, 'height': 525, 'label': '720p{0} (HD){1}'},    #   3     |   720p  HD
        2:   {'width': 854, 'height': 350, 'label': '480p{0}{1}'},          #   2     |   480p
        1:   {'width': 640, 'height': 263, 'label': '360p{0}{1}'},          #   1     |   360p
        0:   {'width': 426, 'height': 175, 'label': '240p{0}{1}'},          #   0     |   240p
        -1:  {'width': 256, 'height': 105, 'label': '144p{0}{1}'},          #   N/A   |   144p
        -2:  {'width': 0, 'height': 0, 'label': '{2}p{0}{1}'},              #   N/A   |   Custom
    }

    def mpd_video_qualities(self, value=None):
        if value is not None:
            return self.set_int(settings.MPD_QUALITY_SELECTION, value)
        if not self.use_mpd_videos():
            return []
        value = self.get_int(settings.MPD_QUALITY_SELECTION, 4)
        return [quality
                for key, quality in sorted(self._QUALITY_SELECTIONS.items(),
                                           reverse=True)
                if value >= key]

    def stream_features(self, value=None):
        if value is not None:
            return self.set_string_list(settings.MPD_STREAM_FEATURES, value)
        return frozenset(self.get_string_list(settings.MPD_STREAM_FEATURES))

    _STREAM_SELECT = {
        1: 'auto',
        2: 'list',
        3: 'auto+list',
        4: 'ask+auto+list',
    }

    def stream_select(self, value=None):
        if value is not None:
            return self.set_int(settings.MPD_STREAM_SELECT, value)
        default = 3
        value = self.get_int(settings.MPD_STREAM_SELECT, default)
        if value in self._STREAM_SELECT:
            return self._STREAM_SELECT[value]
        return self._STREAM_SELECT[default]

    def hide_short_videos(self):
        return self.get_bool(settings.HIDE_SHORT_VIDEOS, False)

    def client_selection(self, value=None):
        if value is not None:
            return self.set_int(settings.CLIENT_SELECTION, value)
        return self.get_int(settings.CLIENT_SELECTION, 0)

    def show_detailed_description(self, value=None):
        if value is not None:
            return self.set_bool(settings.DETAILED_DESCRIPTION, value)
        return self.get_bool(settings.DETAILED_DESCRIPTION, True)

    def show_detailed_labels(self, value=None):
        if value is not None:
            return self.set_bool(settings.DETAILED_LABELS, value)
        return self.get_bool(settings.DETAILED_LABELS, True)

    def get_language(self):
        return self.get_string(settings.LANGUAGE, 'en_US').replace('_', '-')

    def get_region(self):
        return self.get_string(settings.REGION, 'US')

    def get_watch_later_playlist(self):
        return self.get_string(settings.WATCH_LATER_PLAYLIST, '').strip()

    def set_watch_later_playlist(self, value):
        return self.set_string(settings.WATCH_LATER_PLAYLIST, value)

    def get_history_playlist(self):
        return self.get_string(settings.HISTORY_PLAYLIST, '').strip()

    def set_history_playlist(self, value):
        return self.set_string(settings.HISTORY_PLAYLIST, value)

    if current_system_version.compatible(20, 0):
        def get_label_color(self, label_part):
            setting_name = '.'.join((settings.LABEL_COLOR, label_part))
            return self.get_string(setting_name, 'white')
    else:
        _COLOR_MAP = {
            'commentCount': 'cyan',
            'favoriteCount': 'gold',
            'likeCount': 'lime',
            'viewCount': 'lightblue',
        }

        def get_label_color(self, label_part):
            return self._COLOR_MAP.get(label_part, 'white')
