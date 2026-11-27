# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Settings > Maintenance: clear what the add-on keeps on disk, for when something is corrupt or for testing.

Only caches and leftovers are cleared here. Accounts, settings and the menu layout are left alone; they have
their own Sign out and Reset menu actions."""
import os
import re
import shutil

import xbmc

from . import art, descriptions, kodi

PLAYING_MANIFEST = re.compile(r'/(?:mpd|hls)/([A-Za-z0-9_-]{11})\.(?:mpd|m3u8)')

def _size(path):
    if os.path.isdir(path):
        return sum(_size(os.path.join(path, name)) for name in os.listdir(path))
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def _remove(path):
    """Remove a file or folder; returns the bytes freed (0 when it wasn't there)."""
    size = _size(path) if os.path.exists(path) else 0
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            return 0
    return size


def _playing_video():
    """The video the add-on is playing right now, if any: its manifest and subtitles must stay."""
    player = xbmc.Player()
    try:
        if player.isPlayingVideo():
            match = PLAYING_MANIFEST.search(player.getPlayingFile())
            return match.group(1) if match else None
    except RuntimeError:
        pass
    return None


def clear_cache():
    return _remove(kodi.CACHE_DIR)


def clear_temp():
    if not os.path.isdir(kodi.TEMP_DIR):
        return 0
    keep = _playing_video()
    freed = 0
    for name in os.listdir(kodi.TEMP_DIR):
        if keep and name.startswith(keep + '.'):
            continue
        freed += _remove(os.path.join(kodi.TEMP_DIR, name))
    return freed


def clear_art():
    return sum(_remove(os.path.join(kodi.PROFILE, name)) for name in (art.STORE, descriptions.STORE))


def _clear_state_key(key):
    state = kodi.load_json('state.json', {})
    if key not in state:
        return 0
    freed = len(repr(state.pop(key)))
    kodi.save_json('state.json', state)
    return max(freed, 1)


def clear_search_history():
    return _clear_state_key('search_history')


def clear_visitor():
    """YouTube's anonymous visitor ID; a fresh one is fetched with the next request."""
    return _clear_state_key('visitor')


ACTIONS = {
    'cache': (30151, clear_cache),
    'temp': (30152, clear_temp),
    'art': (30153, clear_art),
    'search': (30154, clear_search_history),
    'visitor': (30155, clear_visitor),
}


EACH = tuple(action for _, action in ACTIONS.values())


def clear_all():
    return sum(action() for action in EACH)


ACTIONS['all'] = (30156, clear_all)


def human_size(size):
    for unit in ('B', 'KB', 'MB'):
        if size < 1024 or unit == 'MB':
            return ('%d %s' if unit == 'B' else '%.1f %s') % (size, unit)
        size /= 1024.0
    return ''
