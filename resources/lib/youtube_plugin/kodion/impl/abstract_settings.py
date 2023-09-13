# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import sys

from ..constants import setting as SETTINGS
from ..logger import log_debug


class AbstractSettings(object):
    def __init__(self):
        object.__init__(self)

    def get_string(self, setting_id, default_value=None):
        raise NotImplementedError()

    def set_string(self, setting_id, value):
        raise NotImplementedError()

    def open_settings(self):
        raise NotImplementedError()

    def get_int(self, setting_id, default_value, converter=None):
        if not converter:
            def converter(x):
                return x

        value = self.get_string(setting_id)
        if value is None or value == '':
            return default_value

        try:
            return converter(int(value))
        except Exception as ex:
            log_debug("Failed to get setting '%s' as 'int' (%s)" % setting_id, ex.__str__())

        return default_value

    def set_int(self, setting_id, value):
        self.set_string(setting_id, str(value))

    def set_bool(self, setting_id, value):
        if value:
            self.set_string(setting_id, 'true')
        else:
            self.set_string(setting_id, 'false')

    def get_bool(self, setting_id, default_value):
        value = self.get_string(setting_id)
        if value is None or value == '':
            return default_value

        if value != 'false' and value != 'true':
            return default_value

        return value == 'true'

    def get_items_per_page(self):
        return self.get_int(SETTINGS.ITEMS_PER_PAGE, 50)

    def get_video_quality(self, quality_map_override=None):
        vq_dict = {0: 240,
                   1: 360,
                   2: 480,  # 576 seems not to work well
                   3: 720,
                   4: 1080}

        if quality_map_override is not None:
            vq_dict = quality_map_override

        vq = self.get_int(SETTINGS.VIDEO_QUALITY, 1)
        return vq_dict[vq]

    def ask_for_video_quality(self):
        return self.get_bool(SETTINGS.VIDEO_QUALITY_ASK, False)

    def show_fanart(self):
        return self.get_bool(SETTINGS.SHOW_FANART, True)

    def get_search_history_size(self):
        return self.get_int(SETTINGS.SEARCH_SIZE, 50)

    def is_setup_wizard_enabled(self):
        return self.get_bool(SETTINGS.SETUP_WIZARD, False)

    def is_support_alternative_player_enabled(self):
        return self.get_bool(SETTINGS.SUPPORT_ALTERNATIVE_PLAYER, False)

    def alternative_player_web_urls(self):
        return self.get_bool(SETTINGS.ALTERNATIVE_PLAYER_WEB_URLS, False)

    def use_mpd(self):
        return self.get_bool(SETTINGS.USE_MPD, False)

    def subtitle_languages(self):
        return self.get_int(SETTINGS.SUBTITLE_LANGUAGE, 0)

    def subtitle_download(self):
        return self.get_bool(SETTINGS.SUBTITLE_DOWNLOAD, False)

    def audio_only(self):
        return self.get_bool(SETTINGS.AUDIO_ONLY, False)

    def set_subtitle_languages(self, value):
        return self.set_int(SETTINGS.SUBTITLE_LANGUAGE, value)

    def set_subtitle_download(self, value):
        return self.set_bool(SETTINGS.SUBTITLE_DOWNLOAD, value)

    def use_thumbnail_size(self):
        size = self.get_int(SETTINGS.THUMB_SIZE, 0)
        sizes = {0: 'medium', 1: 'high'}
        return sizes[size]

    def safe_search(self):
        index = self.get_int(SETTINGS.SAFE_SEARCH, 0)
        values = {0: 'moderate', 1: 'none', 2: 'strict'}
        return values[index]

    def age_gate(self):
        return self.get_bool(SETTINGS.AGE_GATE, True)

    def verify_ssl(self):
        verify = self.get_bool(SETTINGS.VERIFY_SSL, False)
        if sys.version_info <= (2, 7, 9):
            verify = False
        return verify

    def allow_dev_keys(self):
        return self.get_bool(SETTINGS.ALLOW_DEV_KEYS, False)

    def use_mpd_videos(self):
        if self.use_mpd():
            return self.get_bool(SETTINGS.MPD_VIDEOS, False)
        return False

    _LIVE_STREAM_TYPES = {
        0: 'mpegts',
        1: 'hls',
        2: 'ia_hls',
        3: 'ia_mpd',
    }

    def get_live_stream_type(self):
        if self.use_mpd():
            stream_type = self.get_int(SETTINGS.LIVE_STREAMS + '.1', 0)
        else:
            stream_type = self.get_int(SETTINGS.LIVE_STREAMS + '.2', 0)
        return self._LIVE_STREAM_TYPES.get(stream_type) or self._LIVE_STREAM_TYPES[0]

    def use_adaptive_live_streams(self):
        if self.use_mpd():
            return self.get_int(SETTINGS.LIVE_STREAMS + '.1', 0) > 1
        return self.get_int(SETTINGS.LIVE_STREAMS + '.2', 0) > 1

    def use_mpd_live_streams(self):
        if self.use_mpd():
            return self.get_int(SETTINGS.LIVE_STREAMS + '.1', 0) == 3
        return False

    def httpd_port(self):
        return self.get_int(SETTINGS.HTTPD_PORT, 50152)

    def httpd_listen(self, default='0.0.0.0', for_request=False):
        ip_address = self.get_string(SETTINGS.HTTPD_LISTEN, default)
        try:
            ip_address = ip_address.strip()
        except AttributeError:
            pass
        if not ip_address:
            ip_address = default
        if for_request and ip_address == default:
            ip_address = '127.0.0.1'
        return ip_address

    def set_httpd_listen(self, value):
        return self.set_string(SETTINGS.HTTPD_LISTEN, value)

    def httpd_whitelist(self):
        return self.get_string(SETTINGS.HTTPD_WHITELIST, '')

    def api_config_page(self):
        return self.get_bool(SETTINGS.API_CONFIG_PAGE, False)

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
        else:
            return ''

    def set_location(self, value):
        self.set_string(SETTINGS.LOCATION, value)

    def get_location_radius(self):
        return ''.join([str(self.get_int(SETTINGS.LOCATION_RADIUS, 500)), 'km'])

    def get_play_count_min_percent(self):
        return self.get_int(SETTINGS.PLAY_COUNT_MIN_PERCENT, 0)

    def use_local_history(self):
        return self.get_bool(SETTINGS.USE_LOCAL_HISTORY, False)

    def use_remote_history(self):
        return self.get_bool(SETTINGS.USE_REMOTE_HISTORY, False)

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

    def get_mpd_video_qualities(self):
        if not self.use_mpd_videos():
            return []
        selected = self.get_int(SETTINGS.MPD_QUALITY_SELECTION, 4)
        return [quality for key, quality in self._QUALITY_SELECTIONS.items()
                if selected >= key]

    def stream_features(self):
        return self.get_string(SETTINGS.MPD_STREAM_FEATURES, '').split(',')

    _STREAM_SELECT = {
        1: 'auto',
        2: 'list',
        3: 'auto+list',
    }

    def stream_select(self):
        select_type = self.get_int(SETTINGS.MPD_STREAM_SELECT, 1)
        return self._STREAM_SELECT.get(select_type) or self._STREAM_SELECT[1]

    def remote_friendly_search(self):
        return self.get_bool(SETTINGS.REMOTE_FRIENDLY_SEARCH, False)

    def hide_short_videos(self):
        return self.get_bool(SETTINGS.HIDE_SHORT_VIDEOS, False)

    def client_selection(self):
        return self.get_int(SETTINGS.CLIENT_SELECTION, 0)
