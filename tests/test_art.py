import xbmcplugin

from resources.lib.leanback import art, parser, router


def test_banners_remember_and_report_missing(monkeypatch):
    banners = art.Banners()
    assert banners.get('UCaaaaaaaaaaaaaaaaaaaaaa') == ''
    assert banners.get('not-a-channel') == ''
    assert banners.missing == ['UCaaaaaaaaaaaaaaaaaaaaaa']
    banners.remember('UCaaaaaaaaaaaaaaaaaaaaaa', 'https://yt3/banner')
    assert banners.missing == []
    assert art.Banners().get('UCaaaaaaaaaaaaaaaaaaaaaa') == 'https://yt3/banner'  # stored
    banners.remember('UCbbbbbbbbbbbbbbbbbbbbbb', '')  # no banner: remembered, not fetched again
    fresh = art.Banners()
    assert fresh.get('UCbbbbbbbbbbbbbbbbbbbbbb') == '' and fresh.missing == []

    monkeypatch.setattr(art.time, 'time', lambda: 10 ** 10)  # a week later
    old = art.Banners()
    assert old.get('UCaaaaaaaaaaaaaaaaaaaaaa') == '' and old.missing == ['UCaaaaaaaaaaaaaaaaaaaaaa']


def test_video_tiles_take_their_channel_from_the_menu():
    node = {'lockupViewModel': {
        'contentType': 'LOCKUP_CONTENT_TYPE_VIDEO', 'contentId': 'abcdefghijk',
        'rendererContext': {'commandContext': {'onTap': {'innertubeCommand': {
            'watchEndpoint': {'videoId': 'abcdefghijk'}}}}},
        'metadata': {'lockupMetadataViewModel': {'title': {'content': 'A video'}}},
        'menu': {'menuRenderer': {'items': [{'menuNavigationItemRenderer': {
            'text': {'simpleText': 'Go to channel'},
            'navigationEndpoint': {'browseEndpoint': {'browseId': 'UCcccccccccccccccccccccc'}}}}]}},
    }}
    assert parser.parse_item(node)['channel_id'] == 'UCcccccccccccccccccccccc'


def test_videos_use_their_channel_banner_as_fanart(monkeypatch):
    art.Banners().remember('UCcccccccccccccccccccccc', 'https://yt3/banner')
    item = parser._item_base('video', 'A', 'https://i.ytimg.com/a.jpg', {'type': 'video', 'video_id': 'aaaaaaaaaaa'})
    item.update(id='aaaaaaaaaaa', channel_id='UCcccccccccccccccccccccc', duration=10)
    other = dict(item, id='bbbbbbbbbbb', target={'type': 'video', 'video_id': 'bbbbbbbbbbb'},
                 channel_id='UCdddddddddddddddddddddd')
    plugin = router.Plugin(['plugin://plugin.video.leanback/browse', '1', ''])
    plugin._render_items([item, other])
    fanart = [li.art['fanart'] for _, li, _ in xbmcplugin.ITEMS]
    assert fanart == ['https://yt3/banner', 'https://i.ytimg.com/a.jpg']  # no banner yet: the thumbnail
    assert plugin.banners.missing == ['UCdddddddddddddddddddddd']



from resources.lib.leanback import innertube  # noqa: E402

REAL_FETCH_ALL = art.Banners.fetch_all  # conftest stubs it out for every test


def test_banners_are_looked_up_before_drawing(monkeypatch):
    """Unknown channels get their banner on the very first view, looked up in parallel."""
    looked_up = []

    def fetch_all(self, channel_ids, fetch=None):
        looked_up.append(list(channel_ids))
        return REAL_FETCH_ALL(self, channel_ids, lambda c: 'https://yt3/%s' % c[-4:])

    monkeypatch.setattr(art.Banners, 'fetch_all', fetch_all)
    art.Banners().remember('UCcccccccccccccccccccccc', 'https://yt3/known')
    item = parser._item_base('video', 'A', 'https://i.ytimg.com/a.jpg', {'type': 'video', 'video_id': 'aaaaaaaaaaa'})
    item.update(id='aaaaaaaaaaa', channel_id='UCcccccccccccccccccccccc', duration=10)
    other = dict(item, id='bbbbbbbbbbb', target={'type': 'video', 'video_id': 'bbbbbbbbbbb'},
                 channel_id='UCdddddddddddddddddddddd')
    router.Plugin(['plugin://plugin.video.leanback/browse', '1', ''])._render_items([item, other])
    assert [li.art['fanart'] for _, li, _ in xbmcplugin.ITEMS] == ['https://yt3/known', 'https://yt3/dddd']
    assert art.Banners().get('UCdddddddddddddddddddddd') == 'https://yt3/dddd'  # remembered for next time


def test_fetch_all_skips_known_channels_and_remembers_ones_without_a_banner():
    art.Banners().remember('UCaaaaaaaaaaaaaaaaaaaaaa', 'https://yt3/a')
    asked = []
    banners = art.Banners()
    found = REAL_FETCH_ALL(banners, ['UCaaaaaaaaaaaaaaaaaaaaaa', 'UCbbbbbbbbbbbbbbbbbbbbbb', 'not-a-channel'],
                           lambda c: asked.append(c) or '')
    assert asked == ['UCbbbbbbbbbbbbbbbbbbbbbb'] and found == 0
    assert art.Banners().unknown(['UCbbbbbbbbbbbbbbbbbbbbbb']) == []  # no banner, but not looked up again


def test_banner_lookup_reads_the_small_about_page(monkeypatch):
    sent = []
    monkeypatch.setattr(innertube.http, 'request_json', lambda url, data=None, **kw: sent.append((url, data)) or {})
    monkeypatch.setattr(innertube.InnerTube, 'visitor_data', lambda self, refresh=False: 'V')
    REAL_FETCH_ALL(art.Banners(), ['UCSMOQeBJ2RAnuFungnQOxLg'])
    [(url, data)] = sent
    assert url == 'https://youtubei.googleapis.com/youtubei/v1/browse?prettyPrint=false'
    body = __import__('json').loads(data)
    assert body['params'] == innertube.ABOUT_PARAMS and body['context']['client']['clientName'] == 'VISIONOS'


def test_channel_banner_prefers_the_tv_banner():
    def thumbs(width, height):
        return {'thumbnails': [{'url': 'https://yt3/%dx%d' % (width, height), 'width': width, 'height': height}]}

    resp = {'header': {'c4TabbedHeaderRenderer': {'banner': thumbs(2560, 424), 'tvBanner': thumbs(2120, 1192)}}}
    assert parser.channel_banner(resp) == 'https://yt3/2120x1192'
    del resp['header']['c4TabbedHeaderRenderer']['tvBanner']
    assert parser.channel_banner(resp) == 'https://yt3/2560x424'


def test_tiles_without_a_channel_take_it_from_the_watch_page(monkeypatch):
    """Home's row tiles don't name their channel; the watch page read for the description does."""
    import xbmcaddon

    from resources.lib.leanback import describe, descriptions
    xbmcaddon.SETTINGS['fetch_descriptions'] = True

    def fetch_all(video_ids, store, fetch=None):
        store.remember_all({'video_id': v, 'plot': 'About', 'channel_id': 'UCeeeeeeeeeeeeeeeeeeeeee'}
                           for v in video_ids)
        return len(video_ids)

    monkeypatch.setattr(describe, 'fetch_all', fetch_all)
    monkeypatch.setattr(art.Banners, 'fetch_all',
                        lambda self, ids, fetch=None: REAL_FETCH_ALL(self, ids, lambda c: 'https://yt3/' + c[-4:]))
    item = parser._item_base('video', 'A', 'https://i.ytimg.com/a.jpg', {'type': 'video', 'video_id': 'aaaaaaaaaaa'})
    item.update(id='aaaaaaaaaaa', channel_id='', duration=10)
    router.Plugin(['plugin://plugin.video.leanback/browse', '1', ''])._render_items([item])
    assert [li.art['fanart'] for _, li, _ in xbmcplugin.ITEMS] == ['https://yt3/eeee']
    assert descriptions.Descriptions().get('aaaaaaaaaaa')['c'] == 'UCeeeeeeeeeeeeeeeeeeeeee'


def test_watch_page_names_the_channel():
    meta = {'owner': {'videoOwnerRenderer': {
        'title': {'runs': [{'text': 'Blender'}]},
        'navigationEndpoint': {'browseEndpoint': {'browseId': 'UCSMOQeBJ2RAnuFungnQOxLg'}}}}}
    nxt = {'contents': [{'videoMetadataRenderer': meta}]}
    assert parser.video_details({}, nxt)['channel_id'] == 'UCSMOQeBJ2RAnuFungnQOxLg'


def test_banners_remembered_small_are_given_at_full_width():
    small = 'https://yt3.googleusercontent.com/x=w2120-fcrop64=1,00000000ffffffff-k-c0xffffffff-no-nd-rj'
    art.Banners().remember('UCcccccccccccccccccccccc', small)
    assert art.Banners().get('UCcccccccccccccccccccccc') == small.replace('=w2120-', '=w2560-')
