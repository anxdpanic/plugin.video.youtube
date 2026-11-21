# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""Descriptions for listed videos, fetched in the background.

List tiles carry no description, and each one costs a `next` request. A listing hands the videos it
lacks descriptions for to the service (POST /describe), which fetches them one by one at background
priority, top of the list first, and refreshes the listing every few videos while it is still on screen.
A newer listing replaces the one being worked on."""
import json
import threading
import urllib.request

import xbmc
import xbmcgui

from . import descriptions, http, kodi, parser
from .innertube import InnerTube, InnerTubeError

LIMIT = 60  # videos per listing
REFRESH_EVERY = 5  # refresh the listing after this many new descriptions (and at the end)
REFRESH_WAIT = 2.0  # seconds to let Kodi finish a refresh before checking the next video
SUBMIT_TIMEOUT = 2


def enabled():
    return kodi.setting_bool('fetch_descriptions')


def same_path(a, b):
    return a.rstrip('/') == b.rstrip('/')


def request(path, video_ids):
    """Plugin side: ask the service for these videos' descriptions. Quiet when the service isn't there."""
    port = xbmcgui.Window(10000).getProperty(http.PORT_PROPERTY)
    if not (port and video_ids and enabled()):
        return
    body = json.dumps({'path': path, 'ids': video_ids[:LIMIT]}).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:%s/describe' % port, body, {'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=SUBMIT_TIMEOUT).close()
    except (OSError, ValueError) as exc:
        kodi.log('could not hand descriptions to the service: %s' % exc)


class Describer:
    """Service side: one worker thread, one listing at a time."""

    def __init__(self, fetch=None, current_path=None, refresh=None, wait=None):
        self._fetch = fetch or self._fetch_next
        self._current_path = current_path or (lambda: xbmc.getInfoLabel('Container.FolderPath'))
        self._refresh = refresh or (lambda: xbmc.executebuiltin('Container.Refresh'))
        self._wait = wait or xbmc.Monitor().waitForAbort
        self._cv = threading.Condition()
        self._job = None  # (path, [video ids])
        self._working_on = None
        self._failed = set()
        self._stopped = False
        self._thread = None
        self._api = None

    def start(self):
        self._thread = threading.Thread(target=self._run, name='leanback-describe', daemon=True)
        self._thread.start()

    def stop(self):
        with self._cv:
            self._stopped = True
            self._cv.notify_all()

    def submit(self, path, video_ids):
        with self._cv:
            if self._working_on is not None and same_path(self._working_on, path):
                return  # a refresh of the listing being worked on: carry on with it
            self._job = (path, list(video_ids))
            self._cv.notify_all()

    def _take(self):
        with self._cv:
            while self._job is None and not self._stopped:
                self._cv.wait()
            if self._stopped:
                return None
            job, self._job = self._job, None
            self._working_on = job[0]
            return job

    def _replaced(self):
        with self._cv:
            return self._stopped or self._job is not None

    def _fetch_next(self, video_id):
        if self._api is None:
            self._api = InnerTube(priority=http.BACKGROUND)
        return parser.video_details({}, self._api.watch_page(video_id))

    def _on_screen(self, path):
        return same_path(self._current_path(), path)

    def _run(self):
        while True:
            job = self._take()
            if job is None:
                return
            try:
                self.work(*job)
            finally:
                with self._cv:
                    self._working_on = None

    def work(self, path, video_ids):
        store = descriptions.Descriptions()
        new = 0
        for video_id in video_ids:
            if self._replaced() or not self._on_screen(path):
                break
            known = store.get(video_id)
            if video_id in self._failed or (known and known.get('w')):
                continue
            try:
                info = self._fetch(video_id)
            except (InnerTubeError, http.HTTPError) as exc:
                kodi.log('no description for %s: %s' % (video_id, exc))
                self._failed.add(video_id)
                if getattr(exc, 'blocked', False):
                    break  # YouTube is holding requests back: try again another time
                continue
            info['video_id'] = video_id
            if not info.get('plot'):
                self._failed.add(video_id)
                continue
            store.remember_details(info)
            new += 1
            if new % REFRESH_EVERY == 0 and self._on_screen(path):
                self._refresh()
                self._wait(REFRESH_WAIT)
        if new % REFRESH_EVERY and self._on_screen(path):
            self._refresh()
        if new:
            kodi.log('fetched %d descriptions for %s' % (new, path))
        return new
