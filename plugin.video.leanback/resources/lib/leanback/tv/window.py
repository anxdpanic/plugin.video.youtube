# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""The TV interface's window: a navigation rail, the focused video's details, and rows of tiles.

Kodi can't add rows to a window as it runs, so the window has two row lists: the focused row and a peek at the
next. Moving up or down fills them with other rows of the screen; each row keeps its tiles and the tile it
was on, so coming back to a row is instant."""
import threading
import traceback

import xbmc
import xbmcgui

from .. import auth, describe, descriptions, http, kodi, maintenance, pages, parser, router
from ..innertube import InnerTubeError
from . import items, model

RAIL = 100
ROWS = (200, 201)
MORE_AT = 6  # load more of a row once the focus is this close to its end
PLAY_WAIT = 60  # seconds to wait for a chosen video to start before giving up on following it
PLAY_POLL = 2  # seconds between readings of the playback position

ACTION_LEFT, ACTION_RIGHT, ACTION_UP, ACTION_DOWN = 1, 2, 3, 4
ACTION_BACK = (9, 10, 92)  # parent dir, previous menu, back
ACTION_CONTEXT = (11, 117)  # info, context menu


def _string(string_id, fallback):
    return kodi.string(string_id) or fallback


class TVWindow(xbmcgui.WindowXML):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = pages.Pages()
        self.descriptions = descriptions.Descriptions()
        self.threshold = pages.watched_threshold()
        self.entries = []
        self.stack = []  # screens, the one shown last
        self.top = 0  # index of the focused row
        self.current_entry = None
        self._described = set()
        self.watched = {}  # video id -> percent watched, for videos played from this window

    # ------------------------------------------------------------ Kodi callbacks
    def onInit(self):  # noqa: N802 (Kodi API)
        try:
            self._init()
        except Exception:
            # Kodi only prints a callback's error when debug logging is on; keep it in the log either way.
            kodi.log_error('TV interface failed to open: ' + traceback.format_exc())
            raise

    def _init(self):
        if self.stack:  # back from playback or a dialog: Kodi rebuilt the window
            self._fill_rail()
            self._show_rows()
            return
        self._busy(True)
        try:
            self._load_rail()
            first = next((e for e in self.entries if e['target'].get('type') == 'browse'), None)
            if first:
                self._open_entry(first)
        finally:
            self._busy(False)

    def onAction(self, action):  # noqa: N802
        action_id = action.getId()
        focus = self.getFocusId()
        if action_id in ACTION_BACK:
            self._back(focus)
        elif focus == ROWS[0] and action_id == ACTION_DOWN:
            self._move(1)
        elif focus == ROWS[0] and action_id == ACTION_UP:
            self._move(-1)
        elif focus == ROWS[0] and action_id == ACTION_RIGHT:
            self._more_items()
        elif focus == ROWS[0] and action_id in ACTION_CONTEXT:
            self._context_menu()

    def onClick(self, control_id):  # noqa: N802
        if control_id == RAIL:
            position = self.getControl(RAIL).getSelectedPosition()
            if 0 <= position < len(self.entries):
                self._guarded(self._open_entry, self.entries[position])
        elif control_id == ROWS[0]:
            row = self._row(0)
            position = self.getControl(ROWS[0]).getSelectedPosition()
            if row and 0 <= position < len(row.items):
                row.pos = position  # back from playback, the window is rebuilt on this tile
                self._guarded(self._activate, row.items[position])

    # ------------------------------------------------------------ rail
    def _load_rail(self):
        entries, _ = self.pages.menu_entries()
        account = auth.active_account()[1]
        entries = list(entries) + [
            {'id': 'accounts', 'title': (account or {}).get('name') or _string(30108, 'Accounts'),
             'target': {'type': 'accounts'}, 'thumb': '', 'art': items.icon('account')},
            {'id': 'settings', 'title': xbmc.getLocalizedString(5), 'target': {'type': 'settings'},
             'thumb': '', 'art': items.icon('settings')},
        ]
        self.entries = entries
        self._fill_rail()

    def _fill_rail(self):
        rail = self.getControl(RAIL)
        rail.reset()
        current = 0
        for index, entry in enumerate(self.entries):
            li = items.rail_item(entry)
            if self.current_entry and entry['id'] == self.current_entry:
                li.setProperty('current', '1')
                current = index
            rail.addItem(li)
        rail.selectItem(current)  # the rail opens on the page being shown

    def _open_entry(self, entry):
        target = entry['target']
        kind = target.get('type')
        if entry['id'] == 'search' or kind == 'search':
            self._push(model.LocalScreen(entry['title'], self._search_rows), replace=True, entry='search')
        elif entry['id'] == 'shorts':
            xbmc.executebuiltin('RunPlugin(%s)' % router.url_for('shorts', params=target.get('params')))
        elif kind == 'accounts':
            xbmc.executebuiltin('RunPlugin(%s)' % router.url_for('accounts'), True)
            kodi.Cache.prune(0)
            self.stack = []
            self.onInit()
        elif kind == 'settings':
            kodi.ADDON.openSettings()
        elif kind == 'browse':
            desc = {'ep': 'browse', 'id': target['browse_id'], 'params': target.get('params')}
            self._push(model.Screen(desc, entry['title'], self._load_page, pages.item_filter(target['browse_id']),
                                    _string(30134, 'Channels')), replace=True, entry=entry['id'])

    # ------------------------------------------------------------ screens
    def _push(self, screen, replace=False, entry=None):
        self._busy(True)
        try:
            screen.open()
            screen.ensure(0)
        finally:
            self._busy(False)
        if self.stack:
            self.stack[-1].top = self.top
        if replace:
            self.stack = []
            self.current_entry = entry
            self._fill_rail()
        self.stack.append(screen)
        self.top = 0
        self._show_rows()
        self.setFocusId(ROWS[0] if screen.rows else RAIL)

    def _back(self, focus):
        if focus == RAIL:
            self.close()
        elif len(self.stack) > 1:
            self.stack.pop()
            screen = self.stack[-1]
            if hasattr(screen, 'refresh'):  # the search screen: a search just made goes to the top
                screen.refresh()
            self.top = min(getattr(screen, 'top', 0), max(len(screen.rows) - 1, 0))
            self._show_rows()
        else:
            self.setFocusId(RAIL)

    @property
    def screen(self):
        return self.stack[-1] if self.stack else None

    def _row(self, slot):
        screen = self.screen
        if not screen or self.top + slot >= len(screen.rows):
            return None
        return screen.rows[self.top + slot]

    def _show_rows(self):
        screen = self.screen
        self.setProperty('screen.title', screen.title if screen else '')
        self.setProperty('message', '' if not screen or screen.rows else
                         screen.message or _string(30124, 'This page is empty'))
        for slot, control_id in enumerate(ROWS):
            control = self.getControl(control_id)
            control.reset()
            row = self._row(slot)
            self.setProperty('row%d.title' % slot, row.title if row else '')
            if not row:
                continue
            if row.listitems is None:
                row.listitems = [self._tile(row, i) for i in row.items]
            control.addItems(row.listitems)
            control.selectItem(row.pos if slot == 0 else 0)
        self._describe_soon()

    def _move(self, step):
        screen = self.screen
        if not screen:
            return
        index = self.top + step
        if index < 0:
            return
        if index + model.LOOKAHEAD >= len(screen.rows) and screen.can_grow():
            self._guarded(screen.ensure, index)
        if index >= len(screen.rows):
            return
        row = self._row(0)
        if row:
            row.pos = self.getControl(ROWS[0]).getSelectedPosition()
        self.top = index
        self._show_rows()

    def _more_items(self):
        row = self._row(0)
        control = self.getControl(ROWS[0])
        if not row or not row.token or control.getSelectedPosition() < len(row.items) - MORE_AT:
            return
        fresh = self._guarded(self.screen.more_items, row) or []
        if fresh:
            new = [self._tile(row, i) for i in fresh]
            row.listitems.extend(new)
            control.addItems(new)
            self._describe_soon()

    # ------------------------------------------------------------ tiles
    def _tile(self, row, item):
        video_id = model.video_id_of(item)
        if video_id in self.watched:  # played since YouTube's page was fetched
            item['watched_pct'] = self.watched[video_id]
        return items.tile(item, self.descriptions.get(router.video_id_of(item)), self.threshold, row.avatars)

    def _activate(self, item):
        target = item['target'] or {}
        kind = item['kind']
        if kind == 'action':
            self._search_action(target['type'])
        elif kind == 'query':
            self._search(target['query'])
        elif kind == 'video':
            self._play(item)
        elif kind == 'playlist' or target.get('type') == 'play_playlist' or (
                target.get('type') == 'video' and target.get('playlist_id')):
            playlist_id = target.get('playlist_id') or (target.get('browse_id') or '')[2:] or item.get('id')
            if router.is_mix(playlist_id):
                xbmc.executebuiltin('RunPlugin(%s)' % router.url_for('play_playlist', list=playlist_id))
            else:
                self._open_browse('VL' + playlist_id, None, item['title'])
        elif target.get('type') == 'browse':
            self._open_browse(target['browse_id'], target.get('params'), item['title'])
        elif target.get('type') == 'search':
            self._push(model.Screen({'ep': 'search', 'q': target['query'], 'params': target.get('params')},
                                    target['query'], self._load_page, pages.item_filter()))

    # ------------------------------------------------------------ search
    def _search_rows(self):
        """The search screen: New search (and Clear when there is something to clear), then past searches."""
        past = self.pages._searches()
        actions = [{'kind': 'action', 'title': _string(30101, 'New search'), 'icon': 'search',
                    'target': {'type': 'new_search'}, 'plot': _string(30175, 'Type what to search YouTube for')}]
        if past:
            actions.append({'kind': 'action', 'title': _string(30171, 'Clear search history'), 'icon': 'clear',
                            'target': {'type': 'clear_searches'},
                            'plot': _string(30172, 'Forget all %d past searches') % len(past)})
        rows = [model.Row(_string(30100, 'Search'), actions)]
        if past:
            again = _string(30176, 'Search again for "%s"')
            rows.append(model.Row(_string(30174, 'Recent searches'), [
                {'kind': 'query', 'title': query, 'target': {'type': 'search', 'query': query},
                 'plot': again % query} for query in past]))
        return rows

    def _search_action(self, action):
        if action == 'new_search':
            query = xbmcgui.Dialog().input(_string(30100, 'Search'))
            if query:
                self._search(query)
        elif action == 'clear_searches':
            if xbmcgui.Dialog().yesno(_string(30171, 'Clear search history'),
                                      _string(30173, 'Forget every past search?')):
                maintenance.clear_search_history()
                self._refresh_search()

    def _search(self, query):
        self.pages._remember_search(query)
        self._push(model.Screen({'ep': 'search', 'q': query}, query, self._load_page, pages.item_filter()))

    def _forget(self, query):
        self.pages._forget_search(query)
        self._refresh_search()

    def _refresh_search(self):
        screen = self.screen
        if hasattr(screen, 'refresh'):
            screen.refresh()
            self.top = min(self.top, max(len(screen.rows) - 1, 0))
            self._show_rows()

    def _open_browse(self, browse_id, params, title):
        desc = {'ep': 'browse', 'id': browse_id, 'params': params}
        self._push(model.Screen(desc, title, self._load_page, pages.item_filter(browse_id),
                                _string(30134, 'Channels')))

    def _play(self, item, start=None):
        video_id = router.video_id_of(item)
        if start is None and item['duration'] and 0 < item['watched_pct'] < self.threshold:
            resume_at = item['duration'] * item['watched_pct'] // 100
            choice = xbmcgui.Dialog().contextmenu([xbmc.getLocalizedString(12022) % router.format_time(resume_at),
                                                   xbmc.getLocalizedString(12021)])
            if choice < 0:
                return
            start = resume_at if choice == 0 else 0
        xbmc.executebuiltin('PlayMedia(%s)' % router.url_for('play', v=video_id, t=start or None))
        threading.Thread(target=self._follow_playback, args=(video_id,), name='leanback-tv-progress').start()

    def _follow_playback(self, video_id):
        """Note how far into the video playback gets, then show it on its tiles. Kodi doesn't say where a
        video was stopped, so the position is read every couple of seconds while it plays."""
        player = xbmc.Player()
        monitor = xbmc.Monitor()

        def playing_this():
            try:
                playing = player.getPlayingFile() if player.isPlayingVideo() else ''
            except RuntimeError:
                return False
            # A live stream plays YouTube's own manifest, whose address doesn't name the video.
            return bool(playing) and (video_id in playing or '/mpd/' not in playing)

        for _ in range(PLAY_WAIT * 2):
            if playing_this():
                break
            if monitor.waitForAbort(0.5):
                return
        else:
            return
        position = total = 0
        while playing_this():
            try:
                position, total = player.getTime(), player.getTotalTime()
            except RuntimeError:
                break
            if monitor.waitForAbort(PLAY_POLL):
                return
        percent = model.watched_percent(position, total)
        if percent:
            self._mark_watched(video_id, percent)

    def _mark_watched(self, video_id, percent):
        """Show new progress on every tile of this video, in place: the tiles are the window's own items."""
        self.watched[video_id] = percent
        known = self.descriptions.get(video_id)
        for screen in self.stack:
            for row, index in screen.find_video(video_id):
                item = row.items[index]
                item['watched_pct'] = percent
                if row.listitems and index < len(row.listitems):
                    li = row.listitems[index]
                    li.setProperty('progress', str(percent))
                    li.setProperty('plot', router.video_plot(item, known, self.threshold))

    def _context_menu(self):
        row = self._row(0)
        position = self.getControl(ROWS[0]).getSelectedPosition()
        if not row or not 0 <= position < len(row.items):
            return
        item = row.items[position]
        if item['kind'] == 'query':
            choices = [(_string(30128, 'Remove from search history'), lambda: self._forget(item['title'])),
                       (_string(30171, 'Clear search history'), lambda: self._search_action('clear_searches'))]
            choice = xbmcgui.Dialog().contextmenu([label for label, _ in choices])
            if choice >= 0:
                choices[choice][1]()
            return
        if item['kind'] == 'action':
            return
        channel_id = router.channel_of(item)
        choices = []
        if item['kind'] == 'video':
            video_id = router.video_id_of(item)
            choices.append((_string(30105, 'Full details'),
                            lambda: xbmc.executebuiltin('RunPlugin(%s)' % router.url_for('details', v=video_id))))
            choices.append((_string(30104, 'Related videos'), lambda: self._push(
                model.Screen({'ep': 'next', 'v': video_id}, item['title'], self._load_page, pages.item_filter()))))
            if not item['live'] and not item['short']:
                choices.append((_string(30139, 'Chapters'),
                                lambda: xbmc.executebuiltin('RunPlugin(%s)' % router.url_for('chapters', v=video_id))))
        if channel_id and channel_id != (self.screen.desc.get('id') if self.screen else None):
            choices.append((_string(30103, 'Go to channel'),
                            lambda: self._open_browse(channel_id, None, item['channel'] or item['title'])))
        if not choices:
            return
        choice = xbmcgui.Dialog().contextmenu([label for label, _ in choices])
        if choice >= 0:
            self._guarded(choices[choice][1])

    # ------------------------------------------------------------ descriptions
    def _describe_soon(self):
        """Read the watch pages of the shown rows' videos in the background, then fill in their details."""
        if not describe.enabled():
            return
        rows = [r for r in (self._row(0), self._row(1)) if r and r.listitems]
        wanted = []
        for row in rows:
            for item, li in zip(row.items, row.listitems):
                video_id = router.video_id_of(item) if item['kind'] == 'video' else None
                if video_id and video_id not in self._described and not item.get('upcoming'):
                    self._described.add(video_id)
                    wanted.append((video_id, item, li))
        if wanted:
            threading.Thread(target=self._describe, args=(wanted,), name='leanback-tv-describe').start()

    def _describe(self, wanted):
        try:
            describe.fetch_all([video_id for video_id, _, _ in wanted], self.descriptions)
        except (InnerTubeError, http.HTTPError) as exc:
            kodi.log('TV interface: descriptions failed: %s' % exc)
            return
        for video_id, item, li in wanted:
            known = self.descriptions.get(video_id)
            if known:
                li.setProperty('plot', router.video_plot(item, known, self.threshold))

    # ------------------------------------------------------------ helpers
    def _load_page(self, desc):
        return parser.parse_page(self.pages.fetch(desc))

    def _busy(self, on):
        self.setProperty('busy', _string(30170, 'Loading…') if on else '')

    def _guarded(self, func, *args):
        """Run func, showing a short message instead of failing when YouTube can't be reached."""
        self._busy(True)
        try:
            return func(*args)
        except (InnerTubeError, http.HTTPError) as exc:
            kodi.log('TV interface: %s' % exc)
            xbmcgui.Dialog().notification(kodi.ADDON.getAddonInfo('name'), router.error_message(exc),
                                          xbmcgui.NOTIFICATION_ERROR, 4000)
        except auth.AuthError:
            xbmcgui.Dialog().notification(kodi.ADDON.getAddonInfo('name'), kodi.string(30132),
                                          xbmcgui.NOTIFICATION_ERROR, 4000)
        finally:
            self._busy(False)
        return None
