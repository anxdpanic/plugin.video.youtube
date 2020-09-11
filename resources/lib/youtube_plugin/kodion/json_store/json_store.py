# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import os
import json
from copy import deepcopy

import xbmcaddon
import xbmcvfs
import xbmc

from .. import logger

try:
    xbmc.translatePath = xbmcvfs.translatePath
except AttributeError:
    pass


class JSONStore(object):
    def __init__(self, filename):
        addon_id = 'plugin.video.youtube'
        addon = xbmcaddon.Addon(addon_id)

        try:
            self.base_path = xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
        except AttributeError:
            self.base_path = xbmc.translatePath(addon.getAddonInfo('profile'))

        self.filename = os.path.join(self.base_path, filename)

        self._data = None
        self.load()
        self.set_defaults()

    def set_defaults(self):
        raise NotImplementedError

    def save(self, data):
        if data != self._data:
            self._data = deepcopy(data)
            if not xbmcvfs.exists(self.base_path):
                if not self.make_dirs(self.base_path):
                    logger.log_debug('JSONStore Save |{filename}| failed to create directories.'.format(filename=self.filename.encode("utf-8")))
                    return
            with open(self.filename, 'w') as jsonfile:
                logger.log_debug('JSONStore Save |{filename}|'.format(filename=self.filename.encode("utf-8")))
                json.dump(self._data, jsonfile, indent=4, sort_keys=True)

    def load(self):
        if xbmcvfs.exists(self.filename):
            with open(self.filename, 'r') as jsonfile:
                data = json.load(jsonfile)
                self._data = data
                logger.log_debug('JSONStore Load |{filename}|'.format(filename=self.filename.encode("utf-8")))
        else:
            self._data = dict()

    def get_data(self):
        return deepcopy(self._data)

    @staticmethod
    def make_dirs(path):
        if not path.endswith('/'):
            path = ''.join([path, '/'])
        path = xbmc.translatePath(path)
        if not xbmcvfs.exists(path):
            try:
                _ = xbmcvfs.mkdirs(path)
            except:
                pass
            if not xbmcvfs.exists(path):
                try:
                    os.makedirs(path)
                except:
                    pass
            return xbmcvfs.exists(path)

        return True
