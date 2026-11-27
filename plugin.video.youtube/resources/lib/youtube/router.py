# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Plugin entry: routes, directory listings, playback and the account/menu dialogs."""
import json
import random
import threading
import time
import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin

from . import (
    art,
    auth,
    compat,
    describe,
    descriptions,
    history,
    hls,
    http,
    icons,
    kodi,
    maintenance,
    mpd,
    pages,
    parser,
    playback,
    qr,
    sponsorblock,
)
from .innertube import InnerTube, InnerTubeError

BASE_URL = 'plugin://%s/' % kodi.ADDON_ID
ROW_PAGES = 3  # pages of rows per listing at least: one page holds only three or four rows
ISA = 'inputstream.adaptive'
RATE_TIMEOUT = 2  # seconds for the read of a format's index: playback waits on it
DASH_MIME = 'application/dash+xml'
HLS_MIME = 'application/vnd.apple.mpegurl'


def error_message(exc):
    """A short, TV-friendly message for a failed request; the raw error goes to the log."""
    status = getattr(exc, 'status', None)
    if status == 0:
        string_id = 30138
    elif status in (403, 429):
        string_id = 30135
    elif status in (400, 404):
        string_id = 30136
    elif status and status >= 500:
        string_id = 30137
    else:
        return kodi.formatted(30129, exc)
    return kodi.string(string_id)


def format_count(value):
    """'456789' -> '456,789'; text YouTube already formatted ('456K') is kept."""
    value = str(value)
    return f'{int(value):,}' if value.isdigit() else value


C_INT_MAX = 2 ** 31 - 1


def c_int(value):
    """Clamp for InfoTag setters that take a C int: 32-bit Kodi builds (the Vero) overflow on
    view counts above about 2.1 billion."""
    return min(int(value), C_INT_MAX)


def header_playlist(browse_id):
    """The playlist a page's header can play: the playlist itself, or a channel's uploads."""
    browse_id = browse_id or ''
    if browse_id.startswith('VL'):
        return browse_id[2:]
    if browse_id.startswith('UC'):
        return 'UU' + browse_id[2:]
    return None


def format_time(seconds):
    seconds = int(seconds)
    hours, rest = divmod(seconds, 3600)
    return '%d:%02d:%02d' % (hours, rest // 60, rest % 60) if hours else '%d:%02d' % (rest // 60, rest % 60)


def is_mix(playlist_id):
    """YouTube Mixes (RD...) are generated on the fly and can't be browsed as a playlist page."""
    return (playlist_id or '').startswith('RD')


def video_id_of(item):
    return item['target'].get('video_id') or item.get('id')


def channel_of(item):
    """The channel an item is, or belongs to."""
    browse_id = item['target'].get('browse_id') or ''
    return browse_id if browse_id.startswith('UC') else item.get('channel_id')


def video_plot(item, known, threshold):
    """The info panel's text, laid out like Full details: channel, subscribers, age, views and likes,
    then status, then the description."""
    known = known or {}
    lines = [' • '.join(x for x in _plot_facts(item, known) if x), ' • '.join(_plot_status(item, threshold))]
    if known.get('d'):
        lines.append('\n' + known['d'])
    else:
        lines.extend(_tile_extras(item, ' '.join(lines)))
    return '\n'.join(line for line in lines if line)


def _plot_facts(item, known):
    """Channel, subscribers, age, views and likes. `known` is what the watch page said, keyed by one
    letter to keep the descriptions store small (s subscribers, t/p age, l likes); it fills what the
    tile lacks."""
    facts = [item['channel'], item.get('subscribers') or known.get('s'),
             item['published'] or known.get('t') or known.get('p')]
    if item['views']:
        facts.append('{:,} {}'.format(item['views'], 'watching' if item['live'] else 'views'))
    if known.get('l'):
        facts.append('%s likes' % format_count(known['l']))
    return facts


def _plot_status(item, threshold):
    """Live or upcoming, the tile's badges, and how much of it has been watched."""
    status = []
    if item['live']:
        status.append(kodi.string(30127))
    elif item.get('upcoming'):
        status.append(item['upcoming'])
    status.extend(item['badges'])
    if item['watched_pct'] >= threshold:
        status.append(kodi.string(30142))
    elif item['watched_pct'] > 0:
        status.append(kodi.formatted(30141, item['watched_pct']))
    return status


def _tile_extras(item, said):
    """Lines from the tile that say more than `said` already does (e.g. "Scheduled for ..."), for when
    there's no description to show instead. Counts are dropped: the facts line has them."""
    extras = []
    for line in item['plot_lines']:
        parts = [p for p in line.split(' • ') if p and p not in said and not parser.is_count(p)]
        if parts:
            extras.append(' • '.join(parts))
    return extras


def _order_videos(videos, order, start):
    """Put a playlist's videos in place in the order asked for ('reverse' or 'shuffle'). A chosen first
    video keeps the playlist's order, so shuffle is ignored then."""
    if order == 'reverse':
        videos.reverse()
    elif order == 'shuffle' and not start:
        random.shuffle(videos)


def _details_plot(info):
    """The Info dialog's plot: a facts line (channel, subscribers, date, views, likes), then the
    description."""
    facts = [x for x in (info['channel'], info.get('subscribers'), info.get('published') or info.get('date'),
                         ('%s views' % '{:,}'.format(info['views'])) if info['views'] else '',
                         ('%s likes' % format_count(info['likes'])) if info.get('likes') else '') if x]
    plot = info['plot']
    if facts:
        plot = ' • '.join(facts) + ('\n\n' + plot if plot else '')
    return plot


def _set_details_tag(tag, info):
    """Fill a video's info tag from its watch page details. The channel stands in as both studio and
    director, which is where skins show who made a video."""
    tag.setMediaType('video')
    tag.setTitle(info['title'])
    tag.setPlot(_details_plot(info))
    if info['channel']:
        tag.setStudios([info['channel']])
        tag.setDirectors([info['channel']])
    if info['duration']:
        tag.setDuration(info['duration'])
    if info['tags']:
        tag.setTags(info['tags'][:20])
    if info['views']:
        tag.setVotes(c_int(info['views']))
    if info.get('date'):
        tag.setPremiered(info['date'])
    if info.get('genre'):
        tag.setGenres([info['genre']])


def _folder_url(item):
    """Where a channel, playlist or other folder tile leads, or None for tiles that lead nowhere here.
    A playlist's page is VL<playlist id>; it opens that page whether the tile points at the page or at
    the playlist's first video (a "play all" tile)."""
    target = item['target'] or {}
    kind = item['kind']
    if kind == 'playlist' or (target.get('type') == 'video' and target.get('playlist_id') and kind != 'video'):
        playlist_id = target.get('playlist_id') or (target.get('browse_id') or '')[2:] or item.get('id')
        browse_id = target.get('browse_id') if target.get('type') == 'browse' else 'VL' + playlist_id
        return url_for('browse', id=browse_id, title=item['title'])
    if target.get('type') == 'browse':
        return url_for('browse', id=target['browse_id'], params=target.get('params'), title=item['title'])
    if target.get('type') == 'search':
        return url_for('search', q=target['query'], params=target.get('params'))
    if target.get('type') == 'play_playlist':
        return url_for('browse', id='VL' + target['playlist_id'], title=item['title'])
    return None


def _folder_plot(item):
    lines = list(item['plot_lines'])
    if item['badges']:
        lines.append(' • '.join(item['badges']))
    return '\n'.join(lines)


def _folder_menu(item):
    target = item['target'] or {}
    browse_id = target.get('browse_id') or ''
    menu = []
    if item['kind'] == 'channel' or browse_id.startswith('UC'):
        menu.append((kodi.string(30106), 'RunPlugin(%s)' % url_for(
            'pin', id=browse_id or item.get('id'), title=item['title'], thumb=item.get('thumb'))))
    if item['kind'] == 'playlist':
        playlist_id = browse_id[2:] if browse_id.startswith('VL') else (target.get('playlist_id') or item.get('id'))
        menu.append((kodi.string(30126), 'RunPlugin(%s)' % url_for('play_playlist', list=playlist_id)))
    return menu


def _player_error_message(exc):
    """What to tell the viewer when YouTube offers no streams."""
    # YouTube's own playability reasons ("Video unavailable") read fine; HTTP failures don't.
    # An upcoming stream's reason already says it all ("This live event will begin in 61 minutes.").
    if exc.status is not None:
        return error_message(exc)
    if getattr(exc, 'bot_check', False):
        # YouTube's own wording ("Sign in to confirm...") reads as if signing in to the add-on would
        # help, but it judges the connection: see InnerTube.player.
        return kodi.string(30183)
    if str(exc) in ('', 'unplayable'):
        return kodi.string(30120)
    return str(exc)


def _is_live(resp):
    """A live stream (or one only offered as HLS, which a DASH manifest can't address)."""
    data = resp.get('streamingData', {})
    return bool(resp.get('videoDetails', {}).get('isLive')) or bool(
        data.get('hlsManifestUrl') and not any(f.get('initRange') for f in data.get('adaptiveFormats', [])))


def _subtitle_languages(hl):
    """Languages to offer machine-translated captions in: the setting (or Kodi's language) plus extras."""
    languages = [x.strip() for x in (kodi.setting('subs_translate').strip() or hl).split(',')]
    return languages + [x.strip() for x in kodi.setting('subs_more').split(',') if x.strip()]


def _rate_kind(resp, ua):
    """mpd.rate_kind() for the video, from one small read of the start of the smallest MP4 format's
    index. None, so the manifest keeps YouTube's whole frame rates, when it doesn't answer."""
    candidates = mpd.index_candidates(resp.get('streamingData', {}).get('adaptiveFormats', []))
    if not candidates:
        kodi.log('frame rate: no MP4 video index, using whole rates')
        return None
    fmt, byte_range = candidates[0]
    try:
        # background: it is optional, so it is refused rather than queued while the host holds requests
        _, index = http.request(fmt['url'], headers={'User-Agent': ua, 'Range': 'bytes=' + byte_range},
                                timeout=RATE_TIMEOUT, priority=http.BACKGROUND)
    except http.HTTPError as exc:
        kodi.log('frame rate: unknown, using whole rates: index of %s not read (%s)' % (fmt['itag'], exc))
        return None
    kind, reason = mpd.rate_kind(index, fmt['fps'])
    if kind:
        kodi.log('frame rate: %s, from the index of %s' % (kind, fmt['itag']))
    else:
        kodi.log('frame rate: unknown, using whole rates: index of %s: %s' % (fmt['itag'], reason))
    return kind


def _proxy_subtitles(video_id, subs, ua, port):
    """Point subtitles at the local server, which retries YouTube's rate limits (429 on translated
    tracks) and returns an empty track instead of an error."""
    with open(kodi.temp_file('%s.subs.json' % video_id), 'w', encoding='utf-8') as handle:
        json.dump({'ua': ua, 'urls': [s['url'] for s in subs]}, handle)
    for index, sub in enumerate(subs):
        sub['url'] = 'http://127.0.0.1:%s/sub/%s/%d.vtt' % (port, video_id, index)


# ISA's resolution caps (inputstream.adaptive.chooser_resolution_max), tallest first.
ISA_RESOLUTIONS = ((2160, '4K'), (1440, '1440p'), (1080, '1080p'), (720, '720p'), (480, '480p'))


def isa_resolution_cap(max_quality):
    """The Maximum quality setting as ISA's resolution cap, '' for none. ISA applies it in its Adaptive and
    Fixed resolution modes only, so in Manual OSD and Ask quality every resolution stays on offer."""
    if not max_quality or max_quality > ISA_RESOLUTIONS[0][0]:
        return ''
    return next((name for height, name in ISA_RESOLUTIONS if height <= max_quality), '')


def manifest_height_cap(max_quality):
    """The Maximum quality setting where ISA can't cap it (below its lowest cap, 480p): the manifest is
    cut down to it instead. 0 otherwise."""
    return max_quality if 0 < max_quality < ISA_RESOLUTIONS[-1][0] else 0


def _stream_item(path, mime, ua, live):
    """The ListItem inputstream.adaptive plays, with YouTube's user agent on every request."""
    headers = 'User-Agent=%s' % urllib.parse.quote(ua)
    li = xbmcgui.ListItem(path=path, offscreen=True)
    li.setMimeType(mime)
    li.setContentLookup(False)
    li.setProperty('inputstream', ISA)
    li.setProperty(ISA + '.manifest_headers', headers)
    li.setProperty(ISA + '.stream_headers', headers)
    if live:
        li.setProperty(ISA + '.play_timeshift_buffer', 'true')
    return li


def _cap_resolution(li):
    """Hand the Maximum quality setting to ISA, which keeps the manifest whole for its other modes."""
    cap = isa_resolution_cap(kodi.setting_int('max_quality'))
    if cap:
        li.setProperty(ISA + '.chooser_resolution_max', cap)


def video_label(item):
    """A video's listing label, flagged when it is live or upcoming."""
    if item['live']:
        return '[COLOR red]%s[/COLOR] %s' % (kodi.string(30127), item['title'])
    if item.get('upcoming'):
        return '[COLOR yellow]%s[/COLOR] %s' % (item['upcoming'], item['title'])
    return item['title']


def _set_video_tag(tag, item, known, threshold):
    """Fill a video's info tag: plot, channel, duration, watch progress, badges and views."""
    tag.setMediaType('video')
    tag.setTitle(item['title'])
    plot = video_plot(item, known, threshold)
    tag.setPlot(plot)
    # Some views (Estuary's Poster, Shift, Fanart) show the outline instead of the plot when it is set.
    tag.setPlotOutline(plot)
    if known and known.get('p'):
        tag.setPremiered(known['p'])
    if item['channel']:
        tag.setStudios([item['channel']])
        tag.setDirectors([item['channel']])
    if item['duration']:
        tag.setDuration(item['duration'])
        if 0 < item['watched_pct'] < threshold:
            tag.setResumePoint(item['duration'] * item['watched_pct'] / 100.0, item['duration'])
    if item['watched_pct'] >= threshold:
        tag.setPlaycount(1)
    if item['badges']:
        tag.setTags(item['badges'])
    if item['views']:
        tag.setVotes(c_int(item['views']))


# Codec families -> their names in the Preferred video codec setting.
CODEC_NAMES = {'avc1': 30060, 'vp9': 30058, 'av01': 30059}


def format_bitrate(bits_per_second):
    """'2.1 Mbps', '850 kbps'."""
    if bits_per_second >= 1000000:
        return '%.1f Mbps' % (bits_per_second / 1000000.0)
    return '%d kbps' % round(bits_per_second / 1000.0)


def quality_label(height, fps, hdr=False, codec=None, bitrate=0):
    """'1080p60 HDR', '720p' as YouTube names a quality, then the codec and bitrate when known:
    '1080p • VP9 • 2.1 Mbps'."""
    parts = ['%dp%s%s' % (height, fps if fps > 30 else '', ' HDR' if hdr else '')]
    if codec:
        parts.append(kodi.string(CODEC_NAMES[codec]) if codec in CODEC_NAMES else codec)
    if bitrate:
        parts.append(format_bitrate(bitrate))
    return ' • '.join(parts)


def _select_quality(labels):
    """The index of the quality the viewer picks, -1 when they cancel."""
    return xbmcgui.Dialog().select(kodi.string(30185), labels)


def _sort_methods(items, dated):
    """Kodi's sort options for a listing: YouTube's order and the title always; with videos listed, also
    the upload date (when any listed video's is known), duration, channel and whether it was watched."""
    methods = [xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL]
    if any(i.get('kind') == 'video' for i in items):
        if dated:
            methods.append(xbmcplugin.SORT_METHOD_DATE)
        methods.extend((xbmcplugin.SORT_METHOD_DURATION, xbmcplugin.SORT_METHOD_STUDIO,
                        xbmcplugin.SORT_METHOD_PLAYCOUNT))
    return methods


def _video_menu(item, video_id, channel_id):
    """A video's context menu: play at a chosen quality, its channel, related videos, details and chapters."""
    menu = []
    if not item.get('upcoming'):
        menu.append((kodi.string(30184), 'PlayMedia(%s)' % url_for('play', v=video_id, choose=1)))
    if channel_id:
        menu.append((kodi.string(30103), 'Container.Update(%s)' % url_for(
            'browse', id=channel_id, title=item['channel'])))
    menu.append((kodi.string(30104), 'Container.Update(%s)' % url_for('related', v=video_id)))
    menu.append((kodi.string(30105), 'RunPlugin(%s)' % url_for('details', v=video_id)))
    if not item['live'] and not item['short']:
        menu.append((kodi.string(30139), 'RunPlugin(%s)' % url_for('chapters', v=video_id)))
    return menu


def _device_code_message(code):
    """Where to go and what code to enter, for the sign-in dialog."""
    url = code.get('verification_url') or 'youtube.com/activate'
    url = url.replace('https://', '').replace('http://', '').replace('www.', '')
    go_to = kodi.formatted(30110, url)
    return '%s\n[B][COLOR yellow]%s[/COLOR][/B]\n%s' % (go_to, code['user_code'], kodi.string(30111))


def url_for(route, **params):
    params = {k: v for k, v in params.items() if v not in (None, '')}
    return BASE_URL + route + ('?' + urllib.parse.urlencode(params) if params else '')


ROUTES = {
    '': 'root',
    'browse': 'browse',
    'shelf': 'shelf',
    'page': 'page',
    'search': 'search',
    'search/new': 'search_new',
    'search/remove': 'search_remove',
    'related': 'related',
    'play': 'play',
    'play_playlist': 'play_playlist',
    'shorts': 'shorts',
    'details': 'details',
    'chapters': 'chapters',
    'pin': 'pin',
    'unpin': 'unpin',
    'accounts': 'accounts_menu',
    'account/sign_in': 'sign_in',
    'account/switch': 'switch_account',
    'account/sign_out': 'sign_out',
    'menu/customise': 'customise_menu',
    'menu/reset': 'reset_menu',
    'maintenance': 'maintenance',
    'tv': 'tv_interface',
}


class Plugin(pages.Pages):
    def __init__(self, argv):
        parsed = urllib.parse.urlparse(argv[0])
        self.route = parsed.path.strip('/')
        self.handle = int(argv[1]) if len(argv) > 1 and argv[1].lstrip('-').isdigit() else -1
        query = argv[2][1:] if len(argv) > 2 and argv[2].startswith('?') else (argv[2] if len(argv) > 2 else '')
        self.params = dict(urllib.parse.parse_qsl(query))
        self.route, self.params = compat.translate(self.route, self.params, ROUTES)
        super().__init__(InnerTube())
        self.banners = art.Banners()
        self.fanart = ''  # a channel page's banner, for everything listed on it
        self.dated = False  # a listed video's upload date is known, so sorting by date means something
        self.descriptions = descriptions.Descriptions()

    def dispatch(self):
        name = ROUTES.get(self.route)
        if name is None:
            kodi.log('unknown route %s' % self.route)
            return self._end(False)
        handler = getattr(self, name)
        # When Kodi loses its navigation history (e.g. after playback) it builds a ".." path by
        # dropping the query string, e.g. plugin://.../browse/. Show the main menu instead of failing.
        required = {'browse': 'id', 'shelf': 'src', 'page': 'ctoken', 'related': 'v', 'play': 'v',
                    'play_playlist': 'list', 'pin': 'id', 'unpin': 'id',
                    'chapters': 'v', 'maintenance': 'what'}
        if self.route in required and not self.params.get(required[self.route]):
            kodi.log('route %s without %s, showing main menu' % (self.route, required[self.route]))
            handler = self.root
        try:
            handler()
        except (InnerTubeError, http.HTTPError) as exc:
            kodi.log('InnerTube error on %s: %s' % (self.route, exc))
            self._notify(error_message(exc), error=True)
            self._end(False)
        except auth.AuthError:
            self._notify(kodi.string(30132), error=True)
            self._end(False)

    def _add_sort_methods(self, methods):
        for method in methods:
            xbmcplugin.addSortMethod(self.handle, method)

    def _end(self, succeeded=True, cache=False):
        if self.handle >= 0:
            xbmcplugin.endOfDirectory(self.handle, succeeded=succeeded, cacheToDisc=cache)

    @staticmethod
    def _notify(message, error=False):
        xbmcgui.Dialog().notification(kodi.ADDON.getAddonInfo('name'), message,
                                      xbmcgui.NOTIFICATION_ERROR if error else xbmcgui.NOTIFICATION_INFO, 4000)

    def _add(self, url, li, folder):
        xbmcplugin.addDirectoryItem(self.handle, url, li, isFolder=folder)

    def root(self):
        kodi.Cache.prune()
        self._maybe_whos_watching()
        entries, channels = self.menu_entries()
        for entry in entries:
            self._add_menu_entry(entry)
        if kodi.setting_bool('show_channels'):
            if kodi.setting_bool('sort_subscriptions'):
                channels = sorted(channels, key=lambda e: e['title'].lower())
            for entry in channels:
                self._add_menu_entry(entry)
        li = xbmcgui.ListItem(kodi.string(30167), offscreen=True)
        li.setArt({'icon': icons.TV_INTERFACE, 'thumb': icons.TV_INTERFACE})
        # Opens a window rather than listing anything, so not a folder (see _add_accounts_entry).
        self._add(url_for('tv'), li, self._browsed_from_outside())
        if kodi.setting_bool('show_accounts'):
            self._add_accounts_entry()
        xbmcplugin.setContent(self.handle, 'files')
        self._add_sort_methods(_sort_methods([], False))
        self._end()

    def _add_accounts_entry(self):
        _, account = auth.active_account()
        li = xbmcgui.ListItem(kodi.string(30108), offscreen=True)
        li.setLabel2(account.get('name') or '' if account else kodi.string(30123))
        li.getVideoInfoTag().setPlot(kodi.formatted(30112, account.get('name') or '') if account
                                     else kodi.string(30123))
        li.setArt({'icon': icons.media('user.png'), 'thumb': icons.media('user.png')})
        # Only opens a dialog: as a folder its failed listing made Kodi leave the add-on (and re-run it on Back).
        self._add(url_for('accounts'), li, self._browsed_from_outside())

    @staticmethod
    def _browsed_from_outside():
        """True when the menu is read from outside a media window, e.g. by a skin's shortcut picker or a
        home widget. Those only offer folders, so the window-opening entries are listed as folders there;
        opened from a shortcut (ActivateWindow(...,return)) their failed listing just goes back."""
        return not xbmc.getCondVisibility('Window.IsMedia')

    def _add_menu_entry(self, entry):
        target = entry['target']
        if entry['id'] == 'search':
            url = url_for('search')
            default = 'DefaultAddonsSearch.png'
        elif entry['id'] == 'shorts':
            url = url_for('shorts', params=target.get('params'))
            default = 'DefaultVideo.png'
        elif target['type'] == 'browse':
            url = url_for('browse', id=target['browse_id'], params=target.get('params'), title=entry['title'])
            default = 'DefaultFolder.png'
        else:
            return
        li = xbmcgui.ListItem(entry['title'], offscreen=True)
        thumb = entry.get('thumb') or icons.menu_entry(entry, default)
        li.setArt({'icon': thumb, 'thumb': thumb})
        menu = []
        if target['type'] == 'browse' and (target.get('browse_id') or '').startswith('UC'):
            if entry.get('pinned'):
                menu.append((kodi.string(30107), 'RunPlugin(%s)' % url_for('unpin', id=entry['id'])))
            else:
                menu.append((kodi.string(30106), 'RunPlugin(%s)' % url_for(
                    'pin', id=entry['id'], title=entry['title'], thumb=entry.get('thumb'))))
        menu.append((kodi.string(30011), 'RunPlugin(%s)' % url_for('menu/customise')))
        li.addContextMenuItems(menu)
        # Shorts starts playback rather than listing anything: as a folder its failed listing made Kodi
        # leave the add-on, so run it as a script.
        self._add(url, li, entry['id'] != 'shorts')

    def _maybe_whos_watching(self):
        if not kodi.setting_bool('whos_watching') or not auth.accounts():
            return
        window = xbmcgui.Window(10000)
        if window.getProperty('youtube.whos_watching'):
            return
        window.setProperty('youtube.whos_watching', '1')
        self._choose_account(kodi.string(30114), allow_add=False)

    def browse(self):
        browse_id = self.params.get('id')
        if is_mix(browse_id[2:]):
            playlist_id = browse_id[2:]
            items, token = self._mix_items(playlist_id, self.params.get('ctoken'))
            items, token = self._more_pages('next', items, token,
                                            lambda page: self._mix_batch(page, playlist_id))
            self._render_items(items, browse_id=browse_id)
            if token:
                self._add_next_url(url_for('browse', id=browse_id, ctoken=token, title=self.params.get('title'),
                                           n=self._page_number() + 1))
            self._finish_listing(items)
            return
        desc = {'ep': 'browse', 'id': browse_id, 'params': self.params.get('params')}
        self.render(desc, browse_id=browse_id)

    def _mix_items(self, playlist_id, token=None):
        """A Mix (RD...) is generated per viewer and has no playlist page: browse VLRD... is rejected.
        The TV app lists it in the watch-next panel instead, so take the items that belong to it.
        Returns (items, continuation token for the next batch or None)."""
        desc = {'ep': 'next', 'ctoken': token} if token else {'ep': 'next', 'list': playlist_id}
        return self._mix_batch(parser.parse_page(self.fetch(desc)), playlist_id)

    @staticmethod
    def _mix_batch(page, playlist_id):
        for shelf in page['shelves']:
            items = [i for i in shelf['items']
                     if i['kind'] == 'video' and i['target'].get('playlist_id') == playlist_id]
            if items:
                return items, shelf['continuation']
        return [], None

    def _pages_per_listing(self):
        return min(max(kodi.setting_int('pages_per_listing') or 1, 1), 5)

    def _page_number(self):
        try:
            return int(self.params.get('n') or 1)
        except ValueError:
            return 1

    def _more_pages(self, ep, items, token, batch=None):
        """Follow the continuation until the listing holds pages_per_listing pages, so each listing
        is longer and needs fewer Next page clicks. Returns (items, token for the page after)."""
        batch = batch or pages.list_batch
        seen = {i.get('id') for i in items if i.get('id')}
        for _ in range(self._pages_per_listing() - 1):
            if not token:
                break
            try:
                more, next_token = batch(parser.parse_page(self.fetch({'ep': ep, 'ctoken': token})))
            except (InnerTubeError, http.HTTPError) as exc:
                kodi.log('stopped loading more pages: %s' % exc)  # keep what loaded, page on from here
                break
            # Pages can overlap where they meet.
            fresh = [i for i in more if not i.get('id') or i['id'] not in seen]
            seen.update(i['id'] for i in fresh if i.get('id'))
            items = items + fresh
            token = next_token if next_token != token else None
        return items, token

    def _more_rows(self, ep, token, titles):
        """Add the rows of the next few pages as folders too. A page of rows (Home, the topic pages)
        holds only three or four of them. Returns the token for the page after, or None."""
        for _ in range(max(self._pages_per_listing(), ROW_PAGES) - 1):
            if not token:
                break
            desc = {'ep': ep, 'ctoken': token}
            try:
                page = parser.parse_page(self.fetch(desc))
            except (InnerTubeError, http.HTTPError) as exc:
                kodi.log('stopped loading more rows: %s' % exc)  # keep what loaded, page on from here
                break
            for index, shelf in enumerate(pages.visible_shelves(page)):
                if shelf['title'] and shelf['title'] in titles:
                    continue  # a row repeated where pages meet
                titles.add(shelf['title'])
                self._add_shelf_folder(desc, index, shelf)
            token = page['continuation'] if page['continuation'] != token else None
        return token

    def page(self):
        """A continuation page: ?ep=browse|search|next&ctoken=..."""
        desc = {'ep': self.params['ep'], 'ctoken': self.params['ctoken']}
        self.render(desc, browse_id=self.params.get('bid'))

    def shelf(self):
        desc = json.loads(self.params['src'])
        page = parser.parse_page(self.fetch(desc))
        shelves = pages.visible_shelves(page)
        index = int(self.params.get('i', 0))
        if index >= len(shelves):
            return self._end(False)
        shelf = shelves[index]
        self._use_channel_fanart(desc.get('id'), page['header'])
        items, token = self._more_pages(desc['ep'], shelf['items'], shelf['continuation'])
        self._render_items(items, browse_id=desc.get('id'))
        if token:
            self._add_next(desc['ep'], token, desc.get('id'))
        self._finish_listing(items)

    def related(self):
        desc = {'ep': 'next', 'v': self.params['v']}
        page = parser.parse_page(self.fetch(desc))
        items = [i for s in page['shelves'] for i in s['items']]
        self._render_items(items)
        self._finish_listing(items)

    def render(self, desc, browse_id=None):
        page = parser.parse_page(self.fetch(desc))
        self._use_channel_fanart(browse_id, page['header'])
        if page['header']:
            self._add_header(page['header'], header_playlist(browse_id))
        tabs = page['tabs']
        if tabs and self.params.get('tabs'):
            return self._render_tabs(tabs)
        if len(tabs) > 2 and not desc.get('params'):
            # Like the TV app: show the selected tab ("All") and put the other tabs in one folder.
            self._add_channels_folder([t for t in tabs if not t.get('selected')], browse_id, desc.get('params'))
        shelves = self._listing_shelves(desc, page)
        rendered = self._render_shelves(desc, page, shelves, browse_id)
        if not tabs and not shelves and not page['header']:
            self._notify(self._empty_message(page, browse_id))
        self._finish_listing(rendered or [{'kind': 'folder'}])

    def _render_tabs(self, tabs):
        """The secondary navigation on its own (e.g. every subscribed channel)."""
        tabs = [t for t in tabs if not t.get('selected')]
        if kodi.setting_bool('sort_subscriptions'):
            tabs = sorted(tabs, key=lambda t: t['title'].lower())
        self.banners.fetch_batch([channel_of(tab) for tab in tabs])
        for tab in tabs:
            self._add_folder_item(tab)
        self._finish_listing([{'kind': 'folder'}])

    def _add_channels_folder(self, others, browse_id, params):
        label = kodi.string(30134)
        li = xbmcgui.ListItem('[B]%s[/B] (%d)' % (label, len(others)), offscreen=True)
        li.setArt({'icon': icons.media('channels.png'), 'thumb': icons.media('channels.png')})
        li.getVideoInfoTag().setPlot(', '.join(t['title'] for t in others[:40]))
        li.setProperty('SpecialSort', 'top')
        self._add(url_for('browse', id=browse_id, params=params, tabs=1), li, True)

    @staticmethod
    def _listing_shelves(desc, page):
        """The rows to show: on a continuation page, only those it continues."""
        shelves = pages.visible_shelves(page)
        if desc.get('ctoken'):
            continued = pages.continued_rows(page)
            shelves = [s for s in shelves if s in continued]
        return shelves

    @staticmethod
    def _flatten_shelves(shelves):
        """Whether to list every row's items as one list rather than a folder per row. Untitled rows
        (the Subscriptions feed, a channel's uploads) read better as one list."""
        if len(shelves) == 1:
            return True
        untitled = sum(1 for s in shelves if not s['title'])
        return bool(shelves) and (not kodi.setting_bool('shelves_as_folders') or untitled * 2 >= len(shelves))

    def _render_shelves(self, desc, page, shelves, browse_id):
        """List the rows; returns the items listed when they were flattened into one list."""
        if self._flatten_shelves(shelves):
            # One list; with search's extra rows flattened in, the results shelf is the one that pages.
            items, token = self._more_pages(desc['ep'], [i for s in shelves for i in s['items']],
                                            pages.paged_token(shelves, page))
            rendered = self._render_items(items, browse_id=browse_id)
        else:
            for index, shelf in enumerate(shelves):
                self._add_shelf_folder(desc, index, shelf)
            # Rows as folders: the continuation brings more rows, not more items.
            token = page['continuation'] and self._more_rows(desc['ep'], page['continuation'],
                                                             {s['title'] for s in shelves})
            rendered = []
        if token:
            self._add_next(desc['ep'], token, browse_id)
        return rendered

    def _empty_message(self, page, browse_id):
        """YouTube's own words for an empty page, else why it's empty."""
        if page.get('message'):
            return page['message']
        if (browse_id or '').startswith('FE') and not self.api.signed_in():
            return kodi.string(30125)
        return kodi.string(30124)

    def _finish_listing(self, items):
        videos = sum(1 for i in items if i.get('kind') == 'video')
        # 'videos' keeps skins on 16:9 layouts; 'movies' puts the thumbnails in 2:3 poster frames.
        xbmcplugin.setContent(self.handle, 'videos' if videos and videos >= len(items) / 2 else 'files')
        self._add_sort_methods(_sort_methods(items, self.dated))
        self._end()

    def _add_next(self, ep, token, browse_id=None):
        self._add_next_url(url_for('page', ep=ep, ctoken=token, bid=browse_id, n=self._page_number() + 1))

    def _add_next_url(self, url):
        """The Next page item, numbered so it's clear how far in the listing is."""
        number = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get('n', ['2'])[0]
        li = xbmcgui.ListItem('%s (%s)' % (kodi.string(30102), number), offscreen=True)
        li.setArt({'icon': 'DefaultFolder.png'})
        li.setProperty('SpecialSort', 'bottom')
        self._add(url, li, True)

    def _add_shelf_folder(self, desc, index, shelf):
        title = shelf['title'] or kodi.string(30133) or shelf['items'][0]['title']
        li = xbmcgui.ListItem(title, offscreen=True)
        first = shelf['items'][0]
        art = first.get('thumb') or 'DefaultFolder.png'
        li.setArt({'icon': 'DefaultFolder.png', 'thumb': art, 'fanart': self.fanart or art})
        tag = li.getVideoInfoTag()
        tag.setTitle(title)
        tag.setPlot('\n'.join('• ' + i['title'] for i in shelf['items'][:12]))
        # Prefer the shelf's own full page (Library: History -> FEhistory, Liked videos -> VLLL), or the
        # playlist every item belongs to (Watch later -> VLWL); otherwise open the shelf itself.
        endpoint = shelf.get('endpoint') or {}
        playlists = {i['target'].get('playlist_id') for i in shelf['items'] if i['kind'] == 'video'}
        # A channel's Videos / Popular videos / Playlists rows point back at the channel with a web tab's
        # params, which the TV client ignores: it returns the channel page again. The row pages by itself.
        same_page = endpoint.get('browse_id') == desc.get('id') and not desc.get('ctoken')
        if endpoint.get('type') == 'browse' and endpoint.get('browse_id') and not same_page:
            url = url_for('browse', id=endpoint['browse_id'], params=endpoint.get('params'), title=title)
        elif endpoint.get('type') == 'search' and endpoint.get('query'):
            url = url_for('search', q=endpoint['query'], params=endpoint.get('params'))
        elif len(playlists) == 1 and None not in playlists and not is_mix(next(iter(playlists))):
            url = url_for('browse', id='VL' + next(iter(playlists)), title=title)
        else:
            url = url_for('shelf', src=json.dumps(desc, sort_keys=True), i=index)
        self._add(url, li, True)

    def _add_header(self, header, playlist_id=None):
        li = xbmcgui.ListItem('[B]%s[/B]' % header['title'], offscreen=True)
        tag = li.getVideoInfoTag()
        tag.setTitle(header['title'])
        tag.setPlot('\n\n'.join(line for line in header['plot_lines'] if line))
        art = {'thumb': header.get('thumb'), 'icon': header.get('thumb'),
               'fanart': header.get('fanart') or header.get('thumb')}
        li.setArt({k: v for k, v in art.items() if v})
        li.setProperty('SpecialSort', 'top')
        li.setProperty('IsPlayable', 'false')
        self._add(url_for('details', header=json.dumps({'title': header['title'], 'plot': tag.getPlot(),
                                                        'thumb': header.get('thumb'),
                                                        'fanart': header.get('fanart')}),
                          list=playlist_id), li, False)

    def _render_items(self, items, browse_id=None):
        hide_shorts = kodi.setting_bool('hide_shorts')
        keep = pages.item_filter(browse_id)
        threshold = pages.watched_threshold()
        self._prefetch(items, hide_shorts)
        shown = []
        for item in items:
            if not keep(item):
                continue
            if item['kind'] == 'video':
                self._add_video(item, threshold)
            else:
                self._add_folder_item(item)
            shown.append(item)
        return shown

    def _prefetch(self, items, hide_shorts):
        """Before anything is drawn: the banners of channels not seen before and, when turned on, the
        descriptions of listed videos, all looked up at once and in parallel."""
        banner_lookup = self._start_banner_lookup([channel_of(item) for item in items])
        if describe.enabled():
            self._fetch_descriptions(items, hide_shorts)
        if banner_lookup:
            banner_lookup.join()
        if not self.fanart:
            self._fetch_banners_named_by_descriptions(items)

    def _start_banner_lookup(self, channels):
        """Look up unknown channels' banners in the background. Returns the thread, or None when there's
        nothing to look up or a channel page's own banner already covers everything."""
        if self.fanart or not self.banners.unknown(channels):
            return None
        lookup = threading.Thread(target=self.banners.fetch_all, args=(channels,), name='youtube-art')
        lookup.start()
        return lookup

    def _fetch_descriptions(self, items, hide_shorts):
        """Read the watch pages of listed videos not read yet ('w' marks a full read). Upcoming
        streams have nothing to read, and hidden Shorts aren't shown."""
        wanted = [video_id_of(item) for item in items
                  if item['kind'] == 'video' and not item.get('upcoming') and not (hide_shorts and item['short'])]
        missing = [v for v in wanted if v and not (self.descriptions.get(v) or {}).get('w')]
        if missing:
            describe.fetch_all(missing, self.descriptions)

    def _fetch_banners_named_by_descriptions(self, items):
        """Some tiles (Home's rows) don't name their channel; the watch pages just read do ('c')."""
        named = [(self.descriptions.get(video_id_of(item)) or {}).get('c')
                 for item in items if item['kind'] == 'video' and not item.get('channel_id')]
        if self.banners.unknown(named):
            self.banners.fetch_all(named)

    def _use_channel_fanart(self, browse_id, header):
        """On a channel's pages, its banner is the fanart for everything listed."""
        if not (browse_id or '').startswith('UC'):
            return
        if header and header['kind'] == 'channel':
            self.banners.remember(browse_id, header.get('fanart'))
        self.fanart = self.banners.get(browse_id)

    def _channel_fanart(self, channel_id):
        return self.fanart or self.banners.get(channel_id)

    def _add_video(self, item, threshold):
        video_id = video_id_of(item)
        if not video_id:
            return
        known = self.descriptions.get(video_id)
        channel_id = item['channel_id'] or (known or {}).get('c')
        li = xbmcgui.ListItem(video_label(item), offscreen=True)
        _set_video_tag(li.getVideoInfoTag(), item, known, threshold)
        if known and known.get('p'):
            # The upload date (YYYY-MM-DD) is what Kodi's Date sort orders by.
            li.setDateTime(known['p'] + 'T00:00:00Z')
            self.dated = True
        li.setArt({'thumb': item['thumb'], 'icon': item['thumb'],
                   'fanart': self._channel_fanart(channel_id) or item['thumb'], 'landscape': item['thumb']})
        li.setProperty('IsPlayable', 'true')
        li.setProperty('youtube.video_id', video_id)
        li.addContextMenuItems(_video_menu(item, video_id, channel_id))
        self._add(url_for('play', v=video_id), li, False)

    def _add_folder_item(self, item):
        url = _folder_url(item)
        if not url:
            return
        li = xbmcgui.ListItem(item['title'], offscreen=True)
        tag = li.getVideoInfoTag()
        tag.setTitle(item['title'])
        tag.setPlot(_folder_plot(item))
        thumb = item.get('thumb') or 'DefaultFolder.png'
        li.setArt({'thumb': thumb, 'icon': thumb,
                   'fanart': self._channel_fanart(channel_of(item)) or item.get('thumb') or ''})
        menu = _folder_menu(item)
        if menu:
            li.addContextMenuItems(menu)
        self._add(url, li, True)

    def search(self):
        query = self.params.get('q')
        if query:
            if not self.params.get('params'):  # refinements like "Recently uploaded" aren't the user's searches
                self._remember_search(query)
            self.render({'ep': 'search', 'q': query, 'params': self.params.get('params')})
            return
        li = xbmcgui.ListItem('[B]%s[/B]' % kodi.string(30101), offscreen=True)
        li.setArt({'icon': icons.media('new_search.png'), 'thumb': icons.media('new_search.png')})
        # Not a folder: Kodi runs it as a script, so the Container.Update to the results isn't
        # undone by Kodi going back from a failed folder.
        self._add(url_for('search/new'), li, False)
        for past in self._searches():
            li = xbmcgui.ListItem(past, offscreen=True)
            li.setArt({'icon': icons.media('search.png'), 'thumb': icons.media('search.png')})
            li.addContextMenuItems([(kodi.string(30128), 'RunPlugin(%s)' % url_for('search/remove', q=past))])
            self._add(url_for('search', q=past), li, True)
        self._add_sort_methods(_sort_methods([], False))
        self._end()

    def search_new(self):
        query = xbmcgui.Dialog().input(kodi.string(30100))
        self._end(False)
        if query:
            xbmc.executebuiltin('Container.Update(%s)' % url_for('search', q=query))

    def search_remove(self):
        self._forget_search(self.params.get('q'))
        xbmc.executebuiltin('Container.Refresh')

    def play(self):
        video_id = self.params['v']
        try:
            resp, client = self.api.player(video_id)
        except (InnerTubeError, http.HTTPError) as exc:
            kodi.log('no streams for %s: %s' % (video_id, exc))
            return self._fail_resolve(_player_error_message(exc))
        live = _is_live(resp)
        if self.params.get('choose'):
            path, mime = self._chosen_source(video_id, resp, client['ua'], live)
            if path is False:  # the viewer cancelled the choice
                xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem(offscreen=True))
                return None
        else:
            path, mime = self._stream_source(video_id, resp, client['ua'], live)
        if not path:
            return self._fail_resolve(kodi.string(30120))
        li = _stream_item(path, mime, client['ua'], live)
        if not self.params.get('choose'):
            _cap_resolution(li)
        self._apply_details(li, parser.video_details(resp))
        if not live:
            sponsorblock.apply(li, video_id)
        if self.params.get('t'):  # start part way in (a chapter, or a start time in the path)
            li.setProperty('StartOffset', self.params['t'])
            playback.request(video_id, self.params['t'])
        if self.api.signed_in() and kodi.setting_bool('report_history'):
            history.publish(video_id, path)
        xbmcplugin.setResolvedUrl(self.handle, True, li)

    def _fail_resolve(self, message):
        self._notify(message, error=True)
        xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem(offscreen=True))

    def _stream_source(self, video_id, resp, ua, live):
        """(path, mime) to play: the local DASH manifest, else YouTube's HLS manifest, else (None, None)."""
        if not live:
            path = self._serve_manifest(video_id, resp, ua)
            if path:
                return path, DASH_MIME
        hls = resp.get('streamingData', {}).get('hlsManifestUrl')
        if hls:
            return hls, HLS_MIME
        return None, None

    def _chosen_source(self, video_id, resp, ua, live):
        """Like _stream_source, at a quality the viewer picks: a DASH manifest of only that quality, or a live
        stream's HLS playlist cut down to that variant. (False, None) when they cancel. With nothing to
        choose from, it plays as _stream_source would."""
        if live:
            url = resp.get('streamingData', {}).get('hlsManifestUrl')
            playlist = self._hls_playlist(url, ua)
            options = hls.variants(playlist, url) if playlist else []
            if options:
                index = _select_quality([quality_label(height, fps, bitrate=rate) for height, fps, _, rate in options])
                if index < 0:
                    return False, None
                path = self._serve_hls(video_id, hls.keep_variant(playlist, url, options[index][2]))
                if path:
                    return path, HLS_MIME
        else:
            formats = resp.get('streamingData', {}).get('adaptiveFormats', [])
            options = mpd.qualities(formats, kodi.setting('codec') or 'any', kodi.setting_bool('allow_hdr'))
            if options:
                index = _select_quality([quality_label(*option, bitrate=mpd.bitrate_of(formats, option))
                                         for option in options])
                if index < 0:
                    return False, None
                path = self._serve_manifest(video_id, resp, ua, quality=options[index])
                if path:
                    return path, DASH_MIME
        return self._stream_source(video_id, resp, ua, live)

    @staticmethod
    def _hls_playlist(url, ua):
        """A live stream's HLS master playlist, '' when it can't be read."""
        if not url:
            return ''
        try:
            _, body = http.request(url, headers={'User-Agent': ua})
        except http.HTTPError as exc:
            kodi.log('no HLS playlist: %s' % exc)
            return ''
        return body.decode('utf-8', 'replace')

    @staticmethod
    def _serve_hls(video_id, playlist):
        """Write an HLS master playlist for the local server and return its URL, or None without the server."""
        port = xbmcgui.Window(10000).getProperty(http.PORT_PROPERTY)
        if not port:
            kodi.log('manifest server not running, playing every quality')
            return None
        with open(kodi.temp_file('%s.m3u8' % video_id), 'w', encoding='utf-8') as handle:
            handle.write(playlist)
        return 'http://127.0.0.1:%s/hls/%s.m3u8' % (port, video_id)

    def _serve_manifest(self, video_id, resp, ua, quality=None):
        """Write the DASH manifest for the local server and return its URL, or None. `quality` (an
        mpd.quality_of() tuple) limits it to that quality; otherwise it holds every quality and codec, and
        the Maximum quality setting goes to ISA (see _cap_resolution)."""
        port = xbmcgui.Window(10000).getProperty(http.PORT_PROPERTY)
        subs = mpd.subtitle_tracks(resp, kodi.setting_bool('subs_asr'), _subtitle_languages(self.api.hl))
        if subs and port:
            _proxy_subtitles(video_id, subs, ua, port)
        manifest = mpd.build(resp, max_height=0 if quality else manifest_height_cap(kodi.setting_int('max_quality')),
                             codec=kodi.setting('codec') or 'any', allow_hdr=kodi.setting_bool('allow_hdr'),
                             audio_pref=kodi.setting('audio_track') or 'original', ui_lang=self.api.hl,
                             subtitles=subs, quality=quality, rate=_rate_kind(resp, ua) if port else None)
        if not manifest:
            return None
        if not port:
            kodi.log('manifest server not running, falling back to HLS')
            return None
        with open(kodi.temp_file('%s.mpd' % video_id), 'w', encoding='utf-8') as handle:
            handle.write(manifest)
        return 'http://127.0.0.1:%s/mpd/%s.mpd' % (port, video_id)

    def play_playlist(self):
        """Play a playlist (or a mix) as Kodi's video playlist, in the order asked for, from the video
        asked for."""
        playlist_id = self.params['list']
        if self.handle >= 0:
            # Started as a playable item (the Play button in a page header's info dialog): let Kodi's own
            # attempt fail now, before the playlist starts, or Kodi counts the failure against the
            # playlist and skips its first video.
            xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem(offscreen=True))
        items = self._playlist_videos(playlist_id)
        if not items:
            self._notify(kodi.string(30124))
            return
        self._end(False)
        videos = [(video_id_of(item), item['title'], item['thumb']) for item in items]
        start = self.params.get('v')
        _order_videos(videos, self.params.get('order'), start)
        position = next((i for i, video in enumerate(videos) if video[0] == start), 0)
        self._play_videos(videos, position)

    def _playlist_videos(self, playlist_id):
        """A playlist's video tiles. Mixes (RD...) have no playlist page; they come from the watch page."""
        if is_mix(playlist_id):
            return self._mix_items(playlist_id)[0]
        page = parser.parse_page(self.fetch({'ep': 'browse', 'id': 'VL' + playlist_id}))
        return [i for s in page['shelves'] for i in s['items'] if i['kind'] == 'video']

    def shorts(self):
        """Like the TV app's Shorts button: start playing the Shorts feed as a playlist."""
        self._end(False)
        videos = self.api.shorts(self.params.get('params'))
        if not videos:
            self._notify(kodi.string(30124))
            return
        self._play_videos((video_id, video_id, thumb) for video_id, thumb in videos)

    @staticmethod
    def _play_videos(videos, position=0):
        """Play (video_id, title, thumb) entries as Kodi's video playlist, from the one at `position`."""
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()
        for video_id, title, thumb in videos:
            li = xbmcgui.ListItem(title, offscreen=True)
            li.setArt({'thumb': thumb, 'icon': thumb})
            li.getVideoInfoTag().setTitle(title)
            li.setProperty('IsPlayable', 'true')
            playlist.add(url_for('play', v=video_id), li)
        xbmc.Player().play(playlist, startpos=position)

    def _apply_details(self, li, info):
        # Keep the description, so the video's plot in listings has it from now on.
        self.descriptions.remember_details(info)
        _set_details_tag(li.getVideoInfoTag(), info)
        thumb = 'https://i.ytimg.com/vi/%s/maxresdefault.jpg' % info['video_id'] if info['video_id'] else info['thumb']
        li.setArt({'thumb': info['thumb'] or thumb, 'icon': info['thumb'] or thumb,
                   'fanart': self._channel_fanart(info.get('channel_id')) or thumb})

    def chapters(self):
        """Pick a chapter: seek to it when this video is playing, otherwise start the video there."""
        video_id = self.params['v']
        found = parser.chapters(self.fetch({'ep': 'next', 'v': video_id}))
        if not found:
            self._notify(kodi.string(30140))
            return
        items = []
        for chapter in found:
            li = xbmcgui.ListItem(chapter['title'], format_time(chapter['start']), offscreen=True)
            li.setArt({'thumb': chapter['thumb'], 'icon': chapter['thumb']})
            items.append(li)
        player = xbmc.Player()
        playing = player.isPlayingVideo() and video_id in player.getPlayingFile()
        current = player.getTime() if playing else -1
        preselect = max([i for i, c in enumerate(found) if c['start'] <= current] or [0])
        choice = xbmcgui.Dialog().select(kodi.string(30139), items, preselect=preselect,
                                         useDetails=True)
        if choice < 0:
            return
        start = found[choice]['start']
        if playing:
            player.seekTime(start)
        else:
            li = xbmcgui.ListItem(found[choice]['title'], offscreen=True)
            li.setProperty('IsPlayable', 'true')
            li.setProperty('StartOffset', '%.3f' % start)
            player.play(url_for('play', v=video_id, t='%.3f' % start), li)

    def details(self):
        if self.params.get('header'):
            self._header_details(json.loads(self.params['header']))
            return
        video_id = self.params['v']
        info = parser.video_details(*self._fetch_details(video_id))
        info['video_id'] = info['video_id'] or video_id
        li = xbmcgui.ListItem(info['title'], offscreen=True)
        self._apply_details(li, info)
        li.setPath(url_for('play', v=video_id))
        li.setProperty('IsPlayable', 'true')
        xbmcgui.Dialog().info(li)

    def _header_details(self, header):
        li = xbmcgui.ListItem(header['title'], offscreen=True)
        tag = li.getVideoInfoTag()
        tag.setTitle(header['title'])
        tag.setPlot(header['plot'])
        li.setArt({k: v for k, v in (('thumb', header.get('thumb')), ('fanart', header.get('fanart'))) if v})
        # The info dialog always has a Play button; without a path it fails with "One or more items
        # failed to play". On a playlist or channel page it plays everything, like "Play all".
        if self.params.get('list'):
            li.setPath(url_for('play_playlist', list=self.params['list']))
        xbmcgui.Dialog().info(li)

    def _fetch_details(self, video_id):
        """(player response, watch page) for a video, behind a busy dialog. The player response only
        adds details (duration, tags), so the dialog still opens when YouTube refuses it."""
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        try:
            try:
                player_resp, _ = self.api.player(video_id)
            except InnerTubeError:
                player_resp = None
            return player_resp or {}, self.api.watch_page(video_id)
        finally:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')

    def tv_interface(self):
        from .tv import open_window

        if self.handle >= 0:
            # Opened as a folder: a home menu shortcut (ActivateWindow(Videos,...)) or a widget. Kodi gets no
            # listing, so it would show the Videos window behind the TV interface and again once it closes;
            # put Home in its place instead.
            self._end(False)
            xbmc.executebuiltin('ReplaceWindow(Home)')
        open_window()

    def pin(self):
        state = self._state()
        menu = state.setdefault('menu', {})
        pinned = [p for p in menu.get('pinned', []) if p['id'] != self.params['id']]
        pinned.append({'id': self.params['id'], 'title': self.params.get('title', ''),
                       'thumb': self.params.get('thumb', '')})
        menu['pinned'] = pinned
        self._save_state(state)
        self._notify(kodi.string(30119))

    def unpin(self):
        state = self._state()
        menu = state.setdefault('menu', {})
        menu['pinned'] = [p for p in menu.get('pinned', []) if p['id'] != self.params['id']]
        menu['order'] = [x for x in menu.get('order', []) if x != self.params['id']]
        self._save_state(state)
        xbmc.executebuiltin('Container.Refresh')

    def customise_menu(self):
        dialog = xbmcgui.Dialog()
        changed = False
        while True:
            choice = dialog.select(kodi.string(30011), [kodi.string(30116), kodi.string(30117), kodi.string(30122)])
            if choice == 0:
                changed |= self._choose_hidden()
            elif choice == 1:
                changed |= self._reorder()
            else:
                break
        if changed:
            self._notify(kodi.string(30119))
            xbmc.executebuiltin('Container.Refresh')

    def _choose_hidden(self):
        entries, _ = self.menu_entries(include_hidden=True)
        state = self._state()
        menu = state.setdefault('menu', {})
        hidden = set(menu.get('hidden', []))
        labels = [e['title'] for e in entries]
        preselect = [i for i, e in enumerate(entries) if e['id'] not in hidden]
        chosen = xbmcgui.Dialog().multiselect(kodi.string(30116), labels, preselect=preselect)
        if chosen is None:
            return False
        menu['hidden'] = [e['id'] for i, e in enumerate(entries) if i not in chosen]
        self._save_state(state)
        return True

    def _reorder(self):
        changed = False
        while True:
            entries, _ = self.menu_entries(include_hidden=True)
            labels = [e['title'] for e in entries]
            index = xbmcgui.Dialog().select(kodi.string(30121), labels)
            if index < 0:
                return changed
            target = xbmcgui.Dialog().select(kodi.formatted(30118, labels[index]),
                                             ['%d. %s' % (i + 1, label) for i, label in enumerate(labels)],
                                             preselect=index)
            if target < 0 or target == index:
                continue
            order = [e['id'] for e in entries]
            moved = order.pop(index)
            order.insert(target, moved)
            state = self._state()
            state.setdefault('menu', {})['order'] = order
            self._save_state(state)
            changed = True

    def maintenance(self):
        """Settings > Maintenance buttons: confirm, clear, and say what it freed."""
        entry = maintenance.ACTIONS.get(self.params['what'])
        if entry is None:
            return
        string_id, action = entry
        label = kodi.string(string_id)
        question = kodi.formatted(30157, label)
        if not xbmcgui.Dialog().yesno(kodi.ADDON.getAddonInfo('name'), question):
            return
        freed = action()
        kodi.log('maintenance: cleared %s (%d bytes)' % (self.params['what'], freed))
        if freed:
            cleared = '%s, %s' % (label, maintenance.human_size(freed))
            message = kodi.formatted(30158, cleared)
        else:
            message = kodi.string(30159)
        self._notify(message)

    def reset_menu(self):
        state = self._state()
        state['menu'] = {'pinned': state.get('menu', {}).get('pinned', [])}
        self._save_state(state)
        self._notify(kodi.string(30119))

    def accounts_menu(self):
        self._end(False)
        self._choose_account(kodi.string(30108), allow_add=True)

    def _choose_account(self, heading, allow_add):
        accounts = auth.accounts()
        active = auth.active_account()[0]
        labels = [('* ' if key == active else '') + name for key, name in accounts]
        labels.append(('* ' if active is None else '') + kodi.string(30115))
        if allow_add:
            labels.append(kodi.string(30109))
            if accounts:
                labels.append(kodi.string(30043))
        choice = xbmcgui.Dialog().select(heading, labels)
        if choice < 0:
            return
        if choice < len(accounts):
            auth.set_active(accounts[choice][0])
        elif choice == len(accounts):
            auth.set_active(None)
        elif choice == len(accounts) + 1:
            self.sign_in()
            return
        else:
            self.sign_out()
            return
        xbmc.executebuiltin('Container.Refresh')

    def switch_account(self):
        self._choose_account(kodi.string(30042), allow_add=True)

    def sign_in(self):
        try:
            code = auth.request_device_code()
        except Exception as exc:  # network or OAuth errors
            self._notify(kodi.formatted(30113, exc), error=True)
            return
        token = self._wait_for_approval(code)
        if token:
            self._add_signed_in_account(token)

    def _wait_for_approval(self, code):
        """Show the device code until the viewer approves it; returns the token, or None after
        cancelling, an error or the code expiring (the viewer has been told why)."""
        expires_in = int(code.get('expires_in', 1800))
        interval = max(int(code.get('interval', 5)), 2)
        deadline = time.time() + expires_in
        message = _device_code_message(code)
        # Only of the address Google gave, as given; never of the stand-in in _device_code_message
        qr_png = qr.image(code['verification_url']) if code.get('verification_url') else None
        progress = qr.Dialog(qr_png) if qr_png else xbmcgui.DialogProgress()
        progress.create(kodi.string(30109), message)
        monitor = xbmc.Monitor()
        try:
            while time.time() < deadline:
                if progress.iscanceled() or monitor.abortRequested():
                    return None
                progress.update(int((deadline - time.time()) / float(expires_in) * 100), message)
                if monitor.waitForAbort(interval):
                    return None
                try:
                    token = auth.poll_token(code['device_code'])
                except auth.AuthError as exc:
                    self._notify(kodi.formatted(30113, exc), error=True)
                    return None
                if token:
                    return token
        finally:
            progress.close()
        self._notify(kodi.string(30130), error=True)
        return None

    def _add_signed_in_account(self, token):
        account_id = auth.add_account(token)
        name = InnerTube().account_name() or kodi.formatted(30131, len(auth.accounts()))
        auth.rename_account(account_id, name)
        self._notify(kodi.formatted(30112, name))
        xbmc.executebuiltin('Container.Refresh')

    def sign_out(self):
        accounts = auth.accounts()
        if not accounts:
            return
        if len(accounts) == 1:
            index = 0 if xbmcgui.Dialog().yesno(kodi.string(30043), accounts[0][1]) else -1
        else:
            index = xbmcgui.Dialog().select(kodi.string(30043), [name for _, name in accounts])
        if index < 0:
            return
        auth.remove_account(accounts[index][0])
        self._notify(kodi.string(30123))
        xbmc.executebuiltin('Container.Refresh')


def run(argv):
    kodi.refresh()  # the module may still be loaded from an earlier run (reuselanguageinvoker)
    Plugin(argv).dispatch()
