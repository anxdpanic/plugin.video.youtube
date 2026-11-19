import xbmcaddon
import xbmcplugin

from resources.lib.leanback import parser, router


def run(path, query=''):
    plugin = router.Plugin(['plugin://plugin.video.leanback/' + path, '1', query])
    return plugin


def test_url_for_drops_empty_params():
    assert router.url_for('browse', id='FEtopics', params=None) == 'plugin://plugin.video.leanback/browse?id=FEtopics'


def test_route_without_required_params_shows_main_menu(monkeypatch):
    """Kodi can open plugin://.../browse/ when it loses history; that must not hit the API."""
    calls = []
    monkeypatch.setattr(router.Plugin, 'root', lambda self: calls.append('root'))
    monkeypatch.setattr(router.Plugin, 'browse', lambda self: calls.append('browse'))
    run('browse/').dispatch()
    assert calls == ['root']


def test_unknown_route_ends_directory_unsuccessfully():
    run('nope').dispatch()
    assert xbmcplugin.ENDED == [False]


def guide_entries():
    return [
        {'id': 'search', 'title': 'Search', 'target': {'type': 'search', 'query': ''}, 'thumb': '', 'channel': False},
        {'id': 'FEtopics', 'title': 'Home', 'target': {'type': 'browse', 'browse_id': 'FEtopics'},
         'thumb': '', 'channel': False},
        {'id': 'shorts', 'title': 'Shorts', 'target': {'type': 'video', 'short': True, 'params': 'CA8='},
         'thumb': '', 'channel': False},
        {'id': 'UCgrian', 'title': 'Grian', 'target': {'type': 'browse', 'browse_id': 'UCgrian'},
         'thumb': 'x', 'channel': True},
    ]


def test_menu_customisation_order_hidden_pinned_and_shorts(monkeypatch):
    monkeypatch.setattr(router.Plugin, 'guide', lambda self: guide_entries())
    plugin = run('')
    plugin._save_state({'menu': {'order': ['FEtopics', 'search'], 'hidden': ['search'],
                                 'pinned': [{'id': 'UCpinned', 'title': 'Pinned', 'thumb': ''}]}})
    entries, channels = plugin.menu_entries()
    assert [e['id'] for e in entries] == ['FEtopics', 'shorts', 'UCpinned']
    assert [c['id'] for c in channels] == ['UCgrian']
    xbmcaddon.SETTINGS['hide_shorts'] = True
    entries, _ = plugin.menu_entries()
    assert 'shorts' not in [e['id'] for e in entries]
    every, _ = plugin.menu_entries(include_hidden=True)
    assert 'search' in [e['id'] for e in every]


def video(video_id, watched=0, short=False):
    item = parser._item_base('video', video_id, '', {'type': 'video', 'video_id': video_id})
    item.update(id=video_id, watched_pct=watched, short=short, duration=100)
    return item


def test_render_items_hides_shorts_and_watched():
    xbmcaddon.SETTINGS.update(hide_shorts=True, hide_watched=True, watched_threshold=80)
    plugin = run('browse', '?id=FEtopics')
    shown = plugin._render_items([video('a'), video('b', watched=90), video('c', short=True), video('d', 50)],
                                 browse_id='FEtopics')
    assert [i['id'] for i in shown] == ['a', 'd']
    resume = [li for url, li, _ in xbmcplugin.ITEMS if url.endswith('v=d')][0]
    assert resume.tag.values['resumepoint'] == (50.0, 100)


def test_history_is_not_filtered_for_watched():
    xbmcaddon.SETTINGS.update(hide_watched=True, watched_threshold=80)
    shown = run('browse', '?id=FEhistory')._render_items([video('a', watched=100)], browse_id='FEhistory')
    assert [i['id'] for i in shown] == ['a']


def test_mix_lists_watch_next_panel_instead_of_browsing(monkeypatch):
    """browse VLRD... is rejected by YouTube, so a Mix is read from the next endpoint."""
    mix = 'RDAjc1PXQvWBY'
    in_mix = video('a')
    in_mix['target']['playlist_id'] = mix
    fetched = []

    def fetch(self, desc, use_cache=True):
        fetched.append(desc)
        return {}

    monkeypatch.setattr(router.Plugin, 'fetch', fetch)
    monkeypatch.setattr(parser, 'parse_page', lambda resp: {'shelves': [{'items': [in_mix, video('b')]}]})
    run('browse', '?id=VL' + mix).dispatch()
    assert fetched == [{'ep': 'next', 'list': mix}]
    assert [url.rsplit('=', 1)[-1] for url, _, _ in xbmcplugin.ITEMS] == ['a']
