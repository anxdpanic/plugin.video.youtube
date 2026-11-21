# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""Plugin entry: routes, directory listings, playback and the account/menu dialogs."""
import json
import random
import threading
import time
import urllib.parse

import xbmc
import xbmcgui
import xbmcplugin

from . import art, auth, describe, descriptions, history, http, kodi, maintenance, mpd, parser
from .innertube import InnerTube, InnerTubeError

BASE_URL = 'plugin://%s/' % kodi.ADDON_ID
PAGE_TTL = 600
GUIDE_TTL = 3600
ROW_PAGES = 3  # pages of rows per listing at least: one page holds only three or four rows
NO_WATCHED_FILTER = ('FEhistory', 'FElibrary', 'FEmy_youtube', 'FEplaylist_aggregation')
ISA = 'inputstream.adaptive'


ERRORS = {  # string id -> English fallback (Kodi only loads new strings after a restart)
    30135: 'YouTube is busy right now, try again in a moment',
    30136: "YouTube couldn't open this page",
    30137: "YouTube isn't responding, try again later",
    30138: "Can't reach YouTube, check the network connection",
}


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
        return kodi.string(30129) % exc
    return kodi.string(string_id) or ERRORS[string_id]


def format_count(value):
    """'456789' -> '456,789'; text YouTube already formatted ('456K') is kept."""
    value = str(value)
    return f'{int(value):,}' if value.isdigit() else value


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


def paged_token(shelves, page):
    """The token that continues these rows as one list: the one row that pages, else the page's own."""
    paged = [s for s in shelves if s['continuation']]
    return paged[0]['continuation'] if len(paged) == 1 else page['continuation']


def url_for(route, **params):
    params = {k: v for k, v in params.items() if v not in (None, '')}
    return BASE_URL + route + ('?' + urllib.parse.urlencode(params) if params else '')


class Plugin:
    def __init__(self, argv):
        parsed = urllib.parse.urlparse(argv[0])
        self.route = parsed.path.strip('/')
        self.handle = int(argv[1]) if len(argv) > 1 and argv[1].lstrip('-').isdigit() else -1
        query = argv[2][1:] if len(argv) > 2 and argv[2].startswith('?') else (argv[2] if len(argv) > 2 else '')
        self.params = dict(urllib.parse.parse_qsl(query))
        self.api = InnerTube()
        self.banners = art.Banners()
        self.fanart = ''  # a channel page's banner, for everything listed on it
        self.descriptions = descriptions.Descriptions()

    # ================================================================ dispatch
    def dispatch(self):
        routes = {
            '': self.root,
            'browse': self.browse,
            'shelf': self.shelf,
            'page': self.page,
            'search': self.search,
            'search/new': self.search_new,
            'search/remove': self.search_remove,
            'related': self.related,
            'play': self.play,
            'play_playlist': self.play_playlist,
            'shorts': self.shorts,
            'details': self.details,
            'chapters': self.chapters,
            'pin': self.pin,
            'unpin': self.unpin,
            'accounts': self.accounts_menu,
            'account/sign_in': self.sign_in,
            'account/switch': self.switch_account,
            'account/sign_out': self.sign_out,
            'menu/customise': self.customise_menu,
            'menu/reset': self.reset_menu,
            'maintenance': self.maintenance,
        }
        handler = routes.get(self.route)
        if handler is None:
            kodi.log('unknown route %s' % self.route)
            return self._end(False)
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

    # ================================================================ helpers
    def _end(self, succeeded=True, cache=False):
        if self.handle >= 0:
            xbmcplugin.endOfDirectory(self.handle, succeeded=succeeded, cacheToDisc=cache)

    @staticmethod
    def _notify(message, error=False):
        xbmcgui.Dialog().notification(kodi.ADDON.getAddonInfo('name'), message,
                                      xbmcgui.NOTIFICATION_ERROR if error else xbmcgui.NOTIFICATION_INFO, 4000)

    def _add(self, url, li, folder):
        xbmcplugin.addDirectoryItem(self.handle, url, li, isFolder=folder)

    def _state(self):
        return kodi.load_json('state.json', {})

    def _save_state(self, state):
        kodi.save_json('state.json', state)

    def _account_key(self):
        return auth.active_account()[0] or 'guest'

    # --------------------------------------------------------- page fetching
    def fetch(self, desc, use_cache=True):
        """Fetch a page described by desc = {'ep': browse|search|next, ...}; cached briefly so opening
        a shelf from a page re-uses the response."""
        key = self._account_key() + ':' + json.dumps(desc, sort_keys=True)
        if use_cache:
            cached = kodi.Cache.get(key, PAGE_TTL)
            if cached is not None:
                return cached
        ep = desc['ep']
        token = desc.get('ctoken')
        if ep == 'browse':
            resp = self.api.browse(desc.get('id'), desc.get('params'), continuation=token)
        elif ep == 'search':
            resp = self.api.search(desc.get('q'), desc.get('params'), continuation=token)
        elif ep == 'next':
            resp = self.api.next(desc.get('v'), desc.get('list'), continuation=token)
        else:
            raise InnerTubeError('bad page %s' % ep)
        kodi.Cache.set(key, resp)
        return resp

    def guide(self):
        key = 'guide:' + self._account_key() + ':' + self.api.hl
        entries = kodi.Cache.get(key, GUIDE_TTL)
        if entries is None:
            entries = parser.parse_guide(self.api.guide())
            kodi.Cache.set(key, entries)
        return entries

    # ================================================================ root menu
    def menu_entries(self, include_hidden=False):
        """Sidebar entries after the user's customisation (order, hidden, pinned channels)."""
        state = self._state().get('menu', {})
        guide = self.guide()
        entries = [e for e in guide if not e['channel']]
        channels = [e for e in guide if e['channel']]
        for pin in state.get('pinned', []):
            if not any(e['id'] == pin['id'] for e in entries):
                entries.append({'id': pin['id'], 'title': pin['title'], 'thumb': pin.get('thumb', ''),
                                'target': {'type': 'browse', 'browse_id': pin['id']}, 'channel': False,
                                'pinned': True})
        order = state.get('order', [])
        if order:
            rank = {entry_id: index for index, entry_id in enumerate(order)}
            entries.sort(key=lambda e: rank.get(e['id'], len(rank)))
        if not include_hidden:
            hidden = set(state.get('hidden', []))
            entries = [e for e in entries if e['id'] not in hidden]
            if kodi.setting_bool('hide_shorts'):
                entries = [e for e in entries if e['id'] != 'shorts']
        return entries, channels

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
        account_id, account = auth.active_account()
        li = xbmcgui.ListItem(kodi.string(30108), offscreen=True)
        li.setLabel2(account.get('name') or '' if account else kodi.string(30123))
        li.getVideoInfoTag().setPlot(kodi.string(30112) % (account.get('name') or '') if account
                                     else kodi.string(30123))
        li.setArt({'icon': 'DefaultUser.png', 'thumb': 'DefaultUser.png'})
        # Only opens a dialog: as a folder its failed listing made Kodi leave the add-on (and re-run it on Back).
        self._add(url_for('accounts'), li, False)
        xbmcplugin.setContent(self.handle, 'files')
        self._end()

    def _add_menu_entry(self, entry):
        target = entry['target']
        if entry['id'] == 'search':
            url = url_for('search')
            icon = 'DefaultAddonsSearch.png'
        elif entry['id'] == 'shorts':
            url = url_for('shorts', params=target.get('params'))
            icon = 'DefaultVideo.png'
        elif target['type'] == 'browse':
            url = url_for('browse', id=target['browse_id'], params=target.get('params'), title=entry['title'])
            icon = 'DefaultFolder.png'
        else:
            return
        li = xbmcgui.ListItem(entry['title'], offscreen=True)
        thumb = entry.get('thumb') or icon
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
        if window.getProperty('leanback.whos_watching'):
            return
        window.setProperty('leanback.whos_watching', '1')
        self._choose_account(kodi.string(30114), allow_add=False)

    # ================================================================ listings
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

    @staticmethod
    def _continued_rows(page):
        """The rows a continuation page continues. A row's continuation (search results) comes back
        with side rows such as Songs repeated on every page; keep to the row being paged."""
        shelves = [s for s in page['shelves'] if s['items']]
        if page['continuation'] or len(shelves) < 2:
            return shelves
        paged = [s for s in shelves if s['continuation']]
        return paged[:1] if len(paged) == 1 else shelves[:1]

    def _list_batch(self, page):
        """A continuation page as one list: its items and the token that continues them."""
        shelves = self._continued_rows(page)
        return [i for s in shelves for i in s['items']], paged_token(shelves, page)

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
        batch = batch or self._list_batch
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
            for index, shelf in enumerate(self._visible_shelves(page)):
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
        shelves = self._visible_shelves(page)
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

    def _visible_shelves(self, page):
        shelves = page['shelves']
        if kodi.setting_bool('hide_shorts'):
            shelves = [s for s in shelves if not s['shorts']]
        return [s for s in shelves if s['items']]

    def render(self, desc, browse_id=None):
        resp = self.fetch(desc)
        page = parser.parse_page(resp)
        rendered = []
        self._use_channel_fanart(browse_id, page['header'])

        if page['header']:
            self._add_header(page['header'])

        tabs = page['tabs']
        if tabs and self.params.get('tabs'):
            # The secondary navigation on its own (e.g. every subscribed channel).
            tabs = [t for t in tabs if not t.get('selected')]
            if kodi.setting_bool('sort_subscriptions'):
                tabs = sorted(tabs, key=lambda t: t['title'].lower())
            for tab in tabs:
                self._add_folder_item(tab)
            return self._finish_listing([{'kind': 'folder'}])
        if len(tabs) > 2 and not desc.get('params'):
            # Like the TV app: show the selected tab ("All") and put the other tabs in one folder.
            others = [t for t in tabs if not t.get('selected')]
            label = kodi.string(30134) or 'Channels'
            li = xbmcgui.ListItem('[B]%s[/B] (%d)' % (label, len(others)), offscreen=True)
            li.setArt({'icon': 'DefaultArtist.png', 'thumb': 'DefaultArtist.png'})
            li.getVideoInfoTag().setPlot(', '.join(t['title'] for t in others[:40]))
            li.setProperty('SpecialSort', 'top')
            self._add(url_for('browse', id=browse_id, params=desc.get('params'), tabs=1), li, True)
        shelves = self._visible_shelves(page)
        if desc.get('ctoken'):
            continued = self._continued_rows(page)
            shelves = [s for s in shelves if s in continued]
        # Untitled rows (the Subscriptions feed, a channel's uploads) read better as one list.
        untitled = sum(1 for s in shelves if not s['title'])
        flatten = not kodi.setting_bool('shelves_as_folders') or (shelves and untitled * 2 >= len(shelves))
        if len(shelves) == 1 or (shelves and flatten):
            # One list; with search's extra rows flattened in, the results shelf is the one that pages.
            items, token = self._more_pages(desc['ep'], [i for s in shelves for i in s['items']],
                                            paged_token(shelves, page))
            rendered.extend(self._render_items(items, browse_id=browse_id))
            if token:
                self._add_next(desc['ep'], token, browse_id)
        elif page['continuation']:
            # Rows as folders: the continuation brings more rows, not more items.
            for index, shelf in enumerate(shelves):
                self._add_shelf_folder(desc, index, shelf)
            token = self._more_rows(desc['ep'], page['continuation'], {s['title'] for s in shelves})
            if token:
                self._add_next(desc['ep'], token, browse_id)
        else:
            for index, shelf in enumerate(shelves):
                self._add_shelf_folder(desc, index, shelf)

        if not tabs and not shelves and not page['header']:
            if page.get('message'):
                message = page['message']
            elif (browse_id or '').startswith('FE') and not self.api.signed_in():
                message = kodi.string(30125)
            else:
                message = kodi.string(30124)
            self._notify(message)
        self._finish_listing(rendered or [{'kind': 'folder'}])

    def _finish_listing(self, items):
        videos = sum(1 for i in items if i.get('kind') == 'video')
        if videos and videos >= len(items) / 2:
            # Skins offer most of their views (walls, posters, info panels) for movies.
            content = 'videos' if kodi.setting('listing_content') == 'videos' else 'movies'
        else:
            content = 'files'
        xbmcplugin.setContent(self.handle, content)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_LABEL)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_DURATION)
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

    def _add_header(self, header):
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
                                                        'fanart': header.get('fanart')})), li, False)

    # ------------------------------------------------------------------ items
    def _render_items(self, items, browse_id=None):
        hide_shorts = kodi.setting_bool('hide_shorts')
        hide_watched = kodi.setting_bool('hide_watched') and browse_id not in NO_WATCHED_FILTER \
            and not (browse_id or '').startswith('VL')
        threshold = kodi.setting_int('watched_threshold') or 80
        self._prefetch(items, hide_shorts)
        shown = []
        for item in items:
            if hide_shorts and item['short']:
                continue
            if hide_watched and item['kind'] == 'video' and item['watched_pct'] >= threshold:
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
        channels = [channel_of(item) for item in items]
        banner_lookup = None
        if not self.fanart and self.banners.unknown(channels):
            banner_lookup = threading.Thread(target=self.banners.fetch_all, args=(channels,), name='leanback-art')
            banner_lookup.start()
        if describe.enabled():
            missing = [video_id_of(item) for item in items
                       if item['kind'] == 'video' and not item.get('upcoming')
                       and not (hide_shorts and item['short'])]
            missing = [v for v in missing if v and not (self.descriptions.get(v) or {}).get('w')]
            if missing:
                describe.fetch_all(missing, self.descriptions)
        if banner_lookup:
            banner_lookup.join()
        if not self.fanart:
            # Some tiles (Home's rows) don't name their channel; the watch pages just read do.
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

    @staticmethod
    def _video_plot(item, known, threshold):
        """The info panel's text, laid out like Full details: channel, subscribers, age, views and likes,
        then status, then the description."""
        known = known or {}
        facts = [item['channel'], item.get('subscribers') or known.get('s'),
                 item['published'] or known.get('t') or known.get('p')]
        if item['views']:
            facts.append('{:,} {}'.format(item['views'], 'watching' if item['live'] else 'views'))
        if known.get('l'):
            facts.append('%s likes' % format_count(known['l']))
        status = []
        if item['live']:
            status.append(kodi.string(30127) or 'Live')
        elif item.get('upcoming'):
            status.append(item['upcoming'])
        status.extend(item['badges'])
        if item['watched_pct'] >= threshold:
            status.append(kodi.string(30142) or 'Watched')
        elif item['watched_pct'] > 0:
            label = kodi.string(30141)
            status.append(label % item['watched_pct'] if '%d' in label else 'Watched %d%%' % item['watched_pct'])
        lines = [' • '.join(x for x in facts if x), ' • '.join(status)]
        if known and known.get('d'):
            lines.append('\n' + known['d'])
        else:
            # Lines from the tile that say more than the facts above (e.g. "Scheduled for ...").
            said = ' '.join(lines)
            for line in item['plot_lines']:
                parts = [p for p in line.split(' • ') if p and p not in said and not parser.is_count(p)]
                if parts:
                    lines.append(' • '.join(parts))
        return '\n'.join(line for line in lines if line)

    def _add_video(self, item, threshold):
        video_id = video_id_of(item)
        if not video_id:
            return
        title = item['title']
        if item['live']:
            label = '[COLOR red]%s[/COLOR] %s' % (kodi.string(30127), title)
        elif item.get('upcoming'):
            label = '[COLOR yellow]%s[/COLOR] %s' % (item['upcoming'], title)
        else:
            label = title
        li = xbmcgui.ListItem(label, offscreen=True)
        tag = li.getVideoInfoTag()
        tag.setMediaType('video')
        tag.setTitle(title)
        known = self.descriptions.get(video_id)
        channel_id = item['channel_id'] or (known or {}).get('c')
        plot = self._video_plot(item, known, threshold)
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
            tag.setVotes(item['views'])
        li.setArt({'thumb': item['thumb'], 'icon': item['thumb'],
                   'fanart': self._channel_fanart(channel_id) or item['thumb'], 'landscape': item['thumb']})
        li.setProperty('IsPlayable', 'true')
        li.setProperty('leanback.video_id', video_id)
        menu = []
        if channel_id:
            menu.append((kodi.string(30103), 'Container.Update(%s)' % url_for(
                'browse', id=channel_id, title=item['channel'])))
        menu.append((kodi.string(30104), 'Container.Update(%s)' % url_for('related', v=video_id)))
        menu.append((kodi.string(30105), 'RunPlugin(%s)' % url_for('details', v=video_id)))
        if not item['live'] and not item['short']:
            menu.append((kodi.string(30139) or 'Chapters', 'RunPlugin(%s)' % url_for('chapters', v=video_id)))
        li.addContextMenuItems(menu)
        self._add(url_for('play', v=video_id), li, False)

    def _add_folder_item(self, item):
        target = item['target'] or {}
        kind = item['kind']
        if kind == 'playlist' or (target.get('type') == 'video' and target.get('playlist_id') and kind != 'video'):
            playlist_id = target.get('playlist_id') or (target.get('browse_id') or '')[2:] or item.get('id')
            browse_id = target.get('browse_id') if target.get('type') == 'browse' else 'VL' + playlist_id
            url = url_for('browse', id=browse_id, title=item['title'])
        elif target.get('type') == 'browse':
            url = url_for('browse', id=target['browse_id'], params=target.get('params'), title=item['title'])
        elif target.get('type') == 'search':
            url = url_for('search', q=target['query'], params=target.get('params'))
        elif target.get('type') == 'play_playlist':
            url = url_for('browse', id='VL' + target['playlist_id'], title=item['title'])
        else:
            return
        li = xbmcgui.ListItem(item['title'], offscreen=True)
        tag = li.getVideoInfoTag()
        tag.setTitle(item['title'])
        lines = list(item['plot_lines'])
        if item['badges']:
            lines.append(' • '.join(item['badges']))
        tag.setPlot('\n'.join(lines))
        thumb = item.get('thumb') or 'DefaultFolder.png'
        browse_id = target.get('browse_id') or ''
        channel_id = channel_of(item)
        li.setArt({'thumb': thumb, 'icon': thumb,
                   'fanart': self._channel_fanart(channel_id) or item.get('thumb') or ''})
        menu = []
        if kind == 'channel' or browse_id.startswith('UC'):
            menu.append((kodi.string(30106), 'RunPlugin(%s)' % url_for(
                'pin', id=browse_id or item.get('id'), title=item['title'], thumb=item.get('thumb'))))
        if kind == 'playlist':
            playlist_id = browse_id[2:] if browse_id.startswith('VL') else (target.get('playlist_id') or item.get('id'))
            menu.append((kodi.string(30126), 'RunPlugin(%s)' % url_for('play_playlist', list=playlist_id)))
        if menu:
            li.addContextMenuItems(menu)
        self._add(url, li, True)

    # ================================================================ search
    def search(self):
        query = self.params.get('q')
        if query:
            if not self.params.get('params'):  # refinements like "Recently uploaded" aren't the user's searches
                self._remember_search(query)
            self.render({'ep': 'search', 'q': query, 'params': self.params.get('params')})
            return
        li = xbmcgui.ListItem('[B]%s[/B]' % kodi.string(30101), offscreen=True)
        li.setArt({'icon': 'DefaultAddonsSearch.png'})
        # Not a folder: Kodi runs it as a script, so the Container.Update to the results isn't
        # undone by Kodi going back from a failed folder.
        self._add(url_for('search/new'), li, False)
        for past in self._state().get('search_history', []):
            li = xbmcgui.ListItem(past, offscreen=True)
            li.setArt({'icon': 'DefaultAddonsSearch.png'})
            li.addContextMenuItems([(kodi.string(30128), 'RunPlugin(%s)' % url_for('search/remove', q=past))])
            self._add(url_for('search', q=past), li, True)
        self._end()

    def search_new(self):
        query = xbmcgui.Dialog().input(kodi.string(30100))
        self._end(False)
        if query:
            xbmc.executebuiltin('Container.Update(%s)' % url_for('search', q=query))

    def search_remove(self):
        state = self._state()
        state['search_history'] = [q for q in state.get('search_history', []) if q != self.params.get('q')]
        self._save_state(state)
        xbmc.executebuiltin('Container.Refresh')

    def _remember_search(self, query):
        state = self._state()
        history = [q for q in state.get('search_history', []) if q.lower() != query.lower()]
        state['search_history'] = [query] + history[:19]
        self._save_state(state)

    # ================================================================ playback
    def play(self):
        video_id = self.params['v']
        try:
            resp, client = self.api.player(video_id)
        except (InnerTubeError, http.HTTPError) as exc:
            kodi.log('no streams for %s: %s' % (video_id, exc))
            # YouTube's own playability reasons ("Video unavailable") read fine; HTTP failures don't.
            # An upcoming stream's reason already says it all ("This live event will begin in 61 minutes.").
            if exc.status is not None:
                message = error_message(exc)
            elif str(exc) in ('', 'unplayable'):
                message = kodi.string(30120)
            else:
                message = str(exc)
            self._notify(message, error=True)
            xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem(offscreen=True))
            return
        data = resp.get('streamingData', {})
        details = resp.get('videoDetails', {})
        headers = 'User-Agent=%s' % urllib.parse.quote(client['ua'])
        hl = self.api.hl
        live = bool(details.get('isLive')) or bool(
            data.get('hlsManifestUrl') and not any(f.get('initRange') for f in data.get('adaptiveFormats', [])))

        path = None
        mime = None
        if not live:
            translate = [x.strip() for x in (kodi.setting('subs_translate').strip() or hl).split(',')]
            translate += [x.strip() for x in kodi.setting('subs_more').split(',') if x.strip()]
            subs = mpd.subtitle_tracks(resp, kodi.setting_bool('subs_asr'), translate)
            port = xbmcgui.Window(10000).getProperty(http.PORT_PROPERTY)
            if subs and port:
                # Subtitles go through the local server, which retries YouTube's rate limits (429 on
                # translated tracks) and returns an empty track instead of an error.
                with open(kodi.temp_file('%s.subs.json' % video_id), 'w', encoding='utf-8') as handle:
                    json.dump({'ua': client['ua'], 'urls': [s['url'] for s in subs]}, handle)
                for index, sub in enumerate(subs):
                    sub['url'] = 'http://127.0.0.1:%s/sub/%s/%d.vtt' % (port, video_id, index)
            manifest = mpd.build(resp, max_height=kodi.setting_int('max_quality'),
                                 codec=kodi.setting('codec') or 'any', allow_hdr=kodi.setting_bool('allow_hdr'),
                                 audio_pref=kodi.setting('audio_track') or 'original', ui_lang=hl, subtitles=subs)
            if manifest and port:
                with open(kodi.temp_file('%s.mpd' % video_id), 'w', encoding='utf-8') as handle:
                    handle.write(manifest)
                path = 'http://127.0.0.1:%s/mpd/%s.mpd' % (port, video_id)
                mime = 'application/dash+xml'
            elif manifest:
                kodi.log('manifest server not running, falling back to HLS')
        if not path and data.get('hlsManifestUrl'):
            path = data['hlsManifestUrl']
            mime = 'application/vnd.apple.mpegurl'
        if not path:
            self._notify(kodi.string(30120), error=True)
            xbmcplugin.setResolvedUrl(self.handle, False, xbmcgui.ListItem(offscreen=True))
            return

        li = xbmcgui.ListItem(path=path, offscreen=True)
        li.setMimeType(mime)
        li.setContentLookup(False)
        li.setProperty('inputstream', ISA)
        li.setProperty(ISA + '.manifest_headers', headers)
        li.setProperty(ISA + '.stream_headers', headers)
        if live:
            li.setProperty(ISA + '.play_timeshift_buffer', 'true')
        info = parser.video_details(resp)
        self._apply_details(li, info)
        if self.params.get('t'):  # start at a chapter
            li.setProperty('StartOffset', self.params['t'])
        if self.api.signed_in() and kodi.setting_bool('report_history'):
            history.publish(video_id, path)
        xbmcplugin.setResolvedUrl(self.handle, True, li)

    def play_playlist(self):
        playlist_id = self.params['list']
        if is_mix(playlist_id):
            items = self._mix_items(playlist_id)[0]
        else:
            page = parser.parse_page(self.fetch({'ep': 'browse', 'id': 'VL' + playlist_id}))
            items = [i for s in page['shelves'] for i in s['items'] if i['kind'] == 'video']
        if not items:
            self._notify(kodi.string(30124))
            return
        self._end(False)
        videos = [(video_id_of(item), item['title'], item['thumb']) for item in items]
        start = self.params.get('v')
        order = self.params.get('order')
        if order == 'reverse':
            videos.reverse()
        elif order == 'shuffle' and not start:  # a chosen first video keeps the playlist's order
            random.shuffle(videos)
        position = next((i for i, video in enumerate(videos) if video[0] == start), 0)
        self._play_videos(videos, position)

    def shorts(self):
        """Like the TV app's Shorts button: start playing the Shorts feed as a playlist."""
        self._end(False)
        videos = self.api.shorts(self.params.get('params') or 'CA8=')
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
        # Played or opened in Info: keep the description for the video's plot in listings.
        self.descriptions.remember_details(info)
        tag = li.getVideoInfoTag()
        tag.setMediaType('video')
        tag.setTitle(info['title'])
        plot = info['plot']
        facts = [x for x in (info['channel'], info.get('subscribers'), info.get('published') or info.get('date'),
                             ('%s views' % '{:,}'.format(info['views'])) if info['views'] else '',
                             ('%s likes' % format_count(info['likes'])) if info.get('likes') else '') if x]
        if facts:
            plot = ' • '.join(facts) + ('\n\n' + plot if plot else '')
        tag.setPlot(plot)
        if info['channel']:
            tag.setStudios([info['channel']])
            tag.setDirectors([info['channel']])
        if info['duration']:
            tag.setDuration(info['duration'])
        if info['tags']:
            tag.setTags(info['tags'][:20])
        if info['views']:
            tag.setVotes(info['views'])
        if info.get('date'):
            tag.setPremiered(info['date'])
        if info.get('genre'):
            tag.setGenres([info['genre']])
        thumb = 'https://i.ytimg.com/vi/%s/maxresdefault.jpg' % info['video_id'] if info['video_id'] else info['thumb']
        li.setArt({'thumb': info['thumb'] or thumb, 'icon': info['thumb'] or thumb,
                   'fanart': self._channel_fanart(info.get('channel_id')) or thumb})

    def chapters(self):
        """Pick a chapter: seek to it when this video is playing, otherwise start the video there."""
        video_id = self.params['v']
        found = parser.chapters(self.fetch({'ep': 'next', 'v': video_id}))
        if not found:
            self._notify(kodi.string(30140) or 'This video has no chapters')
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
        choice = xbmcgui.Dialog().select(kodi.string(30139) or 'Chapters', items, preselect=preselect,
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
            header = json.loads(self.params['header'])
            li = xbmcgui.ListItem(header['title'], offscreen=True)
            tag = li.getVideoInfoTag()
            tag.setTitle(header['title'])
            tag.setPlot(header['plot'])
            li.setArt({k: v for k, v in (('thumb', header.get('thumb')), ('fanart', header.get('fanart'))) if v})
            xbmcgui.Dialog().info(li)
            return
        video_id = self.params['v']
        xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
        try:
            player_resp = None
            try:
                player_resp, _ = self.api.player(video_id)
            except InnerTubeError:
                pass
            next_resp = self.api.watch_page(video_id)
        finally:
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
        info = parser.video_details(player_resp or {}, next_resp)
        info['video_id'] = info['video_id'] or video_id
        li = xbmcgui.ListItem(info['title'], offscreen=True)
        self._apply_details(li, info)
        li.setPath(url_for('play', v=video_id))
        li.setProperty('IsPlayable', 'true')
        xbmcgui.Dialog().info(li)

    # ================================================================ menu customisation
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
            target = xbmcgui.Dialog().select(kodi.string(30118) % labels[index],
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
        label = maintenance.text(string_id)
        if not xbmcgui.Dialog().yesno(kodi.ADDON.getAddonInfo('name'), maintenance.text(30157) % label):
            return
        freed = action()
        kodi.log('maintenance: cleared %s (%d bytes)' % (self.params['what'], freed))
        if freed:
            message = maintenance.text(30158) % ('%s, %s' % (label, maintenance.human_size(freed)))
        else:
            message = maintenance.text(30159)
        self._notify(message)

    def reset_menu(self):
        state = self._state()
        state['menu'] = {'pinned': state.get('menu', {}).get('pinned', [])}
        self._save_state(state)
        self._notify(kodi.string(30119))

    # ================================================================ accounts
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
            self._notify(kodi.string(30113) % exc, error=True)
            return
        url = code.get('verification_url') or 'youtube.com/activate'
        url = url.replace('https://', '').replace('http://', '').replace('www.', '')
        interval = max(int(code.get('interval', 5)), 2)
        deadline = time.time() + int(code.get('expires_in', 1800))
        progress = xbmcgui.DialogProgress()
        message = '%s\n[B][COLOR yellow]%s[/COLOR][/B]\n%s' % (kodi.string(30110) % url, code['user_code'],
                                                              kodi.string(30111))
        progress.create(kodi.string(30109), message)
        token = None
        monitor = xbmc.Monitor()
        try:
            while time.time() < deadline:
                if progress.iscanceled() or monitor.abortRequested():
                    return
                remaining = (deadline - time.time()) / float(code.get('expires_in', 1800))
                progress.update(int(remaining * 100), message)
                if monitor.waitForAbort(interval):
                    return
                try:
                    token = auth.poll_token(code['device_code'])
                except auth.AuthError as exc:
                    self._notify(kodi.string(30113) % exc, error=True)
                    return
                if token:
                    break
        finally:
            progress.close()
        if not token:
            self._notify(kodi.string(30130), error=True)
            return
        account_id = auth.add_account(token)
        name = InnerTube().account_name() or kodi.string(30131) % len(auth.accounts())
        auth.rename_account(account_id, name)
        self._notify(kodi.string(30112) % name)
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
    Plugin(argv).dispatch()
