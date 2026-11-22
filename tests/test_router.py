import json

import xbmc
import xbmcaddon
import xbmcgui
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


def test_huge_view_counts_fit_a_c_int():
    """Music playlists hold videos with billions of views; 32-bit Kodi overflowed on setVotes."""
    item = video('a')
    item['views'] = 8_900_000_000
    run('browse', '?id=VLPLx')._render_items([item], browse_id='VLPLx')
    [(_, li, _)] = xbmcplugin.ITEMS
    assert li.tag.values['votes'] == 2 ** 31 - 1


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


def test_flattened_search_keeps_next_page_and_rows_open_as_searches(monkeypatch):
    results = {'title': 'Search results for cats', 'items': [video('aaaaaaaaaaa')], 'continuation': 'MORE',
               'shorts': False, 'endpoint': None}
    recent = {'title': 'Recently uploaded', 'items': [video('bbbbbbbbbbb')], 'continuation': None,
              'shorts': False, 'endpoint': {'type': 'search', 'query': 'cats videos', 'params': 'eAE='}}
    page = {'header': None, 'tabs': [], 'shelves': [results, recent], 'continuation': None}
    monkeypatch.setattr(router.Plugin, 'fetch', lambda self, desc, use_cache=True: {})
    monkeypatch.setattr(parser, 'parse_page', lambda resp: page)

    xbmcaddon.SETTINGS['shelves_as_folders'] = False
    run('search', '?q=cats').dispatch()
    assert router.url_for('page', ep='search', ctoken='MORE', n=2) in [u for u, _, _ in xbmcplugin.ITEMS]

    xbmcplugin.reset()
    xbmcaddon.SETTINGS['shelves_as_folders'] = True
    run('search', '?q=cats').dispatch()
    assert router.url_for('search', q='cats videos', params='eAE=') in [u for u, _, _ in xbmcplugin.ITEMS]
    assert run('')._state()['search_history'] == ['cats']


def test_listing_loads_several_pages_and_numbers_next_page(monkeypatch):
    def shelf(ids, token):
        return {'title': '', 'items': [video(i) for i in ids], 'continuation': token, 'shorts': False,
                'endpoint': None}
    pages = {None: ['a', 'b'], 'T2': ['b', 'c'], 'T3': ['d'], 'T4': ['e']}
    tokens = {None: 'T2', 'T2': 'T3', 'T3': 'T4', 'T4': None}
    fetched = []

    def fetch(self, desc, use_cache=True):
        fetched.append(desc.get('ctoken'))
        return desc.get('ctoken')
    monkeypatch.setattr(router.Plugin, 'fetch', fetch)
    monkeypatch.setattr(parser, 'parse_page', lambda token: {
        'header': None, 'tabs': [], 'continuation': None, 'shelves': [shelf(pages[token], tokens[token])]})

    xbmcaddon.SETTINGS['pages_per_listing'] = 3
    run('browse', '?id=FEsubscriptions').dispatch()
    urls = [u for u, _, _ in xbmcplugin.ITEMS]
    assert fetched == [None, 'T2', 'T3']
    assert urls[:-1] == [router.url_for('play', v=v) for v in 'abcd']  # the overlap ('b') shows once
    assert urls[-1] == router.url_for('page', ep='browse', ctoken='T4', bid='FEsubscriptions', n=2)
    assert xbmcplugin.ITEMS[-1][1].label == 'str30102 (2)'

    xbmcplugin.reset()
    run('page', '?ep=browse&ctoken=T4&bid=FEsubscriptions&n=2').dispatch()
    assert [u for u, _, _ in xbmcplugin.ITEMS] == [router.url_for('play', v='e')]


def test_rows_listing_loads_three_pages_of_rows(monkeypatch):
    """Home shows rows as folders; one page holds only a few rows, so the next two come with it."""
    def shelf(title):
        return {'title': title, 'items': [video(title.lower())], 'continuation': None, 'shorts': False,
                'endpoint': None}
    pages = {None: ['Recommended', 'Music'], 'T2': ['Music', 'News'], 'T3': ['Gaming'], 'T4': ['Live']}
    tokens = {None: 'T2', 'T2': 'T3', 'T3': 'T4', 'T4': None}
    fetched = []

    def fetch(self, desc, use_cache=True):
        fetched.append(desc.get('ctoken'))
        return desc.get('ctoken')
    monkeypatch.setattr(router.Plugin, 'fetch', fetch)
    monkeypatch.setattr(parser, 'parse_page', lambda token: {
        'header': None, 'tabs': [], 'continuation': tokens[token], 'shelves': [shelf(t) for t in pages[token]]})

    xbmcaddon.SETTINGS['pages_per_listing'] = 2
    run('browse', '?id=FEtopics').dispatch()
    assert fetched[:3] == [None, 'T2', 'T3']
    labels = [li.label for _, li, _ in xbmcplugin.ITEMS]
    assert labels == ['Recommended', 'Music', 'News', 'Gaming', 'str30102 (2)']  # 'Music' repeated once
    gaming = xbmcplugin.ITEMS[3][0]
    assert gaming == router.url_for('shelf', src=json.dumps({'ctoken': 'T3', 'ep': 'browse'}, sort_keys=True), i=0)
    assert xbmcplugin.ITEMS[-1][0] == router.url_for('page', ep='browse', ctoken='T4', bid='FEtopics', n=2)


def test_search_continuation_keeps_to_the_results_row(monkeypatch):
    """Each page of search results repeats side rows such as Songs; only the results continue."""
    def shelf(title, ids, token):
        return {'title': title, 'items': [video(i) for i in ids], 'continuation': token, 'shorts': False,
                'endpoint': None}
    pages = {'T2': [shelf('Results', ['a'], 'T3'), shelf('Songs', ['s'], None)],
             'T3': [shelf('Results', ['b'], 'T4'), shelf('Songs', ['s'], None)]}
    monkeypatch.setattr(router.Plugin, 'fetch', lambda self, desc, use_cache=True: desc['ctoken'])
    monkeypatch.setattr(parser, 'parse_page', lambda token: {
        'header': None, 'tabs': [], 'continuation': None, 'shelves': pages[token]})
    xbmcaddon.SETTINGS['pages_per_listing'] = 2
    run('page', '?ep=search&ctoken=T2&n=2').dispatch()
    assert [u for u, _, _ in xbmcplugin.ITEMS] == [router.url_for('play', v='a'), router.url_for('play', v='b'),
                                                    router.url_for('page', ep='search', ctoken='T4', n=3)]


def test_new_search_runs_as_a_script_not_a_folder():
    """As a folder, Kodi undid the Container.Update to the results by going back from the failed folder."""
    run('search').dispatch()
    new_search = [entry for entry in xbmcplugin.ITEMS if entry[0] == router.url_for('search/new')]
    assert new_search and new_search[0][2] is False


def test_shorts_menu_entry_runs_as_a_script(monkeypatch):
    """Shorts starts playback; as a folder its failed listing made Kodi leave the add-on."""
    monkeypatch.setattr(router.Plugin, 'guide', lambda self: guide_entries())
    run('').dispatch()
    folders = {url: folder for url, _, folder in xbmcplugin.ITEMS}
    assert folders[router.url_for('shorts', params='CA8=')] is False
    assert folders[router.url_for('accounts')] is False  # only opens a dialog
    assert folders[router.url_for('browse', id='FEtopics', title='Home')] is True


def test_empty_page_shows_youtubes_own_message(monkeypatch):
    import xbmcgui

    promo = {'bodyText': {'runs': [{'text': 'Videos you upload to YouTube will appear here'}]}}
    resp = {'contents': {'tvBrowseRenderer': {'content': {'tvSurfaceContentRenderer': {'content': {
        'genericPromoRenderer': promo}}}}}}
    monkeypatch.setattr(router.Plugin, 'fetch', lambda self, desc, use_cache=True: resp)
    run('browse', '?id=FEmy_videos').dispatch()
    assert 'Videos you upload to YouTube will appear here' in str(xbmcgui.NOTIFICATIONS)


def test_channel_rows_pointing_back_at_the_channel_open_the_row(monkeypatch):
    """The TV client ignores a channel's web tab params and returns the channel page again."""
    def shelf(title, endpoint):
        return {'title': title, 'items': [video(title[:11].ljust(11, 'x'))], 'continuation': 'C', 'shorts': False,
                'endpoint': endpoint}
    page = {'header': None, 'tabs': [], 'continuation': None, 'shelves': [
        shelf('Videos', {'type': 'browse', 'browse_id': 'UCchan', 'params': 'EgZ2aWRlb3M='}),
        shelf('A playlist', {'type': 'browse', 'browse_id': 'VLPLx', 'params': None})]}
    monkeypatch.setattr(router.Plugin, 'fetch', lambda self, desc, use_cache=True: {})
    monkeypatch.setattr(parser, 'parse_page', lambda resp: page)
    run('browse', '?id=UCchan').dispatch()
    urls = [u for u, _, _ in xbmcplugin.ITEMS]
    assert urls[0].startswith(router.url_for('shelf'))
    assert urls[1] == router.url_for('browse', id='VLPLx', title='A playlist')


def playlist_items(monkeypatch, ids):
    items = []
    for video_id in ids:
        item = parser._item_base('video', 'T ' + video_id, '', {'type': 'video', 'video_id': video_id})
        item['id'] = video_id
        items.append(item)
    monkeypatch.setattr(router.Plugin, 'fetch', lambda self, desc, use_cache=True: {})
    monkeypatch.setattr(parser, 'parse_page', lambda resp: {'shelves': [{'items': items}]})


def queued(query):
    del xbmc.Player.PLAYED[:], xbmc.Player.START_POSITIONS[:]
    router.Plugin(['plugin://plugin.video.leanback/play_playlist', '1', query]).dispatch()
    playlist = xbmc.Player.PLAYED[-1]
    return [url.rsplit('=', 1)[1] for url, _ in playlist.items], xbmc.Player.START_POSITIONS[-1]


def test_playlist_order_and_start_video(monkeypatch):
    playlist_items(monkeypatch, ['a', 'b', 'c'])
    assert queued('?list=PLx') == (['a', 'b', 'c'], 0)
    assert queued('?list=PLx&order=reverse') == (['c', 'b', 'a'], 0)
    assert queued('?list=PLx&v=b') == (['a', 'b', 'c'], 1)
    # A chosen first video keeps the playlist's order, even when shuffle is asked for.
    assert queued('?list=PLx&order=shuffle&v=c') == (['a', 'b', 'c'], 2)
    shuffled, position = queued('?list=PLx&order=shuffle')
    assert sorted(shuffled) == ['a', 'b', 'c'] and position == 0


class PlayerApi:
    """Just enough InnerTube for play(): one player response, signed out."""
    hl = 'en'

    def __init__(self, resp=None, error=None):
        self.resp, self.error = resp, error

    def player(self, video_id):
        if self.error:
            raise self.error
        return self.resp, {'ua': 'Test UA/1.0'}

    def signed_in(self):
        return False


def play(api, monkeypatch, port='50152'):
    monkeypatch.setitem(xbmcgui._PROPERTIES, 'leanback.port', port)
    plugin = run('play', '?v=abcdefghijk')
    plugin.api = api
    plugin.play()
    [(ok, li)] = xbmcplugin.RESOLVED
    return ok, li


def test_play_serves_a_dash_manifest(monkeypatch):
    from test_mpd import FORMATS
    resp = {'streamingData': {'adaptiveFormats': FORMATS}, 'videoDetails': {'videoId': 'abcdefghijk', 'title': 'T'}}
    ok, li = play(PlayerApi(resp), monkeypatch)
    assert ok and li.path == 'http://127.0.0.1:50152/mpd/abcdefghijk.mpd'
    assert li.mime == 'application/dash+xml'
    assert li.properties['inputstream.adaptive.stream_headers'] == 'User-Agent=Test%20UA/1.0'
    assert 'inputstream.adaptive.play_timeshift_buffer' not in li.properties


def test_play_live_uses_hls_with_timeshift(monkeypatch):
    resp = {'streamingData': {'hlsManifestUrl': 'https://manifest.googlevideo.com/x.m3u8'},
            'videoDetails': {'videoId': 'abcdefghijk', 'isLive': True}}
    ok, li = play(PlayerApi(resp), monkeypatch)
    assert ok and li.path.endswith('x.m3u8') and li.mime == 'application/vnd.apple.mpegurl'
    assert li.properties['inputstream.adaptive.play_timeshift_buffer'] == 'true'


def test_play_without_streams_fails_with_youtubes_reason(monkeypatch):
    from resources.lib.leanback.innertube import InnerTubeError
    ok, _ = play(PlayerApi(error=InnerTubeError('Video unavailable')), monkeypatch)
    assert not ok
    assert xbmcgui.NOTIFICATIONS[-1][1] == 'Video unavailable'


def sign_in(monkeypatch, polls, expires_in=1800):
    """Run the sign-in flow with the dialog left open and auth.poll_token returning each poll in turn."""
    import xbmc

    from resources.lib.leanback import auth
    added = []
    monkeypatch.setattr(xbmcgui.DialogProgress, 'iscanceled', lambda self: False)
    monkeypatch.setattr(xbmc.Monitor, 'waitForAbort', lambda self, timeout=0: False)
    monkeypatch.setattr(auth, 'request_device_code', lambda: {
        'device_code': 'D', 'user_code': 'ABC-DEF', 'verification_url': 'https://www.google.com/device',
        'interval': 0, 'expires_in': expires_in})
    pending = list(polls)
    monkeypatch.setattr(auth, 'poll_token', lambda device_code: pending.pop(0) if pending else None)
    monkeypatch.setattr(auth, 'add_account', lambda token: added.append(token) or 'acct')
    monkeypatch.setattr(auth, 'rename_account', lambda account_id, name: None)
    monkeypatch.setattr(router.InnerTube, 'account_name', lambda self: 'Viewer')
    run('account/sign_in').sign_in()
    return added


def test_sign_in_adds_the_account_once_approved(monkeypatch):
    assert sign_in(monkeypatch, [None, None, {'access_token': 'T'}]) == [{'access_token': 'T'}]
    assert 'Viewer' in xbmcgui.NOTIFICATIONS[-1][1]


def test_sign_in_stops_when_the_code_expires(monkeypatch):
    assert sign_in(monkeypatch, [], expires_in=0) == []
    assert xbmcgui.NOTIFICATIONS
