# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""Turns TVHTML5 InnerTube responses into plain items, shelves and tabs.

Handles both item shapes the TV client sends: legacy `tileRenderer` and the newer
`lockupViewModel`, plus shelves, grids, secondary-nav tabs, playlists and continuations.
"""
import json
import re
import urllib.parse
from urllib.parse import unquote

SHELF_SHORTS = 'TVHTML5_SHELF_RENDERER_TYPE_SHORTS'
TILE_SHORTS = 'TVHTML5_TILE_RENDERER_TYPE_SHORTS'


def text(node):
    if not node:
        return ''
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        if 'simpleText' in node:
            return node['simpleText']
        if 'runs' in node:
            return ''.join(run.get('text', '') for run in node['runs'])
        if 'content' in node:
            return node['content']
    return ''


def best_thumb(thumbs):
    if not thumbs:
        return ''
    thumb = max(thumbs, key=lambda t: (t.get('width') or 0) * (t.get('height') or 0))
    url = thumb.get('url', '')
    return 'https:' + url if url.startswith('//') else url


def parse_duration(value):
    """'1:02:03' -> 3723. Returns 0 for anything else (e.g. 'LIVE', 'SHORTS')."""
    if not value or not re.match(r'^\d+(:\d{1,2}){0,2}$', value.strip()):
        return 0
    seconds = 0
    for part in value.strip().split(':'):
        seconds = seconds * 60 + int(part)
    return seconds


def parse_count(value):
    """'1.2M views' -> 1200000, '51K' -> 51000, '1,234 views' -> 1234."""
    if not value:
        return 0
    match = re.search(r'([\d.,]+)\s*([KMB]?)', value.replace(' ', ' '), re.I)
    if not match:
        return 0
    number = match.group(1).replace(',', '')
    try:
        amount = float(number)
    except ValueError:
        return 0
    return int(amount * {'': 1, 'K': 1e3, 'M': 1e6, 'B': 1e9}[match.group(2).upper()])


def walk_dicts(node):
    """Every dict in a response, depth first in document order: for finding a renderer wherever a client
    nests it."""
    if isinstance(node, dict):
        yield node
        children = node.values()
    elif isinstance(node, list):
        children = node
    else:
        return
    for child in children:
        yield from walk_dicts(child)


# ------------------------------------------------------------------ endpoints
def _unquote(value):
    """The TV client sends endpoint params percent-encoded ('...%3D'); InnerTube wants them raw."""
    return unquote(value) if value and '%' in value else value


def endpoint_target(command):
    """Map an InnerTube command to a navigation target dict, or None."""
    if not isinstance(command, dict):
        return None
    if 'innertubeCommand' in command:
        command = command['innertubeCommand']
    if 'watchEndpoint' in command:
        ep = command['watchEndpoint']
        return {'type': 'video', 'video_id': ep.get('videoId'), 'playlist_id': ep.get('playlistId'),
                'start': ep.get('startTimeSeconds', 0)}
    if 'reelWatchEndpoint' in command:
        ep = command['reelWatchEndpoint']
        return {'type': 'video', 'video_id': ep.get('videoId'), 'short': True,
                'params': _unquote(ep.get('params'))}
    if 'watchPlaylistEndpoint' in command:
        ep = command['watchPlaylistEndpoint']
        return {'type': 'play_playlist', 'playlist_id': ep.get('playlistId')}
    if 'browseEndpoint' in command:
        ep = command['browseEndpoint']
        return {'type': 'browse', 'browse_id': ep.get('browseId'), 'params': _unquote(ep.get('params'))}
    if 'searchEndpoint' in command:
        ep = command['searchEndpoint']
        return {'type': 'search', 'query': ep.get('query', ''), 'params': _unquote(ep.get('params'))}
    for sub in command.get('commandExecutorCommand', {}).get('commands', []):
        target = endpoint_target(sub)
        if target:
            return target
    return None


# --------------------------------------------------------------------- items
def _item_base(kind, title, thumb='', target=None):
    return {'kind': kind, 'title': title, 'thumb': thumb, 'target': target or {},
            'plot_lines': [], 'duration': 0, 'channel': '', 'channel_id': '', 'views': 0,
            'published': '', 'watched_pct': 0, 'short': False, 'live': False, 'upcoming': '', 'badges': []}


def _resolve_kind(kind, target):
    """The item kind from its content type, or from where it leads when the type is unknown."""
    if not kind:
        return 'video' if target and target['type'] == 'video' else 'folder'
    if kind == 'video' and target and target['type'] == 'browse':
        # A show ("629 episodes") is a video card of its latest episode that opens the show's playlist.
        return 'playlist' if (target.get('browse_id') or '').startswith('VL') else 'folder'
    return kind


def parse_tile(tile):
    content_type = tile.get('contentType', '')
    header = tile.get('header', {}).get('tileHeaderRenderer', {})
    meta = tile.get('metadata', {}).get('tileMetadataRenderer', {})
    target = endpoint_target(tile.get('onSelectCommand'))
    title = text(meta.get('title'))
    thumb = best_thumb(header.get('thumbnail', {}).get('thumbnails'))
    kind = {
        'TILE_CONTENT_TYPE_VIDEO': 'video',
        'TILE_CONTENT_TYPE_CHANNEL': 'channel',
        'TILE_CONTENT_TYPE_PLAYLIST': 'playlist',
    }.get(content_type)
    kind = _resolve_kind(kind, target)
    item = _item_base(kind, title, thumb, target)
    item['id'] = tile.get('contentId') or (target or {}).get('video_id') or (target or {}).get('browse_id')
    item['short'] = tile.get('tvhtml5ShelfRendererType') == TILE_SHORTS or bool(target and target.get('short'))

    for overlay in header.get('thumbnailOverlays', []):
        if 'tileMetadataRenderer' in overlay:
            # Shortcut tiles (Library's History, Watch later...; Movies' Explore) print their name on the image.
            item['title'] = item['title'] or text(overlay['tileMetadataRenderer'].get('title'))
        elif 'thumbnailOverlayResumePlaybackRenderer' in overlay:
            item['watched_pct'] = overlay['thumbnailOverlayResumePlaybackRenderer'].get('percentDurationWatched', 0)
        elif 'thumbnailOverlayTimeStatusRenderer' in overlay:
            status = overlay['thumbnailOverlayTimeStatusRenderer']
            label = text(status.get('text'))
            if status.get('style') == 'LIVE' or label.upper() == 'LIVE':
                item['live'] = True
            elif status.get('style') == 'SHORTS':
                item['short'] = True
            elif status.get('style') == 'UPCOMING':
                item['upcoming'] = label  # "Upcoming" / "Premiere", already in the UI language
            elif kind == 'video':
                item['duration'] = parse_duration(label)

    lines = []
    for line in meta.get('lines', []):
        parts = []
        for line_item in line.get('lineRenderer', {}).get('items', []):
            renderer = line_item.get('lineItemRenderer', {})
            value = text(renderer.get('text'))
            if renderer.get('badge'):
                badge = text(renderer['badge'].get('metadataBadgeRenderer', {}).get('label'))
                if badge:
                    item['badges'].append(badge)
            if not value or value.strip() == '•':
                continue
            parts.append(value)
            runs = (renderer.get('text') or {}).get('runs') or []
            for run in runs:
                nav = endpoint_target(run.get('navigationEndpoint'))
                if nav and nav['type'] == 'browse' and (nav['browse_id'] or '').startswith('UC'):
                    item['channel'] = run.get('text', '')
                    item['channel_id'] = nav['browse_id']
        if parts:
            lines.append(parts)
    if not lines or not item['title']:
        # Carousel tiles (TILE_STYLE_YTLR_CAROUSEL) carry no metadata block; the long-press menu has it.
        menu = (tile.get('onLongPressCommand') or {}).get('showMenuCommand', {})
        item['title'] = item['title'] or text(menu.get('title'))
        subtitle = text(menu.get('subtitle'))
        if subtitle and not lines:
            lines.append([part.strip() for part in subtitle.split('•') if part.strip()][:1] or [subtitle])
    _apply_lines(item, lines)
    return item


def parse_lockup(lockup):
    content_type = lockup.get('contentType', '')
    target = endpoint_target(lockup.get('rendererContext', {}).get('commandContext', {}).get('onTap'))
    meta = lockup.get('metadata', {}).get('lockupMetadataViewModel', {})
    title = text(meta.get('title'))
    image = lockup.get('contentImage', {})
    thumb_vm = image.get('thumbnailViewModel') or image.get('collectionThumbnailViewModel', {}).get(
        'primaryThumbnail', {}).get('thumbnailViewModel') or {}
    thumb = best_thumb(thumb_vm.get('image', {}).get('sources'))
    if not thumb and 'decoratedAvatarViewModel' in image:
        avatar = image['decoratedAvatarViewModel'].get('avatar', {}).get('avatarViewModel', {})
        thumb = best_thumb(avatar.get('image', {}).get('sources'))
    kind = {
        'LOCKUP_CONTENT_TYPE_VIDEO': 'video',
        'LOCKUP_CONTENT_TYPE_SHORT': 'video',
        'LOCKUP_CONTENT_TYPE_CHANNEL': 'channel',
        'LOCKUP_CONTENT_TYPE_PLAYLIST': 'playlist',
        'LOCKUP_CONTENT_TYPE_PODCAST': 'playlist',
        'LOCKUP_CONTENT_TYPE_ALBUM': 'playlist',
    }.get(content_type)
    kind = _resolve_kind(kind, target)
    item = _item_base(kind, title, thumb, target)
    item['id'] = lockup.get('contentId')
    item['short'] = content_type == 'LOCKUP_CONTENT_TYPE_SHORT' or bool(target and target.get('short'))

    for overlay in thumb_vm.get('overlays', []):
        for badge_vm in overlay.get('thumbnailBottomOverlayViewModel', {}).get('badges', []) + \
                overlay.get('thumbnailOverlayBadgeViewModel', {}).get('thumbnailBadges', []):
            badge = badge_vm.get('thumbnailBadgeViewModel', {})
            label = badge.get('text', '')
            style = badge.get('badgeStyle', '')
            if 'LIVE' in style or label.upper() == 'LIVE':
                item['live'] = True
            elif parse_duration(label):
                item['duration'] = parse_duration(label)
            elif label and kind == 'playlist':
                item['badges'].append(label)
            elif label and kind == 'video' and not item['short']:
                item['upcoming'] = label  # "Upcoming" / "Premiere", already in the UI language
        progress = overlay.get('thumbnailBottomOverlayViewModel', {}).get('progressBar', {}) \
            .get('thumbnailOverlayProgressBarViewModel', {})
        if progress.get('startPercent') is not None:
            item['watched_pct'] = progress['startPercent']

    lines = []
    rows = meta.get('metadata', {}).get('contentMetadataViewModel', {}).get('metadataRows', [])
    for row in rows:
        parts = []
        for part in row.get('metadataParts', []):
            value = text(part.get('text'))
            if value:
                parts.append(value)
                cmd = part.get('text', {}).get('commandRuns') or []
                for run in cmd:
                    nav = endpoint_target(run.get('onTap'))
                    if nav and nav['type'] == 'browse' and (nav['browse_id'] or '').startswith('UC'):
                        item['channel_id'] = nav['browse_id']
                        item['channel'] = value
        if parts:
            lines.append(parts)
    _apply_lines(item, lines)
    return item


_VIEWS = re.compile(r'(view|watching|aufrufe|vues|visualizaciones)', re.I)
_AGO = re.compile(r'(ago|vor |il y a|hace|streamed|premiered|\d{4})', re.I)
_SUBS = re.compile(r'subscriber', re.I)


def is_count(part):
    """A tile's view count, age or subscriber count ("556K views", "3 days ago")."""
    return bool(_VIEWS.search(part) or _AGO.search(part) or _SUBS.search(part))


def _apply_lines(item, lines):
    """Spread the metadata lines of a tile/lockup over channel, views, date and plot."""
    item['plot_lines'] = [' • '.join(parts) for parts in lines]
    for index, parts in enumerate(lines):
        for part in parts:
            if _VIEWS.search(part) and not item['views']:
                item['views'] = parse_count(part)
                if 'watching' in part.lower():
                    item['live'] = True
            elif _AGO.search(part) and not item['published']:
                item['published'] = part
            elif _SUBS.search(part):
                item['subscribers'] = part
            elif index == 0 and not item['channel'] and item['kind'] == 'video':
                item['channel'] = part
            elif item.get('upcoming') and index > 0 and not item['published']:
                item['published'] = part  # "Scheduled for 11/19/26, 9:00 AM" / "Premieres ..."


def parse_channel_header(header):
    item = _item_base('channel', text(header.get('title')))
    item['thumb'] = best_thumb(header.get('thumbnail', {}).get('thumbnails')
                               or header.get('avatar', {}).get('thumbnails'))
    item['fanart'] = best_thumb(header.get('backgroundImage', {}).get('thumbnails'))
    subtitle = header.get('subtitle', {}).get('lineRenderer') or header.get('lineRenderer') or {}
    parts = []
    for line_item in subtitle.get('items', []):
        value = text(line_item.get('lineItemRenderer', {}).get('text'))
        if value and value.strip() != '•':
            parts.append(value)
            if _SUBS.search(value):
                item['subscribers'] = value
    lines = [' • '.join(parts)] if parts else []
    description = _find_description(header.get('selectableDescription'))
    if description:
        lines.append(description)
    item['plot_lines'] = lines
    return item


DESCRIPTION_KEYS = ('description', 'content', 'compactDescription', 'descriptionText')


def _find_description(node):
    """Longest text in a channel's description panel (falls back to the compact one)."""
    best = ''
    for value in walk_dicts(node or {}):
        for key in DESCRIPTION_KEYS:
            candidate = text(value.get(key)).replace(' ...more', '')
            if len(candidate) > len(best):
                best = candidate
    return best


def _with_channel(item, node):
    """Most video tiles name their channel only in the long-press menu (Go to channel)."""
    if item and item['kind'] == 'video' and not item['channel_id']:
        for value in walk_dicts(node):
            endpoint = value.get('browseEndpoint')
            browse_id = endpoint.get('browseId') or '' if isinstance(endpoint, dict) else ''
            if browse_id.startswith('UC'):
                item['channel_id'] = browse_id
                break
    return item


def parse_item(node):
    """Any list entry -> item dict, or None for things we don't show."""
    if not isinstance(node, dict):
        return None
    if 'tileRenderer' in node:
        return _with_channel(parse_tile(node['tileRenderer']), node)
    if 'lockupViewModel' in node:
        return _with_channel(parse_lockup(node['lockupViewModel']), node)
    if 'pivotVideoRenderer' in node:
        pivot = node['pivotVideoRenderer']
        item = _item_base('video', text(pivot.get('title')),
                          best_thumb(pivot.get('thumbnail', {}).get('thumbnails')),
                          endpoint_target(pivot.get('navigationEndpoint')))
        item['id'] = pivot.get('videoId')
        item['channel'] = text(pivot.get('shortBylineText'))
        item['views'] = parse_count(text(pivot.get('viewCountText')))
        item['published'] = text(pivot.get('publishedTimeText'))
        item['duration'] = parse_duration(text(pivot.get('lengthText')))
        return item
    if 'playlistVideoRenderer' in node:
        video = node['playlistVideoRenderer']
        item = _item_base('video', text(video.get('title')),
                          best_thumb(video.get('thumbnail', {}).get('thumbnails')),
                          endpoint_target(video.get('navigationEndpoint')))
        item['id'] = video.get('videoId')
        item['channel'] = text(video.get('shortBylineText'))
        item['duration'] = int(video.get('lengthSeconds') or 0)
        return item
    if 'gridButtonRenderer' in node or 'tileButtonRenderer' in node:
        button = node.get('gridButtonRenderer') or node.get('tileButtonRenderer')
        target = endpoint_target(button.get('onPress') or button.get('navigationEndpoint'))
        if target:
            return _item_base('folder', text(button.get('title') or button.get('text')),
                              best_thumb(button.get('thumbnail', {}).get('thumbnails')), target)
    return None


# ------------------------------------------------------------------- shelves
def _continuation(container):
    for entry in container.get('continuations', []) or []:
        # nextRadioContinuationData pages through a Mix; reload only re-fetches the same items.
        for key in ('nextContinuationData', 'nextRadioContinuationData', 'reloadContinuationData'):
            if key in entry:
                return entry[key].get('continuation')
    return None


def _list_items(content):
    """Find the list inside a shelf's content and return (raw items, continuation, renderer key)."""
    for key in ('horizontalListRenderer', 'verticalListRenderer', 'gridRenderer', 'expandedShelfContentsRenderer'):
        if key in content:
            inner = content[key]
            return inner.get('items', []), _continuation(inner), key
    return [], None, None


def _shelf(title, raw_items, continuation, shelf_type='', endpoint=None):
    items = [i for i in (parse_item(n) for n in raw_items) if i]
    # Trailing continuationItemRenderer (newer layouts)
    for node in raw_items:
        if 'continuationItemRenderer' in node:
            cmd = node['continuationItemRenderer'].get('continuationEndpoint', {})
            continuation = cmd.get('continuationCommand', {}).get('token') or continuation
    return {'title': title, 'items': items, 'continuation': continuation,
            'shorts': shelf_type == SHELF_SHORTS, 'endpoint': endpoint}


def parse_shelf(shelf):
    header = shelf.get('headerRenderer', {}).get('shelfHeaderRenderer', {})
    title = text(shelf.get('title')) or text(header.get('title'))
    if not title:
        avatar = header.get('avatarLockup', {}).get('avatarLockupRenderer') or header.get('avatarLockupRenderer', {})
        title = text(avatar.get('title'))
    raw, cont, _ = _list_items(shelf.get('content', {}))
    endpoint = endpoint_target(shelf.get('endpoint') or shelf.get('navigationEndpoint'))
    return _shelf(title.strip(), raw, cont, shelf.get('tvhtml5ShelfRendererType', ''), endpoint)


def parse_page(resp):
    """Normalise any browse/search/next response into:

    {'header': item|None, 'tabs': [..], 'shelves': [..], 'continuation': token|None, 'message': str}
    'message' is what YouTube says about an empty page, if anything.
    Each shelf: {'title', 'items', 'continuation', 'shorts', 'endpoint'}.
    """
    page = {'header': None, 'tabs': [], 'shelves': [], 'continuation': None, 'message': ''}

    def handle_section_list(section_list):
        for entry in section_list.get('contents', []):
            if 'shelfRenderer' in entry:
                page['shelves'].append(parse_shelf(entry['shelfRenderer']))
            elif 'itemSectionRenderer' in entry:
                raw = entry['itemSectionRenderer'].get('contents', [])
                shelf = _shelf('', raw, _continuation(entry['itemSectionRenderer']))
                if shelf['items']:
                    page['shelves'].append(shelf)
            elif 'clusterShelfRenderer' in entry:
                # Search rows such as "Recently uploaded" or "Shows", each headed by a button.
                for cluster in entry['clusterShelfRenderer'].get('clusters', []):
                    renderer = cluster.get('clusterRenderer', {})
                    button = renderer.get('headerRenderer', {}).get('buttonViewModel', {})
                    shelf = _shelf(text(button.get('title')).strip(), renderer.get('items', []), None,
                                   endpoint=endpoint_target(button.get('onTap')))
                    if shelf['items']:
                        page['shelves'].append(shelf)
            elif 'gridRenderer' in entry:
                grid = entry['gridRenderer']
                page['shelves'].append(_shelf(text(grid.get('header', {}).get('gridHeaderRenderer', {}).get('title')),
                                              grid.get('items', []), _continuation(grid)))
        page['continuation'] = _continuation(section_list) or page['continuation']

    def handle_surface(surface):
        content = surface.get('content', {})
        header = surface.get('header', {})
        if 'channelHeaderRenderer' in header:
            page['header'] = parse_channel_header(header['channelHeaderRenderer'])
        elif 'channelHeaderRenderer' in surface:
            page['header'] = parse_channel_header(surface['channelHeaderRenderer'])
        if 'genericPromoRenderer' in content:
            # An empty page's own explanation ("Videos you upload to YouTube will appear here").
            promo = content['genericPromoRenderer']
            page['message'] = text(promo.get('bodyText')) or text(promo.get('title'))
        if 'sectionListRenderer' in content:
            handle_section_list(content['sectionListRenderer'])
        elif 'gridRenderer' in content:
            grid = content['gridRenderer']
            page['shelves'].append(_shelf('', grid.get('items', []), _continuation(grid)))
        elif 'twoColumnRenderer' in content:
            handle_two_column(content['twoColumnRenderer'])

    def handle_two_column(two):
        left = two.get('leftColumn', {})
        for key in ('entityMetadataRenderer', 'playlistHeaderRenderer'):
            if key in left:
                meta = left[key]
                header = _item_base('playlist', text(meta.get('title')),
                                    best_thumb(meta.get('thumbnail', {}).get('thumbnails')))
                header['plot_lines'] = [text(meta.get('description'))] + \
                    [text(b) for b in meta.get('bylines', []) if text(b)]
                page['header'] = header
        right = two.get('rightColumn', {})
        if 'playlistVideoListRenderer' in right:
            vlist = right['playlistVideoListRenderer']
            page['shelves'].append(_shelf('', vlist.get('contents', []), _continuation(vlist)))
        elif 'sectionListRenderer' in right:
            handle_section_list(right['sectionListRenderer'])

    contents = resp.get('contents', {})
    browse = contents.get('tvBrowseRenderer', {}).get('content', {})
    if 'tvSurfaceContentRenderer' in browse:
        handle_surface(browse['tvSurfaceContentRenderer'])
    if 'tvSecondaryNavRenderer' in browse:
        # A channel can sit in more than one section (recently active and the full list); list it once.
        seen_tabs = set()
        for section in browse['tvSecondaryNavRenderer'].get('sections', []):
            for tab in section.get('tvSecondaryNavSectionRenderer', {}).get('tabs', []):
                tab_r = tab.get('tabRenderer')
                if not tab_r:
                    continue
                thumb = best_thumb(tab_r.get('thumbnail', {}).get('thumbnails'))
                entry = _item_base('tab', text(tab_r.get('title')), thumb, endpoint_target(tab_r.get('endpoint')))
                entry['selected'] = tab_r.get('selected', False)
                key = json.dumps(entry['target'], sort_keys=True) if entry['target'] else entry['title']
                if key in seen_tabs:
                    continue
                seen_tabs.add(key)
                page['tabs'].append(entry)
                surface = tab_r.get('content', {}).get('tvSurfaceContentRenderer')
                if surface and tab_r.get('selected'):
                    handle_surface(surface)
    if 'sectionListRenderer' in contents:  # search
        handle_section_list(contents['sectionListRenderer'])
    if 'singleColumnWatchNextResults' in contents:  # next
        pivot = contents['singleColumnWatchNextResults'].get('pivot', {})
        if 'sectionListRenderer' in pivot:
            handle_section_list(pivot['sectionListRenderer'])

    cont = resp.get('continuationContents', {})
    for key, value in cont.items():
        if key == 'sectionListContinuation':
            handle_section_list(value)
        elif key in ('horizontalListContinuation', 'gridContinuation', 'playlistVideoListContinuation',
                     'verticalListContinuation'):
            raw = value.get('items') or value.get('contents') or []
            page['shelves'].append(_shelf('', raw, _continuation(value)))
        elif key == 'tvSurfaceContentContinuation':
            handle_surface(value)
    for action in resp.get('onResponseReceivedActions', []) or []:
        append = action.get('appendContinuationItemsAction') or action.get('reloadContinuationItemsCommand')
        if append:
            page['shelves'].append(_shelf('', append.get('continuationItems', []), None))
    return page


def parse_guide(resp):
    """Sidebar entries: [{'id', 'title', 'target', 'thumb', 'channel'}]."""
    entries = []
    seen = set()  # a channel can be listed in more than one guide section
    for section in resp.get('items', []):
        for value in section.values():
            for item in value.get('items', []) or []:
                guide = item.get('guideEntryRenderer')
                if not guide:
                    continue
                target = endpoint_target(guide.get('navigationEndpoint'))
                if not target:
                    continue
                title = text(guide.get('formattedTitle')) or text(guide.get('title'))
                if target['type'] == 'browse':
                    entry_id = target['browse_id']
                elif target['type'] == 'search':
                    entry_id = 'search'
                elif target.get('short'):
                    entry_id = 'shorts'
                else:
                    entry_id = title
                if entry_id in seen:
                    continue
                seen.add(entry_id)
                thumb = best_thumb(guide.get('thumbnail', {}).get('thumbnails'))
                entries.append({'id': entry_id, 'title': title, 'target': target, 'thumb': thumb,
                                'channel': bool(thumb) and target['type'] == 'browse'
                                and (target['browse_id'] or '').startswith('UC'),
                                'icon': guide.get('icon', {}).get('iconType', '')})
    return entries


def chapters(next_resp):
    """Chapters from a next response: [{'title', 'start' (seconds), 'thumb'}], empty when there are none."""
    for mutation in (next_resp or {}).get('frameworkUpdates', {}).get('entityBatchUpdate', {}).get('mutations', []):
        markers = mutation.get('payload', {}).get('macroMarkersListEntity', {}).get('markersList', {})
        if markers.get('markerType') != 'MARKER_TYPE_CHAPTERS':
            continue
        return [{'title': text(marker.get('title')),
                 'start': int(marker.get('startMillis') or 0) / 1000.0,
                 'thumb': best_thumb(marker.get('thumbnailDetails', {}).get('thumbnails'))}
                for marker in markers.get('markers', [])]
    return []


def _find_renderer(node, key):
    """The first `key` renderer anywhere in a response (clients nest the watch page differently)."""
    return next((value[key] for value in walk_dicts(node) if key in value), None)


def channel_banner(resp):
    """The banner from a channel page: the TV-sized one (2120x1192) where there is one."""
    header = _find_renderer(resp, 'c4TabbedHeaderRenderer') or {}
    for key in ('tvBanner', 'banner'):
        url = best_thumb(header.get(key, {}).get('thumbnails'))
        if url:
            return url
    return (parse_page(resp).get('header') or {}).get('fanart', '')


def description_text(node):
    """A description's text with its links in full: the runs show them shortened ("https://ex.com/a...")."""
    if not isinstance(node, dict) or 'runs' not in node:
        return text(node)
    parts = []
    for run in node['runs']:
        url = run.get('navigationEndpoint', {}).get('urlEndpoint', {}).get('url', '')
        if url.startswith('https://www.youtube.com/redirect'):
            url = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get('q', [url])[0]
        parts.append(url if url and run.get('text', '').endswith('...') else run.get('text', ''))
    return ''.join(parts)


def video_details(player_resp, next_resp=None):
    """Full information for a single video from the player (and optionally next) response."""
    details = player_resp.get('videoDetails', {}) if player_resp else {}
    info = {
        'video_id': details.get('videoId'),
        'title': details.get('title', ''),
        'plot': details.get('shortDescription', ''),
        'channel': details.get('author', ''),
        'channel_id': details.get('channelId', ''),
        'duration': int(details.get('lengthSeconds') or 0),
        'views': int(details.get('viewCount') or 0),
        'tags': details.get('keywords', []),
        'live': details.get('isLive', False),
        'thumb': best_thumb(details.get('thumbnail', {}).get('thumbnails')),
        'published': '',
        'date': '',
        'subscribers': '',
        'likes': '',
    }
    micro = (player_resp or {}).get('microformat', {}).get('playerMicroformatRenderer', {})
    if micro:
        info['date'] = (micro.get('publishDate') or micro.get('uploadDate') or '')[:10]
        info['genre'] = micro.get('category', '')
    meta = _find_renderer(next_resp, 'videoMetadataRenderer') if next_resp else None
    if meta:
        info['title'] = info['title'] or text(meta.get('title'))
        info['published'] = text(meta.get('dateText')) or text(meta.get('publishedTimeText'))
        owner = meta.get('owner', {}).get('videoOwnerRenderer', {})
        info['channel'] = info['channel'] or text(owner.get('title'))
        owner_link = owner.get('navigationEndpoint', {}).get('browseEndpoint', {})
        info['channel_id'] = info['channel_id'] or owner_link.get('browseId', '')
        info['subscribers'] = text(owner.get('subscriberCountText'))
        info['channel_thumb'] = best_thumb(owner.get('thumbnail', {}).get('thumbnails'))
        desc = description_text(meta.get('description'))
        if desc and len(desc) > len(info['plot']):
            info['plot'] = desc
        likes = meta.get('likeButton', {}).get('likeButtonRenderer', {}).get('likeCount')
        if likes:
            info['likes'] = str(likes)
    return info
