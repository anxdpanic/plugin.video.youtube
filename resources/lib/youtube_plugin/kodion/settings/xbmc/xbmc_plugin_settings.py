# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import xbmcaddon

from ..abstract_settings import AbstractSettings
from ...logger import log_debug
from ...utils.methods import get_kodi_setting
from ...utils.system_version import current_system_version


class XbmcPluginSettings(AbstractSettings):
    def __init__(self, xbmc_addon):
        super(XbmcPluginSettings, self).__init__()

        self.flush(xbmc_addon)

        if self._funcs:
            return
        if current_system_version.compatible(20, 0):
            _class = xbmcaddon.Settings

            self._funcs.update({
                'get_bool': _class.getBool,
                'set_bool': _class.setBool,
                'get_int': _class.getInt,
                'set_int': _class.setInt,
                'get_str': _class.getString,
                'set_str': _class.setString,
                'get_str_list': _class.getStringList,
                'set_str_list': _class.setStringList,
            })
        else:
            _class = xbmcaddon.Addon

            def _get_string_list(store, setting):
                return _class.getSetting(store, setting).split(',')

            def _set_string_list(store, setting, value):
                value = ','.join(value)
                return _class.setSetting(store, setting, value)

            self._funcs.update({
                'get_bool': _class.getSettingBool,
                'set_bool': _class.setSettingBool,
                'get_int': _class.getSettingInt,
                'set_int': _class.setSettingInt,
                'get_str': _class.getSettingString,
                'set_str': _class.setSettingString,
                'get_str_list': _get_string_list,
                'set_str_list': _set_string_list,
            })

    @classmethod
    def flush(cls, xbmc_addon):
        cls._echo = get_kodi_setting('debug.showloginfo')
        cls._cache = {}
        if current_system_version.compatible(20, 0):
            cls._store = xbmc_addon.getSettings()
        else:
            cls._store = xbmc_addon

    def get_bool(self, setting, default=None, echo=None):
        if setting in self._cache:
            return self._cache[setting]

        error = False
        try:
            value = bool(self._funcs['get_bool'](self._store, setting))
        except (AttributeError, TypeError) as ex:
            error = ex
            value = self.get_string(setting, echo=False)
            value = AbstractSettings.VALUE_FROM_STR.get(value.lower(), default)
        except RuntimeError as ex:
            error = ex
            value = default

        if self._echo and echo is not False:
            log_debug('Get |{setting}|: {value} (bool, {status})'.format(
                setting=setting,
                value=value,
                status=error if error else 'success'
            ))
        self._cache[setting] = value
        return value

    def set_bool(self, setting, value, echo=None):
        try:
            error = not self._funcs['set_bool'](self._store, setting, value)
            if not error:
                self._cache[setting] = value
        except RuntimeError as ex:
            error = ex

        if self._echo and echo is not False:
            log_debug('Set |{setting}|: {value} (bool, {status})'.format(
                setting=setting,
                value=value,
                status=error if error else 'success'
            ))
        return not error

    def get_int(self, setting, default=-1, process=None, echo=None):
        if setting in self._cache:
            return self._cache[setting]

        error = False
        try:
            value = int(self._funcs['get_int'](self._store, setting))
            if process:
                value = process(value)
        except (AttributeError, TypeError, ValueError) as ex:
            error = ex
            value = self.get_string(setting, echo=False)
            try:
                value = int(value)
            except (TypeError, ValueError) as ex:
                error = ex
                value = default
        except RuntimeError as ex:
            error = ex
            value = default

        if self._echo and echo is not False:
            log_debug('Get |{setting}|: {value} (int, {status})'.format(
                setting=setting,
                value=value,
                status=error if error else 'success'
            ))
        self._cache[setting] = value
        return value

    def set_int(self, setting, value, echo=None):
        try:
            error = not self._funcs['set_int'](self._store, setting, value)
            if not error:
                self._cache[setting] = value
        except RuntimeError as ex:
            error = ex

        if self._echo and echo is not False:
            log_debug('Set |{setting}|: {value} (int, {status})'.format(
                setting=setting,
                value=value,
                status=error if error else 'success'
            ))
        return not error

    def get_string(self, setting, default='', echo=None):
        if setting in self._cache:
            return self._cache[setting]

        error = False
        try:
            value = self._funcs['get_str'](self._store, setting) or default
        except RuntimeError as ex:
            error = ex
            value = default

        if self._echo and echo is not False:
            log_debug('Get |{setting}|: "{value}" (str, {status})'.format(
                setting=setting,
                value=value,
                status=error if error else 'success'
            ))
        self._cache[setting] = value
        return value

    def set_string(self, setting, value, echo=None):
        try:
            error = not self._funcs['set_str'](self._store, setting, value)
            if not error:
                self._cache[setting] = value
        except RuntimeError as ex:
            error = ex

        if self._echo and echo is not False:
            log_debug('Set |{setting}|: "{value}" (str, {status})'.format(
                setting=setting,
                value=value,
                status=error if error else 'success'
            ))
        return not error

    def get_string_list(self, setting, default=None, echo=None):
        if setting in self._cache:
            return self._cache[setting]

        error = False
        try:
            value = self._funcs['get_str_list'](self._store, setting)
            if not value:
                value = [] if default is None else default
        except RuntimeError as ex:
            error = ex
            value = default

        if self._echo and echo is not False:
            log_debug('Get |{setting}|: "{value}" (str list, {status})'.format(
                setting=setting,
                value=value,
                status=error if error else 'success'
            ))
        self._cache[setting] = value
        return value

    def set_string_list(self, setting, value, echo=None):
        try:
            error = not self._funcs['set_str_list'](self._store, setting, value)
            if not error:
                self._cache[setting] = value
        except RuntimeError as ex:
            error = ex

        if self._echo and echo is not False:
            log_debug('Set |{setting}|: "{value}" (str list, {status})'.format(
                setting=setting,
                value=value,
                status=error if error else 'success'
            ))
        return not error
