from resources.lib.youtube import parser


def tile(video_id='abcdefghijk', title='A video', overlays=None, lines=None, **extra):
    """A TVHTML5 tileRenderer shaped like the TV client sends it."""
    renderer = {
        'contentId': video_id,
        'contentType': 'TILE_CONTENT_TYPE_VIDEO',
        'header': {'tileHeaderRenderer': {
            'thumbnail': {'thumbnails': [{'url': 'https://i.ytimg.com/vi/%s/hq720.jpg' % video_id,
                                          'width': 640, 'height': 360}]},
            'thumbnailOverlays': overlays or [],
        }},
        'onSelectCommand': {'watchEndpoint': {'videoId': video_id}},
    }
    if lines is not None:
        renderer['metadata'] = {'tileMetadataRenderer': {'title': {'simpleText': title}, 'lines': lines}}
    renderer.update(extra)
    return {'tileRenderer': renderer}


def line(*texts):
    return {'lineRenderer': {'items': [{'lineItemRenderer': {'text': t if isinstance(t, dict) else {'simpleText': t}}}
                                       for t in texts]}}


def test_text_handles_all_shapes():
    assert parser.text({'simpleText': 'a'}) == 'a'
    assert parser.text({'runs': [{'text': 'a'}, {'text': 'b'}]}) == 'ab'
    assert parser.text({'content': 'c'}) == 'c'
    assert parser.text(None) == ''


def test_parse_duration_and_count():
    assert parser.parse_duration('1:02:03') == 3723
    assert parser.parse_duration('5:55') == 355
    assert parser.parse_duration('LIVE') == 0
    assert parser.parse_count('1.2M views') == 1200000
    assert parser.parse_count('51K views') == 51000
    assert parser.parse_count('1,234 views') == 1234
    assert parser.parse_count('') == 0


def test_endpoint_target_unquotes_params():
    target = parser.endpoint_target({'browseEndpoint': {'browseId': 'UCx', 'params': 'EgZ2aWRlb3M%3D'}})
    assert target == {'type': 'browse', 'browse_id': 'UCx', 'params': 'EgZ2aWRlb3M='}
    short = parser.endpoint_target({'reelWatchEndpoint': {'videoId': 'v1', 'params': 'CA8%3D'}})
    assert short['short'] and short['params'] == 'CA8='
    assert parser.endpoint_target({'innertubeCommand': {'watchEndpoint': {'videoId': 'v2'}}})['video_id'] == 'v2'


def test_parse_tile_metadata():
    channel = {'runs': [{'text': 'Blender', 'navigationEndpoint': {'browseEndpoint': {'browseId': 'UCblender'}}}]}
    item = parser.parse_item(tile(
        lines=[line(channel), line('23M views', '•', '12 years ago')],
        overlays=[{'thumbnailOverlayResumePlaybackRenderer': {'percentDurationWatched': 40}},
                  {'thumbnailOverlayTimeStatusRenderer': {'text': {'simpleText': '10:35'}, 'style': 'DEFAULT'}}]))
    assert item['kind'] == 'video'
    assert item['title'] == 'A video'
    assert item['channel'] == 'Blender' and item['channel_id'] == 'UCblender'
    assert item['views'] == 23000000
    assert item['published'] == '12 years ago'
    assert item['duration'] == 635
    assert item['watched_pct'] == 40


def test_parse_tile_live_and_shorts():
    live = parser.parse_item(tile(lines=[line('Channel')], overlays=[
        {'thumbnailOverlayTimeStatusRenderer': {'text': {'simpleText': 'LIVE'}, 'style': 'LIVE'}}]))
    assert live['live'] and live['duration'] == 0
    short = parser.parse_item(tile(lines=[line('Channel')], tvhtml5ShelfRendererType=parser.TILE_SHORTS))
    assert short['short']


def test_parse_carousel_tile_uses_long_press_menu():
    item = parser.parse_item(tile(onLongPressCommand={'showMenuCommand': {
        'title': {'simpleText': 'Carousel title'}, 'subtitle': {'simpleText': 'Some Artist • @artist'}}}))
    assert item['title'] == 'Carousel title'
    assert item['channel'] == 'Some Artist'


def test_parse_lockup():
    lockup = {'lockupViewModel': {
        'contentId': 'dOA4XhsUj54',
        'contentType': 'LOCKUP_CONTENT_TYPE_VIDEO',
        'contentImage': {'thumbnailViewModel': {
            'image': {'sources': [{'url': 'https://i.ytimg.com/x.jpg', 'width': 640, 'height': 360}]},
            'overlays': [{'thumbnailBottomOverlayViewModel': {'badges': [{'thumbnailBadgeViewModel': {
                'text': '14:09', 'badgeStyle': 'THUMBNAIL_OVERLAY_BADGE_STYLE_DEFAULT'}}]}}],
        }},
        'metadata': {'lockupMetadataViewModel': {
            'title': {'content': 'Setup guide'},
            'metadata': {'contentMetadataViewModel': {'metadataRows': [
                {'metadataParts': [{'text': {'content': "DJ's Tutorials"}}]},
                {'metadataParts': [{'text': {'content': '64K views'}}, {'text': {'content': '2 weeks ago'}}]},
            ]}},
        }},
        'rendererContext': {'commandContext': {'onTap': {'innertubeCommand': {
            'watchEndpoint': {'videoId': 'dOA4XhsUj54'}}}}},
    }}
    item = parser.parse_item(lockup)
    assert item['kind'] == 'video'
    assert item['title'] == 'Setup guide'
    assert item['duration'] == 849
    assert item['channel'] == "DJ's Tutorials"
    assert item['views'] == 64000
    assert item['published'] == '2 weeks ago'


def browse_response(content=None, header=None):
    surface = {'content': content or {}}
    if header:
        surface['header'] = header
    return {'contents': {'tvBrowseRenderer': {'content': {'tvSurfaceContentRenderer': surface}}}}


def test_parse_page_shelves_header_and_continuations():
    shelf = {'shelfRenderer': {
        'headerRenderer': {'shelfHeaderRenderer': {'avatarLockup': {'avatarLockupRenderer': {
            'title': {'runs': [{'text': 'Videos'}]}}}}},
        'endpoint': {'browseEndpoint': {'browseId': 'FEhistory'}},
        'content': {'horizontalListRenderer': {
            'items': [tile('aaaaaaaaaaa', lines=[line('c')]), tile('bbbbbbbbbbb', lines=[line('c')])],
            'continuations': [{'nextContinuationData': {'continuation': 'SHELF_TOKEN'}}]}},
    }}
    header = {'channelHeaderRenderer': {
        'title': {'simpleText': 'Blender'},
        'avatar': {'thumbnails': [{'url': '//yt3.example/a.jpg', 'width': 72, 'height': 72}]},
        'subtitle': {'lineRenderer': {'items': [
            {'lineItemRenderer': {'text': {'simpleText': '@BlenderOfficial'}}},
            {'lineItemRenderer': {'text': {'simpleText': '•'}}},
            {'lineItemRenderer': {'text': {'simpleText': '1.26M subscribers'}}}]}},
    }}
    resp = browse_response({'sectionListRenderer': {
        'contents': [shelf], 'continuations': [{'nextContinuationData': {'continuation': 'PAGE_TOKEN'}}]}}, header)
    page = parser.parse_page(resp)
    assert page['header']['title'] == 'Blender'
    assert page['header']['thumb'] == 'https://yt3.example/a.jpg'
    assert page['header']['subscribers'] == '1.26M subscribers'
    assert page['continuation'] == 'PAGE_TOKEN'
    [parsed] = page['shelves']
    assert parsed['title'] == 'Videos'
    assert [i['id'] for i in parsed['items']] == ['aaaaaaaaaaa', 'bbbbbbbbbbb']
    assert parsed['continuation'] == 'SHELF_TOKEN'
    assert parsed['endpoint']['browse_id'] == 'FEhistory'


def test_parse_page_secondary_nav_tabs():
    def tab(title, selected=False):
        return {'tabRenderer': {'title': title, 'selected': selected,
                                'endpoint': {'browseEndpoint': {'browseId': 'FEsubscriptions', 'params': title}},
                                'content': {'tvSurfaceContentRenderer': {'content': {'gridRenderer': {
                                    'items': [tile(lines=[line('c')])]}}}} if selected else {}}}
    resp = {'contents': {'tvBrowseRenderer': {'content': {'tvSecondaryNavRenderer': {'sections': [
        {'tvSecondaryNavSectionRenderer': {'tabs': [tab('All', True), tab('Grian'), tab('LTT')]}}]}}}}}
    page = parser.parse_page(resp)
    assert [t['title'] for t in page['tabs']] == ['All', 'Grian', 'LTT']
    assert page['tabs'][0]['selected']
    assert len(page['shelves']) == 1 and len(page['shelves'][0]['items']) == 1


def test_parse_continuation_response():
    resp = {'continuationContents': {'horizontalListContinuation': {
        'items': [tile(lines=[line('c')])],
        'continuations': [{'nextContinuationData': {'continuation': 'MORE'}}]}}}
    page = parser.parse_page(resp)
    assert page['shelves'][0]['continuation'] == 'MORE'


def test_parse_guide():
    def entry(title, endpoint, thumb=None):
        guide = {'formattedTitle': {'simpleText': title}, 'navigationEndpoint': endpoint}
        if thumb:
            guide['thumbnail'] = {'thumbnails': [{'url': thumb, 'width': 88, 'height': 88}]}
        return {'guideEntryRenderer': guide}
    resp = {'items': [{'guideSectionRenderer': {'items': [
        entry('Search', {'searchEndpoint': {'query': ''}}),
        entry('Home', {'browseEndpoint': {'browseId': 'FEtopics'}}),
        entry('Shorts', {'reelWatchEndpoint': {'params': 'CA8%3D'}}),
        entry('Grian', {'browseEndpoint': {'browseId': 'UCgrian'}}, thumb='https://yt3.example/g.jpg'),
    ]}}]}
    entries = parser.parse_guide(resp)
    assert [e['id'] for e in entries] == ['search', 'FEtopics', 'shorts', 'UCgrian']
    assert [e['channel'] for e in entries] == [False, False, False, True]


def test_video_details_merges_player_and_next():
    player = {'videoDetails': {'videoId': 'v', 'title': 'T', 'shortDescription': 'short', 'author': 'A',
                               'lengthSeconds': '60', 'viewCount': '10', 'keywords': ['k']}}
    nxt = {'contents': {'singleColumnWatchNextResults': {'results': {'results': {'contents': [
        {'itemSectionRenderer': {'contents': [{'videoMetadataRenderer': {
            'title': {'runs': [{'text': 'T'}]}, 'dateText': {'simpleText': '12y ago'},
            'owner': {'videoOwnerRenderer': {'title': {'simpleText': 'A'},
                                             'subscriberCountText': {'simpleText': '1M subscribers'}}},
            'description': {'runs': [{'text': 'a much longer description'}]},
        }}]}}]}}}}}
    info = parser.video_details(player, nxt)
    assert info['duration'] == 60 and info['views'] == 10 and info['tags'] == ['k']
    assert info['published'] == '12y ago'
    assert info['subscribers'] == '1M subscribers'
    assert info['plot'] == 'a much longer description'


def test_upcoming_lockup_shows_status_and_schedule():
    lockup = {'lockupViewModel': {
        'contentId': '7pWu0ScRFdw', 'contentType': 'LOCKUP_CONTENT_TYPE_VIDEO',
        'contentImage': {'thumbnailViewModel': {'image': {'sources': []}, 'overlays': [
            {'thumbnailBottomOverlayViewModel': {'badges': [{'thumbnailBadgeViewModel': {
                'text': 'Upcoming', 'badgeStyle': 'THUMBNAIL_OVERLAY_BADGE_STYLE_DEFAULT'}}]}}]}},
        'metadata': {'lockupMetadataViewModel': {
            'title': {'content': 'Mission update'},
            'metadata': {'contentMetadataViewModel': {'metadataRows': [
                {'metadataParts': [{'text': {'content': 'FOX 10 Phoenix'}}]},
                {'metadataParts': [{'text': {'content': 'Scheduled for 11/19/26, 9:00 AM'}}]},
            ]}},
        }},
        'rendererContext': {'commandContext': {'onTap': {'innertubeCommand': {
            'watchEndpoint': {'videoId': '7pWu0ScRFdw'}}}}},
    }}
    item = parser.parse_item(lockup)
    assert item['upcoming'] == 'Upcoming' and not item['live'] and item['duration'] == 0
    assert item['channel'] == 'FOX 10 Phoenix'
    assert item['published'] == 'Scheduled for 11/19/26, 9:00 AM'


def test_upcoming_tile():
    item = parser.parse_item(tile(lines=[line('Channel'), line('Premieres 11/20/26')], overlays=[
        {'thumbnailOverlayTimeStatusRenderer': {'text': {'simpleText': 'PREMIERE'}, 'style': 'UPCOMING'}}]))
    assert item['upcoming'] == 'PREMIERE'
    assert item['published'] == 'Premieres 11/20/26'


def test_chapters_from_macro_markers():
    marker = {'title': {'simpleText': 'Intro'}, 'startMillis': '5000',
              'thumbnailDetails': {'thumbnails': [{'url': 'https://i.ytimg.com/c.jpg', 'width': 320}]}}
    resp = {'frameworkUpdates': {'entityBatchUpdate': {'mutations': [
        {'payload': {'macroMarkersListEntity': {'markersList': {'markerType': 'MARKER_TYPE_HEATMAP'}}}},
        {'payload': {'macroMarkersListEntity': {'markersList': {'markerType': 'MARKER_TYPE_CHAPTERS',
                                                                'markers': [marker]}}}},
    ]}}}
    assert parser.chapters(resp) == [{'title': 'Intro', 'start': 5.0, 'thumb': 'https://i.ytimg.com/c.jpg'}]
    assert parser.chapters({}) == []
    assert parser.chapters(None) == []


def test_search_cluster_rows_become_shelves():
    button = {'buttonViewModel': {'title': 'Recently uploaded', 'onTap': {'innertubeCommand': {
        'searchEndpoint': {'query': 'cats videos', 'params': 'eAE%3D'}}}}}
    resp = {'contents': {'sectionListRenderer': {'contents': [{'clusterShelfRenderer': {'clusters': [
        {'clusterRenderer': {'headerRenderer': button, 'items': [tile('aaaaaaaaaaa', lines=[line('x')])]}},
        {'clusterRenderer': {'headerRenderer': button, 'items': []}},
    ]}}]}}}
    shelves = parser.parse_page(resp)['shelves']
    assert [(s['title'], len(s['items'])) for s in shelves] == [('Recently uploaded', 1)]
    assert shelves[0]['endpoint'] == {'type': 'search', 'query': 'cats videos', 'params': 'eAE='}


def test_show_tile_opens_its_playlist_not_one_episode():
    """Home's Recommended shows: a video tile of the latest episode whose select opens the show."""
    status = {'thumbnailOverlayTimeStatusRenderer': {'text': {'runs': [{'text': '629'}, {'text': ' episodes'}]},
                                                     'style': 'DEFAULT'}}
    node = tile('mAGzebdONa0', title='This Is', overlays=[status], lines=[line('This Is')])
    node['tileRenderer']['onSelectCommand'] = {'browseEndpoint': {'browseId': 'VLPLshow', 'params': 'kgY'}}
    item = parser.parse_item(node)
    assert item['kind'] == 'playlist'
    assert item['target'] == {'type': 'browse', 'browse_id': 'VLPLshow', 'params': 'kgY'}
    assert item['duration'] == 0


def test_show_lockup_opens_its_playlist_not_one_episode():
    node = {'lockupViewModel': {
        'contentType': 'LOCKUP_CONTENT_TYPE_VIDEO', 'contentId': 'mAGzebdONa0',
        'metadata': {'lockupMetadataViewModel': {'title': {'content': 'This Is'}}},
        'rendererContext': {'commandContext': {'onTap': {'innertubeCommand': {
            'browseEndpoint': {'browseId': 'VLPLshow'}}}}}}}
    item = parser.parse_item(node)
    assert item['kind'] == 'playlist' and item['target']['browse_id'] == 'VLPLshow'


def test_shortcut_tile_title_comes_from_its_image_overlay():
    """Library's shortcut row (History, Watch later...) has no metadata block, only a title on the image."""
    node = {'tileRenderer': {
        'contentType': 'TILE_CONTENT_TYPE_CHANNEL',
        'header': {'tileHeaderRenderer': {
            'thumbnail': {'thumbnails': [{'url': 'https://lh3.googleusercontent.com/x', 'width': 640}]},
            'thumbnailOverlays': [{'tileMetadataRenderer': {'title': {'simpleText': 'Watch later'}}}]}},
        'onSelectCommand': {'browseEndpoint': {'browseId': 'FEmy_youtube', 'params': 'cAc%3D'}}}}
    item = parser.parse_item(node)
    assert item['title'] == 'Watch later'
    assert item['target'] == {'type': 'browse', 'browse_id': 'FEmy_youtube', 'params': 'cAc='}


def test_channels_in_two_sections_are_listed_once():
    def tab(channel):
        return {'tabRenderer': {'title': {'simpleText': channel}, 'endpoint': {'browseEndpoint': {
            'browseId': 'FEsubscriptions', 'params': 'p-' + channel}}}}
    resp = {'contents': {'tvBrowseRenderer': {'content': {'tvSecondaryNavRenderer': {'sections': [
        {'tvSecondaryNavSectionRenderer': {'tabs': [tab('All'), tab('Grian')]}},
        {'tvSecondaryNavSectionRenderer': {'tabs': [tab('Grian'), tab('Scott')]}},
    ]}}}}}
    assert [t['title'] for t in parser.parse_page(resp)['tabs']] == ['All', 'Grian', 'Scott']

    def entry(browse_id):
        return {'guideEntryRenderer': {'title': {'simpleText': browse_id}, 'thumbnail': {'thumbnails': [
            {'url': 'https://yt3.ggpht.com/x', 'width': 88}]}, 'navigationEndpoint': {
            'browseEndpoint': {'browseId': browse_id}}}}
    guide = {'items': [{'guideSectionRenderer': {'items': [entry('UCa'), entry('UCb')]}},
                       {'guideSubscriptionsSectionRenderer': {'items': [entry('UCb'), entry('UCc')]}}]}
    assert [e['id'] for e in parser.parse_guide(guide)] == ['UCa', 'UCb', 'UCc']


def test_video_details_from_the_visionos_watch_page():
    """visionOS nests the watch page in tabs and is the client whose watch page has the description."""
    meta = {
        'title': {'runs': [{'text': 'T'}]},
        'dateText': {'runs': [{'text': '12 years ago'}]},
        'owner': {'videoOwnerRenderer': {'title': {'runs': [{'text': 'Blender'}]},
                                         'subscriberCountText': {'runs': [{'text': '1.26M subscribers'}]}}},
        'description': {'runs': [
            {'text': 'More info: '},
            {'text': 'https://studio.blender.org/projects/b...',
             'navigationEndpoint': {'urlEndpoint': {'url': 'https://studio.blender.org/projects/big-buck-bunny/'}}},
            {'text': ' and '},
            {'text': 'example.com/x...', 'navigationEndpoint': {'urlEndpoint': {
                'url': 'https://www.youtube.com/redirect?event=video_description&q=https%3A%2F%2Fexample.com%2Fxyz'}}},
            {'text': ' or '},
            {'text': '#blender', 'navigationEndpoint': {'browseEndpoint': {'browseId': 'FEhashtag'}}},
        ]},
        'likeButton': {'likeButtonRenderer': {'likeCount': 110530}},
    }
    nxt = {'contents': {'singleColumnWatchNextResults': {'results': {'watchNextTabbedResultsRenderer': {
        'tabs': [{'tabRenderer': {'content': {'sectionListRenderer': {'contents': [
            {'itemSectionRenderer': {'contents': [{'videoMetadataRenderer': meta}]}}]}}}}]}}}}}
    info = parser.video_details({}, nxt)
    assert info['plot'] == ('More info: https://studio.blender.org/projects/big-buck-bunny/'
                            ' and https://example.com/xyz or #blender')
    assert info['likes'] == '110530'
    assert info['subscribers'] == '1.26M subscribers'
    assert info['published'] == '12 years ago'


def test_channel_pictures_are_asked_for_larger():
    avatar = 'https://yt3.ggpht.com/abc-DEF_1=s176-c-k-c0x00ffffff-no-rj-mo'
    assert parser.best_thumb([{'url': avatar, 'width': 176, 'height': 176}]) == \
        'https://yt3.ggpht.com/abc-DEF_1=s800-c-k-c0x00ffffff-no-rj-mo'
    assert parser.square_art_at('https://yt3.googleusercontent.com/x=s72', 800) == \
        'https://yt3.googleusercontent.com/x=s800'
    banner = 'https://yt3.googleusercontent.com/x=w2120-fcrop64=1,00000000ffffffff-k-c0xffffffff-no-nd-rj'
    assert parser.square_art_at(banner, 800) == banner
    assert parser.square_art_at('https://i.ytimg.com/vi/a/s176.jpg', 800) == 'https://i.ytimg.com/vi/a/s176.jpg'


def test_banners_are_asked_for_at_full_width():
    banner = 'https://yt3.googleusercontent.com/x=w2120-fcrop64=1,00000000ffffffff-k-c0xffffffff-no-nd-rj'
    assert parser.larger_art(banner) == banner.replace('=w2120-', '=w2560-')
    other = 'https://lh3.googleusercontent.com/x=w3840-h2160'
    assert parser.larger_art(other) == other


def test_video_pictures_lose_the_query_that_shrinks_them():
    base = 'https://i.ytimg.com/vi/abc/'
    for name in ('hq720.jpg', 'hq720_2.jpg', 'maxresdefault.jpg', 'oardefault.jpg', 'oar2.jpg', 'sardefault.jpg'):
        shrunk = base + name + '?sqp=-oaymwEVCIAFEOgCSFDyq4qpAwcVAACIQhgB&rs=AOn4CL&usqp=CBE'
        assert parser.larger_art(shrunk) == base + name
    for kept in ('hqdefault.jpg?sqp=-oaymwExCOADEI4CSFryq4qpAyMIARUAAIhCGAHwAQH4Ae4HgALQBYoCDAgAEAEYZSBFKEIwDw==&rs=A',
                 'hq720_custom_2.jpg?sqp=CPDRjNgG-oaymwEVCIAFEOgCSFDyq4qpAwcVAACIQhgB&rs=AOn4CL',
                 'sddefault.jpg?v=6aff0d94', 'hq720.jpg'):
        assert parser.larger_art(base + kept) == base + kept
    localized = 'https://i.ytimg.com/vi_lc/abc/hq720_en.jpg?sqp=-oaymwEVCIAFEOgCSFDyq4qpAwcVAACIQhgB&rs=A'
    assert parser.larger_art(localized) == localized
    thumbs = [{'url': base + 'hq720.jpg?sqp=-oaymwEVCIAFEOgC&rs=A', 'width': 640, 'height': 360}]
    assert parser.best_thumb(thumbs) == base + 'hq720.jpg'


def test_image_quality_setting_scales_every_kind(monkeypatch):
    import xbmcaddon

    avatar = 'https://yt3.ggpht.com/x=s176-c-k-c0x00ffffff-no-rj-mo'
    banner = 'https://yt3.googleusercontent.com/x=w2560-fcrop64=1,00000000ffffffff-k-c0xffffffff-no-nd-rj'
    thumb = 'https://i.ytimg.com/vi/abc/hq720.jpg?sqp=-oaymwEVCIAFEOgC&rs=A'
    expected = {
        2: ('=s800-', '=w2560-', 'https://i.ytimg.com/vi/abc/hq720.jpg'),
        1: ('=s400-', '=w2120-', 'https://i.ytimg.com/vi/abc/hq720.jpg'),
        0: ('=s176-', '=w2120-', thumb),  # as YouTube sends them; a banner remembered larger goes back
    }
    for quality, (square, width, full) in expected.items():
        monkeypatch.setitem(xbmcaddon.SETTINGS, 'image_quality', quality)
        assert square in parser.larger_art(avatar)
        assert width in parser.larger_art(banner)
        assert parser.larger_art(thumb) == full
