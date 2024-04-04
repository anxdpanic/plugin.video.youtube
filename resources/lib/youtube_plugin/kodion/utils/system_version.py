# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .methods import jsonrpc
from ..compatibility import string_type


class SystemVersion(object):
    def __init__(self, version=None, releasename=None, appname=None):
        self._version = (
            version if version and isinstance(version, tuple)
            else (0, 0, 0, 0)
        )

        self._releasename = (
            releasename if releasename and isinstance(releasename, string_type)
            else 'UNKNOWN'
        )

        self._appname = (
            appname if appname and isinstance(appname, string_type)
            else 'UNKNOWN'
        )

        try:
            response = jsonrpc(method='Application.GetProperties',
                               params={'properties': ['version', 'name']})
            version_installed = response['result']['version']
            self._version = (version_installed.get('major', 1),
                             version_installed.get('minor', 0))
            self._appname = response['result']['name']
        except (KeyError, TypeError):
            self._version = (1, 0)  # Frodo
            self._appname = 'Unknown Application'

        if self._version >= (21, 0):
            self._releasename = 'Omega'
        elif self._version >= (20, 0):
            self._releasename = 'Nexus'
        elif self._version >= (19, 0):
            self._releasename = 'Matrix'
        elif self._version >= (18, 0):
            self._releasename = 'Leia'
        elif self._version >= (17, 0):
            self._releasename = 'Krypton'
        elif self._version >= (16, 0):
            self._releasename = 'Jarvis'
        elif self._version >= (15, 0):
            self._releasename = 'Isengard'
        elif self._version >= (14, 0):
            self._releasename = 'Helix'
        elif self._version >= (13, 0):
            self._releasename = 'Gotham'
        elif self._version >= (12, 0):
            self._releasename = 'Frodo'
        else:
            self._releasename = 'Unknown Release'

    def __str__(self):
        obj_str = '{releasename} ({appname}-{version[0]}.{version[1]})'.format(
            releasename=self._releasename,
            appname=self._appname,
            version=self._version
        )
        return obj_str

    def get_release_name(self):
        return self._releasename

    def get_version(self):
        return self._version

    def get_app_name(self):
        return self._appname

    def compatible(self, *version):
        return self._version >= version


current_system_version = SystemVersion()
