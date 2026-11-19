import xbmc

from resources.lib.leanback import kodi


def test_log_is_debug_only():
    del xbmc.LOG[:]
    kodi.log('hello')
    assert xbmc.LOG == [(xbmc.LOGDEBUG, '[plugin.video.leanback] hello')]


def test_log_error_keeps_error_level():
    del xbmc.LOG[:]
    kodi.log_error('boom')
    assert xbmc.LOG == [(xbmc.LOGERROR, '[plugin.video.leanback] boom')]
