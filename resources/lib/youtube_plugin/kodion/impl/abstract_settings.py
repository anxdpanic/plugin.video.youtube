# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import sys

from .. import constants
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
        return self.get_int(constants.setting.ITEMS_PER_PAGE, 50, lambda x: (x + 1) * 5)

    def get_video_quality(self, quality_map_override=None):
        vq_dict = {0: 240,
                   1: 360,
                   2: 480,  # 576 seems not to work well
                   3: 720,
                   4: 1080}

        if quality_map_override is not None:
            vq_dict = quality_map_override

        vq = self.get_int(constants.setting.VIDEO_QUALITY, 1)
        return vq_dict[vq]

    def ask_for_video_quality(self):
        return self.get_bool(constants.setting.VIDEO_QUALITY_ASK, False)

    def show_fanart(self):
        return self.get_bool(constants.setting.SHOW_FANART, True)

    def get_search_history_size(self):
        return self.get_int(constants.setting.SEARCH_SIZE, 50)

    def is_setup_wizard_enabled(self):
        return self.get_bool(constants.setting.SETUP_WIZARD, False)

    def is_support_alternative_player_enabled(self):
        return self.get_bool(constants.setting.SUPPORT_ALTERNATIVE_PLAYER, False)

    def alternative_player_web_urls(self):
        return self.get_bool(constants.setting.ALTERNATIVE_PLAYER_WEB_URLS, False)

    def use_dash(self):
        return self.get_bool(constants.setting.USE_DASH, False)

    def subtitle_languages(self):
        return self.get_int(constants.setting.SUBTITLE_LANGUAGE, 0)

    def subtitle_download(self):
        return self.get_bool(constants.setting.SUBTITLE_DOWNLOAD, False)

    def audio_only(self):
        return self.get_bool(constants.setting.AUDIO_ONLY, False)

    def set_subtitle_languages(self, value):
        return self.set_int(constants.setting.SUBTITLE_LANGUAGE, value)

    def set_subtitle_download(self, value):
        return self.set_bool(constants.setting.SUBTITLE_DOWNLOAD, value)

    def use_thumbnail_size(self):
        size = self.get_int(constants.setting.THUMB_SIZE, 0)
        sizes = {0: 'medium', 1: 'high'}
        return sizes[size]

    def safe_search(self):
        index = self.get_int(constants.setting.SAFE_SEARCH, 0)
        values = {0: 'moderate', 1: 'none', 2: 'strict'}
        return values[index]

    def age_gate(self):
        return self.get_bool(constants.setting.AGE_GATE, True)

    def verify_ssl(self):
        verify = self.get_bool(constants.setting.VERIFY_SSL, False)
        if sys.version_info <= (2, 7, 9):
            verify = False
        return verify

    def allow_dev_keys(self):
        return self.get_bool(constants.setting.ALLOW_DEV_KEYS, False)

    def use_dash_videos(self):
        if self.use_dash():
            return self.get_bool(constants.setting.DASH_VIDEOS, False)
        return False

    def include_hdr(self):
        return self.get_bool(constants.setting.DASH_INCL_HDR, False)

    def get_live_stream_type(self):
        stream_type_map = {0: 'mpegts',
                           1: 'hls',
                           2: 'ia_hls',
                           3: 'ia_mpd'}

        if self.use_dash():
            stream_type = self.get_int(constants.setting.LIVE_STREAMS + '.1', 0)
        else:
            stream_type = self.get_int(constants.setting.LIVE_STREAMS + '.2', 0)
        return stream_type_map.get(stream_type) or stream_type_map[0]

    def use_adaptive_live_streams(self):
        if self.use_dash():
            return self.get_int(constants.setting.LIVE_STREAMS + '.1', 0) > 1
        return self.get_int(constants.setting.LIVE_STREAMS + '.2', 0) > 1

    def use_dash_live_streams(self):
        if self.use_dash():
            return self.get_int(constants.setting.LIVE_STREAMS + '.1', 0) == 3
        return False

    def httpd_port(self):
        return self.get_int(constants.setting.HTTPD_PORT, 50152)

    def httpd_listen(self, default='0.0.0.0'):
        ip_address = self.get_string(constants.setting.HTTPD_LISTEN, default)
        try:
            ip_address = ip_address.strip()
        except AttributeError:
            pass
        if not ip_address:
            ip_address = default
        return ip_address

    def set_httpd_listen(self, value):
        return self.set_string(constants.setting.HTTPD_LISTEN, value)

    def httpd_whitelist(self):
        return self.get_string(constants.setting.HTTPD_WHITELIST, '')

    def api_config_page(self):
        return self.get_bool(constants.setting.API_CONFIG_PAGE, False)

    def get_location(self):
        location = self.get_string(constants.setting.LOCATION, '').replace(' ', '').strip()
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
        self.set_string(constants.setting.LOCATION, value)

    def get_location_radius(self):
        return ''.join([str(self.get_int(constants.setting.LOCATION_RADIUS, 500)), 'km'])

    def get_play_count_min_percent(self):
        return self.get_int(constants.setting.PLAY_COUNT_MIN_PERCENT, 0)

    def use_playback_history(self):
        return self.get_bool(constants.setting.USE_PLAYBACK_HISTORY, False)

    # Selections based on max width and min height at common (utra-)wide aspect ratios
    # 8K and 4K at 32:9, 2K at 8:3, remainder at 22:9 (2.444...)
                                                                                          # MPD_QUALITY_SELECTION value
    _QUALITY_SELECTIONS = ['mp4',                                                         # 8 (default)
                           'webm',                                                        # 9
                           {'width': 256, 'height': 105, 'label': '144p{0}{1}'},          # No setting
                           {'width': 426, 'height': 175, 'label': '240p{0}{1}'},          # 0
                           {'width': 640, 'height': 263, 'label': '360p{0}{1}'},          # 1
                           {'width': 854, 'height': 350, 'label': '480p{0}{1}'},          # 2
                           {'width': 1280, 'height': 525, 'label': '720p{0} (HD){1}'},    # 3
                           {'width': 1920, 'height': 787, 'label': '1080p{0} (FHD){1}'},  # 4
                           {'width': 2560, 'height': 984, 'label': '1440p{0} (2K){1}'},   # 5
                           {'width': 3840, 'height': 1080, 'label': '2160p{0} (4K){1}'},  # 6
                           {'width': 7680, 'height': 3148, 'label': '4320p{0} (8K){1}'},  # 7
                           {'width': 0, 'height': 0, 'label': '{2}p{0}{1}'}]              # Unknown quality

    def get_mpd_video_qualities(self, list_all=False):
        if not self.use_dash_videos():
            return []
        if list_all:
            # to be converted to selection index 2
            selected = 7
        else:
            selected = self.get_int(constants.setting.MPD_QUALITY_SELECTION, 8)
        if 8 <= selected <= 9:
            # converted to selection index 0 or 1
            return self._QUALITY_SELECTIONS[selected - 8]
        # converted to selection index starting from 2
        qualities = self._QUALITY_SELECTIONS[2:]
        del qualities[2 + selected:-1]
        return qualities

    def mpd_30fps_limit(self):
        return self.get_bool(constants.setting.MPD_30FPS_LIMIT, False)

    def remote_friendly_search(self):
        return self.get_bool(constants.setting.REMOTE_FRIENDLY_SEARCH, False)

    def hide_short_videos(self):
        return self.get_bool(constants.setting.HIDE_SHORT_VIDEOS, False)

    def client_selection(self):
        return self.get_int(constants.setting.CLIENT_SELECTION, 0)
