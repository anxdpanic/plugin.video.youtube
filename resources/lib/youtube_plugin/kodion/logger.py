# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .compatibility import xbmc
from .constants import ADDON_ID


class Logger(object):
    LOGDEBUG = xbmc.LOGDEBUG
    LOGINFO = xbmc.LOGINFO
    LOGNOTICE = xbmc.LOGNOTICE
    LOGWARNING = xbmc.LOGWARNING
    LOGERROR = xbmc.LOGERROR
    LOGFATAL = xbmc.LOGFATAL
    LOGSEVERE = xbmc.LOGSEVERE
    LOGNONE = xbmc.LOGNONE

    @staticmethod
    def log(text, log_level=LOGDEBUG, addon_id=ADDON_ID):
        log_line = '[%s] %s' % (addon_id, text)
        xbmc.log(msg=log_line, level=log_level)

    @staticmethod
    def log_debug(text, addon_id=ADDON_ID):
        log_line = '[%s] %s' % (addon_id, text)
        xbmc.log(msg=log_line, level=Logger.LOGDEBUG)

    @staticmethod
    def log_info(text, addon_id=ADDON_ID):
        log_line = '[%s] %s' % (addon_id, text)
        xbmc.log(msg=log_line, level=Logger.LOGINFO)

    @staticmethod
    def log_notice(text, addon_id=ADDON_ID):
        log_line = '[%s] %s' % (addon_id, text)
        xbmc.log(msg=log_line, level=Logger.LOGNOTICE)

    @staticmethod
    def log_warning(text, addon_id=ADDON_ID):
        log_line = '[%s] %s' % (addon_id, text)
        xbmc.log(msg=log_line, level=Logger.LOGWARNING)

    @staticmethod
    def log_error(text, addon_id=ADDON_ID):
        log_line = '[%s] %s' % (addon_id, text)
        xbmc.log(msg=log_line, level=Logger.LOGERROR)

    @staticmethod
    def debug_log(on=False, off=True):
        if on:
            Logger.LOGDEBUG = Logger.LOGNOTICE
        elif off:
            Logger.LOGDEBUG = xbmc.LOGDEBUG
        return Logger.LOGDEBUG
