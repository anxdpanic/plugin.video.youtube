# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Paths shaped like those of earlier plugin.video.youtube versions, so .strm files, keymaps and favourites
written for them keep working: plugin://plugin.video.youtube/play/?video_id=... and the like.

translate() turns such a path into one of the add-on's own routes before dispatch. Its own routes are
never rewritten."""
import re


def _search(params):
    return 'search', {'q': params['q']} if params.get('q') else {}


def _playlist(match, params):
    return 'browse', {'id': 'VL' + match.group('id')}


def _play(params):
    if params.get('playlist_id'):
        mapped = {'list': params['playlist_id'], 'order': params.get('order'), 'v': params.get('video_id')}
        return 'play_playlist', mapped
    if params.get('video_id'):
        return 'play', {'v': params['video_id'], 't': params.get('seek') or params.get('start')}
    return None


# (pattern, handler): handler(match, params) -> (route, params) or None to leave the path alone.
ALIASES = (
    (r'home', lambda m, p: ('', {})),
    (r'play', lambda m, p: _play(p)),
    (r'channel/mine/playlists', lambda m, p: ('browse', {'id': 'FEplaylist_aggregation'})),
    (r'(?:channel/[^/]+/)?playlist/(?P<id>[^/]+)', _playlist),
    (r'channel/(?P<id>UC[^/]+)', lambda m, p: ('browse', {'id': m.group('id')})),
    (r'special/related_videos', lambda m, p: ('related', {'v': p.get('video_id')})),
    (r'special/recommendations', lambda m, p: ('browse', {'id': 'FEwhat_to_watch'})),
    (r'special/my_subscriptions', lambda m, p: ('browse', {'id': 'FEsubscriptions'})),
    (r'special/saved_playlists', lambda m, p: ('browse', {'id': 'FEplaylist_aggregation'})),
    (r'subscriptions/list', lambda m, p: ('browse', {'id': 'FEsubscriptions', 'tabs': '1'})),
    (r'(?:kodion/)?search(?:/query)?', lambda m, p: _search(p)),
    (r'(?:kodion/)?search/input', lambda m, p: ('search/new', {})),
    (r'(?:kodion/)?search/list', lambda m, p: ('search', {})),
    (r'kodion/search/remove', lambda m, p: ('search/remove', {'q': p.get('q')})),
    (r'kodion/playback_history(?:/list)?', lambda m, p: ('browse', {'id': 'FEhistory'})),
    (r'kodion/watch_later(?:/list)?', lambda m, p: ('browse', {'id': 'VLWL'})),
)
_COMPILED = tuple((re.compile(pattern + '$'), handler) for pattern, handler in ALIASES)


def translate(route, params, native):
    """(route, params) for the add-on. `route` has no leading or trailing slash; `native` is the set of
    its own routes, which pass through unchanged (except search and play, whose own
    parameters tell them apart)."""
    if route in native and route not in ('search', 'play'):
        return route, params
    if route == 'search' and 'q' in params or route == 'play' and 'v' in params:
        return route, params
    for pattern, handler in _COMPILED:
        match = pattern.match(route)
        if match:
            result = handler(match, params)
            if result is None:
                return route, params
            new_route, new_params = result
            return new_route, {k: v for k, v in new_params.items() if v not in (None, '')}
    return route, params
