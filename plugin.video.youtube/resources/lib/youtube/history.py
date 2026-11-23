# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Report playback to YouTube so watched videos land in the signed-in account's history and keep
their progress. The streams come from anonymous player requests, whose stats URLs YouTube doesn't
tie to the account, so the service asks the TV client's player for the account's own stats URLs
and pings them while the video plays."""
import json
import threading
import time
import urllib.parse

import xbmc
import xbmcgui

from . import auth, http, innertube, kodi

PROPERTY = 'youtube.tracking'
INTERVAL = 30


def tracking_info(player_resp, ua):
    """The stats URLs to report a playback with, or None when YouTube gave none."""
    tracking = (player_resp or {}).get('playbackTracking', {})
    playback = tracking.get('videostatsPlaybackUrl', {}).get('baseUrl')
    watchtime = tracking.get('videostatsWatchtimeUrl', {}).get('baseUrl')
    if not playback or not watchtime:
        return None
    try:
        length = int(player_resp.get('videoDetails', {}).get('lengthSeconds') or 0)
    except ValueError:
        length = 0
    return {'playback': playback, 'watchtime': watchtime, 'ua': ua, 'length': length}


def stats_url(base, params):
    parts = urllib.parse.urlsplit(base)
    query = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
    query.update({k: str(v) for k, v in params.items()})
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


class Session:
    """One playback of one video: a playback ping at the start, watch-time segments after."""

    def __init__(self, info, send=None):
        self.info = info
        self.cpn = innertube.new_cpn()
        self.started = time.time()
        self.last_report = self.started
        self.position = 0.0
        self.segment_start = 0.0
        self.send = send or _send

    def _params(self, position, **extra):
        params = {'ver': 2, 'cpn': self.cpn, 'cmt': '%.3f' % position,
                  'rt': '%.3f' % (time.time() - self.started), 'el': 'detailpage'}
        if self.info.get('length'):
            params['len'] = self.info['length']
        params.update(extra)
        return params

    def start(self, position):
        self.position = self.segment_start = position
        self.send(stats_url(self.info['playback'], self._params(position)), self.info['ua'])

    def update(self, position, state='playing', final=False, force=False):
        """Called every few seconds while playing; reports a segment every INTERVAL seconds."""
        if position is not None:
            self.position = position
        if not force and time.time() - self.last_report < INTERVAL:
            return
        extra = {'st': '%.3f' % self.segment_start, 'et': '%.3f' % self.position, 'state': state}
        if final:
            extra['final'] = 1
        self.send(stats_url(self.info['watchtime'], self._params(self.position, **extra)), self.info['ua'])
        self.last_report = time.time()
        self.segment_start = self.position

    def seeked(self, position):
        """Close the segment before the jump, so it doesn't count the skipped part as watched."""
        self.update(None, force=True)
        self.position = self.segment_start = position


def _send(url, ua):
    def run():
        try:
            token = auth.access_token()
        except auth.AuthError:
            token = None
        if not token:
            return
        headers = {'User-Agent': ua, 'Authorization': 'Bearer ' + token}
        try:
            http.request(url, headers=headers, timeout=10, priority=http.BACKGROUND)
        except http.HTTPError as exc:
            kodi.log('history report failed: %s' % exc)
    thread = threading.Thread(target=run, name='youtube-history')
    thread.daemon = True
    thread.start()


def publish(video_id, path):
    """From the plugin: tell the service which video it is about to play."""
    xbmcgui.Window(10000).setProperty(PROPERTY, json.dumps({'video_id': video_id, 'path': path}))


def _account_stats(video_id):
    resp = innertube.InnerTube(priority=http.BACKGROUND).player_tracking(video_id)
    return tracking_info(resp, innertube.TV['ua'])


class Tracker(xbmc.Player):
    """Lives in the service; watches Kodi's player for videos the plugin started."""

    def __init__(self, stats=None):
        xbmc.Player.__init__(self)
        self.session = None
        self.paused = False
        self.playing = None  # the claimed playback, so a late answer for an old one is dropped
        self.stats = stats or _account_stats

    def _claim(self):
        window = xbmcgui.Window(10000)
        raw = window.getProperty(PROPERTY)
        window.clearProperty(PROPERTY)
        if not raw:
            return None
        info = json.loads(raw)
        try:
            playing = self.getPlayingFile()
        except RuntimeError:
            return None
        # Only the video the plugin just resolved, not whatever else Kodi plays next.
        if playing != info['path'] and info['video_id'] not in playing:
            return None
        return info

    def _time(self):
        try:
            return self.getTime()
        except RuntimeError:
            return None

    def onAVStarted(self):  # noqa: N802 (Kodi API)
        self.finish()
        self.paused = False
        claimed = self._claim()
        self.playing = claimed
        if claimed:
            thread = threading.Thread(target=self._begin, args=(claimed, self._time() or 0.0),
                                      name='youtube-history')
            thread.daemon = True
            thread.start()

    def _begin(self, claimed, position):
        try:
            info = self.stats(claimed['video_id'])
        except (innertube.InnerTubeError, http.HTTPError) as exc:
            kodi.log('no history stats for %s: %s' % (claimed['video_id'], exc))
            return
        if not info or self.playing is not claimed:
            return
        kodi.log('reporting %s to history' % claimed['video_id'])
        session = Session(info)
        session.start(position)
        self.session = session

    def onPlayBackSeek(self, time_ms, offset_ms):  # noqa: N802
        if self.session:
            self.session.seeked(time_ms / 1000.0)

    def onPlayBackPaused(self):  # noqa: N802
        self.paused = True
        if self.session:
            self.session.update(self._time(), state='paused', force=True)

    def onPlayBackResumed(self):  # noqa: N802
        self.paused = False

    def onPlayBackStopped(self):  # noqa: N802
        self.finish()

    def onPlayBackEnded(self):  # noqa: N802
        self.finish()

    def onPlayBackError(self):  # noqa: N802
        self.finish()

    def tick(self):
        if self.session and not self.paused and self.isPlaying():
            self.session.update(self._time())

    def finish(self):
        self.playing = None
        if self.session:
            self.session.update(None, state='paused', final=True, force=True)
            self.session = None
