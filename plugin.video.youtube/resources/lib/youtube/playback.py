# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Starting a video part way in. Kodi ignores StartOffset on an item a plugin resolves when the item it
was asked to play didn't carry one (a .strm file, a favourite, Player.Open), so the plugin leaves the start
time here and the service seeks once the video is playing."""
import json

import xbmc
import xbmcgui

PROPERTY = 'youtube.start_at'
TOLERANCE = 2.0  # seconds: already this close (StartOffset did work), so don't seek again


def request(video_id, seconds):
    """From the plugin: start this video at `seconds` once it plays."""
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        return
    if seconds > 0:
        xbmcgui.Window(10000).setProperty(PROPERTY, json.dumps({'v': video_id, 't': seconds}))


class StartAt(xbmc.Player):
    """Lives in the service; seeks a video the plugin asked to start part way in."""

    def onAVStarted(self):  # noqa: N802 (Kodi API)
        window = xbmcgui.Window(10000)
        raw = window.getProperty(PROPERTY)
        if not raw:
            return
        window.clearProperty(PROPERTY)
        wanted = json.loads(raw)
        try:
            if wanted['v'] in self.getPlayingFile() and abs(self.getTime() - wanted['t']) > TOLERANCE:
                self.seekTime(wanted['t'])
        except RuntimeError:  # playback already ended
            pass
