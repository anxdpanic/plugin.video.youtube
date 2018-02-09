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
import xbmcvfs
import xbmc


class JSONStore(object):
    def __init__(self, context, filename):
        self.context = context
        self.base_path = context._data_path
        self.filename = os.path.join(context._data_path, filename)
        self._data = None
        if xbmcvfs.exists(self.filename):
            self.load(force=True)
        else:
            self.save({})
        self.set_defaults()

    def set_defaults(self):
        pass

    def save(self, data):
        self._data = data
        if not xbmcvfs.exists(self.base_path):
            if not self.make_dirs(self.base_path):
                self.context.log_debug('JSONStore Save |{filename}| failed to create directories.'.format(filename=self.filename))
                return
        with open(self.filename, 'w') as jsonfile:
            self.context.log_debug('JSONStore Save |{filename}|'.format(filename=self.filename))
            json.dump(data, jsonfile, indent=4, sort_keys=True)

    def load(self, force=False):
        if force or not self._data:
            with open(self.filename, 'r') as jsonfile:
                data = json.load(jsonfile)
                self._data = data
                self.context.log_debug('JSONStore Load |{filename}|'.format(filename=self.filename))
                return data
        else:
            return self._data

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
