# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Paths shaped like those of earlier plugin.video.youtube versions, so .strm files, keymaps and favourites
written for them keep working: plugin://plugin.video.youtube/play/?video_id=... and the like.

translate() turns such a path into one of the add-on's own routes before dispatch. Its own routes are
never rewritten."""
import re
import urllib.parse


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


VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')
YOUTUBE_HOSTS = ('youtube.com', 'youtu.be', 'youtube-nocookie.com')
# Paths whose next segment is a video id: youtube.com/shorts/ID, /live/ID, /embed/ID, /v/ID.
VIDEO_PATHS = ('shorts', 'live', 'embed', 'v')


def _seconds(value):
    """A start time as YouTube writes it in a link ('90', '90s', '1m30s', '1h2m3s') in seconds, as text;
    None when it doesn't read as one."""
    if not value or not re.fullmatch(r'(?:\d+[hms]?)+', value):
        return None
    units = {'h': 3600, 'm': 60}
    return str(sum(int(number) * units.get(unit, 1) for number, unit in re.findall(r'(\d+)([hms]?)', value)))


def _link_video(host, segments, query):
    """The video id a YouTube link points at, or None."""
    if host == 'youtu.be' and segments:
        candidate = segments[0]
    elif len(segments) > 1 and segments[0] in VIDEO_PATHS:
        candidate = segments[1]
    else:
        candidate = query.get('v')
    return candidate if candidate and VIDEO_ID.match(candidate) else None


def _uri(params):
    """A YouTube web address handed over as uri=..., as phone remotes like Yatse do when a link is shared to
    Kodi: plays the video (from its t=), or the playlist, or opens the channel. None for anything else."""
    parts = urllib.parse.urlsplit(params.get('uri') or '')
    host = (parts.hostname or '').lower()
    if not any(host == h or host.endswith('.' + h) for h in YOUTUBE_HOSTS):
        return None
    query = dict(urllib.parse.parse_qsl(parts.query))
    # An address passed without encoding leaves everything after its first & in the plugin's own query.
    query.update({k: v for k, v in params.items() if k != 'uri' and k not in query})
    segments = [s for s in parts.path.split('/') if s]
    video_id = _link_video(host, segments, query)
    if video_id:
        return 'play', {'v': video_id, 't': _seconds(query.get('t') or query.get('start'))}
    if query.get('list'):
        return 'play_playlist', {'list': query['list']}
    if len(segments) > 1 and segments[0] == 'channel' and segments[1].startswith('UC'):
        return 'browse', {'id': segments[1]}
    return None


# (pattern, handler): handler(match, params) -> (route, params) or None to leave the path alone.
ALIASES = (
    (r'home', lambda m, p: ('', {})),
    (r'play', lambda m, p: _play(p)),
    (r'uri2addon', lambda m, p: _uri(p)),
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
