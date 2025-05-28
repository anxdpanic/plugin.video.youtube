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

from .. import logging
from ..constants import DATA_PATH
from ..utils import make_dirs, merge_dicts, to_unicode


class JSONStore(object):
    log = logging.getLogger(__name__)

    BASE_PATH = make_dirs(DATA_PATH)

    _process_data = None

    def __init__(self, filename):
        if self.BASE_PATH:
            self.filepath = os.path.join(self.BASE_PATH, filename)
        else:
            self.log.error_trace(('Addon data directory not available',
                                  'Path: %s'),
                                 DATA_PATH,
                                 stacklevel=2)
            self.filepath = None

        self._data = {}
        self.load(stacklevel=3)
        self.set_defaults()

    def set_defaults(self, reset=False):
        raise NotImplementedError

    def save(self, data, update=False, process=True, stacklevel=2):
        if not self.filepath:
            return False

        if update:
            data = merge_dicts(self._data, data)
        if data == self._data:
            self.log.debug(('Data unchanged', 'File: %s'),
                           self.filepath,
                           stacklevel=stacklevel)
            return None
        self.log.debug(('Saving', 'File: %s'),
                       self.filepath,
                       stacklevel=stacklevel)
        try:
            if not data:
                raise ValueError
            _data = json.loads(
                json.dumps(data, ensure_ascii=False),
                object_pairs_hook=(self._process_data if process else None),
            )
            with open(self.filepath, mode='w', encoding='utf-8') as jsonfile:
                jsonfile.write(to_unicode(json.dumps(_data,
                                                     ensure_ascii=False,
                                                     indent=4,
                                                     sort_keys=True)))
            self._data = _data
        except (IOError, OSError):
            self.log.exception(('Access error', 'File: %s'),
                               self.filepath,
                               stacklevel=stacklevel)
            return False
        except (TypeError, ValueError):
            self.log.exception(('Invalid data', 'Data: %s'),
                               data,
                               stacklevel=stacklevel)
            self.set_defaults(reset=True)
            return False
        return True

    def load(self, process=True, stacklevel=2):
        if not self.filepath:
            return

        self.log.debug(('Loading', 'File: %s'),
                       self.filepath,
                       stacklevel=stacklevel)
        try:
            with open(self.filepath, mode='r', encoding='utf-8') as jsonfile:
                data = jsonfile.read()
            if not data:
                raise ValueError
            _data = json.loads(
                data,
                object_pairs_hook=(self._process_data if process else None),
            )
            self._data = _data
        except (IOError, OSError):
            self.log.exception(('Access error', 'File: %s'),
                               self.filepath,
                               stacklevel=stacklevel)
        except (TypeError, ValueError):
            self.log.exception(('Invalid data', 'Data: %s'),
                               data,
                               stacklevel=stacklevel)

    def get_data(self, process=True, fallback=True, stacklevel=2):
        try:
            if not self._data:
                raise ValueError
            _data = json.loads(
                json.dumps(self._data, ensure_ascii=False),
                object_pairs_hook=(self._process_data if process else None),
            )
            return _data
        except (TypeError, ValueError) as exc:
            self.log.exception(('Invalid data', 'Data: %s'),
                               self._data,
                               stacklevel=stacklevel)
            if fallback:
                self.set_defaults(reset=True)
                return self.get_data(process=process, fallback=False)
            raise exc

    def load_data(self, data, process=True, stacklevel=2):
        try:
            _data = json.loads(
                data,
                object_pairs_hook=(self._process_data if process else None),
            )
            return _data
        except (TypeError, ValueError):
            self.log.exception(('Invalid data', 'Data: %s'),
                               self._data,
                               stacklevel=stacklevel)
        return {}
