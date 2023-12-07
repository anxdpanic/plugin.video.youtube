# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import xbmc
import xbmcaddon

DEBUG = xbmc.LOGDEBUG
INFO = xbmc.LOGINFO
NOTICE = INFO
WARNING = xbmc.LOGWARNING
ERROR = xbmc.LOGERROR
FATAL = xbmc.LOGFATAL
SEVERE = FATAL
NONE = xbmc.LOGNONE

_ADDON_ID = 'plugin.video.youtube'


def log(text, log_level=DEBUG, addon_id=_ADDON_ID):
    if not addon_id:
        addon_id = xbmcaddon.Addon().getAddonInfo('id')
    log_line = '[%s] %s' % (addon_id, text)
    xbmc.log(msg=log_line, level=log_level)


def log_debug(text, addon_id=_ADDON_ID):
    log(text, DEBUG, addon_id)


def log_info(text, addon_id=_ADDON_ID):
    log(text, INFO, addon_id)


def log_notice(text, addon_id=_ADDON_ID):
    log(text, NOTICE, addon_id)


def log_warning(text, addon_id=_ADDON_ID):
    log(text, WARNING, addon_id)


def log_error(text, addon_id=_ADDON_ID):
    log(text, ERROR, addon_id)
