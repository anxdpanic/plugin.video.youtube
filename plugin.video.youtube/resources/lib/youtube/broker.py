# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""One place every request to Google goes through.

Kodi runs each listing as its own short-lived interpreter, so they can't share a lock or a queue.
The background service lives as long as Kodi does, so it owns the one Broker: listings hand their
requests to it over the local HTTP server (see http.request), and the service's own work (subtitles,
history reports) submits to it directly.

The broker keeps a small, fixed pool of worker threads and, per host:
- paces requests (bursts from one IP get Google's "automated queries" block page),
- runs what's on screen before background work (banners, history reports),
- merges identical requests that are already queued or running,
- and when Google answers with its block page, holds that host back for a while: requests for the
  screen wait it out and try once more, background requests are dropped.
"""
import itertools
import threading
import time
import urllib.parse

from . import kodi

FOREGROUND, BACKGROUND = 0, 1
WORKERS = 32  # paced hosts still get one request at a time; the rest (e.g. descriptions) run in parallel
# Seconds between requests to a host. Tested 2026-11-19 against www.youtube.com: back to back 4/16
# requests got the block page, 2 s apart about 1 in 6, 10 s apart none.
GAPS = {'www.youtube.com': 1.0}
BACKGROUND_GAP = 3.0  # background work (banners, history) to a paced host goes at most this often
BACKOFF = (10, 20, 40, 60)  # seconds a host is held back after each block in a row
MAX_HOLD_WAIT = 12  # a request for the screen waits out at most this much of a hold, then gives up


def is_block(status, body):
    """Google's "your computer or network may be sending automated queries" page."""
    return status == 403 and (b'automated queries' in (body or b'') or b'<title>Sorry...</title>' in (body or b''))


class Blocked(Exception):
    """Raised for a request the broker didn't send, or gave up on, because the host is blocking us."""


class _Job:
    def __init__(self, key, host, args, priority):
        self.key = key
        self.host = host
        self.args = args
        self.priority = priority
        self.retried = False
        self.sent_at = 0
        self.done = threading.Event()
        self.result = None
        self.error = None

    def finish(self, result=None, error=None):
        self.result, self.error = result, error
        self.done.set()


class Broker:
    def __init__(self, send, workers=WORKERS, gaps=None, backoff=BACKOFF, background_gap=BACKGROUND_GAP,
                 max_hold_wait=MAX_HOLD_WAIT):
        """send(url, data, headers, method, timeout) -> (status, body), raising for HTTP errors; errors
        that carry .status and .body are checked for the block page."""
        self._send = send
        self._gaps = GAPS if gaps is None else gaps
        self._backoff = backoff
        self._background_gap = background_gap
        self._max_hold_wait = max_hold_wait
        self._cv = threading.Condition()
        self._queue = []
        self._order = itertools.count()
        self._jobs = {}  # key -> job, queued or running
        self._next_slot = {}  # host -> earliest time for its next request
        self._next_background = {}  # host -> earliest time for its next background request
        self._hold_started = {}  # host -> when its current hold began
        self._blocked_until = {}
        self._strikes = {}  # host -> blocks in a row
        self._stopped = False
        self._threads = [threading.Thread(target=self._work, name='youtube-net-%d' % i) for i in range(workers)]
        for thread in self._threads:
            thread.daemon = True
            thread.start()

    def request(self, url, data=None, headers=None, method=None, timeout=20, priority=FOREGROUND):
        """Queue a request and wait for it; returns (status, body) or raises what send raised (or Blocked)."""
        job = self.submit(url, data, headers, method, timeout, priority)
        job.done.wait()
        if job.error is not None:
            raise job.error
        return job.result

    def submit(self, url, data=None, headers=None, method=None, timeout=20, priority=FOREGROUND):
        host = urllib.parse.urlsplit(url).hostname or ''
        # Same method, URL, body and auth: one response serves everyone who asked.
        key = (method or ('POST' if data else 'GET'), url, data, (headers or {}).get('Authorization'))
        with self._cv:
            job = self._jobs.get(key)
            if job is not None:
                if priority < job.priority:
                    job.priority = priority  # takes effect when it is next queued
                return job
            job = _Job(key, host, (url, data, headers, method, timeout), priority)
            job.order = next(self._order)
            if priority == BACKGROUND and self._held_back(host):
                job.finish(error=Blocked('%s is holding requests back' % host))
                return job
            self._jobs[key] = job
            self._push(job)
            return job

    def stop(self):
        with self._cv:
            self._stopped = True
            self._cv.notify_all()

    def _held_back(self, host):
        return self._blocked_until.get(host, 0) > time.time()

    def _push(self, job):
        self._queue.append(job)
        self._cv.notify()

    def _next_ready(self):
        """With the lock held: take the most urgent job whose host is free now and reserve its slot.
        Returns (job, None), or (None, seconds until a host frees up / None when the queue is empty).
        Background jobs for a host that is holding back are dropped here."""
        now = time.time()
        soonest = None
        for job in sorted(self._queue, key=lambda j: (j.priority, j.order)):
            blocked = self._blocked_until.get(job.host, 0)
            # Background work is dropped during a hold; the screen waits a short hold out, not a long one.
            if blocked > now and (job.priority == BACKGROUND or blocked - now > self._max_hold_wait):
                self._queue.remove(job)
                self._jobs.pop(job.key, None)
                job.finish(error=Blocked('%s is holding requests back' % job.host))
                continue
            ready = max(blocked, self._next_slot.get(job.host, 0))
            paced = job.host in self._gaps
            if job.priority == BACKGROUND and paced:
                ready = max(ready, self._next_background.get(job.host, 0))
            if ready <= now:
                self._queue.remove(job)
                self._next_slot[job.host] = now + self._gaps.get(job.host, 0)
                if job.priority == BACKGROUND and paced:
                    self._next_background[job.host] = now + self._background_gap
                job.sent_at = now
                return job, None
            soonest = ready if soonest is None else min(soonest, ready)
        return None, (None if soonest is None else soonest - now)

    def _work(self):
        """A worker thread: take the next job whose host is ready, send it, hand back the result.
        A block page (YouTube's "unusual traffic" answer) puts the host on hold; a foreground job is
        then queued again once, to run when the hold ends, and anything else fails as blocked."""
        while True:
            with self._cv:
                while True:
                    if self._stopped:
                        return
                    job, wait = self._next_ready()
                    if job is not None:
                        break
                    self._cv.wait(wait)
            try:
                result = self._send(*job.args)
            except Exception as exc:  # handed back to the caller as is
                if is_block(getattr(exc, 'status', None), getattr(exc, 'body', b'')):
                    self._note_block(job)
                    exc.blocked = True
                    if job.priority == FOREGROUND and not job.retried:
                        job.retried = True
                        kodi.log('%s blocked us, retrying %s after the hold' % (job.host, job.args[0].split('?')[0]))
                        with self._cv:
                            self._push(job)
                        continue
                self._done(job, error=exc)
                continue
            with self._cv:
                self._strikes[job.host] = 0
            self._done(job, result=result)

    def _note_block(self, job):
        host = job.host
        with self._cv:
            if job.sent_at < self._hold_started.get(host, 0):
                return  # already in flight when the hold began: the same block, not another one
            strikes = self._strikes.get(host, 0)
            hold = self._backoff[min(strikes, len(self._backoff) - 1)]
            self._strikes[host] = strikes + 1
            self._hold_started[host] = time.time()
            self._blocked_until[host] = max(self._blocked_until.get(host, 0), time.time() + hold)
        kodi.log('%s sent its block page; holding requests to it for %ds' % (host, hold))

    def _done(self, job, result=None, error=None):
        with self._cv:
            if self._jobs.get(job.key) is job:
                del self._jobs[job.key]
        job.finish(result, error)
