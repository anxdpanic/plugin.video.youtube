__author__ = 'bromix'

import xbmc
import json
from ..abstract_system_version import AbstractSystemVersion


class XbmcSystemVersion(AbstractSystemVersion):
    def __init__(self, version, releasename, appname):
        super(XbmcSystemVersion, self).__init__(version, releasename, appname)
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
