import xbmcplugin

from resources.lib.leanback import descriptions, parser, router


def video(video_id, **extra):
    item = parser._item_base('video', 'Title ' + video_id, 'https://i.ytimg.com/%s.jpg' % video_id,
                             {'type': 'video', 'video_id': video_id})
    item.update(id=video_id, channel_id='UCcccccccccccccccccccccc', channel='Chan', views=1234567,
                published='2 days ago', duration=754, **extra)
    return item


def test_played_videos_keep_their_description():
    store = descriptions.Descriptions()
    store.remember('aaaaaaaaaaa', 'Full text', '2026-11-18')
    store.remember('bbbbbbbbbbb', '')
    again = descriptions.Descriptions()
    assert again.get('aaaaaaaaaaa')['d'] == 'Full text' and again.get('aaaaaaaaaaa')['p'] == '2026-11-18'
    assert again.get('bbbbbbbbbbb') is None


def test_video_plot_lists_info_then_description():
    descriptions.Descriptions().remember('aaaaaaaaaaa', 'The description.', '2026-11-18')
    plugin = router.Plugin(['plugin://plugin.video.leanback/browse', '1', ''])
    plugin._render_items([video('aaaaaaaaaaa', badges=['4K'], watched_pct=40),
                          video('bbbbbbbbbbb', live=True, plot_lines=['Chan • 1.2M watching', 'Extra line'])])
    plots = [li.tag.values['plot'] for _, li, _ in xbmcplugin.ITEMS]
    assert plots[0] == 'Chan • 1,234,567 views • 2 days ago • 12:34\n4K • Watched 40%\n\nThe description.'
    # No description yet: the tile's own lines, minus what the info line already says.
    assert plots[1] == 'Chan • 1,234,567 watching • 2 days ago • 12:34\nstr30127\nExtra line'
