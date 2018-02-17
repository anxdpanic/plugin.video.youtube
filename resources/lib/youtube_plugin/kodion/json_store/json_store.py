# -*- coding: utf-8 -*-
"""
    Modified: Feb. 06, 2018 plugin.video.youtube

    Copyright (C) 2016 Twitch-on-Kodi

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import json
from copy import deepcopy

import xbmcvfs
import xbmc


class JSONStore(object):
    def __init__(self, filename):
        self.base_path = 'special://profile/addon_data/plugin.video.youtube/'
        self.filename = xbmc.translatePath(self.base_path + filename)
        self._data = None
        if xbmcvfs.exists(self.filename):
            self.load(force=True)
        else:
            self._data = dict()
        self.set_defaults()

    def set_defaults(self):
        self.save(self._data)

    def save(self, data):
        if data != self._data or self._data == dict():
            self._data = data
            if not xbmcvfs.exists(self.base_path):
                if not self.make_dirs(self.base_path):
                    xbmc.log('[plugin.video.youtube] JSONStore Save |{filename}| failed to create directories.'.format(filename=self.filename), xbmc.LOGDEBUG)
                    return
            with open(self.filename, 'w') as jsonfile:
                xbmc.log('[plugin.video.youtube] JSONStore Save |{filename}|'.format(filename=self.filename), xbmc.LOGDEBUG)
                json.dump(data, jsonfile, indent=4, sort_keys=True)

    def load(self, force=False):
        if force or not self._data:
            with open(self.filename, 'r') as jsonfile:
                data = json.load(jsonfile)
                self._data = data
                xbmc.log('[plugin.video.youtube] JSONStore Load |{filename}|'.format(filename=self.filename), xbmc.LOGDEBUG)
                return deepcopy(self._data)
        else:
            return deepcopy(self._data)

    def make_dirs(self, path):
        if not path.endswith('/'):
            path += '/'
        path = xbmc.translatePath(path)
        if not xbmcvfs.exists(path):
            try:
                r = xbmcvfs.mkdirs(path)
            except:
                pass
            if not xbmcvfs.exists(path):
                try:
                    os.makedirs(path)
                except:
                    pass
            return xbmcvfs.exists(path)

        return True
