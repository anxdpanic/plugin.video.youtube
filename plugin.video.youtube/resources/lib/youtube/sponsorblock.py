# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""SponsorBlock: skip the parts of a video its viewers marked (sponsor messages, intros, ...). Kodi skips
them itself from an EDL file named by the EDLPath property; where Kodi lacks that property, or the seek
setting asks for it, the plugin leaves the segments here and the service seeks past each one."""
import hashlib
import json
import threading
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui

from . import http, kodi

API_URL = 'https://sponsor.ajay.app/api/skipSegments/'
EDL_SCENE_MARKER, EDL_COMMERCIAL_BREAK = 2, 3
EDL_PATH_MIN_PYTHON_API = (3, 1, 1)  # the first xbmc.python whose Kodi honours EDLPath
PROPERTY = 'youtube.skip_segments'
POLL = 0.5  # seconds between position checks while seeking past segments


def edl_path_supported():
    try:
        version = xbmcaddon.Addon('xbmc.python').getAddonInfo('version')
        return tuple(int(part) for part in version.split('.')[:3]) >= EDL_PATH_MIN_PYTHON_API
    except (RuntimeError, ValueError):
        return False


def merge(segments, max_gap=1.0):
    """Sorted (start, end) pairs, with overlapping or nearly touching segments joined."""
    merged = []
    for start, end in sorted(segments):
        if merged and start <= merged[-1][1] + max_gap:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def fetch(video_id, categories):
    """The video's skip segments; [] when it has none or the lookup fails."""
    # Asked for by hash prefix, so the server doesn't learn which video plays
    prefix = hashlib.sha256(video_id.encode('utf-8')).hexdigest()[:4]
    url = API_URL + prefix + '?' + urllib.parse.urlencode({'categories': json.dumps(categories),
                                                           'actionType': 'skip'})
    try:
        # Not http.request: the broker only forwards to Google's hosts
        _, body = http.send(url, timeout=3)
        videos = json.loads(body.decode('utf-8'))
    except (http.HTTPError, ValueError):  # 404 is the answer for no segments
        return []
    for video in videos:
        if video.get('videoID') == video_id:
            return merge(tuple(s['segment']) for s in video.get('segments', ())
                         if s.get('actionType') == 'skip')
    return []


def write_edl(video_id, segments, action):
    if action == EDL_SCENE_MARKER:
        lines = ['%.3f\t%.3f\t%d\n' % (t, t, action) for segment in segments for t in segment]
    else:
        lines = ['%.3f\t%.3f\t%d\n' % (start, end, action) for start, end in segments]
    path = kodi.temp_file('%s.edl' % video_id)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.writelines(lines)
    return path


def apply(li, video_id):
    """From the plugin: skip or mark the segments of the video `li` plays, as the settings ask."""
    if not kodi.setting_bool('sponsorblock'):
        return
    categories = [c for c in kodi.setting('sponsorblock_categories').split(',') if c]
    segments = fetch(video_id, categories) if categories else []
    if not segments:
        return
    action = kodi.setting_int('sponsorblock_action')
    # Seeking only ever skips: markers need the EDL file, whatever the (then disabled) seek setting holds.
    seek = action == EDL_COMMERCIAL_BREAK and kodi.setting_bool('sponsorblock_seek')
    if not seek and edl_path_supported():
        li.setProperty('EDLPath', write_edl(video_id, segments, action))
    elif action == EDL_COMMERCIAL_BREAK:
        xbmcgui.Window(10000).setProperty(PROPERTY, json.dumps({'v': video_id, 'segments': segments}))


class Skipper(xbmc.Player):
    """Lives in the service; seeks past the segments of a video the plugin asked it to skip."""

    def __init__(self):
        xbmc.Player.__init__(self)
        self.playing = None

    def onAVStarted(self):  # noqa: N802 (Kodi API)
        self.playing = None
        window = xbmcgui.Window(10000)
        raw = window.getProperty(PROPERTY)
        if not raw:
            return
        window.clearProperty(PROPERTY)
        wanted = json.loads(raw)
        try:
            if wanted['v'] not in self.getPlayingFile():
                return
        except RuntimeError:
            return
        self.playing = wanted
        thread = threading.Thread(target=self._watch, args=(wanted,), name='youtube-sponsorblock')
        thread.daemon = True
        thread.start()

    def _watch(self, wanted):
        segments = wanted['segments']
        monitor = xbmc.Monitor()
        while segments and self.playing is wanted and not monitor.waitForAbort(POLL):
            self.step(segments)

    def step(self, segments):
        """Seek past the segment playback is in, if any, once: seeking back into it later plays it."""
        try:
            now = self.getTime()
        except RuntimeError:
            return
        for segment in segments:
            if segment[0] <= now < segment[1]:
                segments.remove(segment)
                self.seekTime(segment[1])
                return

    def onPlayBackStopped(self):  # noqa: N802
        self.playing = None

    def onPlayBackEnded(self):  # noqa: N802
        self.playing = None

    def onPlayBackError(self):  # noqa: N802
        self.playing = None
