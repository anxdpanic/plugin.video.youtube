# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""Descriptions for listed videos, fetched before the listing is shown.

List tiles carry no description, and each video's costs a watch page request. They are all fetched at
once, in parallel, before the listing is drawn, so every view shows the full text straight away and
nothing refreshes afterwards. The requests go to youtubei.googleapis.com (see InnerTube.watch_page),
which takes a burst like this without the block page www.youtube.com answers bursts with."""
import threading

from . import http, kodi, parser
from .innertube import InnerTube, InnerTubeError

WORKERS = 32


def enabled():
    return kodi.setting_bool('fetch_descriptions')


def fetch_all(video_ids, store, fetch=None):
    """Fetch the watch pages of these videos in parallel and keep what they say in `store`.
    Returns how many were described. Videos whose page failed are left as they were."""
    todo = [v for v in dict.fromkeys(video_ids) if v]
    total = len(todo)
    if not todo:
        return 0
    if fetch is None:
        api = InnerTube()

        def fetch(video_id):
            return parser.video_details({}, api.watch_page(video_id))

    found = {}
    lock = threading.Lock()
    blocked = []

    def work():
        while not blocked:
            with lock:
                if not todo:
                    return
                video_id = todo.pop(0)
            try:
                info = fetch(video_id)
            except (InnerTubeError, http.HTTPError) as exc:
                kodi.log('no description for %s: %s' % (video_id, exc))
                if getattr(exc, 'blocked', False):
                    blocked.append(True)  # YouTube is holding requests back: the rest can wait
                continue
            info['video_id'] = video_id
            found[video_id] = info  # kept even without a description, so it isn't read again

    threads = [threading.Thread(target=work, name='leanback-describe') for _ in range(min(WORKERS, total))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    if found:
        store.remember_all(found.values())
    kodi.log('read %d of %d watch pages' % (len(found), total))
    return len(found)
