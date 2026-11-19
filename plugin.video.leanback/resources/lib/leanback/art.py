# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""Channel banners, used as fanart for a channel's videos. A banner only comes with the channel's
own page, which is large, so banners are remembered for a week and missing ones are fetched after
a listing is already on screen."""
import threading
import time

from . import http, kodi, parser
from .innertube import InnerTube, InnerTubeError

STORE = 'channel_art.json'
TTL = 7 * 86400
FETCH_LIMIT = 12  # channel pages fetched after one listing (about 0.8 MB each)
WORKERS = 4


def _fresh(entries):
    now = time.time()
    return {k: v for k, v in entries.items() if isinstance(v, dict) and now - v.get('ts', 0) < TTL}


class Banners:
    def __init__(self):
        self._entries = None
        self.missing = []  # channel ids asked for that have no remembered banner

    def _load(self):
        if self._entries is None:
            self._entries = _fresh(kodi.load_json(STORE, {}))
        return self._entries

    def get(self, channel_id):
        """The remembered banner, '' when the channel has none or it isn't known yet."""
        if not (channel_id or '').startswith('UC'):
            return ''
        entry = self._load().get(channel_id)
        if entry is None:
            if channel_id not in self.missing:
                self.missing.append(channel_id)
            return ''
        return entry['url']

    def remember(self, channel_id, url):
        if not (channel_id or '').startswith('UC'):
            return
        url = url or ''
        if channel_id in self.missing:
            self.missing.remove(channel_id)
        entries = self._load()
        if channel_id in entries and entries[channel_id]['url'] == url:
            return
        entries[channel_id] = {'url': url, 'ts': time.time()}
        self._save()

    def _save(self):
        # Another listing may have added banners since this one loaded them.
        stored = _fresh(kodi.load_json(STORE, {}))
        stored.update(self._entries or {})
        kodi.save_json(STORE, stored)

    def fetch_missing(self, limit=FETCH_LIMIT):
        """Fetch banners for channels seen without one; called once the listing is shown."""
        todo = self.missing[:limit]
        if not todo:
            return
        found = {}

        def work():
            # Background: the request broker runs these after anything on screen.
            api = InnerTube(priority=http.BACKGROUND)
            while todo:
                try:
                    channel_id = todo.pop()
                except IndexError:
                    return
                try:
                    header = parser.parse_page(api.browse(channel_id))['header'] or {}
                except (InnerTubeError, http.HTTPError) as exc:
                    kodi.log('no banner for %s: %s' % (channel_id, exc))
                    if getattr(exc, 'blocked', False):
                        del todo[:]  # YouTube is holding requests back: try the rest another time
                    continue
                found[channel_id] = header.get('fanart') or ''

        threads = [threading.Thread(target=work, name='leanback-art') for _ in range(min(WORKERS, len(todo)))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        if found:
            entries = self._load()
            for channel_id, url in found.items():
                entries[channel_id] = {'url': url, 'ts': time.time()}
            self._save()
            kodi.log('remembered %d channel banners' % len(found))
