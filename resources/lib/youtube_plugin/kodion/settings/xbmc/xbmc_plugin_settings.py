# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from weakref import ref

from ..abstract_settings import AbstractSettings
from ... import logging
from ...compatibility import xbmcaddon
from ...constants import ADDON_ID, BOOL_FROM_STR
from ...utils.system_version import current_system_version


class SettingsProxy(object):
    def __init__(self, instance):
        self.ref = instance

    if current_system_version.compatible(21):
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

        if not current_system_version.compatible(19):
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
    log = logging.getLogger(__name__)

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

        self._cache = {}
        if current_system_version.compatible(21):
            self._proxy = SettingsProxy(xbmc_addon.getSettings())
            # set methods in new Settings class are documented as returning a
            # bool, True if value was set, False otherwise, similar to how the
            # old set setting methods of the Addon class function. Except they
            # don't actually return anything...
            # Ignore return value until bug is fixed in Kodi
            self._check_set = False
        else:
            if fill and not current_system_version.compatible(19):
                self.__class__._instances.add(xbmc_addon)
            self._proxy = SettingsProxy(xbmc_addon)

        self._echo_level = self.log_level()

    def get_bool(self, setting, default=None, echo_level=2):
        if setting in self._cache:
            return self._cache[setting]

        error = False
        try:
            value = bool(self._proxy.get_bool(setting))
        except (TypeError, ValueError) as exc:
            error = exc
            try:
                value = self.get_string(setting, echo_level=0)
                value = BOOL_FROM_STR.get(value, default)
            except TypeError as exc:
                error = exc
                value = default
        except RuntimeError as exc:
            error = exc
            value = default

        if echo_level and self._echo_level:
            self.log.debug_trace('Get setting {name!r}:'
                                 ' {value!r} (bool, {state})',
                                 name=setting,
                                 value=value,
                                 state=(error if error else 'success'),
                                 stacklevel=echo_level)
        self._cache[setting] = value
        return value

    def set_bool(self, setting, value, echo_level=2):
        try:
            error = not self._proxy.set_bool(setting, value)
            if error and self._check_set:
                error = 'failed'
            else:
                error = False
                self._cache[setting] = value
        except (RuntimeError, TypeError) as exc:
            error = exc

        if echo_level and self._echo_level:
            self.log.debug_trace('Set setting {name!r}:'
                                 ' {value!r} (bool, {state})',
                                 name=setting,
                                 value=value,
                                 state=(error if error else 'success'),
                                 stacklevel=echo_level)
        return not error

    def get_int(self, setting, default=-1, process=None, echo_level=2):
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
                value = self.get_string(setting, echo_level=0)
                value = int(value)
            except (TypeError, ValueError) as exc:
                error = exc
                value = default
        except RuntimeError as exc:
            error = exc
            value = default

        if echo_level and self._echo_level:
            self.log.debug_trace('Get setting {name!r}:'
                                 ' {value!r} (int, {state})',
                                 name=setting,
                                 value=value,
                                 state=(error if error else 'success'),
                                 stacklevel=echo_level)
        self._cache[setting] = value
        return value

    def set_int(self, setting, value, echo_level=2):
        try:
            error = not self._proxy.set_int(setting, value)
            if error and self._check_set:
                error = 'failed'
            else:
                error = False
                self._cache[setting] = value
        except (RuntimeError, TypeError) as exc:
            error = exc

        if echo_level and self._echo_level:
            self.log.debug_trace('Set setting {name!r}:'
                                 ' {value!r} (int, {state})',
                                 name=setting,
                                 value=value,
                                 state=(error if error else 'success'),
                                 stacklevel=echo_level)
        return not error

    def get_string(self, setting, default='', echo_level=2):
        if setting in self._cache:
            return self._cache[setting]

        error = False
        try:
            value = self._proxy.get_str(setting) or default
        except (RuntimeError, TypeError) as exc:
            error = exc
            value = default

        if echo_level and self._echo_level:
            if setting == self.LOCATION:
                log_value = 'xx.xxxx,xx.xxxx'
            elif setting == self.API_ID:
                log_value = ('...'.join((value[:3], value[-5:]))
                             if len(value) > 11 else
                             '...')
            elif setting in {self.API_KEY, self.API_SECRET}:
                log_value = ('...'.join((value[:3], value[-3:]))
                             if len(value) > 9 else
                             '...')
            else:
                log_value = value
            self.log.debug_trace('Get setting {name!r}:'
                                 ' {value!r} (str, {state})',
                                 name=setting,
                                 value=log_value,
                                 state=(error if error else 'success'),
                                 stacklevel=echo_level)
        self._cache[setting] = value
        return value

    def set_string(self, setting, value, echo_level=2):
        try:
            error = not self._proxy.set_str(setting, value)
            if error and self._check_set:
                error = 'failed'
            else:
                error = False
                self._cache[setting] = value
        except (RuntimeError, TypeError) as exc:
            error = exc

        if echo_level and self._echo_level:
            if setting == self.LOCATION:
                log_value = 'xx.xxxx,xx.xxxx'
            elif setting == self.API_ID:
                log_value = ('...'.join((value[:3], value[-5:]))
                             if len(value) > 11 else
                             '...')
            elif setting in {self.API_KEY, self.API_SECRET}:
                log_value = ('...'.join((value[:3], value[-3:]))
                             if len(value) > 9 else
                             '...')
            else:
                log_value = value
            self.log.debug_trace('Set setting {name!r}:'
                                 ' {value!r} (str, {state})',
                                 name=setting,
                                 value=log_value,
                                 state=(error if error else 'success'),
                                 stacklevel=echo_level)
        return not error

    def get_string_list(self, setting, default=None, echo_level=2):
        if setting in self._cache:
            return self._cache[setting]

        error = False
        try:
            value = self._proxy.get_str_list(setting)
            if not value:
                value = [] if default is None else default
        except (RuntimeError, TypeError) as exc:
            error = exc
            value = [] if default is None else default

        if echo_level and self._echo_level:
            self.log.debug_trace('Get setting {name!r}:'
                                 ' {value} (list[str], {state})',
                                 name=setting,
                                 value=value,
                                 state=(error if error else 'success'),
                                 stacklevel=echo_level)
        self._cache[setting] = value
        return value

    def set_string_list(self, setting, value, echo_level=2):
        try:
            error = not self._proxy.set_str_list(setting, value)
            if error and self._check_set:
                error = 'failed'
            else:
                error = False
                self._cache[setting] = value
        except (RuntimeError, TypeError) as exc:
            error = exc

        if echo_level and self._echo_level:
            self.log.debug_trace('Set setting {name!r}:'
                                 ' {value} (list[str], {state})',
                                 name=setting,
                                 value=value,
                                 state=(error if error else 'success'),
                                 stacklevel=echo_level)
        return not error
