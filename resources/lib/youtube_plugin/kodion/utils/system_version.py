# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from six.moves import map
from six import string_types
from six import python_2_unicode_compatible

import json

import xbmc


@python_2_unicode_compatible
class SystemVersion(object):
    def __init__(self, version, releasename, appname):
        if not isinstance(version, tuple):
            self._version = (0, 0, 0, 0)
        else:
            self._version = version

        if not releasename or not isinstance(releasename, string_types):
            self._releasename = 'UNKNOWN'
        else:
            self._releasename = releasename

        if not appname or not isinstance(appname, string_types):
            self._appname = 'UNKNOWN'
        else:
            self._appname = appname

        try:
            json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", '
                                             '"params": {"properties": ["version", "name"]}, "id": 1 }')
            json_query = str(json_query)
            json_query = json.loads(json_query)

            version_installed = json_query['result']['version']
            self._version = (version_installed.get('major', 1), version_installed.get('minor', 0))
            self._appname = json_query['result']['name']
        except:
            self._version = (1, 0)  # Frodo
            self._appname = 'Unknown Application'

        self._releasename = 'Unknown Release'
        if (19, 0) > self._version >= (18, 0):
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

    def __str__(self):
        obj_str = "%s (%s-%s)" % (self._releasename, self._appname, '.'.join(map(str, self._version)))
        return obj_str

    def get_release_name(self):
        return self._releasename

    def get_version(self):
        return self._version

    def get_app_name(self):
        return self._appname
