__author__ = 'bromix'

from ..abstract_settings import AbstractSettings

import xbmc
import xbmcgui


class XbmcPluginSettings(AbstractSettings):
    def __init__(self, xbmc_addon):
        AbstractSettings.__init__(self)

        self._xbmc_addon = xbmc_addon

    def get_string(self, setting_id, default_value=None):
        return self._xbmc_addon.getSetting(setting_id)

    def set_string(self, setting_id, value, on_changed=True):
        if not on_changed:
            xbmcgui.Window(10000).setProperty('plugin.video.youtube-setting_cb_disabled', 'true')
            self._xbmc_addon.setSetting(setting_id, value)
            i = 0
            while xbmcgui.Window(10000).getProperty('plugin.video.youtube-setting_cb_disabled') == 'true':
                xbmc.sleep(1)
                i += 1
                if i >= 60:
                    xbmcgui.Window(10000).clearProperty('plugin.video.youtube-setting_cb_disabled')
                    break
        else:
            self._xbmc_addon.setSetting(setting_id, value)
