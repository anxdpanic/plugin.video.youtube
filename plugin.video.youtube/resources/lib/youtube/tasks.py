# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Lookups run side by side before a listing is drawn (channel banners, video descriptions)."""
import threading

from . import http, kodi
from .innertube import InnerTubeError


def run_parallel(items, work, workers, name, what):
    """Call work(item) for each item on up to `workers` threads; returns {item: result} for the ones that
    succeeded. A failed item is logged as "no <what> for <item>" and left out. Once YouTube is holding
    requests back, the items not started yet are left for later."""
    todo = iter(items)
    results = {}
    lock = threading.Lock()
    blocked = threading.Event()

    def worker():
        while not blocked.is_set():
            with lock:
                item = next(todo, None)
            if item is None:
                return
            try:
                results[item] = work(item)
            except (InnerTubeError, http.HTTPError) as exc:
                kodi.log('no %s for %s: %s' % (what, item, exc))
                if getattr(exc, 'blocked', False):
                    blocked.set()

    threads = [threading.Thread(target=worker, name=name) for _ in range(min(workers, len(items)))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results
