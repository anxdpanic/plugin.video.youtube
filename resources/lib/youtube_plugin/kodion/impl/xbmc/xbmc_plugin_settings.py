# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from ..abstract_settings import AbstractSettings


class XbmcPluginSettings(AbstractSettings):
    def __init__(self, xbmc_addon):
        AbstractSettings.__init__(self)

        self._xbmc_addon = xbmc_addon

    def get_string(self, setting_id, default_value=None):
        return self._xbmc_addon.getSetting(setting_id)

    def set_string(self, setting_id, value):
        self._xbmc_addon.setSetting(setting_id, value)

    def open_settings(self):
        self._xbmc_addon.openSetting()
