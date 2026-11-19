import pytest

from resources.lib.leanback import http, innertube


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(innertube, 'RETRY_DELAY', 0)
    client = innertube.InnerTube()
    client._state['visitor'] = {'data': 'VISITOR', 'ts': 9e12}
    return client


def responses(monkeypatch, *results):
    """Make http.request_json return/raise each result in turn; returns the list of calls."""
    calls = []
    pending = list(results)

    def request_json(url, data=None, headers=None, **kwargs):
        calls.append(url.split('/v1/')[1].split('?')[0])
        result = pending.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(http, 'request_json', request_json)
    return calls


def test_transient_failure_is_retried_once(api, monkeypatch):
    calls = responses(monkeypatch, http.HTTPError(429), {'ok': True})
    assert api.browse('FEtopics') == {'ok': True}
    assert calls == ['browse', 'browse']


def test_403_refreshes_visitor_before_retrying(api, monkeypatch):
    calls = responses(monkeypatch, http.HTTPError(403),
                      {'responseContext': {'visitorData': 'NEW'}}, {'ok': True})
    assert api.browse('FEtopics') == {'ok': True}
    assert calls == ['browse', 'guide', 'browse']
    assert api.visitor_data() == 'NEW'


def test_second_failure_gives_up_with_status(api, monkeypatch):
    responses(monkeypatch, http.HTTPError(503), http.HTTPError(503))
    with pytest.raises(innertube.InnerTubeError) as err:
        api.browse('FEtopics')
    assert err.value.status == 503


def test_bad_request_is_not_retried(api, monkeypatch):
    calls = responses(monkeypatch, http.HTTPError(400, b'{"error": {"message": "invalid argument"}}'))
    with pytest.raises(innertube.InnerTubeError, match='invalid argument'):
        api.browse('VLRDx')
    assert calls == ['browse']


def test_requests_are_spaced_out_across_processes(monkeypatch):
    """Back-to-back requests trip Google's automated-queries block; each waits for the shared next slot."""
    import xbmcgui

    clock = [1000.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(round(seconds, 3))
        clock[0] += seconds
    monkeypatch.setattr(innertube.time, 'time', lambda: clock[0])
    monkeypatch.setattr(innertube.time, 'sleep', sleep)
    monkeypatch.setattr(innertube, 'REQUEST_GAP', 1.0)
    xbmcgui.Window(10000).clearProperty(innertube.PACE_PROPERTY)

    innertube._pace()            # first request goes straight away
    clock[0] += 0.25
    innertube._pace()            # 0.25 s later: waits out the rest of the gap
    xbmcgui.Window(10000).setProperty(innertube.PACE_PROPERTY, repr(clock[0] + 0.5))
    innertube._pace()            # another process already took the next slot
    clock[0] += 5
    innertube._pace()            # long after: no wait
    assert sleeps == [0.75, 0.5]


def test_threads_of_one_process_get_separate_slots(monkeypatch):
    import threading

    import xbmcgui

    monkeypatch.setattr(innertube, 'REQUEST_GAP', 1.0)
    monkeypatch.setattr(innertube.time, 'time', lambda: 1000.0)
    waits = []
    monkeypatch.setattr(innertube.time, 'sleep', waits.append)
    xbmcgui.Window(10000).clearProperty(innertube.PACE_PROPERTY)
    threads = [threading.Thread(target=innertube._pace) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(waits) == [1.0, 2.0, 3.0]  # one went at once, the others queued a second apart
