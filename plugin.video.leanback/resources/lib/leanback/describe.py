# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""Descriptions for listed videos, fetched in the background.

List tiles carry no description, and each one costs a `next` request. A listing hands the videos it
lacks descriptions for to the service (POST /describe), which fetches them one by one at background
priority, top of the list first, and refreshes the listing every few videos while it is still on screen.
A newer listing replaces the one being worked on.

Info views (Wall info, List info...) show the focused video's description, so the service also watches
the focus: when it rests on a video without one, that video is fetched straight away and the listing
refreshed, ahead of the rest."""
import json
import re
import threading
import time
import urllib.request

import xbmc
import xbmcgui

from . import descriptions, http, kodi, parser
from .innertube import InnerTube, InnerTubeError

LIMIT = 60  # videos per listing
REFRESH_EVERY = 5  # refresh the listing after this many new descriptions (and at the end)
REFRESH_WAIT = 2.0  # seconds to let Kodi finish a refresh before checking the next video
SUBMIT_TIMEOUT = 2
FOCUS_POLL = 0.4  # seconds between looks at the focused item
FOCUS_DWELL = 0.8  # how long focus rests on a video before its description is fetched
BASE = 'plugin://plugin.video.leanback/'
FOCUSED_VIDEO = re.compile(r'^plugin://plugin\.video\.leanback/play\?(?:.*&)?v=([A-Za-z0-9_-]{11})(?:&|$)')


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

    def __init__(self, fetch=None, current_path=None, refresh=None, wait=None, focused=None, fetch_now=None,
                 clock=time.monotonic):
        self._fetch = fetch or self._fetch_next
        self._fetch_now = fetch_now or fetch or (lambda video_id: self._fetch_next(video_id, http.FOREGROUND))
        self._current_path = current_path or (lambda: xbmc.getInfoLabel('Container.FolderPath'))
        self._focused = focused or (lambda: xbmc.getInfoLabel('ListItem.FileNameAndPath'))
        self._clock = clock
        self._refresh = refresh or (lambda: xbmc.executebuiltin('Container.Refresh'))
        self._wait = wait or xbmc.Monitor().waitForAbort
        self._cv = threading.Condition()
        self._job = None  # (path, [video ids])
        self._working_on = None
        self._failed = set()
        self._done = set()  # described while the service runs, by either thread
        self._store_lock = threading.Lock()
        self._stopped = False
        self._apis = {}
        self._focus = (None, 0.0)  # (video id, since when)

    def start(self):
        threading.Thread(target=self._run, name='leanback-describe', daemon=True).start()
        threading.Thread(target=self._watch_focus, name='leanback-describe-focus', daemon=True).start()

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

    def _fetch_next(self, video_id, priority=http.BACKGROUND):
        api = self._apis.get(priority)
        if api is None:
            api = self._apis[priority] = InnerTube(priority=priority)
        return parser.video_details({}, api.watch_page(video_id))

    def _described(self, video_id):
        if video_id in self._done:
            return True
        known = descriptions.Descriptions().get(video_id)
        if known and known.get('w'):
            self._done.add(video_id)
            return True
        return False

    def _describe(self, video_id, fetch):
        """Fetch and keep one video's description. True when one was stored; raises on request errors."""
        try:
            info = fetch(video_id)
        except (InnerTubeError, http.HTTPError) as exc:
            kodi.log('no description for %s: %s' % (video_id, exc))
            self._failed.add(video_id)
            raise
        info['video_id'] = video_id
        if not info.get('plot'):
            self._failed.add(video_id)
            return False
        with self._store_lock:
            descriptions.Descriptions().remember_details(info)
        self._done.add(video_id)
        return True

    # ------------------------------------------------------------ focus
    def _watch_focus(self):
        while True:
            with self._cv:
                self._cv.wait(FOCUS_POLL)
                if self._stopped:
                    return
            try:
                self.check_focus()
            except Exception as exc:  # the watcher must keep running
                kodi.log('focus check failed: %s' % exc)

    def check_focus(self):
        """One look at the focus: fetch the focused video's description once focus has rested on it."""
        path = self._current_path()
        match = FOCUSED_VIDEO.match(self._focused()) if path.startswith(BASE) else None
        video_id = match.group(1) if match else None
        now = self._clock()
        if video_id != self._focus[0]:
            self._focus = (video_id, now)
            return False
        if not video_id or now - self._focus[1] < FOCUS_DWELL:
            return False
        if video_id in self._failed or self._described(video_id):
            return False
        try:
            stored = self._describe(video_id, self._fetch_now)
        except (InnerTubeError, http.HTTPError):
            return False
        if stored and self._on_screen(path):
            self._refresh()
        return stored

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
        new = 0
        for video_id in video_ids:
            if self._replaced() or not self._on_screen(path):
                break
            if video_id in self._failed or self._described(video_id):
                continue
            try:
                stored = self._describe(video_id, self._fetch)
            except (InnerTubeError, http.HTTPError) as exc:
                if getattr(exc, 'blocked', False):
                    break  # YouTube is holding requests back: try again another time
                continue
            if not stored:
                continue
            new += 1
            if new % REFRESH_EVERY == 0 and self._on_screen(path):
                self._refresh()
                self._wait(REFRESH_WAIT)
        if new % REFRESH_EVERY and self._on_screen(path):
            self._refresh()
        if new:
            kodi.log('fetched %d descriptions for %s' % (new, path))
        return new
