import xbmc
import xbmcgui

from resources.lib.leanback import playback


def started(playing, time):
    xbmc.Player.PLAYING, xbmc.Player.TIME = playing, time
    del xbmc.Player.SEEKS[:]
    playback.StartAt().onAVStarted()
    return list(xbmc.Player.SEEKS)


def test_seeks_the_requested_video_once():
    playback.request('abcdefghijk', '60')
    assert started('http://127.0.0.1:61152/mpd/abcdefghijk.mpd', 0.5) == [60.0]
    assert xbmcgui.Window(10000).getProperty(playback.PROPERTY) == ''
    assert started('http://127.0.0.1:61152/mpd/abcdefghijk.mpd', 0.5) == []


def test_other_videos_and_offsets_kodi_already_applied_are_left_alone():
    playback.request('abcdefghijk', 60)
    assert started('http://127.0.0.1:61152/mpd/zzzzzzzzzzz.mpd', 0.5) == []
    playback.request('abcdefghijk', 60)
    assert started('http://127.0.0.1:61152/mpd/abcdefghijk.mpd', 59.8) == []


def test_no_request_for_nothing_or_bad_values():
    for value in (None, '', 'x', 0):
        playback.request('abcdefghijk', value)
        assert xbmcgui.Window(10000).getProperty(playback.PROPERTY) == ''
