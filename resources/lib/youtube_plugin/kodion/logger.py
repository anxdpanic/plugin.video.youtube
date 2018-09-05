__author__ = 'bromix'

import xbmc
import xbmcaddon

DEBUG = 0
INFO = 2
NOTICE = 2
WARNING = 3
ERROR = 4
SEVERE = 5
FATAL = 6
NONE = 7


def log(text, log_level=DEBUG, addon_id=''):
    if not addon_id:
        addon_id = xbmcaddon.Addon().getAddonInfo('id')
    log_line = '[%s] %s' % (addon_id, text)
    xbmc.log(msg=log_line, level=log_level)


def log_debug(text):
    log(text, DEBUG)


def log_info(text):
    log(text, INFO)


def log_notice(text):
    log(text, NOTICE)


def log_warning(text):
    log(text, WARNING)


def log_error(text):
    log(text, ERROR)
