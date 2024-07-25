# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from weakref import ref

from ..abstract_settings import AbstractSettings
from ...compatibility import xbmcaddon
from ...constants import ADDON_ID, VALUE_FROM_STR
from ...logger import log_debug
from ...utils.methods import get_kodi_setting_bool
from ...utils.system_version import current_system_version


class SettingsProxy(object):
    def __init__(self, instance):
        self.ref = instance

    if current_system_version.compatible(21, 0):
        def get_bool(self, *args, **kwargs):
            return self.ref.getBool(*args, **kwargs)

        def set_bool(self, *args, **kwargs):
            return self.ref.setBool(*args, **kwargs)

        def get_int(self, *args, **kwargs):
            return self.ref.getInt(*args, **kwargs)

        def set_int(self, *args, **kwargs):
            return self.ref.setInt(*args, **kwargs)

        def get_str(self, *args, **kwargs):
            return self.ref.getString(*args, **kwargs)

        def set_str(self, *args, **kwargs):
            return self.ref.setString(*args, **kwargs)

        def get_str_list(self, *args, **kwargs):
            return self.ref.getStringList(*args, **kwargs)

        def set_str_list(self, *args, **kwargs):
            return self.ref.setStringList(*args, **kwargs)

    else:
        def get_bool(self, *args, **kwargs):
            return self.ref.getSettingBool(*args, **kwargs)

        def set_bool(self, *args, **kwargs):
            return self.ref.setSettingBool(*args, **kwargs)

        def get_int(self, *args, **kwargs):
            return self.ref.getSettingInt(*args, **kwargs)

        def set_int(self, *args, **kwargs):
            return self.ref.setSettingInt(*args, **kwargs)

        def get_str(self, *args, **kwargs):
            return self.ref.getSettingString(*args, **kwargs)

        def set_str(self, *args, **kwargs):
            return self.ref.setSettingString(*args, **kwargs)

        def get_str_list(self, setting):
            return self.ref.getSetting(setting).split(',')

        def set_str_list(self, setting, value):
            value = ','.join(value)
            return self.ref.setSetting(setting, value)

        if not current_system_version.compatible(19, 0):
            @property
            def ref(self):
                if self._ref:
                    return self._ref()
                return None

            @ref.setter
            def ref(self, value):
                if value:
                    self._ref = ref(value)
                else:
                    self._ref = None

            @ref.deleter
            def ref(self):
                del self._ref


class XbmcPluginSettings(AbstractSettings):
    _instances = set()
    _proxy = None

    def __init__(self, xbmc_addon=None):
        self.flush(xbmc_addon, fill=True)

    def flush(self, xbmc_addon=None, fill=False, flush_all=True):
        if not xbmc_addon:
            if fill:
                xbmc_addon = xbmcaddon.Addon(ADDON_ID)
            else:
                if self.__class__._instances:
                    if flush_all:
                        self.__class__._instances.clear()
                    else:
                        self.__class__._instances.discard(self._proxy.ref)
                del self._proxy.ref
                self._proxy.ref = None
                del self._proxy
                self._proxy = None
                return
        else:
            fill = False

        self._echo = get_kodi_setting_bool('debug.showloginfo')
        self._cache = {}
        if current_system_version.compatible(21, 0):
            self._proxy = SettingsProxy(xbmc_addon.getSettings())
            # set methods in new Settings class are documented as returning a
            # bool, True if value was set, False otherwise, similar to how the
            # old set setting methods of the Addon class function. Except they
            # don't actually return anything...
            # Ignore return value until bug is fixed in Kodi
            self._check_set = False
        else:
            if fill and not current_system_version.compatible(19, 0):
                self.__class__._instances.add(xbmc_addon)
            self._proxy = SettingsProxy(xbmc_addon)

    def get_bool(self, setting, default=None, echo=None):
        if setting in self._cache:
            return self._cache[setting]

        error = False
        try:
            value = bool(self._proxy.get_bool(setting))
        except (TypeError, ValueError) as exc:
            error = exc
            try:
                value = self.get_string(setting, echo=False).lower()
                value = VALUE_FROM_STR.get(value, default)
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
            error = not self._proxy.set_bool(setting, value)
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
            value = int(self._proxy.get_int(setting))
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
            error = not self._proxy.set_int(setting, value)
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
            value = self._proxy.get_str(setting) or default
        except (RuntimeError, TypeError) as exc:
            error = exc
            value = default

        if self._echo and echo is not False:
            if setting == 'youtube.location':
                echo = 'xx.xxxx,xx.xxxx'
            elif setting == 'youtube.api.id':
                echo = '...'.join((value[:3], value[-5:]))
            elif setting in {'youtube.api.key', 'youtube.api.secret'}:
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
            error = not self._proxy.set_str(setting, value)
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
            elif setting in {'youtube.api.key', 'youtube.api.secret'}:
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
            value = self._proxy.get_str_list(setting)
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
            error = not self._proxy.set_str_list(setting, value)
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
