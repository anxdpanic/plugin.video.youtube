__author__ = 'bromix'

import xbmc
import json
from ..abstract_system_version import AbstractSystemVersion


class XbmcSystemVersion(AbstractSystemVersion):
    def __init__(self, version, name):
        super(XbmcSystemVersion, self).__init__(version, name)
        try:
            json_query = xbmc.executeJSONRPC(
                '{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_query = json.loads(json_query)
            version_installed = []
            if 'result' in json_query and 'version' in json_query['result']:
                version_installed = json_query['result']['version']
                self._version = (version_installed.get('major', 1), version_installed.get('minor', 0))
                pass
        except:
            self._version = (1, 0)  # Frodo
            pass
        self._name = 'Unknown XBMC System'
        if self._version >= (12, 0):
            self._name = 'Frodo'
            pass
        if self._version >= (13, 0):
            self._name = 'Gotham'
            pass
        if self._version >= (14, 0):
            self._name = 'Helix'
            pass
        if self._version >= (15, 0):
            self._name = 'Isengard'
            pass
        if self._version >= (16, 0):
            self._name = 'Jarvis'
            pass
        if self._version >= (17, 0):
            self._name = 'Krypton'
            pass

    pass