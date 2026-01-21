# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import os
import errno
from io import open

from .. import logging
from ..constants import DATA_PATH, FILE_READ, FILE_WRITE
from ..utils.convert_format import to_unicode
from ..utils.file_system import make_dirs
from ..utils.methods import merge_dicts


class JSONStore(object):
    log = logging.getLogger(__name__)

    BASE_PATH = make_dirs(DATA_PATH)

    _process_data = None

    def __init__(self, filename, context):
        self._filename = filename
        if self.BASE_PATH:
            self.filepath = os.path.join(self.BASE_PATH, filename)
        else:
            self.log.error_trace(('Addon data directory not available',
                                  'Path: %s'),
                                 DATA_PATH,
                                 stacklevel=2)
            self.filepath = None

        self._context = context
        self._loaded = False
        self._data = {}
        self.init()

    def init(self):
        loaded = self.load(stacklevel=4, ipc=False)
        self.set_defaults(reset=(not loaded))
        return loaded

    def set_defaults(self, reset=False):
        raise NotImplementedError

    def save(self, data, update=False, process=True, ipc=True, stacklevel=2):
        loaded = self._loaded
        filepath = self.filepath
        try:
            if not filepath:
                raise IOError

            self.log.debug(('Saving', 'File: %s'),
                           filepath,
                           stacklevel=stacklevel)

            _data = self._data
            if loaded is False:
                loaded = self.load(stacklevel=4)
                if loaded:
                    self.log.warning(('File state out of sync - data discarded',
                                      'File:     {file}',
                                      'Old data: {old_data!p}',
                                      'New data: {new_data!p}'),
                                     file=filepath,
                                     old_data=_data,
                                     new_data=data,
                                     stacklevel=stacklevel)
                    return None

            if update and _data:
                data = merge_dicts(_data, data)
            if not data:
                raise ValueError

            if data == _data:
                self.log.debug(('Data unchanged', 'File: %s'),
                               filepath,
                               stacklevel=stacklevel)
                return None

            _data = json.dumps(
                data, ensure_ascii=False, indent=4, sort_keys=True
            )
            self._data = json.loads(
                _data,
                object_pairs_hook=(self._process_data if process else None),
            )

            if loaded is False:
                self.log.debug(('File write deferred', 'File: %s'),
                               filepath,
                               stacklevel=stacklevel)
                return None

            if ipc:
                self._context.get_ui().set_property(
                    '-'.join((FILE_WRITE, filepath)),
                    to_unicode(_data),
                    log_value='<redacted>',
                )
                response = self._context.ipc_exec(
                    FILE_WRITE,
                    timeout=5,
                    payload={'filepath': filepath},
                    raise_exc=True,
                )
                if response is False:
                    raise IOError
                if response is None:
                    self.log.debug(('Data unchanged', 'File: %s'),
                                   filepath,
                                   stacklevel=stacklevel)
                    return None
            else:
                with open(filepath, mode='w', encoding='utf-8') as file:
                    file.write(to_unicode(_data))
        except (RuntimeError, IOError, OSError):
            self.log.exception(('Access error', 'File: %s'),
                               filepath or self._filename,
                               stacklevel=stacklevel)
            return False
        except (TypeError, ValueError):
            self.log.exception(('Invalid data', 'Data: {data!r}'),
                               data=data,
                               stacklevel=stacklevel)
            self.set_defaults(reset=True)
            return False
        return True

    def load(self, process=True, ipc=True, stacklevel=2):
        loaded = False
        filepath = self.filepath
        data = ''
        try:
            if not filepath:
                raise IOError

            self.log.debug(('Loading', 'File: %s'),
                           filepath,
                           stacklevel=stacklevel)

            if ipc:
                if self._context.ipc_exec(
                        FILE_READ,
                        timeout=5,
                        payload={'filepath': filepath},
                        raise_exc=True,
                ) is not False:
                    data = self._context.get_ui().get_property(
                        '-'.join((FILE_READ, filepath)),
                        log_value='<redacted>',
                    )
                else:
                    raise IOError
            else:
                with open(filepath, mode='r', encoding='utf-8') as file:
                    data = file.read()
            if not data:
                raise ValueError
            self._data = json.loads(
                data,
                object_pairs_hook=(self._process_data if process else None),
            )
            loaded = True
        except (RuntimeError, EnvironmentError, IOError, OSError) as exc:
            self.log.exception(('Access error', 'File: %s'),
                               filepath or self._filename,
                               stacklevel=stacklevel)
            if exc.errno == errno.ENOENT:
                loaded = None
        except (TypeError, ValueError):
            self.log.exception(('Invalid data', 'Data: {data!r}'),
                               data=data,
                               stacklevel=stacklevel)
            loaded = None

        self._loaded = loaded
        return loaded

    def get_data(self, process=True, fallback=True, stacklevel=2):
        if not self._loaded:
            self.init()
        data = self._data

        try:
            if not data:
                raise ValueError
            return json.loads(
                json.dumps(data, ensure_ascii=False),
                object_pairs_hook=(self._process_data if process else None),
            )
        except (TypeError, ValueError) as exc:
            self.log.exception(('Invalid data', 'Data: {data!r}'),
                               data=data,
                               stacklevel=stacklevel)
            if fallback:
                self.set_defaults(reset=True)
                return self.get_data(process=process, fallback=False)
            if self._loaded:
                raise exc
            return data

    def load_data(self, data, process=True, stacklevel=2):
        try:
            return json.loads(
                data,
                object_pairs_hook=(self._process_data if process else None),
            )
        except (TypeError, ValueError):
            self.log.exception(('Invalid data', 'Data: {data!r}'),
                               data=data,
                               stacklevel=stacklevel)
        return {}
