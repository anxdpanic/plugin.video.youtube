# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import sys

from ..constants import SETTINGS
from ..utils import current_system_version, validate_ip_address


class AbstractSettings(object):
    _vars = vars()
    for name, value in SETTINGS.__dict__.items():
        _vars[name] = value
    del _vars

    _echo = False
    _cache = {}
    _check_set = True

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
            return self.set_int(SETTINGS.ITEMS_PER_PAGE, value)
        return self.get_int(SETTINGS.ITEMS_PER_PAGE, 50)

    _VIDEO_QUALITY_MAP = {
        0: 240,
        1: 360,
        2: 480,  # 576 seems not to work well
        3: 720,
        4: 1080,
    }

    def fixed_video_quality(self, value=None):
        default = 3
        if value is None:
            _value = self.get_int(SETTINGS.VIDEO_QUALITY, default)
        else:
            _value = value
        if _value not in self._VIDEO_QUALITY_MAP:
            _value = default
        if value is not None:
            self.set_int(SETTINGS.VIDEO_QUALITY, _value)
        return self._VIDEO_QUALITY_MAP[_value]

    def ask_for_video_quality(self):
        if self.use_mpd_videos():
            return self.get_int(SETTINGS.MPD_STREAM_SELECT) == 4
        return self.get_bool(SETTINGS.VIDEO_QUALITY_ASK, False)

    def fanart_selection(self):
        return self.get_int(SETTINGS.FANART_SELECTION, 2)

    def cache_size(self, value=None):
        if value is not None:
            return self.set_int(SETTINGS.CACHE_SIZE, value)
        return self.get_int(SETTINGS.CACHE_SIZE, 20)

    def get_search_history_size(self):
        return self.get_int(SETTINGS.SEARCH_SIZE, 10)

    def setup_wizard_enabled(self, value=None):
        # Increment min_required on new release to enable oneshot on first run
        min_required = 5

        if value is False:
            self.set_int(SETTINGS.SETUP_WIZARD_RUNS, min_required)
            return self.set_bool(SETTINGS.SETUP_WIZARD, False)
        if value is True:
            self.set_int(SETTINGS.SETUP_WIZARD_RUNS, 0)
            return self.set_bool(SETTINGS.SETUP_WIZARD, True)

        forced_runs = self.get_int(SETTINGS.SETUP_WIZARD_RUNS, 0)
        if forced_runs < min_required:
            self.set_int(SETTINGS.SETUP_WIZARD_RUNS, min_required)
            self.set_bool(SETTINGS.SETTINGS_END, True)
            return True
        return self.get_bool(SETTINGS.SETUP_WIZARD, False)

    def support_alternative_player(self, value=None):
        if value is not None:
            return self.set_bool(SETTINGS.SUPPORT_ALTERNATIVE_PLAYER, value)
        return self.get_bool(SETTINGS.SUPPORT_ALTERNATIVE_PLAYER, False)

    def default_player_web_urls(self, value=None):
        if value is not None:
            return self.set_bool(SETTINGS.DEFAULT_PLAYER_WEB_URLS, value)
        if self.support_alternative_player():
            return False
        return self.get_bool(SETTINGS.DEFAULT_PLAYER_WEB_URLS, False)

    def alternative_player_web_urls(self, value=None):
        if value is not None:
            return self.set_bool(SETTINGS.ALTERNATIVE_PLAYER_WEB_URLS, value)
        if (self.support_alternative_player()
                and not self.alternative_player_adaptive()):
            return self.get_bool(SETTINGS.ALTERNATIVE_PLAYER_WEB_URLS, False)
        return False

    def alternative_player_adaptive(self, value=None):
        if value is not None:
            return self.set_bool(SETTINGS.ALTERNATIVE_PLAYER_ADAPTIVE, value)
        if self.support_alternative_player():
            return self.get_bool(SETTINGS.ALTERNATIVE_PLAYER_ADAPTIVE, False)
        return False

    def use_isa(self, value=None):
        if value is not None:
            return self.set_bool(SETTINGS.USE_ISA, value)
        return self.get_bool(SETTINGS.USE_ISA, False)

    def subtitle_download(self):
        return self.get_bool(SETTINGS.SUBTITLE_DOWNLOAD, False)

    def audio_only(self):
        return self.get_bool(SETTINGS.AUDIO_ONLY, False)

    def get_subtitle_selection(self):
        return self.get_int(SETTINGS.SUBTITLE_SELECTION, 0)

    def set_subtitle_selection(self, value):
        return self.set_int(SETTINGS.SUBTITLE_SELECTION, value)

    def set_subtitle_download(self, value):
        return self.set_bool(SETTINGS.SUBTITLE_DOWNLOAD, value)

    _THUMB_SIZES = {
        0: {  # Medium (16:9)
            'size': 320 * 180,
            'ratio': 320 / 180,
        },
        1: {  # High (4:3)
            'size': 480 * 360,
            'ratio': 480 / 360,
        },
        2: {  # Best available
            'size': 0,
            'ratio': 0,
        },
    }

    def get_thumbnail_size(self, value=None):
        default = 1
        if value is None:
            value = self.get_int(SETTINGS.THUMB_SIZE, default)
        if value in self._THUMB_SIZES:
            return self._THUMB_SIZES[value]
        return self._THUMB_SIZES[default]

    def safe_search(self):
        index = self.get_int(SETTINGS.SAFE_SEARCH, 0)
        values = {0: 'moderate', 1: 'none', 2: 'strict'}
        return values[index]

    def age_gate(self):
        return self.get_bool(SETTINGS.AGE_GATE, True)

    def verify_ssl(self):
        if sys.version_info <= (2, 7, 9):
            verify = False
        else:
            verify = self.get_bool(SETTINGS.VERIFY_SSL, True)
        return verify

    def get_timeout(self):
        connect_timeout = self.get_int(SETTINGS.CONNECT_TIMEOUT, 9) + 0.5
        read_timout = self.get_int(SETTINGS.READ_TIMEOUT, 27)
        return connect_timeout, read_timout

    def allow_dev_keys(self):
        return self.get_bool(SETTINGS.ALLOW_DEV_KEYS, False)

    def use_mpd_videos(self, value=None):
        if self.use_isa():
            if value is not None:
                return self.set_bool(SETTINGS.MPD_VIDEOS, value)
            return self.get_bool(SETTINGS.MPD_VIDEOS, True)
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
            setting = SETTINGS.LIVE_STREAMS + '.1'
        else:
            default = 0
            setting = SETTINGS.LIVE_STREAMS + '.2'
        if value is not None:
            return self.set_int(setting, value)
        value = self.get_int(setting, default)
        if value in self._LIVE_STREAM_TYPES:
            return self._LIVE_STREAM_TYPES[value]
        return self._LIVE_STREAM_TYPES[default]

    def use_isa_live_streams(self):
        if self.use_isa():
            return self.get_int(SETTINGS.LIVE_STREAMS + '.1', 2) > 1
        return False

    def use_mpd_live_streams(self):
        if self.use_isa():
            return self.get_int(SETTINGS.LIVE_STREAMS + '.1', 2) == 3
        return False

    def httpd_port(self, value=None):
        default = 50152

        if value is None:
            port = self.get_int(SETTINGS.HTTPD_PORT, default)
        else:
            port = value

        try:
            port = int(port)
        except ValueError:
            port = default

        if value is not None:
            return self.set_int(SETTINGS.HTTPD_PORT, port)
        return port

    def httpd_listen(self, value=None):
        default = '0.0.0.0'

        if value is None:
            ip_address = self.get_string(SETTINGS.HTTPD_LISTEN, default)
        else:
            ip_address = value

        octets = validate_ip_address(ip_address)
        ip_address = '.'.join(map(str, octets))

        if value is not None:
            return self.set_string(SETTINGS.HTTPD_LISTEN, ip_address)
        return ip_address

    def httpd_whitelist(self):
        whitelist = self.get_string(SETTINGS.HTTPD_WHITELIST, '')
        whitelist = ''.join(whitelist.split()).split(',')
        allow_list = []
        for ip_address in whitelist:
            octets = validate_ip_address(ip_address)
            if not any(octets):
                continue
            allow_list.append('.'.join(map(str, octets)))
        return allow_list

    def httpd_sleep_allowed(self, value=None):
        if value is not None:
            return self.set_bool(SETTINGS.HTTPD_IDLE_SLEEP, value)
        return self.get_bool(SETTINGS.HTTPD_IDLE_SLEEP, True)

    def api_config_page(self):
        return self.get_bool(SETTINGS.API_CONFIG_PAGE, False)

    def api_id(self, new_id=None):
        if new_id is not None:
            self.set_string(SETTINGS.API_ID, new_id)
            return new_id
        return self.get_string(SETTINGS.API_ID)

    def api_key(self, new_key=None):
        if new_key is not None:
            self.set_string(SETTINGS.API_KEY, new_key)
            return new_key
        return self.get_string(SETTINGS.API_KEY)

    def api_secret(self, new_secret=None):
        if new_secret is not None:
            self.set_string(SETTINGS.API_SECRET, new_secret)
            return new_secret
        return self.get_string(SETTINGS.API_SECRET)

    def get_location(self):
        location = self.get_string(SETTINGS.LOCATION, '').replace(' ', '').strip()
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
        self.set_string(SETTINGS.LOCATION, value)

    def get_location_radius(self):
        return ''.join((self.get_int(SETTINGS.LOCATION_RADIUS, 500, str), 'km'))

    def get_play_count_min_percent(self):
        return self.get_int(SETTINGS.PLAY_COUNT_MIN_PERCENT, 0)

    def use_local_history(self):
        return self.get_bool(SETTINGS.USE_LOCAL_HISTORY, False)

    def use_remote_history(self):
        return self.get_bool(SETTINGS.USE_REMOTE_HISTORY, False)

    # Selections based on max width and min height at common (utra-)wide aspect ratios
    _QUALITY_SELECTIONS = {                                                                         # Setting | Resolution
        7:   {'width': 7680, 'min_height': 3148, 'nom_height': 4320, 'label': '{0}p{1} (8K){2}'},   #   7     |   4320p 8K
        6:   {'width': 3840, 'min_height': 1080, 'nom_height': 2160, 'label': '{0}p{1} (4K){2}'},   #   6     |   2160p 4K
        5:   {'width': 2560, 'min_height': 984,  'nom_height': 1440, 'label': '{0}p{1} (QHD){2}'},  #   5     |   1440p 2.5K / QHD
        4.1: {'width': 2048, 'min_height': 858,  'nom_height': 1152, 'label': '{0}p{1} (2K){2}'},   #   N/A   |   1152p 2K / QWXGA
        4:   {'width': 1920, 'min_height': 787,  'nom_height': 1080, 'label': '{0}p{1} (FHD){2}'},  #   4     |   1080p FHD
        3:   {'width': 1280, 'min_height': 525,  'nom_height': 720,  'label': '{0}p{1} (HD){2}'},   #   3     |   720p  HD
        2:   {'width': 854,  'min_height': 350,  'nom_height': 480,  'label': '{0}p{1}{2}'},        #   2     |   480p
        1:   {'width': 640,  'min_height': 263,  'nom_height': 360,  'label': '{0}p{1}{2}'},        #   1     |   360p
        0:   {'width': 426,  'min_height': 175,  'nom_height': 240,  'label': '{0}p{1}{2}'},        #   0     |   240p
        -1:  {'width': 256,  'min_height': 105,  'nom_height': 144,  'label': '{0}p{1}{2}'},        #   N/A   |   144p
        -2:  {'width': 0,    'min_height': 0,    'nom_height': 0,    'label': '{0}p{1}{2}'},        #   N/A   |   Custom
    }

    def mpd_video_qualities(self, value=None):
        if value is not None:
            return self.set_int(SETTINGS.MPD_QUALITY_SELECTION, value)
        if not self.use_mpd_videos():
            return []
        value = self.get_int(SETTINGS.MPD_QUALITY_SELECTION, 4)
        return [quality
                for key, quality in sorted(self._QUALITY_SELECTIONS.items(),
                                           reverse=True)
                if value >= key]

    def stream_features(self, value=None):
        if value is not None:
            return self.set_string_list(SETTINGS.MPD_STREAM_FEATURES, value)
        return frozenset(self.get_string_list(SETTINGS.MPD_STREAM_FEATURES))

    _STREAM_SELECT = {
        1: 'auto',
        2: 'list',
        3: 'auto+list',
        4: 'ask+auto+list',
    }

    def stream_select(self, value=None):
        if self.use_mpd_videos():
            setting = SETTINGS.MPD_STREAM_SELECT
            default = 3
        else:
            setting = SETTINGS.VIDEO_STREAM_SELECT
            default = 2

        if value is not None:
            return self.set_int(setting, value)
        value = self.get_int(setting, default)
        if value in self._STREAM_SELECT:
            return self._STREAM_SELECT[value]
        return self._STREAM_SELECT[default]

    _DEFAULT_FILTER = {
        'shorts': True,
        'upcoming': True,
        'upcoming_live': True,
        'live': True,
        'premieres': True,
        'completed': True,
        'vod': True,
    }

    def item_filter(self, update=None, override=None):
        types = dict.fromkeys(
            self.get_string_list(SETTINGS.HIDE_VIDEOS)
            if override is None else
            override,
            False
        )
        types = dict(self._DEFAULT_FILTER, **types)
        if update:
            if 'live_folder' in update:
                if 'live_folder' in types:
                    types.update(update)
                else:
                    types.update({
                        'upcoming': True,
                        'upcoming_live': True,
                        'live': True,
                        'premieres': True,
                        'completed': True,
                    })
                types['vod'] = False
            else:
                types.update(update)
        return types

    def show_detailed_description(self, value=None):
        if value is not None:
            return self.set_bool(SETTINGS.DETAILED_DESCRIPTION, value)
        return self.get_bool(SETTINGS.DETAILED_DESCRIPTION, True)

    def show_detailed_labels(self, value=None):
        if value is not None:
            return self.set_bool(SETTINGS.DETAILED_LABELS, value)
        return self.get_bool(SETTINGS.DETAILED_LABELS, True)

    def get_language(self):
        return self.get_string(SETTINGS.LANGUAGE, 'en_US').replace('_', '-')

    def set_language(self, language_id):
        return self.set_string(SETTINGS.LANGUAGE, language_id)

    def get_region(self):
        return self.get_string(SETTINGS.REGION, 'US')

    def set_region(self, region_id):
        return self.set_string(SETTINGS.REGION, region_id)

    def get_watch_later_playlist(self):
        return self.get_string(SETTINGS.WATCH_LATER_PLAYLIST, '').strip()

    def set_watch_later_playlist(self, value):
        return self.set_string(SETTINGS.WATCH_LATER_PLAYLIST, value)

    def get_history_playlist(self):
        return self.get_string(SETTINGS.HISTORY_PLAYLIST, '').strip()

    def set_history_playlist(self, value):
        return self.set_string(SETTINGS.HISTORY_PLAYLIST, value)

    if current_system_version.compatible(20, 0):
        def get_label_color(self, label_part):
            setting_name = '.'.join((SETTINGS.LABEL_COLOR, label_part))
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

    def get_channel_name_aliases(self):
        return frozenset(self.get_string_list(SETTINGS.CHANNEL_NAME_ALIASES))
