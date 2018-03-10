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

    def set_string(self, setting_id, value):
        self._xbmc_addon.setSetting(setting_id, value)
