# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Video descriptions for the plot of listed videos. List tiles carry none, so a description is kept
when the user plays a video or opens its Info, and shows in listings from then on."""
import time

from . import kodi

STORE = 'descriptions.json'
TTL = 30 * 86400
MAX_ENTRIES = 4000


class Descriptions:
    def __init__(self):
        self._videos = None

    def _load(self):
        if self._videos is None:
            now = time.time()
            self._videos = {k: v for k, v in kodi.load_json(STORE, {}).get('videos', {}).items()
                            if now - v.get('ts', 0) < TTL}
        return self._videos

    def get(self, video_id):
        """{'d': description, 'p': upload date, and the watch page's 's', 'l', 't' when known} or None."""
        return self._load().get(video_id)

    def remember(self, video_id, description, published='', facts=None, save=True):
        """facts: what the watch page adds to a video, as {'s': subscribers, 'l': likes, 't': age text,
        'c': channel id},
        with 'w' set once the watch page was read."""
        facts = {k: v for k, v in (facts or {}).items() if v}
        # A watch page without a description (Shorts often have none) is kept too, so it isn't read again.
        if not video_id or not (description or facts.get('w')):
            return
        entry = self.get(video_id)
        unchanged = entry and entry.get('d') == description and (entry.get('p') or not published)
        if unchanged and all(entry.get(k) == v for k, v in facts.items()):
            return
        new = dict(entry or {}, d=description, p=published or (entry or {}).get('p', ''), ts=time.time())
        new.update(facts)
        self._load()[video_id] = new
        if save:
            self._save()

    def remember_details(self, info, save=True):
        """Keep the description and watch-page facts from parser.video_details()."""
        self.remember(info.get('video_id'), info.get('plot'), info.get('date'),
                      {'s': info.get('subscribers'), 'l': info.get('likes'), 't': info.get('published'),
                       'c': info.get('channel_id'), 'w': 1},
                      save=save)

    def remember_all(self, infos):
        """remember_details() for many videos, written to disk once."""
        for info in infos:
            self.remember_details(info, save=False)
        self._save()

    def _save(self):
        # Another listing may have stored descriptions since this one loaded them.
        videos = dict(kodi.load_json(STORE, {}).get('videos', {}), **self._videos)
        if len(videos) > MAX_ENTRIES:
            videos = dict(sorted(videos.items(), key=lambda kv: kv[1].get('ts', 0))[-MAX_ENTRIES:])
        kodi.save_json(STORE, {'videos': videos})
