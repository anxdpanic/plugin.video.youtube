import pytest

from resources.lib.youtube import http, innertube


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


def test_retry_stays_on_the_apps_api_host(api, monkeypatch):
    hosts = []

    def request_json(url, data=None, headers=None, **kwargs):
        hosts.append(url.split('/youtubei/')[0])
        if len(hosts) == 1:
            raise http.HTTPError(503)
        return {'ok': True}

    monkeypatch.setattr(http, 'request_json', request_json)
    assert api.watch_page('abcdefghijk') == {'ok': True}
    assert hosts == ['https://youtubei.googleapis.com'] * 2


def test_401_refreshes_the_token_and_retries(api, monkeypatch):
    from resources.lib.youtube import auth
    refreshed = []
    monkeypatch.setattr(auth, 'access_token', lambda force_refresh=False: refreshed.append(force_refresh) or 'TOKEN')
    calls = responses(monkeypatch, http.HTTPError(401), {'ok': True})
    assert api.browse('FEtopics') == {'ok': True}
    assert calls == ['browse', 'browse']
    assert True in refreshed


def test_blocked_request_is_not_retried(api, monkeypatch):
    calls = responses(monkeypatch, http.HTTPError(429, blocked=True))
    with pytest.raises(innertube.InnerTubeError) as err:
        api.browse('FEtopics')
    assert err.value.blocked and calls == ['browse']


BOT_CHECK = {'playabilityStatus': {'status': 'LOGIN_REQUIRED', 'reason': "Sign in to confirm you're not a bot"}}
PLAYABLE = {'playabilityStatus': {'status': 'OK'},
            'streamingData': {'adaptiveFormats': [{'itag': 137, 'url': 'https://example/v'}]}}


def player_hosts(monkeypatch, *results):
    """Answer player requests with each result in turn; returns the hosts they went to."""
    hosts = []
    pending = list(results)

    def request_json(url, data=None, headers=None, **kwargs):
        hosts.append(url.split('/youtubei/')[0])
        return pending.pop(0)

    monkeypatch.setattr(http, 'request_json', request_json)
    return hosts


def test_bot_check_asks_the_apps_host_again(api, monkeypatch):
    hosts = player_hosts(monkeypatch, BOT_CHECK, PLAYABLE)
    resp, client = api.player('abcdefghijk')
    assert resp is PLAYABLE and client is innertube.PLAYER_CLIENTS[0]
    assert hosts == ['https://www.youtube.com', 'https://youtubei.googleapis.com']


def test_after_a_bot_check_the_other_clients_use_the_apps_host(api, monkeypatch):
    hosts = player_hosts(monkeypatch, BOT_CHECK, BOT_CHECK, PLAYABLE)
    resp, client = api.player('abcdefghijk')
    assert client is innertube.PLAYER_CLIENTS[1]
    assert hosts[1:] == ['https://youtubei.googleapis.com'] * 2


def test_bot_check_everywhere_is_reported_as_one(api, monkeypatch):
    hosts = player_hosts(monkeypatch, *[BOT_CHECK] * (len(innertube.PLAYER_CLIENTS) + 1))
    with pytest.raises(innertube.InnerTubeError) as err:
        api.player('abcdefghijk')
    assert err.value.bot_check and err.value.status is None
    assert len(hosts) == len(innertube.PLAYER_CLIENTS) + 1  # no visitor refreshes in between


def test_other_unplayable_reasons_are_not_bot_checks(api, monkeypatch):
    gone = {'playabilityStatus': {'status': 'ERROR', 'reason': 'Video unavailable'}}
    hosts = player_hosts(monkeypatch, *[gone] * len(innertube.PLAYER_CLIENTS))
    with pytest.raises(innertube.InnerTubeError, match='Video unavailable') as err:
        api.player('abcdefghijk')
    assert not err.value.bot_check
    assert set(hosts) == {'https://www.youtube.com'}
