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


from resources.lib.leanback import art as _art  # noqa: E402

_REAL_FETCH_MISSING = _art.Banners.fetch_missing  # conftest stubs it out for every test


def test_banner_channel_pages_go_to_the_apps_host(monkeypatch):
    from resources.lib.leanback import art, innertube
    monkeypatch.setattr(art.Banners, 'fetch_missing', _REAL_FETCH_MISSING)
    sent = []
    monkeypatch.setattr(innertube.http, 'request_json', lambda url, **kw: sent.append(url) or {})
    monkeypatch.setattr(innertube.InnerTube, 'visitor_data', lambda self, refresh=False: 'V')
    banners = art.Banners()
    banners.missing = ['UCSMOQeBJ2RAnuFungnQOxLg']
    banners.fetch_missing()
    assert sent == ['https://youtubei.googleapis.com/youtubei/v1/browse?prettyPrint=false']
