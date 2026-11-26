import xbmcaddon

from resources.lib.youtube import parser
from resources.lib.youtube.tv import items, model, skin


def video(video_id, short=False, watched=0):
    item = parser._item_base('video', 'Video ' + video_id, 'https://i.ytimg.com/%s.jpg' % video_id,
                             {'type': 'video', 'video_id': video_id})
    item.update(id=video_id, short=short, watched_pct=watched, duration=100)
    return item


def shelf(title, ids, token=None):
    return {'title': title, 'items': [video(i) for i in ids], 'continuation': token, 'shorts': False,
            'endpoint': None}


def page(shelves, token=None, tabs=None):
    return {'header': None, 'tabs': tabs or [], 'shelves': shelves, 'continuation': token, 'message': ''}


def loader(pages_by_token):
    calls = []

    def load(desc):
        calls.append(desc.get('ctoken'))
        return pages_by_token[desc.get('ctoken')]
    load.calls = calls
    return load


def test_shelves_become_rows_and_more_load_near_the_end():
    load = loader({
        None: page([shelf('Trending', 'ab', 'T1'), shelf('Music', 'cd')], token='P2'),
        'P2': page([shelf('Music', 'cd'), shelf('Gaming', 'ef')], token=None),
        'T1': page([shelf('', 'bg', 'T2')]),
    })
    screen = model.Screen({'ep': 'browse', 'id': 'FEtopics'}, 'Home', load).open()
    assert [r.title for r in screen.rows] == ['Trending', 'Music']
    screen.ensure(0)
    assert [r.title for r in screen.rows] == ['Trending', 'Music', 'Gaming']  # repeated Music left out
    assert not screen.can_grow()
    fresh = screen.more_items(screen.rows[0])
    assert [i['id'] for i in fresh] == ['g']  # b was already in the row
    assert screen.rows[0].token == 'T2'


def test_single_list_is_cut_into_rows_and_keeps_filling():
    load = loader({
        None: page([shelf('', 'abcdef', 'G2')]),
        'G2': page([shelf('', 'fghij')]),
    })
    screen = model.Screen({'ep': 'browse', 'id': 'FEsubscriptions'}, 'Subscriptions', load).open()
    assert [len(r.items) for r in screen.rows] == [4, 2]
    first = screen.rows[0]
    first.pos = 3
    screen.ensure(0)
    assert [[i['id'] for i in r.items] for r in screen.rows] == [list('abcd'), list('efgh'), list('ij')]
    assert screen.rows[0] is first and first.pos == 3  # full rows keep their state
    assert all(r.grid for r in screen.rows)


def test_tabs_row_and_filter():
    tabs = [{'kind': 'channel', 'title': t, 'selected': t == 'All', 'target': {'type': 'browse'},
             'thumb': 'https://yt3.example/%s.jpg' % t} for t in ('All', 'Grian', 'LTT')]
    load = loader({None: page([{'title': 'Today', 'items': [video('a'), video('s', short=True)],
                                'continuation': None, 'shorts': False, 'endpoint': None}], tabs=tabs)})
    screen = model.Screen({'ep': 'browse'}, 'Subscriptions', load, keep=lambda i: not i['short'],
                          tabs_title='Channels').open()
    assert screen.rows[0].title == 'Channels'
    assert [t['title'] for t in screen.rows[0].items] == ['Grian', 'LTT']
    assert [i['id'] for i in screen.rows[1].items] == ['a']


def test_pick_fonts_by_size_and_weight():
    fonts = [('font13', 30, False, False), ('font12', 25, False, False), ('font27', 27, False, False),
             ('font52_title', 52, True, False), ('font45_title', 45, True, False), ('font32_title', 32, True, False),
             ('font20_title', 20, True, False), ('font23_narrow', 23, False, False),
             ('font_MainMenu', 60, True, True), ('Mono26', 26, False, False)]
    picked = skin.pick_fonts(fonts)
    assert picked['hero_title'] == 'font52_title'
    assert picked['row_title'] == 'font32_title'
    assert picked['hero_plot'] == 'font27'
    assert picked['tile_meta'] == 'font23_narrow'
    assert picked['badge'] == 'font20_title'
    assert skin.pick_fonts([])['rail'] == 'font13'


def test_read_fonts_scales_and_skips(tmp_path):
    font_xml = tmp_path / 'Font.xml'
    font_xml.write_text('''<fonts><fontset id="Other"><font><name>x</name><filename>a.ttf</filename><size>9</size>
        </font></fontset><fontset id="Arial">
        <font><name>font13</name><filename>arial.ttf</filename><size>20</size></font>
        <font><name>big</name><filename>arial.ttf</filename><size>30</size><style>bold</style></font>
        <font><name>caps</name><filename>arial.ttf</filename><size>30</size><style>uppercase</style></font>
        <font><name>clock</name><filename>Roboto-Thin.ttf</filename><size>50</size></font>
        </fontset></fonts>''')
    fonts = skin.read_fonts(str(font_xml), 'Arial', 720)
    assert fonts == [('font13', 30.0, False, False), ('big', 45.0, True, False), ('caps', 45.0, False, True)]


def test_render_fills_template():
    template = ('<window><controls>@include:tile@<font>@font:rail@</font></controls>'
                '<include name="tile"><texture>@media@/white.png</texture></include></window>')
    xml = skin.render(template, {'rail': 'font30'}, 'C:\\addon\\media', '/icon.png')
    assert xml == '<window><controls><texture>C:/addon/media/white.png</texture><font>font30</font></controls></window>'


def test_video_tile_badges_and_meta():
    xbmcaddon.STRINGS.clear()
    item = video('a', watched=40)
    item.update(channel='Blender', views=1234567, published='2 weeks ago', duration=635)
    li = items.video_tile(item, None, 80)
    assert li.label2 == 'Blender • 1.2M views • 2 weeks ago'
    assert li.getProperty('badge') == '10:35'
    assert li.getProperty('progress') == '40'
    assert items.short_count(51000) == '51K' and items.short_count(999) == '999'


def test_watched_percent():
    assert model.watched_percent(0, 600) == 0
    assert model.watched_percent(30, 0) == 0
    assert model.watched_percent(150, 600) == 25
    assert model.watched_percent(2, 600) == 1  # just started still shows a sliver
    assert model.watched_percent(595, 600) == 100  # stopped in the closing seconds


def test_find_video_on_every_row():
    load = loader({None: page([shelf('A', 'abc'), shelf('B', 'cd')])})
    screen = model.Screen({'ep': 'browse'}, 'Home', load).open()
    assert [(r.title, i) for r, i in screen.find_video('c')] == [('A', 2), ('B', 0)]


def test_local_screen_rebuilds_on_refresh():
    searches = ['cats']
    screen = model.LocalScreen('Search', lambda: [model.Row('Recent', [{'kind': 'query', 'title': q}
                                                                       for q in searches])]).open()
    assert [i['title'] for i in screen.rows[0].items] == ['cats']
    searches.insert(0, 'dogs')
    screen.refresh()
    assert [i['title'] for i in screen.rows[0].items] == ['dogs', 'cats']
    assert not screen.can_grow()


def test_short_clip_is_not_done_at_once():
    assert model.watched_percent(1, 8) == 12
    assert model.watched_percent(7.7, 8) == 100  # within 5% of the end


def test_ensure_gives_up_on_pages_that_stay_empty():
    pages_by_token = {None: page([shelf('', 'abcd', 'T0')])}
    for n in range(20):  # every later page is filtered out entirely
        pages_by_token['T%d' % n] = page([{'title': '', 'items': [video('s%d' % n, short=True)],
                                           'continuation': 'T%d' % (n + 1), 'shorts': False, 'endpoint': None}])
    load = loader(pages_by_token)
    screen = model.Screen({'ep': 'browse'}, 'Feed', load, keep=lambda i: not i['short']).open()
    screen.ensure(0)
    assert len(load.calls) == 1 + model.MAX_EMPTY_PAGES
    assert screen.can_grow()  # a later move may try again


def test_section_tabs_are_not_a_channel_row():
    tabs = [{'kind': 'folder', 'title': t, 'selected': t == 'Home',
             'target': {'type': 'browse', 'browse_id': 'UCx', 'params': t}, 'thumb': ''}
            for t in ('Home', 'Videos', 'Playlists')]
    load = loader({None: page([shelf('Uploads', 'ab'), shelf('Popular', 'cd')], tabs=tabs)})
    screen = model.Screen({'ep': 'browse', 'id': 'UCx'}, 'Channel', load, tabs_title='Channels').open()
    assert screen.rows[0].title == '' and not screen.rows[0].avatars
    assert [t['title'] for t in screen.rows[0].items] == ['Videos', 'Playlists']


def test_resume_label_handles_both_kodi_wordings(monkeypatch):
    import xbmc

    from resources.lib.youtube.tv import window
    assert window.resume_label('1:05') == 'Resume from 1:05'  # Kodi 19+: "Resume from {0:s}"
    monkeypatch.setitem(xbmc.LOCALIZED, 12022, 'Resume from %s')
    assert window.resume_label('1:05') == 'Resume from 1:05'


def test_video_tile_fanart_is_the_channel_banner_when_known():
    item = video('a')
    assert items.video_tile(item, None, 80).art['fanart'] == item['thumb']
    assert items.video_tile(item, None, 80, 'https://banner').art['fanart'] == 'https://banner'
    assert items.tile(item, None, 80, fanart='https://banner').art['fanart'] == 'https://banner'


class FakeBanners:
    def __init__(self, found):
        self.found = found  # channel id -> banner, '' when the channel has none
        self.known = {}

    def fetch_all(self, channel_ids):
        self.known.update((c, self.found[c]) for c in channel_ids if c in self.found)

    def unknown(self, channel_ids):
        return [c for c in channel_ids if c not in self.known]

    def get(self, channel_id):
        return self.known.get(channel_id, '')


def test_window_sets_banners_and_retries_channels_not_looked_up():
    from resources.lib.youtube.tv import window

    win = window.TVWindow()
    win.banners = FakeBanners({'UCa': 'https://banner-a', 'UCb': ''})
    tiles = {v: items.video_tile(video(v), None, 80) for v in ('1', '2', '3')}
    win._bannered.update(tiles)
    win._show_banners([('1', 'UCa', tiles['1']), ('2', 'UCb', tiles['2']), ('3', 'UCc', tiles['3'])])
    assert tiles['1'].art['fanart'] == 'https://banner-a'
    assert tiles['2'].art['fanart'] == video('2')['thumb']  # the channel has no banner
    assert win._bannered == {'1', '2'}  # UCc's lookup failed: tried again next time it is shown


def channel(channel_id):
    return parser._item_base('channel', 'Channel', 'https://yt3/avatar', {'type': 'browse', 'browse_id': channel_id})


def test_channel_tile_fanart_is_its_banner_when_known():
    assert items.tile(channel('UCa'), None, 80, True).art['fanart'] == 'https://yt3/avatar'
    assert items.tile(channel('UCa'), None, 80, True, 'https://banner').art['fanart'] == 'https://banner'


def test_window_puts_channel_banners_behind_channel_tiles():
    from resources.lib.youtube.tv import window

    win = window.TVWindow()
    assert win._banner_channel(channel('UCa'), None) == 'UCa'
    assert win._banner_channel(dict(video('1'), channel_id='UCb'), None) == 'UCb'
    assert win._banner_channel(channel('FEtopics'), None) == ''
    tab = dict(channel('FEsubscriptions'), kind='tab', channel_id='UCc')
    assert win._banner_channel(tab, None) == 'UCc'  # a Subscriptions tab
    win.banners = FakeBanners({'UCa': 'https://banner-a'})
    tile = items.tile(channel('UCa'), None, 80, True)
    win._bannered.add('UCa')
    win._show_banners([('UCa', 'UCa', tile)])
    assert tile.art['fanart'] == 'https://banner-a'


def test_window_looks_up_banners_of_shown_videos_with_a_known_channel(monkeypatch):
    from resources.lib.youtube.tv import window

    win = window.TVWindow()
    shown = [('1', 'UCa', 'tile1'), ('2', '', 'tile2')]
    monkeypatch.setattr(win, '_shown_tiles', lambda: iter(shown))
    started = []
    monkeypatch.setattr(window.threading, 'Thread',
                        lambda target, args, name: type('T', (), {'start': lambda s: started.append(args)})())
    win._banners_soon()
    win._banners_soon()  # already on its way: not asked for again
    assert started == [([('1', 'UCa', 'tile1')],)]


def test_window_draws_playback_under_its_background():
    import os
    import xml.etree.ElementTree as ET

    path = os.path.join(os.path.dirname(skin.__file__), '..', '..', '..', 'tv', 'youtube-tv.xml')
    with open(path) as f:
        xml = skin.render(f.read(), {}, '/media', '/icon.png')
    first, second = ET.fromstring(xml).find('controls')[:2]
    # Kodi only presents video through a videowindow outside fullscreen: without one, playback stalls
    assert first.get('type') == 'videowindow' and first.findtext('visible') == 'Player.HasVideo'
    assert second.get('type') == 'image'
