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
