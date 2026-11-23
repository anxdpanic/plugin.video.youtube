import threading
import time

import pytest
import xbmcgui

from resources.lib.youtube import broker, http, innertube, service

SORRY = (b'<html><head><title>Sorry...</title></head><body>... but your computer or network may be sending '
         b'automated queries.</body></html>')


class FakeNet:
    """Stands in for http.send: records each request and answers from a script per URL."""

    def __init__(self, delay=0.0):
        self.sent = []  # (time, url)
        self.delay = delay
        self.answers = {}
        self.lock = threading.Lock()

    def __call__(self, url, data=None, headers=None, method=None, timeout=20):
        with self.lock:
            self.sent.append((time.time(), url))
            answer = self.answers.get(url, [])
            result = answer.pop(0) if answer else (200, b'ok ' + url.encode())
        if self.delay:
            time.sleep(self.delay)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def net():
    return FakeNet()


def make(net, **kwargs):
    kwargs.setdefault('gaps', {'www.youtube.com': 0.2})
    kwargs.setdefault('backoff', (0.4,))
    kwargs.setdefault('background_gap', 0.2)
    return broker.Broker(net, **kwargs)


def test_requests_to_a_host_are_spaced_out(net):
    pool = make(net, workers=3)
    threads = [threading.Thread(target=pool.request, args=('https://www.youtube.com/youtubei/v1/browse?%d' % i,))
               for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    times = sorted(t for t, _ in net.sent)
    assert len(times) == 4
    assert all(b - a >= 0.18 for a, b in zip(times, times[1:]))
    pool.stop()


def test_what_is_on_screen_goes_before_background_work(net):
    pool = make(net, workers=1)
    pool.request('https://www.youtube.com/first')  # the next slot is now 0.2 s away
    background = [pool.submit('https://www.youtube.com/banner%d' % i, priority=broker.BACKGROUND) for i in range(3)]
    screen = pool.submit('https://www.youtube.com/listing')
    for job in background + [screen]:
        job.done.wait(5)
    order = [url.rsplit('/', 1)[1] for _, url in net.sent]
    assert order[:2] == ['first', 'listing']
    pool.stop()


def test_identical_requests_are_sent_once(net):
    net.delay = 0.3
    pool = make(net, workers=2, gaps={})
    results = []
    threads = [threading.Thread(target=lambda: results.append(pool.request('https://www.youtube.com/same', b'x')))
               for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(net.sent) == 1 and len(results) == 3 and len(set(results)) == 1
    pool.stop()


def test_block_page_holds_the_host_retries_the_screen_and_drops_background(net):
    url = 'https://www.youtube.com/youtubei/v1/browse'
    net.answers[url] = [http.HTTPError(403, SORRY, url, blocked=True)]
    pool = make(net, workers=2)
    start = time.time()
    assert pool.request(url) == (200, b'ok ' + url.encode())  # waited out the hold, then worked
    assert time.time() - start >= 0.38 and len(net.sent) == 2
    # A second block: background work is dropped while the host is held back.
    net.answers[url] = [http.HTTPError(403, SORRY, url, blocked=True)] * 2
    with pytest.raises(http.HTTPError) as caught:
        pool.request(url)  # blocked, retried after the hold, blocked again: give up
    assert caught.value.blocked
    with pytest.raises(broker.Blocked):
        pool.request('https://www.youtube.com/banner', priority=broker.BACKGROUND)
    pool.stop()


def test_a_held_back_host_does_not_hold_up_others(net):
    url = 'https://www.youtube.com/youtubei/v1/browse'
    net.answers[url] = [http.HTTPError(403, SORRY, url, blocked=True)]
    pool = make(net, workers=1, backoff=(2,))
    held = pool.submit(url)  # will wait 2 s for its retry
    time.sleep(0.2)
    start = time.time()
    pool.request('https://oauth2.googleapis.com/token', b'refresh')
    assert time.time() - start < 1  # the single worker wasn't stuck waiting on youtube.com
    held.done.wait(5)
    pool.stop()


def test_listing_requests_reach_the_broker_through_the_service(net, monkeypatch):
    """End to end: a listing's http.request -> local server /fetch -> broker -> (fake) network."""
    url = 'https://www.youtube.com/youtubei/v1/next'
    net.answers[url] = [(200, b'{"ok": true}')]
    pool = make(net)
    monkeypatch.setattr(service._Handler, 'broker', pool)
    server = service._start_server((0,))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    xbmcgui.Window(10000).setProperty(http.PORT_PROPERTY, str(server.server_address[1]))
    try:
        assert http.request_json(url, data=b'{}') == {'ok': True}
        blocked = 'https://www.youtube.com/youtubei/v1/browse'
        net.answers[blocked] = [http.HTTPError(403, SORRY, blocked, blocked=True)] * 2
        with pytest.raises(http.HTTPError) as caught:
            http.request(blocked)
        assert caught.value.status == 403 and caught.value.blocked
        with pytest.raises(http.HTTPError) as refused:  # the service only forwards to Google's hosts
            http.request('https://example.com/elsewhere')
        assert refused.value.status == 0
        assert [u for _, u in net.sent].count('https://example.com/elsewhere') == 0
    finally:
        xbmcgui.Window(10000).clearProperty(http.PORT_PROPERTY)
        server.shutdown()
        server.server_close()
        pool.stop()


def test_only_google_hosts_are_forwarded():
    assert http.allowed('https://www.youtube.com/youtubei/v1/browse')
    assert http.allowed('https://oauth2.googleapis.com/token')
    assert not http.allowed('https://example.com/x')
    assert not http.allowed('http://www.youtube.com/insecure')
    assert not http.allowed('https://youtube.com.evil.example/x')


def test_innertube_does_not_retry_a_blocked_request(monkeypatch):
    calls = []

    def request_json(url, **kwargs):
        calls.append(kwargs.get('priority'))
        raise http.HTTPError(403, SORRY, url, blocked=True)
    monkeypatch.setattr(http, 'request_json', request_json)
    api = innertube.InnerTube(priority=http.BACKGROUND)
    api._state['visitor'] = {'data': 'V', 'ts': 9e12}
    with pytest.raises(innertube.InnerTubeError) as caught:
        api.browse('UCx')
    assert caught.value.blocked and caught.value.status == 403
    assert calls == [http.BACKGROUND]  # one attempt, no visitor refresh, sent as background work


def test_without_the_service_requests_are_paced_across_processes(monkeypatch):
    clock = [1000.0]
    waits = []
    monkeypatch.setattr(http.time, 'time', lambda: clock[0])
    monkeypatch.setattr(http.time, 'sleep', waits.append)
    monkeypatch.setattr(broker, 'GAPS', {'www.youtube.com': 1.0})
    xbmcgui.Window(10000).clearProperty(http.PACE_PROPERTY)
    url = 'https://www.youtube.com/youtubei/v1/browse'
    http._pace(url)
    clock[0] += 0.25
    http._pace(url)
    http._pace('https://oauth2.googleapis.com/token')  # unpaced host
    xbmcgui.Window(10000).setProperty(http.PACE_PROPERTY, repr(clock[0] + 3))  # another process's slot
    http._pace(url)
    assert waits == [0.75, 3]


def test_the_service_own_requests_go_straight_to_its_broker(net, monkeypatch):
    pool = make(net, gaps={})
    monkeypatch.setattr(http, '_broker', pool)
    url = 'https://www.youtube.com/api/timedtext?v=x'
    assert http.request(url) == (200, b'ok ' + url.encode())
    monkeypatch.setattr(pool, 'held_back', lambda host: True)
    pool._blocked_until['www.youtube.com'] = time.time() + 30
    with pytest.raises(http.HTTPError) as caught:
        http.request('https://www.youtube.com/banner', priority=http.BACKGROUND)
    assert caught.value.blocked
    pool.stop()


def test_blocks_on_requests_already_in_flight_count_once(net):
    """Several requests sent before the first block came back all get the block page: one hold, not three."""
    urls = ['https://www.youtube.com/b%d' % i for i in range(3)]
    for url in urls:
        net.answers[url] = [http.HTTPError(403, SORRY, url, blocked=True)]
    net.delay = 0.3  # all three are in flight together
    pool = make(net, workers=3, gaps={'www.youtube.com': 0.0}, backoff=(0.5, 5, 5))
    jobs = [pool.submit(url, priority=broker.BACKGROUND) for url in urls]
    for job in jobs:
        job.done.wait(5)
    assert pool._strikes['www.youtube.com'] == 1
    assert pool._blocked_until['www.youtube.com'] - time.time() < 1
    pool.stop()


def test_screen_requests_give_up_on_a_long_hold(net):
    pool = make(net, max_hold_wait=1)
    pool._blocked_until['www.youtube.com'] = time.time() + 30
    start = time.time()
    with pytest.raises(broker.Blocked):
        pool.request('https://www.youtube.com/youtubei/v1/browse')
    assert time.time() - start < 1  # "YouTube is busy" now, not in 30 s
    pool.stop()


def test_background_work_goes_slower_than_the_screen(net):
    pool = make(net, workers=2, gaps={'www.youtube.com': 0.05}, background_gap=0.4)
    jobs = [pool.submit('https://www.youtube.com/banner%d' % i, priority=broker.BACKGROUND) for i in range(3)]
    for job in jobs:
        job.done.wait(5)
    times = sorted(t for t, _ in net.sent)
    assert all(b - a >= 0.38 for a, b in zip(times, times[1:]))
    pool.stop()
