# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""Channel banners, used as fanart for a channel's videos. List tiles don't carry them, so the banners
of channels not seen before are looked up (from each channel's small About page) before a listing is
drawn, and remembered for a week. Only the addresses are kept: Kodi fetches and caches the images."""
import time

from . import kodi, parser, tasks
from .innertube import InnerTube

STORE = 'channel_art.json'
TTL = 7 * 86400
WORKERS = 16


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
        return parser.larger_art(entry['url'])  # at the width image_quality asks for now

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

    def unknown(self, channel_ids):
        """The channels among these whose banner isn't remembered yet."""
        entries = self._load()
        return [c for c in dict.fromkeys(channel_ids) if (c or '').startswith('UC') and c not in entries]

    def fetch_all(self, channel_ids, fetch=None):
        """Look up these channels' banners in parallel and remember them. Returns how many were found."""
        todo = self.unknown(channel_ids)
        total = len(todo)
        if not todo:
            return 0
        if fetch is None:
            api = InnerTube()

            def fetch(channel_id):
                return parser.channel_banner(api.channel_about(channel_id))

        found = tasks.run_parallel(todo, lambda channel_id: fetch(channel_id) or '', WORKERS, 'youtube-art',
                                   'banner')
        if found:
            entries = self._load()
            for channel_id, url in found.items():
                entries[channel_id] = {'url': url, 'ts': time.time()}
                if channel_id in self.missing:
                    self.missing.remove(channel_id)
            self._save()
        kodi.log('looked up %d of %d channel banners' % (len(found), total))
        return len([u for u in found.values() if u])
