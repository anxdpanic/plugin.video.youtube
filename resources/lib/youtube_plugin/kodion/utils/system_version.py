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
    RELEASE_MAP = {
        (22, 0): 'Piers',
        (21, 0): 'Omega',
        (20, 0): 'Nexus',
        (19, 0): 'Matrix',
        (18, 0): 'Leia',
        (17, 0): 'Krypton',
        (16, 0): 'Jarvis',
        (15, 0): 'Isengard',
        (14, 0): 'Helix',
        (13, 0): 'Gotham',
        (12, 0): 'Frodo',
    }

    def __init__(self, version=None, releasename=None, appname=None):
        if isinstance(version, tuple):
            self._version = version
        else:
            version = None

        if appname and isinstance(appname, string_type):
            self._appname = appname
        else:
            appname = None

        if version is None or appname is None:
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

            if appname is None:
                self._appname = result.get('name', 'Unknown application')

        if releasename and isinstance(releasename, string_type):
            self._releasename = releasename
        else:
            version = (self._version[0], self._version[1])
            self._releasename = self.RELEASE_MAP.get(version, 'Unknown release')

        self._python_version = python_version()

    def __str__(self):
        return '{version[0]}.{version[1]} ({appname} {releasename})'.format(
            releasename=self._releasename,
            appname=self._appname,
            version=self._version
        )

    def get_release_name(self):
        return self._releasename

    def get_version(self):
        return self._version

    def get_app_name(self):
        return self._appname

    def get_python_version(self):
        return self._python_version

    def compatible(self, *version):
        return self._version >= version


current_system_version = SystemVersion()
