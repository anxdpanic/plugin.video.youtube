import json

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.youtube import http, sponsorblock

VIDEO = 'abcdefghijk'
PLAYING = 'http://127.0.0.1:61152/mpd/%s.mpd' % VIDEO


def answer(monkeypatch, segments):
    body = json.dumps([{'videoID': 'zzzzzzzzzzz', 'segments': [{'segment': [1, 2], 'actionType': 'skip'}]},
                       {'videoID': VIDEO, 'segments': [{'segment': s, 'actionType': a} for s, a in segments]}])
    monkeypatch.setattr(http, 'send', lambda url, timeout=20: (200, body.encode('utf-8')))


def enable(monkeypatch, seek=False, edl=True, action=3):
    monkeypatch.setitem(xbmcaddon.SETTINGS, 'sponsorblock', True)
    monkeypatch.setitem(xbmcaddon.SETTINGS, 'sponsorblock_categories', 'sponsor,intro')
    monkeypatch.setitem(xbmcaddon.SETTINGS, 'sponsorblock_action', action)
    monkeypatch.setitem(xbmcaddon.SETTINGS, 'sponsorblock_seek', seek)
    monkeypatch.setattr(sponsorblock, 'edl_path_supported', lambda: edl)


def test_merge_joins_overlapping_and_nearly_touching_segments():
    assert sponsorblock.merge([(50, 60), (0, 10), (10.5, 20), (5, 8)]) == [(0, 20), (50, 60)]


def test_fetch_keeps_only_the_videos_skip_segments(monkeypatch):
    answer(monkeypatch, [([30, 40], 'skip'), ([0, 5], 'skip'), ([60, 70], 'mute')])
    assert sponsorblock.fetch(VIDEO, ['sponsor']) == [(0, 5), (30, 40)]


def test_fetch_failure_means_no_segments(monkeypatch):
    def fail(url, timeout=20):
        raise http.HTTPError(404)
    monkeypatch.setattr(http, 'send', fail)
    assert sponsorblock.fetch(VIDEO, ['sponsor']) == []


def test_edl_file_for_kodi(monkeypatch):
    enable(monkeypatch)
    answer(monkeypatch, [([30, 40.25], 'skip')])
    li = xbmcgui.ListItem()
    sponsorblock.apply(li, VIDEO)
    with open(li.properties['EDLPath'], encoding='utf-8') as edl:
        assert edl.read() == '30.000\t40.250\t3\n'
    assert xbmcgui.Window(10000).getProperty(sponsorblock.PROPERTY) == ''


def test_markers_mark_both_ends(monkeypatch):
    enable(monkeypatch, action=2)
    answer(monkeypatch, [([30, 40], 'skip')])
    li = xbmcgui.ListItem()
    sponsorblock.apply(li, VIDEO)
    with open(li.properties['EDLPath'], encoding='utf-8') as edl:
        assert edl.read() == '30.000\t30.000\t2\n40.000\t40.000\t2\n'



def test_markers_ignore_a_leftover_seek_setting(monkeypatch):
    """The seek toggle is disabled, not cleared, once markers are chosen; markers still need the EDL file."""
    enable(monkeypatch, seek=True, action=2)
    answer(monkeypatch, [([30, 40], 'skip')])
    li = xbmcgui.ListItem()
    sponsorblock.apply(li, VIDEO)
    assert 'EDLPath' in li.properties
    assert xbmcgui.Window(10000).getProperty(sponsorblock.PROPERTY) == ''


def test_service_seeks_past_each_segment_once_without_edl(monkeypatch):
    enable(monkeypatch, edl=False)
    answer(monkeypatch, [([30, 40], 'skip')])
    li = xbmcgui.ListItem()
    sponsorblock.apply(li, VIDEO)
    assert 'EDLPath' not in li.properties
    monkeypatch.setattr(sponsorblock.threading, 'Thread', lambda **kwargs: type('T', (), {'start': lambda s: None})())
    xbmc.Player.PLAYING, xbmc.Player.TIME = PLAYING, 31.0
    del xbmc.Player.SEEKS[:]
    skipper = sponsorblock.Skipper()
    skipper.onAVStarted()
    segments = skipper.playing['segments']
    skipper.step(segments)
    skipper.step(segments)
    assert xbmc.Player.SEEKS == [40]
    assert xbmcgui.Window(10000).getProperty(sponsorblock.PROPERTY) == ''


def test_off_by_default(monkeypatch):
    monkeypatch.setattr(http, 'send', lambda url, timeout=20: 1 / 0)
    li = xbmcgui.ListItem()
    sponsorblock.apply(li, VIDEO)
    assert li.properties == {}
