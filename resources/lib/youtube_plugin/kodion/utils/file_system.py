# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os
import shutil

from .. import logging
from ..compatibility import xbmcvfs


def make_dirs(path):
    if not path.endswith('/'):
        path = ''.join((path, '/'))
    path = xbmcvfs.translatePath(path)

    if xbmcvfs.exists(path) or xbmcvfs.mkdirs(path):
        return path

    try:
        os.makedirs(path)
    except OSError:
        if not xbmcvfs.exists(path):
            logging.exception(('Failed', 'Path: %r'), path)
            return False
    return path


def rm_dir(path):
    if not path.endswith('/'):
        path = ''.join((path, '/'))
    path = xbmcvfs.translatePath(path)

    if not xbmcvfs.exists(path) or xbmcvfs.rmdir(path, force=True):
        return True

    try:
        shutil.rmtree(path)
    except OSError:
        logging.exception(('Failed', 'Path: %r'), path)
    return not xbmcvfs.exists(path)
