# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..abstract_settings import AbstractSettings
from ...compatibility import xbmcaddon
from ...logger import log_debug
from ...utils.methods import get_kodi_setting_bool
from ...utils.system_version import current_system_version


class XbmcPluginSettings(AbstractSettings):
    def __init__(self, xbmc_addon):
        super(XbmcPluginSettings, self).__init__()

        self.flush(xbmc_addon)

        if current_system_version.compatible(21, 0):
            _class = xbmcaddon.Settings

            # set methods in new Settings class are documented as returning a
            # bool, True if value was set, False otherwise, similar to how the
            # old set setting methods of the Addon class function. Except they
            # don't actually return anything...
            # Ignore return value until bug is fixed in Kodi
            XbmcPluginSettings._check_set = False

            self.__dict__.update({
                '_get_bool': _class.getBool,
                '_set_bool': _class.setBool,
                '_get_int': _class.getInt,
                '_set_int': _class.setInt,
                '_get_str': _class.getString,
                '_set_str': _class.setString,
                '_get_str_list': _class.getStringList,
                '_set_str_list': _class.setStringList,
            })
        else:
            _class = xbmcaddon.Addon

            def _get_string_list(store, setting):
                return _class.getSetting(store, setting).split(',')

            def _set_string_list(store, setting, value):
                value = ','.join(value)
                return _class.setSetting(store, setting, value)

            self.__dict__.update({
                '_get_bool': _class.getSettingBool,
                '_set_bool': _class.setSettingBool,
                '_get_int': _class.getSettingInt,
                '_set_int': _class.setSettingInt,
                '_get_str': _class.getSettingString,
                '_set_str': _class.setSettingString,
                '_get_str_list': _get_string_list,
                '_set_str_list': _set_string_list,
            })

    @classmethod
    def flush(cls, xbmc_addon=None):
        if not xbmc_addon:
            del cls._instance
            cls._instance = None
            return

        cls._echo = get_kodi_setting_bool('debug.showloginfo')
        cls._cache = {}
        if current_system_version.compatible(21, 0):
            cls._instance = xbmc_addon.getSettings()
        else:
            cls._instance = xbmcaddon.Addon()

    def get_bool(self, setting, default=None, echo=None):
        if setting in self._cache:
            return self._cache[setting]

        error = False
        try:
            value = bool(self._get_bool(self._instance, setting))
        except (TypeError, ValueError) as exc:
            error = exc
            try:
                value = self.get_string(setting, echo=False).lower()
                value = AbstractSettings.VALUE_FROM_STR.get(value, default)
            except TypeError as exc:
                error = exc
                value = default
        except RuntimeError as exc:
            error = exc
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
            error = not self._set_bool(self._instance, setting, value)
            if error and self._check_set:
                error = 'failed'
            else:
                error = False
                self._cache[setting] = value
        except (RuntimeError, TypeError) as exc:
            error = exc

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
            value = int(self._get_int(self._instance, setting))
            if process:
                value = process(value)
        except (TypeError, ValueError) as exc:
            error = exc
            try:
                value = self.get_string(setting, echo=False)
                value = int(value)
            except (TypeError, ValueError) as exc:
                error = exc
                value = default
        except RuntimeError as exc:
            error = exc
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
            error = not self._set_int(self._instance, setting, value)
            if error and self._check_set:
                error = 'failed'
            else:
                error = False
                self._cache[setting] = value
        except (RuntimeError, TypeError) as exc:
            error = exc

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
            value = self._get_str(self._instance, setting) or default
        except (RuntimeError, TypeError) as exc:
            error = exc
            value = default

        if self._echo and echo is not False:
            if setting == 'youtube.location':
                echo = 'xx.xxxx,xx.xxxx'
            elif setting == 'youtube.api.id':
                echo = '...'.join((value[:3], value[-5:]))
            elif setting in ('youtube.api.key', 'youtube.api.secret'):
                echo = '...'.join((value[:3], value[-3:]))
            else:
                echo = value
            log_debug('Get |{setting}|: "{echo}" (str, {status})'.format(
                setting=setting,
                echo=echo,
                status=error if error else 'success'
            ))
        self._cache[setting] = value
        return value

    def set_string(self, setting, value, echo=None):
        try:
            error = not self._set_str(self._instance, setting, value)
            if error and self._check_set:
                error = 'failed'
            else:
                error = False
                self._cache[setting] = value
        except (RuntimeError, TypeError) as exc:
            error = exc

        if self._echo and echo is not False:
            if setting == 'youtube.location':
                echo = 'xx.xxxx,xx.xxxx'
            elif setting == 'youtube.api.id':
                echo = '...'.join((value[:3], value[-5:]))
            elif setting in ('youtube.api.key', 'youtube.api.secret'):
                echo = '...'.join((value[:3], value[-3:]))
            else:
                echo = value
            log_debug('Set |{setting}|: "{echo}" (str, {status})'.format(
                setting=setting,
                echo=echo,
                status=error if error else 'success'
            ))
        return not error

    def get_string_list(self, setting, default=None, echo=None):
        if setting in self._cache:
            return self._cache[setting]

        error = False
        try:
            value = self._get_str_list(self._instance, setting)
            if not value:
                value = [] if default is None else default
        except (RuntimeError, TypeError) as exc:
            error = exc
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
            error = not self._set_str_list(self._instance, setting, value)
            if error and self._check_set:
                error = 'failed'
            else:
                error = False
                self._cache[setting] = value
        except (RuntimeError, TypeError) as exc:
            error = exc

        if self._echo and echo is not False:
            log_debug('Set |{setting}|: "{value}" (str list, {status})'.format(
                setting=setting,
                value=value,
                status=error if error else 'success'
            ))
        return not error
