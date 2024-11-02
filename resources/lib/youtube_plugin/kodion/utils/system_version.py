# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from platform import python_version

from .methods import jsonrpc
from ..compatibility import string_type


class SystemVersion(object):
    RELEASE_NAME_MAP = {
        22: 'Piers',
        21: 'Omega',
        20: 'Nexus',
        19: 'Matrix',
        18: 'Leia',
        17: 'Krypton',
        16: 'Jarvis',
        15: 'Isengard',
        14: 'Helix',
        13: 'Gotham',
        12: 'Frodo',
    }

    def __init__(self, version=None, release_name=None, app_name=None):
        if isinstance(version, tuple):
            self._version = version
        else:
            version = None

        if app_name and isinstance(app_name, string_type):
            self._app_name = app_name
        else:
            app_name = None

        if version is None or app_name is None:
            try:
                result = jsonrpc(
                    method='Application.GetProperties',
                    params={'properties': ['version', 'name']},
                )['result'] or {}
            except (KeyError, TypeError):
                result = {}

            if version is None:
                version = result.get('version') or {}
                self._version = (version.get('major', 1),
                                 version.get('minor', 0))

            if app_name is None:
                self._app_name = result.get('name', 'Unknown application')

        if release_name and isinstance(release_name, string_type):
            self._release_name = release_name
        else:
            self._release_name = self.RELEASE_NAME_MAP.get(self._version[0],
                                                           'Unknown release')

        self._python_version = python_version()

    def __str__(self):
        return '{version[0]}.{version[1]} ({app_name} {release_name})'.format(
            release_name=self._release_name,
            app_name=self._app_name,
            version=self._version
        )

    def get_release_name(self):
        return self._release_name

    def get_version(self):
        return self._version

    def get_app_name(self):
        return self._app_name

    def get_python_version(self):
        return self._python_version

    def compatible(self, *version):
        return self._version >= version


current_system_version = SystemVersion()
