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
    monkeypatch.setattr(parser, 'parse_page', lambda resp: {'shelves': [
        {'items': [video('related')], 'continuation': 'RELATED'},
        {'items': [in_mix, video('b')], 'continuation': 'MORE'}]})
    run('browse', '?id=VL' + mix).dispatch()
    assert fetched == [{'ep': 'next', 'list': mix}]
    urls = [url for url, _, _ in xbmcplugin.ITEMS]
    assert urls[0].endswith('v=a') and len(urls) == 2
    assert 'ctoken=MORE' in urls[1] and 'id=VL' + mix in urls[1]
    # The next batch comes from the radio continuation.
    run('browse', '?id=VL%s&ctoken=MORE' % mix).dispatch()
    assert fetched[-1] == {'ep': 'next', 'ctoken': 'MORE'}


def test_failed_requests_show_friendly_messages(monkeypatch):
    import xbmcgui

    from resources.lib.leanback.innertube import InnerTubeError

    def fail(status):
        def browse(self):
            raise InnerTubeError('Request contains an invalid argument.', status)
        return browse

    for status, string_id in ((400, 30136), (403, 30135), (0, 30138), (503, 30137)):
        monkeypatch.setattr(router.Plugin, 'browse', fail(status))
        del xbmcgui.NOTIFICATIONS[:]
        run('browse', '?id=VLx').dispatch()
        assert 'str%d' % string_id in str(xbmcgui.NOTIFICATIONS)


def test_format_time():
    assert router.format_time(65) == '1:05'
    assert router.format_time(3725.5) == '1:02:05'


def test_chapters_seek_when_playing_and_start_there_otherwise(monkeypatch):
    import xbmc
    import xbmcgui

    found = [{'title': 'A', 'start': 0.0, 'thumb': ''}, {'title': 'B', 'start': 90.0, 'thumb': ''}]
    monkeypatch.setattr(router.Plugin, 'fetch', lambda self, desc, use_cache=True: {})
    monkeypatch.setattr(parser, 'chapters', lambda resp: found)
    picks = []

    def select(self, heading, items, preselect=-1, **kwargs):
        picks.append(preselect)
        return 1
    monkeypatch.setattr(xbmcgui.Dialog, 'select', select)

    monkeypatch.setattr(xbmc.Player, 'PLAYING', 'http://127.0.0.1:1/mpd/abcdefghijk.mpd')
    monkeypatch.setattr(xbmc.Player, 'TIME', 120.0)
    monkeypatch.setattr(xbmc.Player, 'SEEKS', [])
    run('chapters', '?v=abcdefghijk').dispatch()
    assert picks == [1] and xbmc.Player.SEEKS == [90.0]

    monkeypatch.setattr(xbmc.Player, 'PLAYING', '')
    monkeypatch.setattr(xbmc.Player, 'PLAYED', [])
    run('chapters', '?v=abcdefghijk').dispatch()
    expected = router.url_for('play', v='abcdefghijk', t='90.000')
    assert expected in xbmc.Player.PLAYED
