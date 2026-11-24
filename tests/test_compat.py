import pytest

from resources.lib.youtube import compat, router


def translate(path, **params):
    route = path.strip('/')
    return compat.translate(route, params, router.ROUTES)


@pytest.mark.parametrize('path, params, expected', [
    ('/', {}, ('', {})),
    ('/home/', {}, ('', {})),
    ('/play/', {'video_id': 'abcdefghijk'}, ('play', {'v': 'abcdefghijk'})),
    ('/play/', {'video_id': 'abcdefghijk', 'seek': '90'}, ('play', {'v': 'abcdefghijk', 't': '90'})),
    ('/play/', {'video_id': 'abcdefghijk', 'start': '12'}, ('play', {'v': 'abcdefghijk', 't': '12'})),
    ('/play/', {'playlist_id': 'PLx', 'play': '1'}, ('play_playlist', {'list': 'PLx'})),
    ('/play/', {'playlist_id': 'PLx', 'play': '1', 'order': 'shuffle', 'video_id': 'v1'},
     ('play_playlist', {'list': 'PLx', 'order': 'shuffle', 'v': 'v1'})),
    ('/channel/UCabc/', {}, ('browse', {'id': 'UCabc'})),
    ('/playlist/PLx/', {}, ('browse', {'id': 'VLPLx'})),
    ('/channel/UCabc/playlist/PLx/', {}, ('browse', {'id': 'VLPLx'})),
    ('/channel/mine/playlist/LL/', {}, ('browse', {'id': 'VLLL'})),
    ('/channel/mine/playlists/', {}, ('browse', {'id': 'FEplaylist_aggregation'})),
    ('/special/related_videos/', {'video_id': 'v1'}, ('related', {'v': 'v1'})),
    ('/special/recommendations/', {}, ('browse', {'id': 'FEwhat_to_watch'})),
    ('/special/my_subscriptions/', {}, ('browse', {'id': 'FEsubscriptions'})),
    ('/special/saved_playlists/', {}, ('browse', {'id': 'FEplaylist_aggregation'})),
    ('/subscriptions/list/', {}, ('browse', {'id': 'FEsubscriptions', 'tabs': '1'})),
    ('/kodion/search/query/', {'q': 'cats'}, ('search', {'q': 'cats'})),
    ('/search/', {'q': 'cats'}, ('search', {'q': 'cats'})),
    ('/kodion/search/input/', {}, ('search/new', {})),
    ('/kodion/search/list/', {}, ('search', {})),
    ('/kodion/search/remove/', {'q': 'cats'}, ('search/remove', {'q': 'cats'})),
    ('/kodion/playback_history/', {}, ('browse', {'id': 'FEhistory'})),
    ('/kodion/watch_later/list/', {}, ('browse', {'id': 'VLWL'})),
])
def test_earlier_version_paths_map_to_routes(path, params, expected):
    assert translate(path, **params) == expected


@pytest.mark.parametrize('path, params', [
    ('browse', {'id': 'FEtopics'}),
    ('play', {'v': 'abcdefghijk'}),
    ('search', {'q': 'cats', 'params': 'EgIQAQ=='}),
    ('search', {}),
    ('maintenance', {'what': 'cache'}),
    ('shelf', {'src': '{}', 'i': '0'}),
])
def test_own_routes_pass_through(path, params):
    assert translate(path, **params) == (path, params)


def test_unknown_and_unsupported_paths_are_left_alone():
    # Settings-only and account-editing paths of the other add-on aren't mapped.
    assert translate('/maintenance/clear/', target='data_cache') == ('maintenance/clear', {'target': 'data_cache'})
    assert translate('/users/switch/') == ('users/switch', {})
    assert translate('/sign/in/') == ('sign/in', {})
    assert translate('/config/youtube/') == ('config/youtube', {})
    assert translate('/video/rate/', rating='like') == ('video/rate', {'rating': 'like'})


def test_play_playlist_path_reaches_play_all(monkeypatch):
    calls = []
    monkeypatch.setattr(router.Plugin, 'play_playlist', lambda self: calls.append(self.params))
    router.Plugin(['plugin://plugin.video.youtube/play/', '1', '?playlist_id=PLx&play=1&order=reverse']).dispatch()
    assert calls == [{'list': 'PLx', 'order': 'reverse'}]


def test_plugin_applies_translation():
    plugin = router.Plugin(['plugin://plugin.video.youtube/play/', '1', '?video_id=abcdefghijk&seek=5'])
    assert (plugin.route, plugin.params) == ('play', {'v': 'abcdefghijk', 't': '5'})

