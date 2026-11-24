# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""The TV window's tiles and rail entries, from the parser's items and the guide's entries."""
import os

import xbmcgui

from .. import kodi, router

LIVE_COLOR = 'FFD6304A'
BADGE_COLOR = 'E6000000'
ICONS = os.path.join(kodi.ADDON_PATH, 'resources', 'tv', 'media')

# Guide entries by id, then by words in their icon type -> rail icon.
ICON_BY_ID = {'search': 'search', 'shorts': 'shorts', 'FEwhat_to_watch': 'home', 'FEtopics': 'home',
              'FEsubscriptions': 'subscriptions', 'FElibrary': 'library', 'FEmy_youtube': 'library',
              'FEhistory': 'history'}
ICON_BY_TYPE = (('WHAT_TO_WATCH', 'home'), ('HOME', 'home'), ('SUBSCRIPTION', 'subscriptions'),
                ('BOOKMARK', 'library'), ('LIBRARY', 'library'), ('HISTORY', 'history'), ('MUSIC', 'music'),
                ('BROADCAST', 'podcasts'), ('PODCAST', 'podcasts'), ('GAMING', 'gaming'), ('NEWS', 'news'),
                ('CLAPPERBOARD', 'movies'), ('MOVIE', 'movies'), ('LIVE', 'live'), ('TROPHY', 'sports'),
                ('SPORT', 'sports'), ('SEARCH', 'search'), ('SHORTS', 'shorts'), ('ACCOUNT', 'account'),
                ('SETTINGS', 'settings'))


def short_count(value):
    """123456 -> '123K', 1234567 -> '1.2M', as the TV app writes view counts."""
    for limit, suffix in ((1e9, 'B'), (1e6, 'M'), (1e3, 'K')):
        if value >= limit:
            number = value / limit
            text = ('%.1f' % number).rstrip('0').rstrip('.') if number < 10 else '%d' % number
            return text + suffix
    return str(value)


def icon(name):
    return os.path.join(ICONS, 'icon_%s.png' % name)


def rail_icon(entry):
    name = ICON_BY_ID.get(entry['id'])
    if not name:
        icon_type = (entry.get('icon') or '').upper()
        name = next((n for word, n in ICON_BY_TYPE if word in icon_type), 'topic')
    return icon(name)


def rail_item(entry):
    li = xbmcgui.ListItem(entry['title'], offscreen=True)
    thumb = entry.get('thumb')
    if thumb and (entry.get('pinned') or entry.get('channel')):
        li.setArt({'icon': thumb})
        li.setProperty('round', '1')
    else:
        li.setArt({'icon': entry.get('art') or rail_icon(entry)})
    li.setProperty('tint', 'FFFFFFFF')
    return li


def video_tile(item, known, threshold, fanart=''):
    """A video's tile; `known` is what its watch page said (descriptions store), if it was read, and
    `fanart` its channel's banner, when known.

    Not offscreen: the window's worker threads set its plot and progress while it is shown, and an
    offscreen item skips Kodi's GUI lock, so those writes would race the render thread and crash Kodi."""
    li = xbmcgui.ListItem(item['title'])
    known = known or {}
    meta = [item['channel']]
    if item['views']:
        meta.append('%s %s' % (short_count(item['views']), 'watching' if item['live'] else 'views'))
    if item['published']:
        meta.append(item['published'])
    li.setLabel2(' • '.join(m for m in meta if m))
    li.setArt({'thumb': item['thumb'], 'fanart': fanart or item['thumb']})
    li.setProperty('plot', router.video_plot(item, known, threshold))
    if item['live']:
        li.setProperty('badge', kodi.string(30127))
        li.setProperty('badge_color', LIVE_COLOR)
    elif item.get('upcoming'):
        li.setProperty('badge', kodi.string(30168))
        li.setProperty('badge_color', BADGE_COLOR)
    elif item['duration']:
        li.setProperty('badge', router.format_time(item['duration']))
        li.setProperty('badge_color', BADGE_COLOR)
    if item['watched_pct'] > 0:
        li.setProperty('progress', str(min(item['watched_pct'], 100)))
    return li


def folder_tile(item, avatar=False, fanart=''):
    """A channel, playlist or other page; `avatar` shows its picture round, as for a channel, and `fanart`
    is a channel's banner, when known."""
    li = xbmcgui.ListItem(item['title'], offscreen=True)
    lines = [line for line in item['plot_lines'] if line]
    li.setLabel2(lines[0] if lines else '')
    li.setArt({'thumb': item.get('thumb') or icon('topic'), 'fanart': fanart or item.get('thumb') or ''})
    li.setProperty('plot', '\n'.join(lines + ([' • '.join(item['badges'])] if item['badges'] else [])))
    if avatar or item['kind'] == 'channel' or (item['target'].get('browse_id') or '').startswith('UC'):
        li.setProperty('round', '1')
    elif item['kind'] == 'playlist':
        li.setProperty('badge', kodi.string(30169))
        li.setProperty('badge_color', BADGE_COLOR)
    return li


def action_tile(item):
    """A thing to do rather than a page (New search, Clear search history): an icon on a plain tile."""
    li = xbmcgui.ListItem(item['title'], offscreen=True)
    li.setArt({'icon': icon(item['icon'])})
    li.setProperty('icon_tile', '1')
    li.setProperty('plot', item.get('plot', ''))
    return li


def query_tile(item):
    """A past search, its words written large on the tile."""
    li = xbmcgui.ListItem(item['title'], offscreen=True)
    li.setProperty('text_tile', '1')
    li.setProperty('plot', item.get('plot', ''))
    return li


def tile(item, known, threshold, avatar=False, fanart=''):
    if item['kind'] == 'video':
        return video_tile(item, known, threshold, fanart)
    if item['kind'] == 'action':
        return action_tile(item)
    if item['kind'] == 'query':
        return query_tile(item)
    return folder_tile(item, avatar, fanart)
