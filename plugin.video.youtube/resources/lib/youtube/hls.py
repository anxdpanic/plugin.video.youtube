# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""A live stream's HLS master playlist cut down to one quality.

YouTube's live variants are video only: each names a separate audio rendition (#EXT-X-MEDIA), so a
variant's own playlist can't be played on its own. Playing one quality means a master playlist that
keeps the audio renditions and only that variant."""
import re
import urllib.parse

_ATTRIBUTE = re.compile(r'([A-Z0-9-]+)=("[^"]*"|[^,]*)')
_STREAM = '#EXT-X-STREAM-INF:'


def _attributes(line):
    return {key: value.strip('"') for key, value in _ATTRIBUTE.findall(line.split(':', 1)[1])}


def _streams(lines):
    """(index of the #EXT-X-STREAM-INF line, index of its URI line) for each variant."""
    for index, line in enumerate(lines):
        if line.startswith(_STREAM):
            uri = next((i for i in range(index + 1, len(lines)) if lines[i] and not lines[i].startswith('#')), None)
            if uri is not None:
                yield index, uri


def variants(playlist, base_url):
    """[(height, fps, url, bits per second)] of the playlist's video variants, best first and one per height
    and frame rate (the one with the most bandwidth). Height is the picture's short side, as for DASH
    formats. The rate is the average one where the playlist gives it, the peak otherwise."""
    lines = [line.strip() for line in playlist.splitlines()]
    best = {}
    for info, uri in _streams(lines):
        attrs = _attributes(lines[info])
        width, _, height = attrs.get('RESOLUTION', '').partition('x')
        if not (width.isdigit() and height.isdigit()):
            continue  # audio-only variants have no resolution
        key = (min(int(width), int(height)), round(float(attrs.get('FRAME-RATE') or 0)))
        bandwidth = int(attrs.get('BANDWIDTH') or 0)
        if key not in best or bandwidth > best[key][0]:
            rate = int(attrs.get('AVERAGE-BANDWIDTH') or bandwidth)
            best[key] = (bandwidth, urllib.parse.urljoin(base_url, lines[uri]), rate)
    return [(height, fps, best[(height, fps)][1], best[(height, fps)][2]) for height, fps in sorted(best, reverse=True)]


def keep_variant(playlist, base_url, url):
    """The master playlist with `url` (a variants() url) as its only variant, every other line (the audio
    renditions above all) kept. URIs are made absolute, since the copy is served from elsewhere."""
    lines = [line.strip() for line in playlist.splitlines()]
    dropped = set()
    for info, uri in _streams(lines):
        absolute = urllib.parse.urljoin(base_url, lines[uri])
        if absolute == url:
            lines[uri] = absolute
        else:
            dropped.update((info, uri))
    return '\n'.join(line for index, line in enumerate(lines) if index not in dropped) + '\n'
