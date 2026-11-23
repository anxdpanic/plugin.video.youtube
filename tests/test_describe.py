import threading

import xbmcaddon
import xbmcplugin

from resources.lib.youtube import describe, descriptions, innertube, parser, router
from resources.lib.youtube.innertube import InnerTubeError


def details(video_id):
    return {'video_id': video_id, 'plot': 'About ' + video_id, 'date': '2023-05-01',
            'subscribers': '1M subscribers', 'likes': '1200', 'published': '2 years ago'}


def ids(count):
    return ['%011d' % n for n in range(count)]


def video(video_id, **extra):
    item = parser._item_base('video', 'Title ' + video_id, '', {'type': 'video', 'video_id': video_id})
    item.update(id=video_id, channel='Chan', views=10, published='1 day ago', duration=60, **extra)
    return item


def test_fetch_all_runs_in_parallel_and_saves_once(monkeypatch):
    gate = threading.Barrier(4, timeout=5)  # the first four only finish once all four run together
    saves = []

    def fetch(video_id):
        if int(video_id) < 4:
            gate.wait()
        return details(video_id)

    store = descriptions.Descriptions()
    real_save = store._save
    monkeypatch.setattr(store, '_save', lambda: saves.append(1) or real_save())
    assert describe.fetch_all(ids(20) + ids(2), store, fetch) == 20  # duplicates fetched once
    assert saves == [1]
    entry = descriptions.Descriptions().get('00000000003')
    assert entry['d'] == 'About 00000000003' and entry['s'] == '1M subscribers' and entry['w'] == 1


def test_failures_are_skipped_and_a_block_stops_the_rest(monkeypatch):
    calls = []

    def fetch(video_id):
        calls.append(video_id)
        if video_id == '00000000001':
            raise InnerTubeError('nope', 400)
        if video_id == '00000000002':
            raise InnerTubeError('held', 403, blocked=True)
        return details(video_id)

    monkeypatch.setattr(describe, 'WORKERS', 1)  # in order, so the block comes before the rest
    store = descriptions.Descriptions()
    assert describe.fetch_all(ids(6), store, fetch) == 1
    assert calls == ids(3)
    assert store.get('00000000001') is None


def test_listing_fetches_missing_descriptions_before_drawing(monkeypatch):
    xbmcaddon.SETTINGS['fetch_descriptions'] = True
    asked = []

    def fetch_all(video_ids, store, fetch=None):
        asked.append(list(video_ids))
        store.remember_all(details(v) for v in video_ids)
        return len(video_ids)

    monkeypatch.setattr(describe, 'fetch_all', fetch_all)
    descriptions.Descriptions().remember_details(details('00000000000'))
    items = [video(v) for v in ids(3)] + [video('upcomingxxx', upcoming='Premieres soon')]
    router.Plugin(['plugin://plugin.video.youtube/browse', '1', ''])._render_items(items)
    assert asked == [['00000000001', '00000000002']]  # known and upcoming videos are skipped
    plots = [li.tag.values['plot'] for _, li, _ in xbmcplugin.ITEMS]
    assert plots[2].endswith('About 00000000002')
    # The outline carries the same text: some views show it instead of the plot.
    assert [li.tag.values['plotoutline'] for _, li, _ in xbmcplugin.ITEMS] == plots


def test_listing_skips_fetching_when_turned_off(monkeypatch):
    xbmcaddon.SETTINGS['fetch_descriptions'] = False

    def fail(*args, **kwargs):
        raise AssertionError('fetched while turned off')

    monkeypatch.setattr(describe, 'fetch_all', fail)
    router.Plugin(['plugin://plugin.video.youtube/browse', '1', ''])._render_items([video('00000000001')])


def test_video_listings_use_videos_content():
    plugin = router.Plugin(['plugin://plugin.video.youtube/browse', '1', ''])
    plugin._finish_listing([{'kind': 'video'}, {'kind': 'video'}, {'kind': 'folder'}])
    assert xbmcplugin.CONTENT[-1] == 'videos'
    plugin._finish_listing([{'kind': 'folder'}, {'kind': 'folder'}, {'kind': 'video'}])
    assert xbmcplugin.CONTENT[-1] == 'files'


def test_watch_page_goes_to_the_apps_host(monkeypatch):
    sent = []
    monkeypatch.setattr(innertube.http, 'request_json', lambda url, **kw: sent.append(url) or {})
    api = innertube.InnerTube()
    monkeypatch.setattr(api, 'visitor_data', lambda refresh=False: 'V')
    api.watch_page('aqz-KE-bpKQ')
    assert sent == ['https://youtubei.googleapis.com/youtubei/v1/next?prettyPrint=false']


def test_videos_without_a_description_are_not_read_again():
    """Shorts often have no description; remembering that stops every visit reading them again."""
    store = descriptions.Descriptions()
    assert describe.fetch_all(['shortsxxxxx'], store, lambda v: dict(details(v), plot='')) == 1
    entry = descriptions.Descriptions().get('shortsxxxxx')
    assert entry['w'] == 1 and entry['d'] == '' and entry['s'] == '1M subscribers'
