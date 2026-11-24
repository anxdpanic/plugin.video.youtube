# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Artwork for the plugin's own menu entries, from resources/media. The TV interface has its own icons."""
import os

from . import kodi

TV_INTERFACE = os.path.join(kodi.ADDON_PATH, 'resources', 'tv', 'media', 'icon.png')

# Guide entries by id, then by words in their icon type -> image in resources/media.
BY_ID = {'search': 'search.png', 'shorts': 'shorts.png', 'FEwhat_to_watch': 'home.png', 'FEtopics': 'home.png',
         'FEsubscriptions': 'new_uploads.png', 'FEhistory': 'history.png', 'FElibrary': 'playlist.png',
         'FEmy_youtube': 'playlist.png', 'FEplaylist_aggregation': 'playlist.png', 'FEtrending': 'trending.png',
         'VLWL': 'watch_later.png', 'VLLL': 'likes.png'}
BY_TYPE = (('WHAT_TO_WATCH', 'home.png'), ('HOME', 'home.png'), ('SUBSCRIPTION', 'new_uploads.png'),
           ('HISTORY', 'history.png'), ('WATCH_LATER', 'watch_later.png'), ('LIKE', 'likes.png'),
           ('LIBRARY', 'playlist.png'), ('PLAYLIST', 'playlist.png'), ('BOOKMARK', 'playlist.png'),
           ('TRENDING', 'trending.png'), ('FIRE', 'trending.png'), ('LIVE', 'live.png'),
           ('SEARCH', 'search.png'), ('SHORTS', 'shorts.png'))


def media(name):
    return kodi.icon_path(name)


def menu_entry(entry, fallback):
    """The image for a guide entry, or `fallback` (a Kodi default icon) when none fits."""
    name = BY_ID.get(entry['id'])
    if not name:
        icon_type = (entry.get('icon') or '').upper()
        name = next((n for word, n in BY_TYPE if word in icon_type), None)
    return media(name) if name else fallback
