import json
import urllib.request

import pytest
import xbmcaddon
import xbmcgui

from resources.lib.leanback import describe, descriptions, http
from resources.lib.leanback.innertube import InnerTubeError

PATH = 'plugin://plugin.video.leanback/browse?id=FEtopics'


def details(video_id):
    return {'video_id': video_id, 'plot': 'About ' + video_id, 'date': '2023-05-01',
            'subscribers': '1M subscribers', 'likes': '1200', 'published': '2 years ago'}


class Screen:
    """What Kodi shows and the refreshes the describer asked for."""

    def __init__(self, path=PATH):
        self.path = path
        self.refreshes = 0

    def describer(self, fetch):
        return describe.Describer(fetch=fetch, current_path=lambda: self.path, refresh=self.refresh,
                                  wait=lambda seconds: False)

    def refresh(self):
        self.refreshes += 1


def ids(count):
    return ['%011d' % n for n in range(count)]


def test_fetches_in_order_stores_facts_and_refreshes_in_steps():
    fetched = []
    screen = Screen()

    def fetch(video_id):
        fetched.append(video_id)
        return details(video_id)

    new = screen.describer(fetch).work(PATH, ids(7))
    assert new == 7 and fetched == ids(7)
    assert screen.refreshes == 2  # after 5, then the last 2
    entry = descriptions.Descriptions().get(ids(7)[0])
    assert entry['d'] == 'About 00000000000' and entry['s'] == '1M subscribers' and entry['l'] == '1200'
    assert entry['t'] == '2 years ago' and entry['w'] == 1


def test_skips_videos_already_read_and_ones_that_failed():
    descriptions.Descriptions().remember_details(details('00000000000'))
    calls = []

    def fetch(video_id):
        calls.append(video_id)
        if video_id == '00000000001':
            raise InnerTubeError('nope', 400)
        return details(video_id)

    describer = Screen().describer(fetch)
    assert describer.work(PATH, ids(3)) == 1
    assert describer.work(PATH, ids(3)) == 0  # second pass: nothing left to try
    assert calls == ['00000000001', '00000000002']


def test_stops_when_the_listing_is_left():
    screen = Screen()

    def fetch(video_id):
        screen.path = 'plugin://plugin.video.leanback/'  # the user moved on
        return details(video_id)

    assert screen.describer(fetch).work(PATH, ids(4)) == 1
    assert screen.refreshes == 0  # nothing to refresh off screen


def test_stops_when_youtube_holds_requests_back():
    calls = []

    def fetch(video_id):
        calls.append(video_id)
        raise InnerTubeError('held', 403, blocked=True)

    assert Screen().describer(fetch).work(PATH, ids(4)) == 0
    assert calls == ['00000000000']


def test_newer_listing_replaces_the_queued_one_but_a_refresh_does_not():
    describer = Screen().describer(details)
    describer.submit(PATH, ids(2))
    describer.submit('plugin://plugin.video.leanback/browse?id=FEsubscriptions', ids(3))
    assert describer._take()[0].endswith('FEsubscriptions')
    describer.submit('plugin://plugin.video.leanback/browse?id=FEsubscriptions/', ['x'])  # its own refresh
    assert describer._job is None


def test_service_endpoint_queues_the_listing(monkeypatch):
    from resources.lib.leanback import service
    jobs = []

    class Recorder:
        def submit(self, path, video_ids):
            jobs.append((path, video_ids))

    monkeypatch.setattr(service._Handler, 'describer', Recorder())
    xbmcaddon.SETTINGS['fetch_descriptions'] = True
    server = service._start_server((0,))
    import threading
    threading.Thread(target=server.serve_forever, daemon=True).start()
    xbmcgui.Window(10000).setProperty(http.PORT_PROPERTY, str(server.server_address[1]))
    try:
        describe.request(PATH, ids(80))
        bad = urllib.request.Request('http://127.0.0.1:%d/describe' % server.server_address[1], b'{}',
                                     {'Content-Type': 'application/json'})
        try:
            urllib.request.urlopen(bad, timeout=2)
            status = 200
        except urllib.error.HTTPError as exc:
            status = exc.code
    finally:
        server.shutdown()
        server.server_close()
    assert jobs == [(PATH, ids(describe.LIMIT))]
    assert status == 400


def test_request_respects_the_setting(monkeypatch):
    sent = []
    monkeypatch.setattr(urllib.request, 'urlopen', lambda req, timeout=0: sent.append(json.loads(req.data)))
    xbmcgui.Window(10000).setProperty(http.PORT_PROPERTY, '1')
    xbmcaddon.SETTINGS['fetch_descriptions'] = False
    describe.request(PATH, ids(1))
    assert sent == []


class Focus:
    """A fake clock and focused item for the focus watcher."""

    def __init__(self, screen):
        self.now = 100.0
        self.item = ''
        self.fetched = []
        self.describer = describe.Describer(
            fetch=lambda video_id: pytest.fail('background fetch used'),
            fetch_now=self.fetch, current_path=lambda: screen.path, refresh=screen.refresh,
            wait=lambda seconds: False, focused=lambda: self.item, clock=lambda: self.now)

    def fetch(self, video_id):
        self.fetched.append(video_id)
        return details(video_id)

    def rest_on(self, video_id, seconds):
        self.item = 'plugin://plugin.video.leanback/play?v=' + video_id
        self.describer.check_focus()
        self.now += seconds
        return self.describer.check_focus()


def test_focus_resting_on_a_video_fetches_it_straight_away():
    screen = Screen()
    focus = Focus(screen)
    assert focus.rest_on('fffffffffff', 1.0)
    assert focus.fetched == ['fffffffffff'] and screen.refreshes == 1
    assert descriptions.Descriptions().get('fffffffffff')['w'] == 1
    focus.now += 5
    assert not focus.describer.check_focus()  # already described: nothing more
    assert focus.fetched == ['fffffffffff']


def test_focus_passing_over_videos_fetches_nothing():
    focus = Focus(Screen())
    assert not focus.rest_on('aaaaaaaaaaa', 0.3)
    assert not focus.rest_on('bbbbbbbbbbb', 0.3)
    assert focus.fetched == []


def test_focus_ignores_folders_and_other_addons():
    screen = Screen()
    focus = Focus(screen)
    focus.item = 'plugin://plugin.video.leanback/browse?id=UCx'
    focus.describer.check_focus()
    focus.now += 2
    assert not focus.describer.check_focus()
    screen.path = 'plugin://plugin.video.youtube/'
    assert not focus.rest_on('aaaaaaaaaaa', 2)
    assert focus.fetched == []


def test_background_skips_what_focus_already_described():
    screen = Screen()
    focus = Focus(screen)
    focus.rest_on('00000000001', 1)
    fetched = []

    def fetch(video_id):
        fetched.append(video_id)
        return details(video_id)

    focus.describer._fetch = fetch
    assert focus.describer.work(PATH, ids(3)) == 2
    assert fetched == ['00000000000', '00000000002']
