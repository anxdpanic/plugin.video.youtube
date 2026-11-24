import urllib.parse

import xbmc
import xbmcgui

from resources.lib.youtube import history

PLAYBACK = 'https://s.youtube.com/api/stats/playback?docid=abcdefghijk&ei=E'
WATCHTIME = 'https://s.youtube.com/api/stats/watchtime?docid=abcdefghijk&ei=E'


def resp():
    return {'videoDetails': {'lengthSeconds': '300'},
            'playbackTracking': {'videostatsPlaybackUrl': {'baseUrl': PLAYBACK},
                                 'videostatsWatchtimeUrl': {'baseUrl': WATCHTIME}}}


def query(url):
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))


def test_tracking_info_needs_both_urls():
    info = history.tracking_info(resp(), 'UA')
    assert info == {'playback': PLAYBACK, 'watchtime': WATCHTIME, 'ua': 'UA', 'length': 300}
    assert history.tracking_info({'playbackTracking': {}}, 'UA') is None


def test_session_reports_playback_then_watchtime_segments(monkeypatch):
    sent = []
    info = history.tracking_info(resp(), 'UA')
    session = history.Session(info, send=lambda url, ua: sent.append(url))
    session.start(10.0)
    first = query(sent[0])
    assert sent[0].startswith('https://s.youtube.com/api/stats/playback?')
    assert first['docid'] == 'abcdefghijk' and first['ver'] == '2' and first['cmt'] == '10.000'
    assert first['len'] == '300' and len(first['cpn']) == 16

    session.update(20.0)  # too soon for a report
    assert len(sent) == 1
    session.seeked(100.0)  # closes 10 -> 20
    session.update(130.0, force=True)
    session.update(None, state='paused', final=True, force=True)
    segments = [query(u) for u in sent[1:]]
    assert [(q['st'], q['et']) for q in segments] == [('10.000', '20.000'), ('100.000', '130.000'),
                                                      ('130.000', '130.000')]
    assert segments[-1]['final'] == '1' and segments[-1]['state'] == 'paused'
    assert all(q['cpn'] == first['cpn'] for q in segments)


def test_tracker_only_reports_the_video_the_plugin_resolved(monkeypatch):
    started = []
    monkeypatch.setattr(history.Session, 'start', lambda self, position: started.append(position))
    monkeypatch.setattr(history.threading, 'Thread', lambda target, args, name: type(
        'T', (), {'daemon': False, 'start': lambda self: target(*args)})())
    looked_up = []

    def stats(video_id):
        looked_up.append(video_id)
        return history.tracking_info(resp(), 'UA')
    path = 'http://127.0.0.1:1/mpd/abcdefghijk.mpd'
    tracker = history.Tracker(stats=stats)

    monkeypatch.setattr(xbmc.Player, 'PLAYING', 'smb://nas/movie.mkv')
    history.publish('abcdefghijk', path)
    tracker.onAVStarted()
    assert tracker.session is None and looked_up == []
    assert xbmcgui.Window(10000).getProperty(history.PROPERTY) == ''

    monkeypatch.setattr(xbmc.Player, 'PLAYING', path)
    monkeypatch.setattr(xbmc.Player, 'TIME', 12.0)
    history.publish('abcdefghijk', path)
    tracker.onAVStarted()
    assert looked_up == ['abcdefghijk'] and started == [12.0] and tracker.session is not None
