import os

import pytest
import xbmc
import xbmcgui

from resources.lib.youtube import kodi, maintenance, router


def write(path, data='x' * 100):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(data)
    return path


@pytest.fixture
def stored():
    """One of everything the add-on keeps, plus the user data Maintenance must leave alone."""
    kodi.Cache.set('page', {'a': 1})
    write(kodi.temp_file('aaaaaaaaaaa.mpd'))
    write(kodi.temp_file('aaaaaaaaaaa.subs.json'))
    write(kodi.temp_file('bbbbbbbbbbb.mpd'))
    write(os.path.join(kodi.PROFILE, 'channel_art.json'), '{}')
    write(os.path.join(kodi.PROFILE, 'descriptions.json'), '{}')
    write(os.path.join(kodi.PROFILE, 'accounts.json'), '{"active": "me"}')
    kodi.save_json('state.json', {'visitor': {'data': 'V', 'ts': 1}, 'search_history': ['cats'],
                                  'menu': {'hidden': ['search']}})
    yield
    xbmc.Player.PLAYING = ''


def temp_names():
    return sorted(os.listdir(kodi.TEMP_DIR)) if os.path.isdir(kodi.TEMP_DIR) else []


def test_clear_cache(stored):
    assert maintenance.clear_cache() > 0
    assert kodi.Cache.get('page', 3600) is None
    assert maintenance.clear_cache() == 0


def test_clear_temp_keeps_the_playing_video(stored):
    xbmc.Player.PLAYING = 'http://127.0.0.1:61152/mpd/aaaaaaaaaaa.mpd'
    assert maintenance.clear_temp() > 0
    assert temp_names() == ['aaaaaaaaaaa.mpd', 'aaaaaaaaaaa.subs.json']
    xbmc.Player.PLAYING = ''
    maintenance.clear_temp()
    assert temp_names() == []


def test_clear_art(stored):
    assert maintenance.clear_art() == 4
    assert not os.path.exists(os.path.join(kodi.PROFILE, 'channel_art.json'))
    assert not os.path.exists(os.path.join(kodi.PROFILE, 'descriptions.json'))


def test_state_keys_cleared_one_at_a_time(stored):
    assert maintenance.clear_search_history()
    assert 'search_history' not in kodi.load_json('state.json', {})
    assert maintenance.clear_visitor()
    assert kodi.load_json('state.json', {}) == {'menu': {'hidden': ['search']}}
    assert maintenance.clear_visitor() == 0


def test_clear_all_leaves_accounts_settings_and_menu(stored):
    assert maintenance.clear_all() > 0
    assert temp_names() == []
    assert not os.path.isdir(kodi.CACHE_DIR)
    assert kodi.load_json('accounts.json', {}) == {'active': 'me'}
    assert kodi.load_json('state.json', {}) == {'menu': {'hidden': ['search']}}


def test_human_size():
    assert maintenance.human_size(512) == '512 B'
    assert maintenance.human_size(2048) == '2.0 KB'
    assert maintenance.human_size(3 * 1024 * 1024) == '3.0 MB'


def run(what, confirm, monkeypatch):
    monkeypatch.setattr(xbmcgui.Dialog, 'yesno', lambda self, heading, message, **kw: confirm)
    router.Plugin(['plugin://plugin.video.youtube/maintenance', '-1', '?what=' + what]).dispatch()


def test_route_asks_first_then_clears_and_reports(stored, monkeypatch, english):
    english(30154, 30158)
    run('search', False, monkeypatch)
    assert 'search_history' in kodi.load_json('state.json', {})
    assert xbmcgui.NOTIFICATIONS == []
    run('search', True, monkeypatch)
    assert 'search_history' not in kodi.load_json('state.json', {})
    [(_, message, _)] = xbmcgui.NOTIFICATIONS
    assert message.startswith('Cleared: Search history, ')


def test_route_reports_nothing_to_clear(monkeypatch, english):
    english(30159)
    run('cache', True, monkeypatch)
    assert xbmcgui.NOTIFICATIONS[0][1] == 'Nothing to clear'


def test_unknown_action_does_nothing(monkeypatch):
    run('everything', True, monkeypatch)
    assert xbmcgui.NOTIFICATIONS == []

