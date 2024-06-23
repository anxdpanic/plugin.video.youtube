# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-present plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import os
import random
import re
from traceback import format_stack

from .ratebypass import ratebypass
from .signature.cipher import Cipher
from .subtitles import Subtitles
from .utils import THUMB_TYPES
from ..client.request_client import YouTubeRequestClient
from ..youtube_exceptions import InvalidJSON, YouTubeException
from ...kodion.compatibility import (
    parse_qs,
    quote,
    unescape,
    unquote,
    urlencode,
    urljoin,
    urlsplit,
    xbmcvfs,
)
from ...kodion.constants import TEMP_PATH, paths
from ...kodion.network import get_connect_address
from ...kodion.utils import make_dirs, redact_ip_from_url


class VideoInfo(YouTubeRequestClient):
    BASE_PATH = make_dirs(TEMP_PATH)

    FORMAT = {
        # === Non-DASH ===
        '5': {'container': 'flv',
              'title': '240p',
              'sort': [240, 0],
              'video': {'height': 240, 'codec': 'h.263'},
              'audio': {'bitrate': 64, 'codec': 'mp3'}},
        '6': {'container': 'flv',  # Discontinued
              'discontinued': True,
              'video': {'height': 270, 'codec': 'h.263'},
              'audio': {'bitrate': 64, 'codec': 'mp3'}},
        '13': {'container': '3gp',  # Discontinued
               'discontinued': True,
               'video': {'codec': 'h.264'},
               'audio': {'codec': 'aac'}},
        '17': {'container': '3gp',
               'title': '144p',
               'video': {'height': 144, 'codec': 'h.264'},
               'audio': {'bitrate': 24, 'codec': 'aac'}},
        '18': {'container': 'mp4',
               'title': '360p',
               'video': {'height': 360, 'codec': 'h.264'},
               'audio': {'bitrate': 96, 'codec': 'aac'}},
        '22': {'container': 'mp4',
               'title': '720p',
               'video': {'height': 720, 'codec': 'h.264'},
               'audio': {'bitrate': 192, 'codec': 'aac'}},
        '34': {'container': 'flv',  # Discontinued
               'discontinued': True,
               'video': {'height': 360, 'codec': 'h.264'},
               'audio': {'bitrate': 128, 'codec': 'aac'}},
        '35': {'container': 'flv',  # Discontinued
               'discontinued': True,
               'video': {'height': 480, 'codec': 'h.264'},
               'audio': {'bitrate': 128, 'codec': 'aac'}},
        '36': {'container': '3gp',
               'title': '240p',
               'video': {'height': 240, 'codec': 'h.264'},
               'audio': {'bitrate': 32, 'codec': 'aac'}},
        '37': {'container': 'mp4',
               'title': '1080p',
               'video': {'height': 1080, 'codec': 'h.264'},
               'audio': {'bitrate': 192, 'codec': 'aac'}},
        '38': {'container': 'mp4',
               'title': '3072p',
               'video': {'height': 3072, 'codec': 'h.264'},
               'audio': {'bitrate': 192, 'codec': 'aac'}},
        '43': {'container': 'webm',
               'title': '360p',
               'video': {'height': 360, 'codec': 'vp8'},
               'audio': {'bitrate': 128, 'codec': 'vorbis'}},
        '44': {'container': 'webm',  # Discontinued
               'discontinued': True,
               'video': {'height': 480, 'codec': 'vp8'},
               'audio': {'bitrate': 128, 'codec': 'vorbis'}},
        '45': {'container': 'webm',  # Discontinued
               'discontinued': True,
               'video': {'height': 720, 'codec': 'vp8'},
               'audio': {'bitrate': 192, 'codec': 'vorbis'}},
        '46': {'container': 'webm',  # Discontinued
               'discontinued': True,
               'video': {'height': 1080, 'codec': 'vp8'},
               'audio': {'bitrate': 192, 'codec': 'vorbis'}},
        '59': {'container': 'mp4',
               'title': '480p',
               'video': {'height': 480, 'codec': 'h.264'},
               'audio': {'bitrate': 96, 'codec': 'aac'}},
        '78': {'container': 'mp4',
               'title': '360p',
               'video': {'height': 360, 'codec': 'h.264'},
               'audio': {'bitrate': 96, 'codec': 'aac'}},
        # === 3D ===
        '82': {'container': 'mp4',
               '3D': True,
               'title': '3D 360p',
               'video': {'height': 360, 'codec': 'h.264'},
               'audio': {'bitrate': 96, 'codec': 'aac'}},
        '83': {'container': 'mp4',
               '3D': True,
               'title': '3D 240p',
               'video': {'height': 240, 'codec': 'h.264'},
               'audio': {'bitrate': 96, 'codec': 'aac'}},
        '84': {'container': 'mp4',
               '3D': True,
               'title': '3D 720p',
               'video': {'height': 720, 'codec': 'h.264'},
               'audio': {'bitrate': 192, 'codec': 'aac'}},
        '85': {'container': 'mp4',
               '3D': True,
               'title': '3D 1080p',
               'video': {'height': 1080, 'codec': 'h.264'},
               'audio': {'bitrate': 192, 'codec': 'aac'}},
        '100': {'container': 'webm',
                '3D': True,
                'title': '3D 360p',
                'video': {'height': 360, 'codec': 'vp8'},
                'audio': {'bitrate': 128, 'codec': 'vorbis'}},
        '101': {'container': 'webm',  # Discontinued
                'discontinued': True,
                '3D': True,
                'title': '3D 360p',
                'video': {'height': 360, 'codec': 'vp8'},
                'audio': {'bitrate': 192, 'codec': 'vorbis'}},
        '102': {'container': 'webm',  # Discontinued
                'discontinued': True,
                '3D': True,
                'video': {'height': 720, 'codec': 'vp8'},
                'audio': {'bitrate': 192, 'codec': 'vorbis'}},
        # === Live Streams ===
        '91': {'container': 'ts',
               'title': '144p',
               'video': {'height': 144, 'codec': 'h.264'},
               'audio': {'bitrate': 48, 'codec': 'aac'}},
        '92': {'container': 'ts',
               'title': '240p',
               'video': {'height': 240, 'codec': 'h.264'},
               'audio': {'bitrate': 48, 'codec': 'aac'}},
        '93': {'container': 'ts',
               'title': '360p',
               'video': {'height': 360, 'codec': 'h.264'},
               'audio': {'bitrate': 128, 'codec': 'aac'}},
        '94': {'container': 'ts',
               'title': '480p',
               'video': {'height': 480, 'codec': 'h.264'},
               'audio': {'bitrate': 128, 'codec': 'aac'}},
        '95': {'container': 'ts',
               'title': '720p',
               'video': {'height': 720, 'codec': 'h.264'},
               'audio': {'bitrate': 256, 'codec': 'aac'}},
        '96': {'container': 'ts',
               'title': '1080p',
               'video': {'height': 1080, 'codec': 'h.264'},
               'audio': {'bitrate': 256, 'codec': 'aac'}},
        '120': {'container': 'flv',  # Discontinued
                'discontinued': True,
                'live': True,
                'title': 'Live 720p',
                'video': {'height': 720, 'codec': 'h.264'},
                'audio': {'bitrate': 128, 'codec': 'aac'}},
        '127': {'container': 'ts',
                'live': True,
                'audio': {'bitrate': 96, 'codec': 'aac'}},
        '128': {'container': 'ts',
                'live': True,
                'audio': {'bitrate': 96, 'codec': 'aac'}},
        '132': {'container': 'ts',
                'title': '240p',
                'video': {'height': 240, 'codec': 'h.264'},
                'audio': {'bitrate': 48, 'codec': 'aac'}},
        '151': {'container': 'ts',
                'live': True,
                'unsupported': True,
                'title': 'Live 72p',
                'video': {'height': 72, 'codec': 'h.264'},
                'audio': {'bitrate': 24, 'codec': 'aac'}},
        '300': {'container': 'ts',
                'title': '720p',
                'video': {'height': 720, 'codec': 'h.264'},
                'audio': {'bitrate': 128, 'codec': 'aac'}},
        '301': {'container': 'ts',
                'title': '1080p',
                'video': {'height': 1080, 'codec': 'h.264'},
                'audio': {'bitrate': 128, 'codec': 'aac'}},
        # === DASH (video only)
        '133': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 240, 'codec': 'h.264'}},
        '134': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 360, 'codec': 'h.264'}},
        '135': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 480, 'codec': 'h.264'}},
        '136': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 720, 'codec': 'h.264'}},
        '137': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 1080, 'codec': 'h.264'}},
        '138': {'container': 'mp4',  # Discontinued
                'discontinued': True,
                'dash/video': True,
                'video': {'height': 2160, 'codec': 'h.264'}},
        '160': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 144, 'codec': 'h.264'}},
        '167': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 360, 'codec': 'vp8'}},
        '168': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 480, 'codec': 'vp8'}},
        '169': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 720, 'codec': 'vp8'}},
        '170': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 1080, 'codec': 'vp8'}},
        '218': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 480, 'codec': 'vp8'}},
        '219': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 480, 'codec': 'vp8'}},
        '242': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 240, 'codec': 'vp9'}},
        '243': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 360, 'codec': 'vp9'}},
        '244': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 480, 'codec': 'vp9'}},
        '247': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 720, 'codec': 'vp9'}},
        '248': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 1080, 'codec': 'vp9'}},
        '264': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 1440, 'codec': 'h.264'}},
        '266': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 2160, 'codec': 'h.264'}},
        '271': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 1440, 'codec': 'vp9'}},
        '272': {'container': 'webm',  # was VP9 2160p30
                'dash/video': True,
                'fps': 60,
                'video': {'height': 4320, 'codec': 'vp9'}},
        '278': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 144, 'codec': 'vp9'}},
        '298': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'video': {'height': 720, 'codec': 'h.264'}},
        '299': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'video': {'height': 1080, 'codec': 'h.264'}},
        '302': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'video': {'height': 720, 'codec': 'vp9'}},
        '303': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'video': {'height': 1080, 'codec': 'vp9'}},
        '308': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'video': {'height': 1440, 'codec': 'vp9'}},
        '313': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 2160, 'codec': 'vp9'}},
        '315': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'video': {'height': 2160, 'codec': 'vp9'}},
        '330': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 144, 'codec': 'vp9.2'}},
        '331': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 240, 'codec': 'vp9.2'}},
        '332': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 360, 'codec': 'vp9.2'}},
        '333': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 480, 'codec': 'vp9.2'}},
        '334': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 720, 'codec': 'vp9.2'}},
        '335': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 1080, 'codec': 'vp9.2'}},
        '336': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 1440, 'codec': 'vp9.2'}},
        '337': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 2160, 'codec': 'vp9.2'}},
        '394': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 144, 'codec': 'av1'}},
        '395': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 240, 'codec': 'av1'}},
        '396': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 360, 'codec': 'av1'}},
        '397': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 480, 'codec': 'av1'}},
        '398': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 720, 'codec': 'av1'}},
        '399': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 1080, 'codec': 'av1'}},
        '400': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 1440, 'codec': 'av1'}},
        '401': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 2160, 'codec': 'av1'}},
        '402': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 4320, 'codec': 'av1'}},
        '571': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 4320, 'codec': 'av1'}},
        '694': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 144, 'codec': 'av1'}},
        '695': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 240, 'codec': 'av1'}},
        '696': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 360, 'codec': 'av1'}},
        '697': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 480, 'codec': 'av1'}},
        '698': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 720, 'codec': 'av1'}},
        '699': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 1080, 'codec': 'av1'}},
        '700': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 1440, 'codec': 'av1'}},
        '701': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 2160, 'codec': 'av1'}},
        '702': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 4320, 'codec': 'av1'}},
        # === Dash (audio only)
        '139': {'container': 'mp4',
                'title': 'he-aac@48',
                'dash/audio': True,
                'audio': {'bitrate': 48, 'codec': 'aac'}},
        '140': {'container': 'mp4',
                'title': 'aac-lc@128',
                'dash/audio': True,
                'audio': {'bitrate': 128, 'codec': 'aac'}},
        '141': {'container': 'mp4',
                'title': 'aac-lc@256',
                'dash/audio': True,
                'audio': {'bitrate': 256, 'codec': 'aac'}},
        '256': {'container': 'mp4',
                'title': 'he-aac@192',
                'dash/audio': True,
                'audio': {'bitrate': 192, 'codec': 'aac'}},
        '258': {'container': 'mp4',
                'title': 'aac-lc@384',
                'dash/audio': True,
                'audio': {'bitrate': 384, 'codec': 'aac'}},
        '325': {'container': 'mp4',
                'title': 'dtse@384',
                'dash/audio': True,
                'audio': {'bitrate': 384, 'codec': 'dtse'}},
        '327': {'container': 'mp4',
                'title': 'aac-lc@256',
                'dash/audio': True,
                'audio': {'bitrate': 256, 'codec': 'aac'}},
        '328': {'container': 'mp4',
                'title': 'ec-3@384',
                'dash/audio': True,
                'audio': {'bitrate': 384, 'codec': 'ec-3'}},
        '171': {'container': 'webm',
                'title': 'vorbis@128',
                'dash/audio': True,
                'audio': {'bitrate': 128, 'codec': 'vorbis'}},
        '172': {'container': 'webm',
                'title': 'vorbis@192',
                'dash/audio': True,
                'audio': {'bitrate': 192, 'codec': 'vorbis'}},
        '249': {'container': 'webm',
                'title': 'opus@50',
                'dash/audio': True,
                'audio': {'bitrate': 50, 'codec': 'opus'}},
        '250': {'container': 'webm',
                'title': 'opus@70',
                'dash/audio': True,
                'audio': {'bitrate': 70, 'codec': 'opus'}},
        '251': {'container': 'webm',
                'title': 'opus@160',
                'dash/audio': True,
                'audio': {'bitrate': 160, 'codec': 'opus'}},
        '338': {'container': 'webm',
                'title': 'opus@480',
                'dash/audio': True,
                'audio': {'bitrate': 480, 'codec': 'opus'}},
        '380': {'container': 'mp4',
                'title': 'ac-3@384',
                'dash/audio': True,
                'audio': {'bitrate': 384, 'codec': 'ac-3'}},
        # === HLS
        '229': {'container': 'hls',
                'title': '240p',
                'hls/video': True,
                'video': {'height': 240, 'codec': 'h.264'}},
        '230': {'container': 'hls',
                'title': '360p',
                'hls/video': True,
                'video': {'height': 360, 'codec': 'h.264'}},
        '231': {'container': 'hls',
                'title': '480p',
                'hls/video': True,
                'video': {'height': 480, 'codec': 'h.264'}},
        '232': {'container': 'hls',
                'title': '720p',
                'hls/video': True,
                'video': {'height': 720, 'codec': 'h.264'}},
        '269': {'container': 'hls',
                'title': '144p',
                'hls/video': True,
                'video': {'height': 144, 'codec': 'h.264'}},
        '270': {'container': 'hls',
                'title': 'Premium 1080p',
                'hls/video': True,
                'video': {'height': 1080, 'codec': 'h.264'}},
        '311': {'container': 'hls',
                'title': '720p60',
                'hls/video': True,
                'fps': 60,
                'video': {'height': 720, 'codec': 'h.264'}},
        '312': {'container': 'hls',
                'title': 'Premium 1080p60',
                'hls/video': True,
                'fps': 60,
                'video': {'height': 1080, 'codec': 'h.264'}},
        '602': {'container': 'hls',
                'title': '144p15',
                'hls/video': True,
                'fps': 15,
                'video': {'height': 144, 'codec': 'vp9'}},
        '603': {'container': 'hls',
                'title': '144p',
                'hls/video': True,
                'video': {'height': 144, 'codec': 'vp9'}},
        '604': {'container': 'hls',
                'title': '240p',
                'hls/video': True,
                'video': {'height': 240, 'codec': 'vp9'}},
        '605': {'container': 'hls',
                'title': '360p',
                'hls/video': True,
                'video': {'height': 360, 'codec': 'vp9'}},
        '606': {'container': 'hls',
                'title': '480p',
                'hls/video': True,
                'video': {'height': 480, 'codec': 'vp9'}},
        '609': {'container': 'hls',
                'title': '720p',
                'hls/video': True,
                'video': {'height': 720, 'codec': 'vp9'}},
        '612': {'container': 'hls',
                'title': '720p60',
                'hls/video': True,
                'fps': 60,
                'video': {'height': 720, 'codec': 'vp9'}},
        '614': {'container': 'hls',
                'title': '1080p',
                'hls/video': True,
                'video': {'height': 1080, 'codec': 'vp9'}},
        '616': {'container': 'hls',
                'title': 'Premium 1080p',
                'hls/video': True,
                'video': {'height': 1080, 'codec': 'vp9'}},
        '617': {'container': 'hls',
                'title': 'Premium 1080p60',
                'hls/video': True,
                'fps': 60,
                'video': {'height': 1080, 'codec': 'vp9'}},
        '9994': {'container': 'hls',
                 'title': 'Adaptive HLS',
                 'hls/audio': True,
                 'hls/video': True,
                 'adaptive': True,
                 'sort': 9994,
                 'audio': {'bitrate': 0, 'codec': ''},
                 'video': {'height': 0, 'codec': ''}},
        # === Live HLS
        '9995': {'container': 'hls',
                 'live': True,
                 'title': 'Live HLS',
                 'hls/audio': True,
                 'hls/video': True,
                 'sort': 9995,
                 'audio': {'bitrate': 0, 'codec': ''},
                 'video': {'height': 0, 'codec': ''}},
        # === Live HLS adaptive
        '9996': {'container': 'hls',
                 'live': True,
                 'title': 'Adaptive Live HLS',
                 'hls/audio': True,
                 'hls/video': True,
                 'adaptive': True,
                 'sort': 9996,
                 'audio': {'bitrate': 0, 'codec': ''},
                 'video': {'height': 0, 'codec': ''}},
        # === DASH adaptive audio only
        '9997': {'container': 'mpd',
                 'title': 'DASH Audio',
                 'dash/audio': True,
                 'adaptive': True,
                 'sort': 9997,
                 'audio': {'bitrate': 0, 'codec': ''}},
        # === Live DASH adaptive
        '9998': {'container': 'mpd',
                 'live': True,
                 'title': 'Live DASH',
                 'dash/audio': True,
                 'dash/video': True,
                 'adaptive': True,
                 'sort': 9998,
                 'audio': {'bitrate': 0, 'codec': ''},
                 'video': {'height': 0, 'codec': ''}},
        # === DASH adaptive
        '9999': {'container': 'mpd',
                 'title': 'DASH',
                 'dash/audio': True,
                 'dash/video': True,
                 'adaptive': True,
                 'sort': 9999,
                 'audio': {'bitrate': 0, 'codec': ''},
                 'video': {'height': 0, 'codec': ''}}
    }

    INTEGER_FPS_SCALE = {
        0: '{0}000/1000',  # --.00 fps
        24: '24000/1000',  # 24.00 fps
        25: '25000/1000',  # 25.00 fps
        30: '30000/1000',  # 30.00 fps
        48: '48000/1000',  # 48.00 fps
        50: '50000/1000',  # 50.00 fps
        60: '60000/1000',  # 60.00 fps
    }
    FRACTIONAL_FPS_SCALE = {
        0: '{0}000/1000',  # --.00 fps
        24: '24000/1001',  # 23.976 fps
        25: '25000/1000',  # 25.00 fps
        30: '30000/1001',  # 29.97 fps
        48: '48000/1000',  # 48.00 fps
        50: '50000/1000',  # 50.00 fps
        60: '60000/1001',  # 59.94 fps
    }

    QUALITY_FACTOR = {
        # video - order based on comparative compression ratio
        'av01': 1,
        'vp9': 0.75,
        'vp8': 0.55,
        'avc1': 0.5,
        'h.264': 0.5,
        'h.263': 0.4,
        # audio - order based on preference
        'mp3': 0.5,
        'vorbis': 0.75,
        'aac': 0.9,
        'mp4a': 0.9,
        'opus': 1,
        'ac-3': 1.1,
        'ec-3': 1.2,
        'dts': 1.3,
        'dtse': 1.3,
    }

    def __init__(self, context, access_token='', **kwargs):
        self.video_id = None
        self._context = context
        self._language_base = kwargs.get('language', 'en_US')[0:2]
        self._access_token = access_token
        self._player_js = None
        self._calculate_n = True
        self._cipher = None

        self._selected_client = None
        client_selection = context.get_settings().client_selection()

        # Default client selection uses the Android or iOS client as the first
        # option to ensure that the age gate setting is enforced, regardless of
        # login status

        # Alternate #1
        # Prefer iOS client to access premium streams, however other stream
        # types are limited
        if client_selection == 1:
            self._prioritised_clients = (
                'ios',
                'android',
                'android_youtube_tv',
                'android_testsuite',
                'media_connect_frontend',
                'android_embedded',
            )
        # Alternate #2
        # Prefer use of non-adaptive formats.
        elif client_selection == 2:
            self._prioritised_clients = (
                'media_connect_frontend',
                'android',
                'android_youtube_tv',
                'android_testsuite',
                'ios',
                'android_embedded',
            )
        # Default
        # Will play most videos with subtitles at full resolution with HDR
        # Some restricted videos require additional requests for subtitles
        # Fallback to iOS, media connect, and embedded clients
        else:
            self._prioritised_clients = (
                'android',
                'android_youtube_tv',
                'android_testsuite',
                'ios',
                'media_connect_frontend',
                'android_embedded',
            )

        super(VideoInfo, self).__init__(**kwargs)

    @staticmethod
    def _response_hook_json(**kwargs):
        response = kwargs['response']
        try:
            json_data = response.json()
            if 'error' in json_data:
                kwargs.setdefault('pass_data', True)
                raise YouTubeException('"error" in response JSON data',
                                       json_data=json_data,
                                       **kwargs)
        except ValueError as exc:
            kwargs.setdefault('raise_exc', True)
            raise InvalidJSON(exc, **kwargs)
        response.raise_for_status()
        return json_data

    @staticmethod
    def _response_hook_text(**kwargs):
        response = kwargs['response']
        response.raise_for_status()
        result = response and response.text
        if not result:
            raise YouTubeException('Empty response text', **kwargs)
        return result

    @staticmethod
    def _error_hook(**kwargs):
        exc = kwargs.pop('exc')
        json_data = getattr(exc, 'json_data', None)
        if getattr(exc, 'pass_data', False):
            data = json_data
        else:
            data = None
        if getattr(exc, 'raise_exc', False):
            exception = YouTubeException
        else:
            exception = None

        if not json_data or 'error' not in json_data:
            info = ('exc: |{exc}|\n'
                    'video_id: {video_id}, client: {client}, auth: {auth}')
            return None, info, kwargs, data, None, exception

        details = json_data['error']
        reason = details.get('errors', [{}])[0].get('reason', 'Unknown')
        message = details.get('message', 'Unknown error')

        info = ('exc: |{exc}|\n'
                'reason: {reason}\n'
                'message: |{message}|\n'
                'video_id: {video_id}, client: {client}, auth: {auth}')
        kwargs['message'] = message
        kwargs['reason'] = reason
        return None, info, kwargs, data, None, exception

    @staticmethod
    def _generate_cpn():
        # https://github.com/rg3/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1381
        # LICENSE: The Unlicense
        # cpn generation algorithm is reverse engineered from base.js.
        # In fact it works even with dummy cpn.
        cpn_alphabet = ('abcdefghijklmnopqrstuvwxyz'
                        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                        '0123456789-_')
        return ''.join(random.choice(cpn_alphabet) for _ in range(16))

    def _get_stream_format(self, itag, info=None, max_height=None, **kwargs):
        yt_format = self.FORMAT.get(itag)
        if not yt_format:
            return None
        if yt_format.get('discontinued') or yt_format.get('unsupported'):
            return False

        yt_format = yt_format.copy()
        manual_sort = yt_format.get('sort', 0)

        if info:
            video_info = info.get('video') or {}
            yt_format['title'] = video_info.get('label', '')
            yt_format['video']['codec'] = video_info.get('codec', '')
            yt_format['video']['height'] = video_info.get('height', 0)

            audio_info = info.get('audio') or {}
            yt_format['audio']['codec'] = audio_info.get('codec', '')
            yt_format['audio']['bitrate'] = audio_info.get('bitrate', 0) // 1000

        video_info = yt_format.get('video')
        if video_info:
            video_height = video_info.get('height', 0)
            if max_height and video_height > max_height:
                return False
            video_sort = (
                    video_height
                    * self.QUALITY_FACTOR.get(video_info.get('codec'), 1)
            )
        else:
            video_sort = -1

        audio_info = yt_format.get('audio')
        if audio_info:
            audio_sort = (
                    audio_info.get('bitrate', 0)
                    * self.QUALITY_FACTOR.get(audio_info.get('codec'), 1)
            )
        else:
            audio_sort = 0

        yt_format['sort'] = [
            manual_sort,
            video_sort,
            audio_sort,
        ]
        if kwargs:
            kwargs.update(yt_format)
            return kwargs
        return yt_format

    def load_stream_infos(self, video_id):
        self.video_id = video_id
        return self._get_video_info()

    def _get_player_page(self, client_name='web', embed=False):
        if embed:
            url = 'https://www.youtube.com/embed/{0}'.format(self.video_id)
        else:
            url = 'https://www.youtube.com/watch?v={0}'.format(self.video_id)
        # Manually configured cookies to avoid cookie consent redirect
        cookies = {'SOCS': 'CAISAiAD'}

        client_data = {'json': {'videoId': self.video_id}}
        client = self.build_client(client_name, client_data)

        result = self.request(
            url,
            cookies=cookies,
            headers=client['headers'],
            response_hook=self._response_hook_text,
            error_title='Failed to get player html',
            error_hook=self._error_hook,
            error_hook_kwargs={
                'video_id': self.video_id,
                'client': client_name,
                'auth': False,
            },
        )
        return result

    @staticmethod
    def _get_player_client(config):
        return config.get('INNERTUBE_CONTEXT', {}).get('client', {})

    def _get_player_key(self, html):
        if not html:
            return None

        pattern = 'INNERTUBE_API_KEY":"'
        start_index = html.find(pattern)
        if start_index != -1:
            start_index += len(pattern)
            end_index = html.find('"', start_index)
            player_key = html[start_index:end_index]
            self._context.log_debug('Player key found: {0}'.format(player_key))
            return player_key
        return None

    @staticmethod
    def _get_player_config(page_text):
        if not page_text:
            return None

        # pattern source is from youtube-dl
        # https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L313
        # LICENSE: The Unlicense
        found = re.search(r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;', page_text)

        if found:
            return json.loads(found.group(1))
        return None

    def _get_player_js(self):
        data_cache = self._context.get_data_cache()
        cached = data_cache.get_item('player_js_url', data_cache.ONE_HOUR * 4)
        cached = cached and cached.get('url', '')
        js_url = cached if cached not in {'', 'http://', 'https://'} else None

        if not js_url:
            player_page_text = self._get_player_page()
            player_config = self._get_player_config(player_page_text)
            if not player_config:
                return ''
            js_url = player_config.get('PLAYER_JS_URL')

        if not js_url:
            context = player_config.get('WEB_PLAYER_CONTEXT_CONFIGS', {})
            for configs in context.values():
                if 'jsUrl' in configs:
                    js_url = configs['jsUrl']
                    break

        if not js_url:
            return ''

        js_url = self._normalize_url(js_url)
        data_cache.set_item('player_js_url', {'url': js_url})

        js_cache_key = quote(js_url)
        cached = data_cache.get_item(js_cache_key, data_cache.ONE_HOUR * 4)
        cached = cached and cached.get('js')
        if cached:
            return cached

        client_name = 'web'
        client_data = {'json': {'videoId': self.video_id}}
        client = self.build_client(client_name, client_data)

        result = self.request(
            js_url,
            headers=client['headers'],
            response_hook=self._response_hook_text,
            error_title='Failed to get player JavaScript',
            error_hook=self._error_hook,
            error_hook_kwargs={
                'video_id': self.video_id,
                'client': client_name,
                'auth': False,
            },
        )
        if not result:
            return ''

        data_cache.set_item(js_cache_key, {'js': result})
        return result

    @staticmethod
    def _make_curl_headers(headers, cookies=None):
        output = []
        if cookies:
            output.append('Cookie={0}'.format(quote('; '.join(
                '{0.name}={0.value}'.format(cookie)
                for cookie in cookies
            ))))
        # Headers used in xbmc_items.video_playback_item'
        output.extend('{0}={1}'.format(key, quote(value))
                      for key, value in headers.items())
        return '&'.join(output)

    @staticmethod
    def _normalize_url(url):
        if not url:
            url = ''
        elif url.startswith(('http://', 'https://')):
            pass
        elif url.startswith('//'):
            url = urljoin('https:', url)
        elif url.startswith('/'):
            url = urljoin('https://www.youtube.com', url)
        return url

    def _load_hls_manifest(self, url, is_live=False, meta_info=None,
                           headers=None, playback_stats=None):
        if not url:
            return []

        if not headers and self._selected_client:
            client_name = self._selected_client['_name']
            headers = self._selected_client['headers'].copy()
            if 'Authorization' in headers:
                del headers['Authorization']
        else:
            client_name = 'web'
            client_data = {'json': {'videoId': self.video_id}}
            headers = self.build_client(client_name, client_data)['headers']
        curl_headers = self._make_curl_headers(headers, cookies=None)

        result = self.request(
            url,
            headers=headers,
            response_hook=self._response_hook_text,
            error_title='Failed to get HLS manifest',
            error_hook=self._error_hook,
            error_hook_kwargs={
                'video_id': self.video_id,
                'client': client_name,
                'auth': False,
            },
        )
        if not result:
            return ()

        if meta_info is None:
            meta_info = {'video': {},
                         'channel': {},
                         'thumbnails': {},
                         'subtitles': []}

        if playback_stats is None:
            playback_stats = {}

        if is_live:
            stream_list = [
                self._get_stream_format(
                    itag=yt_format,
                    title='',
                    url=url,
                    meta=meta_info,
                    headers=curl_headers,
                    playback_stats=playback_stats,
                ) for yt_format in ('9995', '9996')
            ]
        else:
            stream_list = [
                self._get_stream_format(
                    itag='9994',
                    title='',
                    url=url,
                    meta=meta_info,
                    headers=curl_headers,
                    playback_stats=playback_stats,
                )
            ]

        settings = self._context.get_settings()
        if settings.use_mpd_videos():
            qualities = settings.mpd_video_qualities()
            selected_height = qualities[0]['nom_height']
        else:
            selected_height = settings.fixed_video_quality()

        # The playlist might include a #EXT-X-MEDIA entry, but it's usually for
        # a small default stream with itag 133 (240p) and can be ignored.
        # Capture the URL of a .m3u8 playlist and the itag value from that URL.
        re_playlist_data = re.compile(
            r'#EXT-X-STREAM-INF[^#]+'
            r'(?P<url>http\S+/itag/(?P<itag>\d+)\S+)'
        )
        for match in re_playlist_data.finditer(result):
            itag = match.group('itag')
            yt_format = self._get_stream_format(
                itag=itag,
                max_height=selected_height,
                title='',
                url=match.group('url'),
                meta=meta_info,
                headers=curl_headers,
                playback_stats=playback_stats,
            )
            if yt_format is None:
                self._context.log_debug('Unknown itag: {itag}\n{stream}'.format(
                    itag=itag, stream=redact_ip_from_url(match[0]),
                ))
            if (not yt_format
                    or (yt_format.get('hls/video')
                        and not yt_format.get('hls/audio'))):
                continue

            if is_live:
                yt_format['live'] = True
                yt_format['title'] = 'Live ' + yt_format['title']
            stream_list.append(yt_format)

        return stream_list

    def _create_stream_list(self,
                            streams,
                            is_live=False,
                            meta_info=None,
                            headers=None,
                            playback_stats=None):
        if not headers and self._selected_client:
            headers = self._selected_client['headers'].copy()
            if 'Authorization' in headers:
                del headers['Authorization']
        else:
            client_name = 'web'
            client_data = {'json': {'videoId': self.video_id}}
            headers = self.build_client(client_name, client_data)['headers']
        curl_headers = self._make_curl_headers(headers, cookies=None)

        if meta_info is None:
            meta_info = {'video': {},
                         'channel': {},
                         'thumbnails': {},
                         'subtitles': []}
        if playback_stats is None:
            playback_stats = {}

        settings = self._context.get_settings()
        if settings.use_mpd_videos():
            qualities = settings.mpd_video_qualities()
            selected_height = qualities[0]['nom_height']
        else:
            selected_height = settings.fixed_video_quality()

        stream_list = []
        for stream_map in streams:
            url = stream_map.get('url')
            conn = stream_map.get('conn')
            stream = stream_map.get('stream')

            if not url and conn and stream:
                new_url = '%s?%s' % (conn, unquote(stream))
            elif not url and self._cipher and 'signatureCipher' in stream_map:
                new_url = self._process_signature_cipher(stream_map)
            else:
                new_url = url

            if not new_url:
                continue
            new_url, _ = self._process_url_params(new_url)

            itag = str(stream_map['itag'])
            stream_map['itag'] = itag
            yt_format = self._get_stream_format(
                itag=itag,
                max_height=selected_height,
                title='',
                url=new_url,
                meta=meta_info,
                headers=curl_headers,
                playback_stats=playback_stats,
            )
            if yt_format is None:
                if url:
                    stream_map['url'] = redact_ip_from_url(url)
                if conn:
                    stream_map['conn'] = redact_ip_from_url(conn)
                if stream:
                    stream_map['stream'] = redact_ip_from_url(stream)
                self._context.log_debug('Unknown itag: {itag}\n{stream}'.format(
                    itag=itag, stream=stream_map,
                ))
            if (not yt_format
                    or (yt_format.get('dash/video')
                        and not yt_format.get('dash/audio'))):
                continue

            if is_live:
                yt_format['live'] = True
                yt_format['title'] = 'Live ' + yt_format['title']

            if 'audioTrack' in stream_map:
                audio_track = stream_map['audioTrack']
                display_name = audio_track['displayName']
                yt_format['title'] = '{0} {1}'.format(
                    yt_format['title'], display_name
                ).strip()
                yt_format['sort'].extend((
                    audio_track['id'].startswith(self._language_base),
                    'original' in display_name,
                    display_name
                ))

            stream_list.append(yt_format)
        return stream_list

    def _process_signature_cipher(self, stream_map):
        signature_cipher = parse_qs(stream_map['signatureCipher'])
        url = signature_cipher.get('url', [None])[0]
        encrypted_signature = signature_cipher.get('s', [None])[0]
        query_var = signature_cipher.get('sp', ['signature'])[0]

        if not url or not encrypted_signature:
            return None

        data_cache = self._context.get_data_cache()
        signature = data_cache.get_item(encrypted_signature,
                                        data_cache.ONE_HOUR * 4)
        signature = signature and signature.get('sig')
        if not signature:
            try:
                signature = self._cipher.get_signature(encrypted_signature)
            except Exception as exc:
                self._context.log_error('VideoInfo._process_signature_cipher - '
                                        'failed to extract URL from |{sig}|\n'
                                        '{exc}:\n{details}'.format(
                    sig=encrypted_signature,
                    exc=exc,
                    details=''.join(format_stack())
                ))
                return None
            data_cache.set_item(encrypted_signature, {'sig': signature})

        if signature:
            url = '{0}&{1}={2}'.format(url, query_var, signature)
            return url
        return None

    def _process_url_params(self, url):
        if not url:
            return url, None

        parts = urlsplit(url)
        query = parse_qs(parts.query)
        new_query = {}
        update_url = {}

        if self._calculate_n and 'n' in query:
            self._player_js = self._player_js or self._get_player_js()
            if self._calculate_n is True:
                self._context.log_debug('nsig detected')
                self._calculate_n = ratebypass.CalculateN(self._player_js)

            # Cipher n to get the updated value
            new_n = self._calculate_n.calculate_n(query['n'])
            if new_n:
                new_query['n'] = new_n
                new_query['ratebypass'] = 'yes'
            else:
                self._context.log_error('nsig handling failed')
                self._calculate_n = False

        if 'range' not in query:
            content_length = query.get('clen', [''])[0]
            new_query['range'] = '0-{0}'.format(content_length)

        if 'mn' in query and 'fvip' in query:
            fvip = query['fvip'][0]
            primary, _, secondary = query['mn'][0].partition(',')
            prefix, separator, server = parts.netloc.partition('---')
            if primary and secondary:
                update_url = {
                    'netloc': separator.join((
                        re.sub(r'\d+', fvip, prefix),
                        server.replace(primary, secondary),
                    )),
                }

        if new_query:
            query.update(new_query)
            query = urlencode(query, doseq=True)
        elif update_url:
            query = parts.query
        else:
            return url, None

        if update_url:
            return (
                parts._replace(query=query).geturl(),
                parts._replace(query=query, **update_url).geturl(),
            )
        return (
            parts._replace(query=query).geturl(),
            None,
        )

    def _get_error_details(self, playability_status, details=None):
        if not playability_status:
            return None
        if not details:
            details = (
                'errorScreen',
                (
                    (
                        'playerErrorMessageRenderer',
                        'reason',
                    ),
                    (
                        'confirmDialogRenderer',
                        'title',
                    ),
                )
            )

        result = self.json_traverse(playability_status, details)

        if not result or 'runs' not in result:
            return result

        detail_texts = [
            text['text']
            for text in result['runs']
            if text and 'text' in text and text['text']
        ]
        if detail_texts:
            return ''.join(detail_texts)
        if 'simpleText' in result:
            return result['simpleText']
        return None

    def _get_video_info(self):
        video_info_url = 'https://www.youtube.com/youtubei/v1/player'

        _settings = self._context.get_settings()
        video_id = self.video_id
        client_name = reason = status = None
        client = playability_status = result = None

        reasons = (
            self._context.localize(574, 'country').lower(),
            # not available error appears to vary by language/region/video type
            # disable this check for now
            # self._context.localize(10005, 'not available').lower(),
        )

        client_data = {'json': {'videoId': video_id}}
        if self._access_token:
            client_data['_access_token'] = self._access_token

        while 1:
            for client_name in self._prioritised_clients:
                if status and status != 'OK':
                    self._context.log_warning(
                        'Failed to retrieve video info - '
                        'video_id: {0}, client: {1}, auth: {2},\n'
                        'status: {3}, reason: {4}'.format(
                            video_id,
                            client['_name'],
                            bool(client.get('_access_token')),
                            status,
                            reason or 'UNKNOWN',
                        )
                    )
                client = self.build_client(client_name, client_data)
                if not client:
                    continue

                result = self.request(
                    video_info_url,
                    'POST',
                    response_hook=self._response_hook_json,
                    error_title='Player request failed',
                    error_hook=self._error_hook,
                    error_hook_kwargs={
                        'video_id': video_id,
                        'client': client_name,
                        'auth': bool(client.get('_access_token')),
                    },
                    **client
                )

                video_details = result.get('videoDetails', {})
                playability_status = result.get('playabilityStatus', {})
                status = playability_status.get('status', '').upper()
                reason = playability_status.get('reason', '')

                if status in {'', 'AGE_CHECK_REQUIRED', 'UNPLAYABLE',
                              'CONTENT_CHECK_REQUIRED', 'LOGIN_REQUIRED',
                              'AGE_VERIFICATION_REQUIRED', 'ERROR'}:
                    if (playability_status.get('desktopLegacyAgeGateReason')
                            and _settings.age_gate()):
                        break
                    # Geo-blocked video with error reasons like:
                    # "This video contains content from XXX, who has blocked it in your country on copyright grounds"
                    # "The uploader has not made this video available in your country"
                    # Reason language will vary based on Accept-Language and
                    # client hl, Kodi localised language is used for comparison
                    # but may not match reason language
                    if (status == 'UNPLAYABLE'
                            and any(why in reason for why in reasons)):
                        break
                    if status != 'ERROR':
                        continue
                    # This is used to check for error like:
                    # "The following content is not available on this app."
                    # Reason language will vary based on Accept-Language and
                    # client hl, so YouTube support url is checked instead
                    url = self._get_error_details(
                        playability_status,
                        details=(
                            'errorScreen',
                            'playerErrorMessageRenderer',
                            'learnMore',
                            'runs', 0,
                            'navigationEndpoint',
                            'urlEndpoint',
                            'url'
                        )
                    )
                    if url and url.startswith('//support.google.com/youtube/answer/12318250'):
                        status = 'CONTENT_NOT_AVAILABLE_IN_THIS_APP'
                        continue
                if video_details and video_id != video_details.get('videoId'):
                    status = 'CONTENT_NOT_AVAILABLE_IN_THIS_APP'
                    reason = 'Watch on the latest version of YouTube'
                    continue
                break
            # Only attempt to remove Authorization header if clients iterable
            # was exhausted i.e. request attempted using all clients
            else:
                if '_access_token' in client_data:
                    del client_data['_access_token']
                    continue
            # Otherwise skip retrying clients without Authorization header
            break

        if status != 'OK':
            if status == 'LIVE_STREAM_OFFLINE':
                if not reason:
                    reason = self._get_error_details(
                        playability_status,
                        details=(
                            'liveStreamability',
                            'liveStreamabilityRenderer',
                            'offlineSlate',
                            'liveStreamOfflineSlateRenderer',
                            'mainText'
                        )
                    )
            elif not reason:
                reason = self._get_error_details(playability_status)
            raise YouTubeException(reason or 'UNKNOWN')

        self._context.log_debug(
            'Retrieved video info - '
            'video_id: {0}, client: {1}, auth: {2}'.format(
                video_id,
                client_name,
                bool(client.get('_access_token')),
            )
        )
        self._selected_client = client.copy()

        if 'Authorization' in client['headers']:
            del client['headers']['Authorization']
        # Make a set of URL-quoted headers to be sent to Kodi when requesting
        # the stream during playback. The YT player doesn't seem to use any
        # cookies when doing that, so for now cookies are ignored.
        # curl_headers = self._make_curl_headers(headers, cookies)
        curl_headers = self._make_curl_headers(client['headers'], cookies=None)

        microformat = (result.get('microformat', {})
                       .get('playerMicroformatRenderer', {}))
        streaming_data = result.get('streamingData', {})
        is_live = video_details.get('isLiveContent', False)
        if is_live:
            is_live = video_details.get('isLive', False)
            live_dvr = video_details.get('isLiveDvrEnabled', False)
            thumb_suffix = '_live' if is_live else ''
        else:
            live_dvr = False
            thumb_suffix = ''

        meta_info = {
            'video': {
                'id': video_id,
                'title': unescape(video_details.get('title', '')
                                  .encode('raw_unicode_escape')
                                  .decode('raw_unicode_escape')),
                'status': {
                    'unlisted': microformat.get('isUnlisted', False),
                    'private': video_details.get('isPrivate', False),
                    'crawlable': video_details.get('isCrawlable', False),
                    'family_safe': microformat.get('isFamilySafe', False),
                    'live': is_live,
                },
            },
            'channel': {
                'id': video_details.get('channelId', ''),
                'author': unescape(video_details.get('author', '')
                                   .encode('raw_unicode_escape')
                                   .decode('raw_unicode_escape')),
            },
            'thumbnails': {
                thumb_type: {
                    'url': thumb['url'].format(video_id, thumb_suffix),
                    'size': thumb['size'],
                    'ratio': thumb['ratio'],
                }
                for thumb_type, thumb in THUMB_TYPES.items()
            },
            'subtitles': None,
        }

        if _settings.use_remote_history():
            playback_stats = {
                'playback_url': 'videostatsPlaybackUrl',
                'watchtime_url': 'videostatsWatchtimeUrl',
            }
            playback_tracking = result.get('playbackTracking', {})
            cpn = self._generate_cpn()

            for key, url_key in playback_stats.items():
                url = playback_tracking.get(url_key, {}).get('baseUrl')
                if url and url.startswith('http'):
                    playback_stats[key] = '&cpn='.join((url, cpn))
                else:
                    playback_stats[key] = ''
        else:
            playback_stats = {
                'playback_url': '',
                'watchtime_url': '',
            }

        use_mpd_vod = _settings.use_mpd_videos()
        use_isa = _settings.use_isa()

        pa_li_info = streaming_data.get('licenseInfos', [])
        if any(pa_li_info) and not use_isa:
            raise YouTubeException('InputStream.Adaptive not enabled')
        for li_info in pa_li_info:
            if li_info.get('drmFamily') != 'WIDEVINE':
                continue
            url = li_info.get('url')
            if not url:
                continue
            self._context.log_debug('Found widevine license url: {0}'
                                    .format(url))
            address, port = get_connect_address(self._context)
            license_info = {
                'url': url,
                'proxy': 'http://{address}:{port}{path}||R{{SSM}}|'.format(
                    address=address,
                    port=port,
                    path=paths.DRM,
                ),
                'token': self._access_token,
            }
            break
        else:
            license_info = {
                'url': None,
                'proxy': None,
                'token': None
            }

        stream_list = []
        if use_isa and use_mpd_vod:
            adaptive_fmts = streaming_data.get('adaptiveFormats', [])
            all_fmts = streaming_data.get('formats', []) + adaptive_fmts
        else:
            adaptive_fmts = None
            all_fmts = streaming_data.get('formats', [])

        if any(True for fmt in all_fmts
               if fmt and 'url' not in fmt and 'signatureCipher' in fmt):
            self._context.log_debug('signatureCipher detected')
            self._player_js = self._get_player_js()
            self._cipher = Cipher(self._context, javascript=self._player_js)

        if 'dashManifestUrl' in streaming_data:
            manifest_url = streaming_data['dashManifestUrl']
            if '?' in manifest_url:
                manifest_url += '&mpd_version=5'
            elif manifest_url.endswith('/'):
                manifest_url += 'mpd_version/5'
            else:
                manifest_url += '/mpd_version/5'

            stream_list.append(self._get_stream_format(
                itag='9998',
                title='',
                url=manifest_url,
                meta=meta_info,
                headers=curl_headers,
                license_info=license_info,
                playback_stats=playback_stats,
            ))
        if 'hlsManifestUrl' in streaming_data:
            stream_list.extend(self._load_hls_manifest(
                streaming_data['hlsManifestUrl'],
                is_live, meta_info, client['headers'], playback_stats
            ))

        subtitles = Subtitles(self._context, video_id)
        query_subtitles = client.get('_query_subtitles')
        if (not is_live or live_dvr) and (
                query_subtitles is True
                or (query_subtitles
                    and subtitles.sub_selection == subtitles.LANG_ALL)):
            for client_name in ('smarttv_embedded', 'web', 'android'):
                caption_client = self.build_client(client_name, client_data)
                if not caption_client:
                    continue
                result = self.request(
                    video_info_url,
                    'POST',
                    response_hook=self._response_hook_json,
                    error_title='Caption player request failed',
                    error_hook=self._error_hook,
                    error_hook_kwargs={
                        'video_id': video_id,
                        'client': client_name,
                        'auth': bool(caption_client.get('_access_token')),
                    },
                    **caption_client
                )
                captions = result and result.get('captions')
                if captions:
                    break
        else:
            captions = result.get('captions')
            caption_client = client
        if captions:
            subtitles.load(captions, caption_client['headers'])
            default_lang = subtitles.get_lang_details()
            subs_data = subtitles.get_subtitles()
            if subs_data and (not use_mpd_vod or subtitles.pre_download):
                meta_info['subtitles'] = [
                    subtitle['url'] for subtitle in subs_data.values()
                ]
                subs_data = None
        else:
            default_lang = {
                'default': 'und',
                'original': 'und',
                'is_asr': False,
            }
            subs_data = None

        # extract adaptive streams and create MPEG-DASH manifest
        if adaptive_fmts:
            video_data, audio_data = self._process_stream_data(
                adaptive_fmts,
                default_lang['default']
                if default_lang['original'] == 'und' else
                default_lang['original']
            )
            manifest_url, main_stream = self._generate_mpd_manifest(
                video_data, audio_data, subs_data, license_info.get('url')
            )

            if main_stream:
                yt_format = self._get_stream_format(
                    itag='9999',
                    info=main_stream,
                    title='',
                    url=manifest_url,
                    meta=meta_info,
                    headers=curl_headers,
                    license_info=license_info,
                    playback_stats=playback_stats,
                )

                title = [yt_format['title']]

                audio_info = main_stream.get('audio') or {}
                if audio_info.get('langCode', '') not in {'', 'und'}:
                    title.extend((' ', audio_info.get('langName', '')))

                if default_lang['default'] != 'und':
                    title.extend((' [', default_lang['default'], ']'))
                elif default_lang['is_asr']:
                    title.append(' [ASR]')

                for _prop in ('multi_lang', 'multi_audio'):
                    if not main_stream.get(_prop):
                        continue
                    _prop = 'stream.' + _prop
                    title.extend((' [', self._context.localize(_prop), ']'))

                if len(title) > 1:
                    yt_format['title'] = ''.join(yt_format['title'])

                stream_list.append(yt_format)

        # extract non-adaptive streams
        if all_fmts:
            stream_list.extend(self._create_stream_list(
                all_fmts, is_live, meta_info, client['headers'], playback_stats
            ))

        if not stream_list:
            raise YouTubeException('No streams found')

        return stream_list

    def _process_stream_data(self, stream_data, default_lang_code='und'):
        _settings = self._context.get_settings()
        qualities = _settings.mpd_video_qualities()
        isa_capabilities = self._context.inputstream_adaptive_capabilities()
        stream_features = _settings.stream_features()
        allow_hdr = 'hdr' in stream_features
        allow_hfr = 'hfr' in stream_features
        disable_hfr_max = 'no_hfr_max' in stream_features
        allow_ssa = 'ssa' in stream_features
        fps_map = (self.INTEGER_FPS_SCALE
                   if 'no_frac_fr_hint' in stream_features else
                   self.FRACTIONAL_FPS_SCALE)
        stream_select = _settings.stream_select()

        audio_data = {}
        video_data = {}
        preferred_audio = {
            'id': '',
            'language_code': None,
            'role_type': 0,
        }
        for stream in stream_data:
            mime_type = stream.get('mimeType')
            if not mime_type:
                continue

            itag = stream.get('itag')
            if not itag:
                continue

            index_range = stream.get('indexRange')
            if not index_range:
                continue

            init_range = stream.get('initRange')
            if not init_range:
                continue

            url = stream.get('url')
            if not url and self._cipher and 'signatureCipher' in stream:
                url = self._process_signature_cipher(stream)
            if not url:
                continue

            mime_type, codecs = unquote(mime_type).split('; ')
            codec = re.match(r'codecs="([a-z0-9]+([.\-][0-9](?="))?)', codecs)
            if codec:
                codec = codec.group(1)
                if codec.startswith('vp9'):
                    codec = 'vp9'
                elif codec.startswith('dts'):
                    codec = 'dts'
            if codec not in stream_features or codec not in isa_capabilities:
                continue
            media_type, container = mime_type.split('/')
            bitrate = stream.get('bitrate', 0)

            if media_type == 'audio':
                data = audio_data
                channels = stream.get('audioChannels', 2)
                if channels > 2 and not allow_ssa:
                    continue

                if 'audioTrack' in stream:
                    audio_track = stream['audioTrack']

                    language = audio_track.get('id', default_lang_code)
                    if '.' in language:
                        language_code, role_type = language.split('.')
                        role_type = int(role_type)
                    else:
                        language_code = language
                        role_type = 4

                    if role_type == 4 or audio_track.get('audioIsDefault'):
                        role = 'main'
                        label = self._context.localize('stream.original')
                    elif role_type == 3:
                        role = 'dub'
                        label = self._context.localize('stream.dubbed')
                    elif role_type == 2:
                        role = 'description'
                        label = self._context.localize('stream.descriptive')
                    # Unsure of what other audio types are actually available
                    # Role set to "alternate" as default fallback
                    else:
                        role = 'alternate'
                        label = self._context.localize('stream.alternate')

                    mime_group = '{0}_{1}.{2}'.format(
                        mime_type, language_code, role_type
                    )
                    if language_code == self._language_base and (
                            not preferred_audio['id']
                            or role == 'main'
                            or role_type > preferred_audio['role_type']
                    ):
                        preferred_audio = {
                            'id': '_{0}.{1}'.format(language_code, role_type),
                            'language_code': language_code,
                            'role_type': role_type,
                        }
                else:
                    language_code = default_lang_code
                    role = 'main'
                    role_type = 4
                    label = self._context.localize('stream.original')
                    mime_group = mime_type

                sample_rate = int(stream.get('audioSampleRate', '0'), 10)
                height = width = fps = frame_rate = hdr = None
                language = self._context.get_language_name(language_code)
                label = '{0} ({1} kbps)'.format(label, bitrate // 1000)
                if channels > 2 or 'auto' not in stream_select:
                    quality_group = '{0}_{1}_{2}.{3}'.format(
                        container, codec, language_code, role_type
                    )
                else:
                    quality_group = mime_group

            else:
                data = video_data
                # Could use "zxx" language code for
                # "Non-Linguistic, Not Applicable" but that is too verbose
                language_code = ''

                fps = stream.get('fps', 0)
                if fps > 30 and not allow_hfr:
                    continue

                hdr = 'HDR' in stream.get('qualityLabel', '')
                if hdr and not allow_hdr:
                    continue

                height = stream.get('height')
                width = stream.get('width')
                if height > width:
                    compare_width = height
                    compare_height = width
                else:
                    compare_width = width
                    compare_height = height

                bounded_quality = None
                for quality in qualities:
                    if compare_width > quality['width']:
                        if bounded_quality:
                            if compare_height >= bounded_quality['min_height']:
                                quality = bounded_quality
                            elif compare_height < quality['min_height']:
                                quality = qualities[-1]
                        if fps > 30 and disable_hfr_max:
                            bounded_quality = None
                        break
                    disable_hfr_max = disable_hfr_max and not bounded_quality
                    bounded_quality = quality
                if not bounded_quality:
                    continue

                # map frame rates to a more common representation to lessen the
                # chance of double refresh changes
                if fps:
                    frame_rate = fps_map.get(fps) or fps_map[0].format(fps)
                else:
                    frame_rate = None

                mime_group = '{mime_type}_{codec}{hdr}'.format(
                    mime_type=mime_type,
                    codec=codec,
                    hdr='_hdr' if hdr else ''
                )
                channels = language = role = role_type = sample_rate = None
                label = quality['label'].format(
                    quality['nom_height'] or compare_height,
                    fps if fps > 30 else '',
                    ' HDR' if hdr else '',
                )
                quality_group = '{0}_{1}_{2}'.format(container, codec, label)

            if mime_group not in data:
                data[mime_group] = {}
            if quality_group not in data:
                data[quality_group] = {}

            url = unquote(url)
            primary_url, secondary_url = self._process_url_params(url)
            primary_url = (primary_url.replace("&", "&amp;")
                           .replace('"', "&quot;")
                           .replace("<", "&lt;")
                           .replace(">", "&gt;"))

            details = {
                'mimeType': mime_type,
                'baseUrl': primary_url,
                'mediaType': media_type,
                'container': container,
                'codecs': codecs,
                'codec': codec,
                'id': itag,
                'width': width,
                'height': height,
                'label': label,
                'bitrate': bitrate,
                'biasedBitrate': bitrate * self.QUALITY_FACTOR.get(codec, 1),
                # integer round up
                'duration': -(-int(stream.get('approxDurationMs', 0)) // 1000),
                'fps': fps,
                'frameRate': frame_rate,
                'hdr': hdr,
                'indexRange': '{start}-{end}'.format(**index_range),
                'initRange': '{start}-{end}'.format(**init_range),
                'langCode': language_code,
                'langName': language,
                'role': role,
                'roleType': role_type,
                'sampleRate': sample_rate,
                'channels': channels,
            }
            if secondary_url:
                secondary_url = (secondary_url.replace("&", "&amp;")
                                 .replace('"', "&quot;")
                                 .replace("<", "&lt;")
                                 .replace(">", "&gt;"))
                details['baseUrlSecondary'] = secondary_url
            data[mime_group][itag] = data[quality_group][itag] = details

        if not video_data:
            self._context.log_debug('Generate MPD: No video mime-types found')
            return None, None

        def _stream_sort(stream):
            if not stream:
                return (1,)

            return (
                - stream['height'],
                - stream['fps'],
                - stream['hdr'],
                - stream['biasedBitrate'],
            ) if stream['mediaType'] == 'video' else (
                - stream['channels'],
                - stream['biasedBitrate'],
            )

        def _group_sort(item):
            group, streams = item
            main_stream = streams[0]

            key = (
                not group.startswith(main_stream['mimeType']),
            ) if main_stream['mediaType'] == 'video' else (
                not group.startswith(main_stream['mimeType']),
                preferred_audio['id'] not in group,
                main_stream['langName'],
                - main_stream['roleType'],
            )
            return key + _stream_sort(main_stream)

        video_data = sorted((
            (group, sorted(streams.values(), key=_stream_sort))
            for group, streams in video_data.items()
        ), key=_group_sort)

        audio_data = sorted((
            (group, sorted(streams.values(), key=_stream_sort))
            for group, streams in audio_data.items()
        ), key=_group_sort)

        return video_data, audio_data

    def _generate_mpd_manifest(self,
                               video_data,
                               audio_data,
                               subs_data,
                               license_url):
        if not video_data or not audio_data:
            return None, None

        if not self.BASE_PATH:
            self._context.log_error('VideoInfo._generate_mpd_manifest - '
                                    'unable to access temp directory')
            return None, None

        def _filter_group(previous_group, previous_stream, item):
            skip_group = True
            if not item:
                return skip_group
            if not previous_group or not previous_stream:
                return not skip_group

            new_group = item[0]
            new_stream = item[1][0]

            media_type = new_stream['mediaType']
            if media_type != previous_stream['mediaType']:
                return not skip_group

            if previous_group.startswith(previous_stream['mimeType']):
                if new_group.startswith(new_stream['container']):
                    return not skip_group

                skip_group = (
                    new_stream['height'] <= previous_stream['height']
                    if media_type == 'video' else
                    new_stream['channels'] <= previous_stream['channels']
                )
            else:
                if new_group.startswith(new_stream['mimeType']):
                    return not skip_group

                skip_group = (
                    new_stream['height'] == previous_stream['height']
                    if media_type == 'video' else
                    2 == new_stream['channels'] == previous_stream['channels']
                )

            skip_group = (
                skip_group
                and new_stream['fps'] == previous_stream['fps']
                and new_stream['hdr'] == previous_stream['hdr']
                if media_type == 'video' else
                skip_group
                and new_stream['langCode'] == previous_stream['langCode']
                and new_stream['role'] == previous_stream['role']
            )
            return skip_group

        _settings = self._context.get_settings()
        stream_features = _settings.stream_features()
        do_filter = 'filter' in stream_features
        frame_rate_hint = 'no_fr_hint' not in stream_features
        stream_select = _settings.stream_select()

        main_stream = {
            'video': video_data[0][1][0],
            'audio': audio_data[0][1][0],
            'multi_audio': False,
            'multi_lang': False,
        }

        output = [
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<MPD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                ' xmlns="urn:mpeg:dash:schema:mpd:2011"'
                ' xmlns:xlink="http://www.w3.org/1999/xlink"'
                ' xsi:schemaLocation="urn:mpeg:dash:schema:mpd:2011 http://standards.iso.org/ittf/PubliclyAvailableStandards/MPEG-DASH_schema_files/DASH-MPD.xsd"'
                ' minBufferTime="PT1.5S"'
                ' mediaPresentationDuration="PT', str(main_stream['video']['duration']), 'S"'
                ' type="static"'
                ' profiles="urn:mpeg:dash:profile:isoff-main:2011"'
                '>\n'
            '\t<Period>\n'
        ]

        set_id = 0
        group = stream = None
        languages = set()
        roles = set()
        for item in (video_data + audio_data):
            default = original = impaired = False

            if do_filter and _filter_group(group, stream, item):
                continue
            group, streams = item
            stream = streams[0]
            container = stream['container']
            media_type = stream['mediaType']
            mime_type = stream['mimeType']
            language = stream['langCode']
            role = stream['role'] or ''

            if group.startswith(mime_type) and 'auto' in stream_select:
                label = '{0} [{1}]'.format(
                    stream['langName']
                    or self._context.localize('stream.automatic'),
                    stream['label']
                )
                if stream == main_stream[media_type]:
                    default = True
                    role = 'main'
            elif group.startswith(container) and 'list' in stream_select:
                if 'auto' in stream_select or media_type == 'video':
                    label = stream['label']
                else:
                    label = '{0} {1}'.format(
                        stream['langName'],
                        stream['label']
                    ).strip()
                    if stream == main_stream[media_type]:
                        default = True
                        role = 'main'
            else:
                continue

            if role == 'main':
                if not default:
                    role = 'alternate'
                original = True
            elif role == 'description':
                impaired = True

            languages.add(language)
            roles.add(role)

            output.extend((
                '\t\t<AdaptationSet'
                    ' subsegmentAlignment="true"'
                    ' subsegmentStartsWithSAP="1"'
                    ' bitstreamSwitching="true"'
                    ' id="', str(set_id), '"'
                    ' contentType="', media_type, '"'
                    ' mimeType="', mime_type, '"'
                    ' lang="', language, '"'
                    # name attribute is ISA specific and does not exist in the
                    # MPD spec. Should be a child Label element instead
                    ' name="[B]', label, '[/B]"'
                    # original / default / impaired are ISA specific attributes
                    ' original="', str(original).lower(), '"'
                    ' default="', str(default).lower(), '"'
                    ' impaired="', str(impaired).lower(), '"'
                    '>\n'
                # AdaptationSet Label element not currently used by ISA
                '\t\t\t<Label>', label, '</Label>\n'
                '\t\t\t<Role'
                    ' schemeIdUri="urn:mpeg:dash:role:2011"'
                    ' value="', role, '"'
                    '/>\n'
            ))

            if license_url:
                license_url = (license_url.replace("&", "&amp;")
                               .replace('"', "&quot;").replace("<", "&lt;")
                               .replace(">", "&gt;"))
                output.extend((
                    '\t\t\t<ContentProtection'
                        ' schemeIdUri="http://youtube.com/drm/2012/10/10"'
                        '>\n'
                    '\t\t\t\t<yt:SystemURL'
                        ' type="widevine"'
                        '>',
                        license_url,
                        '</yt:SystemURL>\n'
                    '\t\t\t</ContentProtection>\n'
                ))

            num_streams = len(streams)
            if media_type == 'audio':
                output.extend(((
                    '\t\t\t<Representation'
                        ' id="{id}"'
                        ' {codecs}'
                        ' mimeType="{mimeType}"'
                        ' bandwidth="{bitrate}"'
                        ' sampleRate="{sampleRate}"'
                        ' numChannels="{channels}"'
                        # quality and priority attributes are not used by ISA
                        ' qualityRanking="{quality}"'
                        ' selectionPriority="{priority}"'
                        '>\n'
                    '\t\t\t\t<AudioChannelConfiguration'
                        ' schemeIdUri="urn:mpeg:dash:23003:3:audio_channel_configuration:2011"'
                        ' value="{channels}"'
                        '/>\n'
                    # Representation Label element is not used by ISA
                    '\t\t\t\t<Label>{label}</Label>\n'
                    '\t\t\t\t<BaseURL>{baseUrl}</BaseURL>\n' +
                    ('\t\t\t\t<BaseURL>{baseUrlSecondary}</BaseURL>\n'
                     if 'baseUrlSecondary' in stream else '') +
                    '\t\t\t\t<SegmentBase indexRange="{indexRange}">\n'
                    '\t\t\t\t\t<Initialization range="{initRange}"/>\n'
                    '\t\t\t\t</SegmentBase>\n'
                    '\t\t\t</Representation>\n'
                ).format(
                    quality=(idx + 1), priority=(num_streams - idx), **stream
                ) for idx, stream in enumerate(streams)))
            elif media_type == 'video':
                output.extend(((
                    '\t\t\t<Representation'
                        ' id="{id}"'
                        ' {codecs}'
                        ' mimeType="{mimeType}"'
                        ' bandwidth="{bitrate}"'
                        ' width="{width}"'
                        ' height="{height}"' +
                        (' frameRate="{frameRate}"' if frame_rate_hint else '') +
                        # quality and priority attributes are not used by ISA
                        ' qualityRanking="{quality}"'
                        ' selectionPriority="{priority}"'
                        '>\n'
                    # Representation Label element is not used by ISA
                    '\t\t\t\t<Label>{label}</Label>\n'
                    '\t\t\t\t<BaseURL>{baseUrl}</BaseURL>\n' +
                    ('\t\t\t\t<BaseURL>{baseUrlSecondary}</BaseURL>\n'
                     if 'baseUrlSecondary' in stream else '') +
                    '\t\t\t\t<SegmentBase indexRange="{indexRange}">\n'
                    '\t\t\t\t\t<Initialization range="{initRange}"/>\n'
                    '\t\t\t\t</SegmentBase>\n'
                    '\t\t\t</Representation>\n'
                ).format(
                    quality=(idx + 1), priority=(num_streams - idx), **stream
                ) for idx, stream in enumerate(streams)))

            output.append('\t\t</AdaptationSet>\n')
            set_id += 1

        if subs_data:
            translation_lang = self._context.localize('subtitles.translation')
            for lang_id, subtitle in subs_data.items():
                lang_code = subtitle['lang']
                label = language = subtitle['language']
                kind = subtitle['kind']
                if kind == 'translation':
                    label = translation_lang % language
                    kind = '_'.join((lang_code, kind))
                else:
                    kind = lang_id

                url = (unquote(subtitle['url'])
                       .replace("&", "&amp;")
                       .replace('"', "&quot;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;"))

                output.extend((
                    '\t\t<AdaptationSet'
                        ' id="', str(set_id), '"'
                        ' mimeType="', subtitle['mime_type'], '"'
                        ' lang="', lang_code, '"'
                        # name attribute is ISA specific and does not exist in
                        # the MPD spec. Should be a child Label element instead
                        ' name="[B]', label, '[/B]"'
                        # original / default are ISA specific attributes
                        ' original="', str(subtitle['original']).lower(), '"'
                        ' default="', str(subtitle['default']).lower(), '"'
                        '>\n'
                    # AdaptationSet Label element not currently used by ISA
                    '\t\t\t<Label>', label, '</Label>\n'
                    '\t\t\t<Role'
                        ' schemeIdUri="urn:mpeg:dash:role:2011"'
                        ' value="subtitle"'
                        '/>\n'
                    '\t\t\t<Representation'
                        ' id="subs_', kind, '"'
                        # unsure about what value to use for bandwidth
                        ' bandwidth="268"'
                        '>\n'
                    '\t\t\t\t<BaseURL>', url, '</BaseURL>\n'
                    '\t\t\t</Representation>\n'
                    '\t\t</AdaptationSet>\n'
                ))
                set_id += 1

        output.append('\t</Period>\n'
                      '</MPD>\n')
        output = ''.join(output)

        if len(languages.difference({'', 'und'})) > 1:
            main_stream['multi_lang'] = True
        if roles.difference({'', 'main', 'dub'}):
            main_stream['multi_audio'] = True

        filename = '.'.join((self.video_id, 'mpd'))
        filepath = os.path.join(self.BASE_PATH, filename)
        try:
            with xbmcvfs.File(filepath, 'w') as mpd_file:
                success = mpd_file.write(output)
        except (IOError, OSError):
            self._context.log_error('VideoInfo._generate_mpd_manifest - '
                                    'file write failed for: {file}'
                                    .format(file=filepath))
            success = False
        if success:
            address, port = get_connect_address(self._context)
            return 'http://{address}:{port}{path}{file}'.format(
                address=address,
                port=port,
                path=paths.MPD,
                file=filename,
            ), main_stream
        return None, None
