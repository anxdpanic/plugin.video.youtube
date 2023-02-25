# -*- coding: utf-8 -*-
"""

    Copyright (C) 2017-2019 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import re

from youtube_plugin.youtube.provider import Provider
from youtube_plugin.kodion.impl import Context


def _get_core_components(addon_id=None):
    provider = Provider()
    if addon_id is not None:
        context = Context(params={'addon_id': addon_id}, plugin_id='plugin.video.youtube')
    else:
        context = Context(plugin_id='plugin.video.youtube')
    client = provider.get_client(context=context)

    return provider, context, client


def resolve(video_id, sort=True, addon_id=None):
    """

    :param video_id: video id / video url
    :param sort: sort results by quality highest->lowest
    :param addon_id: addon id associated with developer keys to use for requests
    :type video_id: str
    :type sort: bool
    :type addon_id: str
    :return: all video items (resolved urls and metadata) for the given video id
    :rtype: list of dict
    """
    provider, context, client = _get_core_components(addon_id)
    matched_id = None
    streams = None

    patterns = [r'(?P<video_id>[\w-]{11})',
                r'(?:http)*s*:*[/]{0,2}(?:w{3}\.|m\.)*youtu(?:\.be/|be\.com/'
                r'(?:embed/|watch/|v/|.*?[?&/]v=))(?P<video_id>[\w-]{11}).*']

    for pattern in patterns:
        v_id = re.search(pattern, video_id)
        if v_id:
            matched_id = v_id.group('video_id')
            break

    if matched_id:
        streams = client.get_video_streams(context=context, video_id=matched_id)

    if sort and streams:
        streams = sorted(streams, key=lambda x: x.get('sort', 0), reverse=True)

    return streams
