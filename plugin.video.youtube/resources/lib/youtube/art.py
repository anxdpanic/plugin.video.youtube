# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Channel banners, used as fanart for a channel's videos. List tiles don't carry them, so the banners
of channels not seen before are looked up (from each channel's small About page) before a listing is
drawn, and remembered for a week. Only the addresses are kept: Kodi fetches and caches the images.

A list of every subscribed channel can name a thousand of them, far more than YouTube answers in one
burst (on a test with 995, about 45 got through before the rest were refused). Such a list looks up one
batch while it loads and queues the rest for the background service, which works through them a few at
a time."""
import time

from . import http, kodi, parser, tasks
from .innertube import InnerTube, InnerTubeError

STORE = 'channel_art.json'
QUEUE = 'banner_queue.json'
TTL = 7 * 86400
WORKERS = 16
BATCH = 24  # banners a listing looks up while it loads
PER_TICK = 3  # banners the service looks up each time round its loop (every 5 s)


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

    def fetch_batch(self, channel_ids):
        """Look up the first BATCH unknown banners now and queue the rest for the service."""
        todo = self.unknown(channel_ids)
        self.fetch_all(todo[:BATCH])
        queue_lookups(todo[BATCH:])


def queue_lookups(channel_ids):
    """Add channels to the service's queue of banners to look up, after those already in it."""
    if not channel_ids:
        return
    queue = kodi.load_json(QUEUE, [])
    kodi.save_json(QUEUE, list(dict.fromkeys(queue + list(channel_ids))))


def _about_banner(channel_id):
    """A channel's banner from its About tab, asked for at background priority."""
    return parser.channel_banner(InnerTube(priority=http.BACKGROUND).channel_about(channel_id))


class Backfill:
    """Lives in the service: looks up the queued banners PER_TICK at a time, one after another, so a long
    list of channels gets its banners without a burst. A failed lookup stays queued for the next tick."""

    def __init__(self, fetch=_about_banner):
        self.fetch = fetch

    def tick(self):
        queue = kodi.load_json(QUEUE, [])
        if not queue:
            return
        banners = Banners()
        todo = banners.unknown(queue)
        for channel_id in todo[:PER_TICK]:
            try:
                banners.remember(channel_id, self.fetch(channel_id) or '')
            except (InnerTubeError, http.HTTPError) as exc:
                kodi.log('no banner for %s yet: %s' % (channel_id, exc))
                break
        self._drop_known(banners)

    @staticmethod
    def _drop_known(banners):
        """Keep only the channels still unknown; a listing may have queued more meanwhile."""
        queue = kodi.load_json(QUEUE, [])
        left = banners.unknown(queue)
        if left != queue:
            kodi.save_json(QUEUE, left)
