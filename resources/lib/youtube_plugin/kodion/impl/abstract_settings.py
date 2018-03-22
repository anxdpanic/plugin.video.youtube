__author__ = 'bromix'

import sys
from .. import constants


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
            converter = lambda x: x

        value = self.get_string(setting_id)
        if value is None or value == '':
            return default_value

        try:
            return converter(int(value))
        except Exception as ex:
            from . import log

            log("Failed to get setting '%s' as 'int' (%s)" % setting_id, ex.__str__())

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

    def use_dash(self):
        return self.get_bool(constants.setting.USE_DASH, False)

    def subtitle_languages(self):
        return self.get_int(constants.setting.SUBTITLE_LANGUAGE, 0)

    def audio_only(self):
        return self.get_bool(constants.setting.AUDIO_ONLY, False)

    def set_subtitle_languages(self, value):
        return self.set_int(constants.setting.SUBTITLE_LANGUAGE, value)

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
        return self.get_bool(constants.setting.ALLOW_DEV_KEYS, True)

    def use_dash_proxy(self):
        return self.get_bool(constants.setting.DASH_PROXY, True)

    def httpd_port(self):
        return self.get_int(constants.setting.HTTPD_PORT, 50152)

    def httpd_listen(self):
        return self.get_string(constants.setting.HTTPD_LISTEN, '0.0.0.0')

    def set_httpd_listen(self, value):
        return self.set_string(constants.setting.HTTPD_LISTEN, value)

    def httpd_whitelist(self):
        return self.get_string(constants.setting.HTTPD_WHITELIST, '')

    def api_config_page(self):
        return self.get_bool(constants.setting.API_CONFIG_PAGE, False)
