# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""What the TV interface shows, as rows: no Kodi calls here, so it can be tested on its own."""
from .. import pages

GRID_COLUMNS = 4  # tiles per row when a single list (a feed, search results, uploads) is cut into rows
LOOKAHEAD = 2  # rows kept loaded below the focused one
END_MARGIN = 10  # seconds: stopped this close to the end counts as watched to the end


def watched_percent(position, total):
    """How much of a video was watched, from where playback stopped; 0 when unknown."""
    if total <= 0 or position <= 0:
        return 0
    if total - position <= END_MARGIN:
        return 100
    return max(1, min(100, int(position * 100 / total)))


def video_id_of(item):
    return item['target'].get('video_id') or item.get('id') if item.get('kind') == 'video' else None


class Row:
    def __init__(self, title, items, token=None, grid=False, avatars=False):
        self.title = title
        self.avatars = avatars  # a row of channels, shown as round pictures
        self.items = items
        self.token = token  # continues this row with more items (rows of shelves only)
        self.grid = grid
        self.pos = 0  # the tile that had focus, restored when the row comes back
        self.listitems = None  # built by the window the first time the row is shown


class Screen:
    """One page as rows. A page of shelves (Home, a topic, a channel) gives a row per shelf and loads more
    shelves as the focus nears the last row; a single list is cut into rows of GRID_COLUMNS tiles and loads
    more of the list the same way."""

    def __init__(self, desc, title, load, keep=None, tabs_title='Channels'):
        self.desc = desc
        self.title = title
        self._load = load  # desc -> parsed page
        self._keep = keep or (lambda item: True)
        self._tabs_title = tabs_title
        self.rows = []
        self.header = None
        self.message = ''
        self.grid = None  # {'items', 'token', 'start', 'title'} when the page is a single list
        self._more_rows = None  # token for the next page of shelves
        self._titles = set()

    @property
    def ep(self):
        return self.desc['ep']

    def open(self):
        page = self._load(self.desc)
        self.header = page['header']
        self.message = page.get('message') or ''
        tabs = [t for t in page['tabs'] if not t.get('selected')]
        if tabs:
            self.rows.append(Row(self._tabs_title, tabs, avatars=True))
        shelves = pages.visible_shelves(page)
        untitled = sum(1 for s in shelves if not s['title'])
        if len(shelves) == 1 or (shelves and untitled * 2 >= len(shelves)):
            first_title = next((s['title'] for s in shelves if s['title']), '')
            self.grid = {'items': [], 'token': None, 'start': len(self.rows), 'title': first_title}
            self._add_grid_items([i for s in shelves for i in s['items']], pages.paged_token(shelves, page))
        else:
            self._add_shelves(shelves, page['continuation'])
        return self

    # ------------------------------------------------------------ growing
    def can_grow(self):
        return bool(self.grid['token'] if self.grid else self._more_rows)

    def ensure(self, index):
        """Load more until there are LOOKAHEAD rows below `index`, or nothing more to load."""
        while index + LOOKAHEAD >= len(self.rows) and self.can_grow():
            before = len(self.rows), self._grid_count()
            self._grow()
            if (len(self.rows), self._grid_count()) == before and not self.can_grow():
                break

    def _grid_count(self):
        return len(self.grid['items']) if self.grid else 0

    def _grow(self):
        if self.grid:
            token = self.grid['token']
            items, next_token = pages.list_batch(self._load({'ep': self.ep, 'ctoken': token}))
            self._add_grid_items(items, next_token if next_token != token else None)
        else:
            token = self._more_rows
            page = self._load({'ep': self.ep, 'ctoken': token})
            self._add_shelves(pages.visible_shelves(page),
                              page['continuation'] if page['continuation'] != token else None)

    def _add_shelves(self, shelves, token):
        for shelf in shelves:
            if shelf['title'] and shelf['title'] in self._titles:
                continue  # a row repeated where pages meet
            self._titles.add(shelf['title'])
            items = [i for i in shelf['items'] if self._keep(i)]
            if items:
                self.rows.append(Row(shelf['title'], items, shelf['continuation']))
        self._more_rows = token

    def _add_grid_items(self, items, token):
        grid = self.grid
        seen = {i.get('id') for i in grid['items'] if i.get('id')}
        for item in items:
            if self._keep(item) and not (item.get('id') and item['id'] in seen):
                grid['items'].append(item)
                seen.add(item.get('id'))
        grid['token'] = token
        # Rows already full keep their state; the last, part-filled one is cut again.
        start = grid['start']
        full = [r for r in self.rows[start:] if len(r.items) == GRID_COLUMNS]
        del self.rows[start + len(full):]
        for offset in range(len(full) * GRID_COLUMNS, len(grid['items']), GRID_COLUMNS):
            chunk = grid['items'][offset:offset + GRID_COLUMNS]
            self.rows.append(Row(grid['title'] if offset == 0 else '', chunk, grid=True))

    def find_video(self, video_id):
        """(row, index) of every tile of this video on the screen."""
        for row in self.rows:
            for index, item in enumerate(row.items):
                if video_id_of(item) == video_id:
                    yield row, index

    def more_items(self, row):
        """The next items of a shelf's row (it scrolls on to the right); [] when it has no more."""
        token = row.token
        if row.grid or not token:
            return []
        items, next_token = pages.list_batch(self._load({'ep': self.ep, 'ctoken': token}))
        row.token = next_token if next_token != token else None
        seen = {i.get('id') for i in row.items if i.get('id')}
        fresh = [i for i in items if self._keep(i) and not (i.get('id') and i['id'] in seen)]
        row.items.extend(fresh)
        return fresh
