# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import os
from io import open

from ..compatibility import xbmcaddon, xbmcvfs
from ..logger import log_debug, log_error
from ..utils import make_dirs, merge_dicts, to_unicode


_addon_id = 'plugin.video.youtube'
_addon = xbmcaddon.Addon(_addon_id)
_addon_data_path = _addon.getAddonInfo('profile')
del _addon


class JSONStore(object):
    def __init__(self, filename):
        self.base_path = xbmcvfs.translatePath(_addon_data_path)

        if not xbmcvfs.exists(self.base_path) and not make_dirs(self.base_path):
            log_error('JSONStore.__init__ - invalid path:\n|{path}|'.format(
                path=self.base_path
            ))
            return

        self.filename = os.path.join(self.base_path, filename)
        self._data = {}
        self.load()
        self.set_defaults()

    def set_defaults(self, reset=False):
        raise NotImplementedError

    def save(self, data, update=False, process=None):
        if update:
            data = merge_dicts(self._data, data)
        if data == self._data:
            log_debug('JSONStore.save - data unchanged:\n|{filename}|'.format(
                filename=self.filename
            ))
            return
        log_debug('JSONStore.save - saving:\n|{filename}|'.format(
            filename=self.filename
        ))
        try:
            if not data:
                raise ValueError
            _data = json.loads(json.dumps(data, ensure_ascii=False))
            with open(self.filename, mode='w', encoding='utf-8') as jsonfile:
                jsonfile.write(to_unicode(json.dumps(_data,
                                                     ensure_ascii=False,
                                                     indent=4,
                                                     sort_keys=True)))
            self._data = process(_data) if process is not None else _data
        except (IOError, OSError):
            log_error('JSONStore.save - access error:\n|{filename}|'.format(
                filename=self.filename
            ))
            return
        except (TypeError, ValueError):
            log_error('JSONStore.save - invalid data:\n|{data}|'.format(
                data=data
            ))
            self.set_defaults(reset=True)

    def load(self, process=None):
        log_debug('JSONStore.load - loading:\n|{filename}|'.format(
            filename=self.filename
        ))
        try:
            with open(self.filename, mode='r', encoding='utf-8') as jsonfile:
                data = jsonfile.read()
            if not data:
                raise ValueError
            _data = json.loads(data)
            self._data = process(_data) if process is not None else _data
        except (IOError, OSError):
            log_error('JSONStore.load - access error:\n|{filename}|'.format(
                filename=self.filename
            ))
        except (TypeError, ValueError):
            log_error('JSONStore.load - invalid data:\n|{data}|'.format(
                data=data
            ))

    def get_data(self, process=None):
        try:
            if not self._data:
                raise ValueError
            _data = json.loads(json.dumps(self._data, ensure_ascii=False))
            return process(_data) if process is not None else _data
        except (TypeError, ValueError):
            log_error('JSONStore.get_data - invalid data:\n|{data}|'.format(
                data=self._data
            ))
            self.set_defaults(reset=True)
        _data = json.loads(json.dumps(self._data, ensure_ascii=False))
        return process(_data) if process is not None else _data
