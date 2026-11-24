# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Fetching YouTube's pages and the main menu, shared by the plugin's listings and the TV interface."""
import json

from . import auth, kodi, parser
from .innertube import InnerTube, InnerTubeError

PAGE_TTL = 600
GUIDE_TTL = 3600
# Pages that are about what was watched: watched videos stay on them even with hide_watched on.
NO_WATCHED_FILTER = ('FEhistory', 'FElibrary', 'FEmy_youtube', 'FEplaylist_aggregation')


def watched_threshold():
    return kodi.setting_int('watched_threshold') or 80


def item_filter(browse_id=None):
    """A test for the items a listing shows: Shorts and watched videos are left out when those settings are
    on (watched ones stay in History, the Library and playlists)."""
    hide_shorts = kodi.setting_bool('hide_shorts')
    hide_watched = (kodi.setting_bool('hide_watched') and browse_id not in NO_WATCHED_FILTER
                    and not (browse_id or '').startswith('VL'))
    threshold = watched_threshold()

    def keep(item):
        if hide_shorts and item['short']:
            return False
        return not (hide_watched and item['kind'] == 'video' and item['watched_pct'] >= threshold)
    return keep


def visible_shelves(page):
    shelves = page['shelves']
    if kodi.setting_bool('hide_shorts'):
        shelves = [s for s in shelves if not s['shorts']]
    return [s for s in shelves if s['items']]


def paged_token(shelves, page):
    """The token that continues these rows as one list: the one row that pages, else the page's own."""
    paged = [s for s in shelves if s['continuation']]
    return paged[0]['continuation'] if len(paged) == 1 else page['continuation']


def continued_rows(page):
    """The rows a continuation page continues. A row's continuation (search results) comes back
    with side rows such as Songs repeated on every page; keep to the row being paged."""
    shelves = [s for s in page['shelves'] if s['items']]
    if page['continuation'] or len(shelves) < 2:
        return shelves
    paged = [s for s in shelves if s['continuation']]
    return paged[:1] if len(paged) == 1 else shelves[:1]


def list_batch(page):
    """A continuation page as one list: its items and the token that continues them."""
    shelves = continued_rows(page)
    return [i for s in shelves for i in s['items']], paged_token(shelves, page)


class Pages:
    def __init__(self, api=None):
        self.api = api or InnerTube()

    @staticmethod
    def _state():
        return kodi.load_json('state.json', {})

    @staticmethod
    def _save_state(state):
        kodi.save_json('state.json', state)

    def _remember_search(self, query):
        state = self._state()
        history = [q for q in state.get('search_history', []) if q.lower() != query.lower()]
        state['search_history'] = [query] + history[:19]
        self._save_state(state)

    def _searches(self):
        return self._state().get('search_history', [])

    def _forget_search(self, query):
        state = self._state()
        state['search_history'] = [q for q in state.get('search_history', []) if q != query]
        self._save_state(state)

    @staticmethod
    def _account_key():
        return auth.active_account()[0] or 'guest'

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
