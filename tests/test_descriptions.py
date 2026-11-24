import xbmcplugin

from resources.lib.youtube import descriptions, parser, router


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


def test_video_plot_lists_info_then_description(english):
    english(30141)
    descriptions.Descriptions().remember('aaaaaaaaaaa', 'The description.', '2026-11-18')
    plugin = router.Plugin(['plugin://plugin.video.youtube/browse', '1', ''])
    plugin._render_items([video('aaaaaaaaaaa', badges=['4K'], watched_pct=40),
                          video('bbbbbbbbbbb', live=True, plot_lines=['Chan • 1.2M watching', 'Extra line'])])
    plots = [li.tag.values['plot'] for _, li, _ in xbmcplugin.ITEMS]
    assert plots[0] == 'Chan • 2 days ago • 1,234,567 views\n4K • Watched 40%\n\nThe description.'
    # No description yet: the tile's own lines, minus what the info line already says.
    assert plots[1] == 'Chan • 2 days ago • 1,234,567 watching\nstr30127\nExtra line'


def test_video_plot_leads_like_full_details():
    """Channel • subscribers • age • views • likes, as Full details shows it."""
    descriptions.Descriptions().remember_details({
        'video_id': 'aaaaaaaaaaa', 'plot': 'Watch page text.', 'date': '2023-05-01',
        'subscribers': '1.2M subscribers', 'likes': '456789', 'published': '3 years ago'})
    plugin = router.Plugin(['plugin://plugin.video.youtube/browse', '1', ''])
    item = video('aaaaaaaaaaa')
    item['published'] = ''  # the tile gave no age: the watch page's is used
    plugin._render_items([item])
    [(_, li, _)] = xbmcplugin.ITEMS
    assert li.tag.values['plot'] == ('Chan • 1.2M subscribers • 3 years ago • 1,234,567 views • 456,789 likes'
                                     '\n\nWatch page text.')


def test_format_count():
    assert router.format_count('456789') == '456,789'
    assert router.format_count(1200) == '1,200'
    assert router.format_count('456K') == '456K'
