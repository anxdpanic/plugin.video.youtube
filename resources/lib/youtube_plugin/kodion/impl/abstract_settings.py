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
        if not self.use_dash():
            return False
        return self.get_bool(constants.setting.DASH_VIDEOS, False)

    def include_hdr(self):
        if self.get_mpd_quality() == 'mp4':
            return False
        return self.get_bool(constants.setting.DASH_INCL_HDR, False)

    def use_dash_live_streams(self):
        if not self.use_dash():
            return False
        return self.get_bool(constants.setting.DASH_LIVE_STREAMS, False)

    def httpd_port(self):
        return self.get_int(constants.setting.HTTPD_PORT, 50152)

    def httpd_listen(self):
        ip_address = self.get_string(constants.setting.HTTPD_LISTEN, '0.0.0.0')
        try:
            ip_address = ip_address.strip()
        except AttributeError:
            pass
        if not ip_address:
            ip_address = '0.0.0.0'
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

    @staticmethod
    def __get_mpd_quality_map():
        return {
            0: 240,
            1: 360,
            2: 480,
            3: 720,
            4: 1080,
            5: 1440,
            6: 2160,
            7: 4320,
            8: 'mp4',
            9: 'webm'
        }

    def get_mpd_quality(self):
        quality_map = self.__get_mpd_quality_map()
        quality_enum = self.get_int(constants.setting.MPD_QUALITY_SELECTION, 8)
        return quality_map.get(quality_enum, 'mp4')

    def mpd_video_qualities(self):
        if not self.use_dash_videos():
            return []

        quality = self.get_mpd_quality()

        if not isinstance(quality, int):
            return quality

        quality_map = self.__get_mpd_quality_map()
        qualities = sorted([x for x in list(quality_map.values())
                            if isinstance(x, int) and x <= quality], reverse=True)

        return qualities

    def mpd_30fps_limit(self):
        if self.include_hdr() or isinstance(self.get_mpd_quality(), str):
            return False
        return self.get_bool(constants.setting.MPD_30FPS_LIMIT, False)

    def remote_friendly_search(self):
        return self.get_bool(constants.setting.REMOTE_FRIENDLY_SEARCH, False)
