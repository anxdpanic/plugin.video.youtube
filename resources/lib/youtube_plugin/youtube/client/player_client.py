# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from base64 import urlsafe_b64encode
from json import dumps as json_dumps, loads as json_loads
from os import path as os_path
from random import choice as random_choice
from re import compile as re_compile, sub as re_sub

from .data_client import YouTubeDataClient
from .subtitles import SUBTITLE_SELECTIONS, Subtitles
from ..helper.ratebypass import ratebypass
from ..helper.signature.cipher import Cipher
from ..helper.utils import THUMB_TYPES, THUMB_URL
from ..youtube_exceptions import YouTubeException
from ...kodion import logging
from ...kodion.compatibility import (
    entity_escape,
    parse_qs,
    quote,
    unescape,
    unquote,
    urlencode,
    urlsplit,
    urlunsplit,
    xbmcvfs,
)
from ...kodion.constants import INCOGNITO, PATHS, TEMP_PATH, VALUE_TO_STR
from ...kodion.network import get_connect_address
from ...kodion.utils.datetime import fromtimestamp
from ...kodion.utils.file_system import make_dirs
from ...kodion.utils.methods import merge_dicts
from ...kodion.utils.redact import redact_ip_in_uri


class YouTubePlayerClient(YouTubeDataClient):
    log = logging.getLogger(__name__)

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
        '597': {'container': 'mp4',
                'dash/video': True,
                'fps': 12,
                'video': {'height': 144, 'codec': 'h.264'}},
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
        '214': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 720, 'codec': 'h.264'}},
        '137': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 1080, 'codec': 'h.264'}},
        '216': {'container': 'mp4',
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
        '356': {'container': 'webm',
                'title': 'Premium 1080p',
                'dash/video': True,
                'video': {'height': 1080, 'codec': 'vp9'}},
        '779': {'container': 'webm',
                'title': '1080p vertical',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 480, 'width': 1080, 'codec': 'vp9'}},
        '780': {'container': 'webm',
                'title': 'Premium 1080p vertical',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 480, 'width': 1080, 'codec': 'vp9'}},
        '788': {'container': 'mp4',
                'title': '608p',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 608, 'width': 1080, 'codec': 'av1'}},
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
        '598': {'container': 'webm',
                'dash/video': True,
                'fps': 12,
                'video': {'height': 144, 'codec': 'vp9'}},
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
                'title': 'Premium 4k',
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
        '599': {'container': 'mp4',
                'title': 'he-aac@32',
                'dash/audio': True,
                'audio': {'bitrate': 32, 'codec': 'aac'}},
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
        '600': {'container': 'webm',
                'title': 'opus@40',
                'dash/audio': True,
                'audio': {'bitrate': 40, 'codec': 'opus'}},
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
        '379': {'container': 'hls',
                'title': 'Premium 720p',
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
        '620': {'container': 'hls',
                'title': '1440p',
                'hls/video': True,
                'video': {'height': 1440, 'codec': 'vp9'}},
        '623': {'container': 'hls',
                'title': '1440p@60',
                'hls/video': True,
                'fps': 60,
                'video': {'height': 1440, 'codec': 'vp9'}},
        '625': {'container': 'hls',
                'title': '4k',
                'hls/video': True,
                'video': {'height': 2160, 'codec': 'vp9'}},
        '628': {'container': 'hls',
                'title': '4k@60',
                'hls/video': True,
                'fps': 60,
                'video': {'height': 2160, 'codec': 'vp9'}},
        '631': {'container': 'hls',
                'title': '144p',
                'hls/video': True,
                'hdr': True,
                'video': {'height': 144, 'codec': 'vp9.2'}},
        '632': {'container': 'hls',
                'title': '240p',
                'hls/video': True,
                'hdr': True,
                'video': {'height': 240, 'codec': 'vp9.2'}},
        '633': {'container': 'hls',
                'title': '360p',
                'hls/video': True,
                'hdr': True,
                'video': {'height': 360, 'codec': 'vp9.2'}},
        '634': {'container': 'hls',
                'title': '480p',
                'hls/video': True,
                'hdr': True,
                'video': {'height': 480, 'codec': 'vp9.2'}},
        '635': {'container': 'hls',
                'title': '720p',
                'hls/video': True,
                'hdr': True,
                'video': {'height': 720, 'codec': 'vp9.2'}},
        '636': {'container': 'hls',
                'title': '1080p',
                'hls/video': True,
                'hdr': True,
                'video': {'height': 1080, 'codec': 'vp9.2'}},
        '639': {'container': 'hls',
                'title': '1440p',
                'hls/video': True,
                'hdr': True,
                'video': {'height': 1440, 'codec': 'vp9.2'}},
        '642': {'container': 'hls',
                'title': '4k',
                'hls/video': True,
                'hdr': True,
                'video': {'height': 2160, 'codec': 'vp9.2'}},
        '9993': {'container': 'hls',
                 'title': 'HLS',
                 'hls/audio': True,
                 'hls/video': True,
                 'sort': 9993,
                 'audio': {'bitrate': 0, 'codec': ''},
                 'video': {'height': 0, 'codec': ''}},
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
        'vp9.2': 0.75,
        'vp9': 0.75,
        'vp8': 0.55,
        'vp08': 0.55,
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

    LANG_ROLE_DETAILS = {
        '4':  ('original', 'main', -1),
        '3':  ('dub', 'dub', -2),
        '6':  ('secondary', 'alternate', -3),
        '10': ('dub.auto', 'dub', -4),
        '2':  ('descriptive', 'description', -5),
        '0':  ('alt', 'alternate', -6),
        '-1': ('original', 'main', -6),
    }

    FAILURE_REASONS = {
        'abort': frozenset((
            'country',
            'not available',
        )),
        'auth': frozenset((
            'not a bot',
            'please sign in',
        )),
        'reauth': frozenset((
            'confirm your age',
            'inappropriate',
            'member',
        )),
        'retry': frozenset((
            'try again later',
            'unavailable',
            'unknown',
        )),
        'skip': frozenset((
            'error code: 6',
            'latest version',
        )),
    }

    def __init__(self,
                 context,
                 clients=None,
                 **kwargs):
        self.video_id = None
        self.yt_item = None

        settings = context.get_settings()
        self._ask_for_quality = settings.ask_for_video_quality()
        self._audio_only = settings.audio_only()
        self._use_mpd = settings.use_mpd_videos()

        audio_language, prefer_default = context.get_player_language()
        if audio_language == 'mediadefault':
            self._language_base = settings.get_language()[0:2]
        elif audio_language == 'original':
            self._language_base = ''
        else:
            self._language_base = audio_language
        self._language_prefer_default = prefer_default

        self._player_js = None
        # signatureCipher and nsig handling currently broken and disabled
        # self._calculate_n = True
        # self._cipher = None
        self._calculate_n = False
        self._cipher = False

        self._visitor_data = {
            'current': None,
            INCOGNITO: None,
        }
        self._visitor_data_key = 'current'
        self._client_groups = (
            ('custom', clients if clients else ()),
            ('auth_enabled|initial_request|no_playable_streams', (
                'tv_unplugged',
                'tv',
            )),
            ('auth_disabled|kids|av1|vp9|vp9.2|avc1|stereo_sound|multi_audio', (
                'ios_testsuite_params',
            )),
            ('auth_disabled|kids|av1|vp9.2|avc1|surround_sound|multi_audio', (
                'android_testsuite_params',
            )),
            ('auth_enabled|no_kids|av1|vp9.2|avc1|surround_sound', (
                'android_vr',
            )),
            ('mpd', (
            )),
            ('ask', (
            )),
        )

        super(YouTubePlayerClient, self).__init__(context=context, **kwargs)

    @staticmethod
    def _player_error_hook(**kwargs):
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
            info = (
                'video_id: {video_id!r}',
                'Client:   {client_name!r}',
                'Auth:     {has_auth!r}',
            )
            return None, info, None, data, exception

        info = (
            'Reason:   {error_reason}',
            'Message:  {error_message}',
            'video_id: {video_id!r}',
            'Client:   {client_name!r}',
            'Auth:     {has_auth!r}',
        )
        details = json_data['error']
        details = {
            'error_reason': (
                    (details.get('errors') or [{}])[0].get('reason')
                    or 'Unknown'
            ),
            'error_message': details.get('message') or 'Unknown error',
        }
        return None, info, details, data, exception

    @staticmethod
    def _generate_cpn(_alphabet=('abcdefghijklmnopqrstuvwxyz'
                                 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                                 '0123456789-_')):
        # https://github.com/rg3/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1381
        # LICENSE: The Unlicense
        # cpn generation algorithm is reverse engineered from base.js.
        # In fact it works even with dummy cpn.
        return ''.join([random_choice(_alphabet) for _ in range(16)])

    def _get_stream_format(self, itag, info=None, max_height=None, **kwargs):
        yt_format = self.FORMAT.get(itag)
        if not yt_format:
            return None
        if yt_format.get('discontinued') or yt_format.get('unsupported'):
            return False

        yt_format = yt_format.copy()
        manual_sort = yt_format.get('sort', 0)
        av_label = [yt_format['container']]

        if info:
            if 'video' in yt_format:
                if self._audio_only:
                    del yt_format['video']
                else:
                    video_info = info['video'] or {}
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
            codec = video_info.get('codec')
            if codec:
                video_sort = video_height * self.QUALITY_FACTOR.get(codec, 1)
                av_label.append(codec)
            else:
                video_sort = video_height
        else:
            video_sort = -1

        audio_info = yt_format.get('audio')
        if audio_info:
            codec = audio_info.get('codec')
            bitrate = audio_info.get('bitrate', 0)
            audio_sort = bitrate * self.QUALITY_FACTOR.get(codec, 1)
            if bitrate:
                av_label.append('@'.join((codec, str(bitrate))))
            elif codec:
                av_label.append(codec)
        else:
            audio_sort = 0

        yt_format['sort'] = [
            manual_sort,
            video_sort,
            audio_sort,
        ]

        if kwargs:
            kwargs.update(yt_format)
            yt_format = kwargs

        yt_format['title'] = ''.join((
            self._context.get_ui().bold(yt_format['title']),
            ' (',
            ' / '.join(av_label),
            ')'
        ))
        return yt_format

    def _get_player_config(self, client_name='web', embed=False):
        video_id = self.video_id
        if embed:
            url = self.BASE_URL + '/embed/%s' % video_id
        else:
            url = self.WATCH_URL.format(_video_id=video_id)
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
            video_id=self.video_id,
            error_hook=self._player_error_hook,
            client_name=client_name,
            has_auth=False,
            cache=False,
        )
        if not result:
            return None

        # pattern source is from youtube-dl
        # https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L313
        # LICENSE: The Unlicense
        match = re_compile(r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;').search(result)
        if match:
            return json_loads(match.group(1))
        return None

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
            self.log.debug('Player key found: %r', player_key)
            return player_key
        return None

    def _get_player_js(self):
        data_cache = self._context.get_data_cache()
        cached = data_cache.get_item('player_js_url', data_cache.ONE_HOUR * 4)
        cached = cached and cached.get('url', '')
        js_url = cached if cached not in {'', 'http://', 'https://'} else None

        if not js_url:
            player_config = self._get_player_config()
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
            error_hook=self._player_error_hook,
            video_id=self.video_id,
            client_name=client_name,
            has_auth=False,
            cache=False,
        )
        if not result:
            return ''

        data_cache.set_item(js_cache_key, {'js': result})
        return result

    @staticmethod
    def _prepare_headers(headers, cookies=None, new_headers=None):
        if cookies or new_headers:
            headers = headers.copy()
        if cookies:
            headers['Cookie'] = '; '.join([
                '='.join((cookie.name, cookie.value)) for cookie in cookies
            ])
        if new_headers:
            headers.update(new_headers)
        return headers

    def _process_mpd(self,
                     stream_list,
                     responses,
                     meta_info=None,
                     playback_stats=None):
        if not responses:
            return

        if meta_info is None:
            meta_info = {'video': {},
                         'channel': {},
                         'thumbnails': {},
                         'subtitles': []}

        if playback_stats is None:
            playback_stats = {}

        itag = '9998'

        for client_name, response in responses.items():
            if itag in stream_list:
                break

            headers = response['client']['headers']
            url = self._process_url_params(
                response['mpd_manifest'],
                mpd_manifest=True,
                headers=headers,
            )
            if not url:
                continue

            stream_list[itag] = self._get_stream_format(
                itag=itag,
                title='',
                url=url,
                meta=meta_info,
                headers=headers,
                playback_stats=playback_stats,
            )

    def _process_hls(self,
                     stream_list,
                     responses,
                     is_live=False,
                     meta_info=None,
                     playback_stats=None):
        if not responses:
            return

        if meta_info is None:
            meta_info = {'video': {},
                         'channel': {},
                         'thumbnails': {},
                         'subtitles': []}

        if playback_stats is None:
            playback_stats = {}

        context = self._context
        settings = context.get_settings()
        if self._use_mpd:
            qualities = settings.mpd_video_qualities()
            selected_height = qualities[0]['nom_height']
        else:
            selected_height = settings.fixed_video_quality()

        # Regular expression used to capture the URL of a HLS m3u8 playlist and
        # the itag from that URL.
        # The playlist might include a #EXT-X-MEDIA entry, but it's usually
        # for a default stream with itag 133 (240p) and can be ignored.
        re_playlist_data = re_compile(
            r'#EXT-X-STREAM-INF[^#]+'
            r'(?P<url>http\S+/itag/(?P<itag>\d+)\S+)'
        )
        itags = ('9995', '9996') if is_live else ('9993', '9994')

        for client_name, response in responses.items():
            headers = response['client']['headers']
            url = self._process_url_params(
                response['hls_manifest'],
                headers=headers,
            )
            if not url:
                continue

            result = self.request(
                url,
                headers=headers,
                response_hook=self._response_hook_text,
                error_title='Failed to get HLS manifest',
                error_hook=self._player_error_hook,
                video_id=self.video_id,
                client_name=client_name,
                has_auth=False,
                cache=False,
            )
            if not result:
                continue

            for itag in itags:
                if itag in stream_list:
                    continue

                stream_list[itag] = self._get_stream_format(
                    itag=itag,
                    title='',
                    url=url,
                    meta=meta_info,
                    headers=headers,
                    playback_stats=playback_stats,
                )

            for match in re_playlist_data.finditer(result):
                itag = match.group('itag')
                if itag in stream_list:
                    continue

                yt_format = self._get_stream_format(
                    itag=itag,
                    max_height=selected_height,
                    title='',
                    url=match.group('url'),
                    meta=meta_info,
                    headers=headers,
                    playback_stats=playback_stats,
                )
                if yt_format is None:
                    stream_info = redact_ip_in_uri(match.group(1))
                    self.log.debug(('Unknown itag - {itag}',
                                    '{stream}'),
                                   itag=itag,
                                   stream=stream_info)
                if (not yt_format
                        or (yt_format.get('hls/video')
                            and not yt_format.get('hls/audio'))):
                    continue

                if is_live:
                    yt_format['live'] = True
                    yt_format['title'] = 'Live ' + yt_format['title']

                stream_list[itag] = yt_format

    def _process_progressive_streams(self,
                                     stream_list,
                                     responses,
                                     is_live=False,
                                     use_adaptive=False,
                                     meta_info=None,
                                     playback_stats=None):
        if not responses:
            return

        if meta_info is None:
            meta_info = {'video': {},
                         'channel': {},
                         'thumbnails': {},
                         'subtitles': []}

        if playback_stats is None:
            playback_stats = {}

        context = self._context
        settings = context.get_settings()
        if self._use_mpd:
            qualities = settings.mpd_video_qualities()
            selected_height = qualities[0]['nom_height']
        else:
            selected_height = settings.fixed_video_quality()

        for client_name, response in responses.items():
            streams = response['progressive_fmts']
            if use_adaptive:
                _streams = response['adaptive_fmts']
                if _streams:
                    if streams:
                        streams += _streams
                    else:
                        streams = _streams
            if not streams:
                continue

            headers = response['client']['headers']

            for stream_map in streams:
                itag = str(stream_map['itag'])
                if itag in stream_list:
                    continue

                url = stream_map.get('url')
                conn = stream_map.get('conn')
                stream = stream_map.get('stream')

                if not url and conn and stream:
                    new_url = '%s?%s' % (conn, unquote(stream))
                elif not url and 'signatureCipher' in stream_map:
                    new_url = self._process_signature_cipher(stream_map)
                else:
                    new_url = url

                new_url = self._process_url_params(
                    new_url,
                    headers=headers,
                )
                if not new_url:
                    continue

                stream_map['itag'] = itag
                yt_format = self._get_stream_format(
                    itag=itag,
                    max_height=selected_height,
                    title='',
                    url=new_url,
                    meta=meta_info,
                    headers=headers,
                    playback_stats=playback_stats,
                )
                if yt_format is None:
                    if url:
                        stream_map['url'] = redact_ip_in_uri(url)
                    if conn:
                        stream_map['conn'] = redact_ip_in_uri(conn)
                    if stream:
                        stream_map['stream'] = redact_ip_in_uri(stream)
                    self.log.debug(('Unknown itag - {itag}',
                                    '{stream}'),
                                   itag=itag,
                                   stream=stream_map)
                if (not yt_format
                        or (yt_format.get('dash/video')
                            and not yt_format.get('dash/audio'))):
                    continue

                if is_live:
                    yt_format['live'] = True
                    yt_format['title'] = 'Live ' + yt_format['title']

                audio_track = stream_map.get('audioTrack')
                if audio_track:
                    track_id = audio_track['id']
                    track_name = audio_track['displayName']
                    is_default = audio_track['audioIsDefault']
                    itag = '.'.join((
                        itag,
                        track_id,
                    ))
                    yt_format['title'] = ' '.join((
                        yt_format['title'],
                        track_name,
                    )).strip()
                    yt_format['sort'].extend((
                        track_id.startswith(self._language_base),
                        is_default or 'original' in track_name,
                        track_name,
                    ))

                stream_list[itag] = yt_format

    def _process_signature_cipher(self, stream_map):
        if self._cipher is None:
            self.log.debug('signatureCipher detected')
            if self._player_js is None:
                self._player_js = self._get_player_js()
            self._cipher = Cipher(self._context, javascript=self._player_js)
        if not self._cipher:
            self.log.warning('signatureCipher handling disabled')
            return None

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
            except Exception:
                self.log.exception(('Failed to extract URL', 'Signature: %r'),
                                   encrypted_signature)
                self._cipher = False
                return None
            data_cache.set_item(encrypted_signature, {'sig': signature})

        if signature:
            url = ''.join((url, '&', query_var, '=', signature))
            return url
        return None

    def _process_url_params(self,
                            url,
                            stream_proxy=False,
                            mpd_manifest=False,
                            headers=None,
                            cpn=False,
                            referrer=None,
                            visitor_data=None,
                            method='POST',
                            digits_re=re_compile(r'\d+')):
        if not url:
            return url

        parts = urlsplit(url)
        params = parse_qs(parts.query)
        new_params = {}

        if 'n' not in params:
            pass
        elif not self._calculate_n:
            self.log.debug('Decoding of nsig value disabled')
            return None
        else:
            if self._player_js is None:
                self._player_js = self._get_player_js()
            if self._calculate_n is True:
                self.log.debug('Detected nsig in stream url')
                self._calculate_n = ratebypass.CalculateN(self._player_js)

            # Cipher n to get the updated value
            new_n = self._calculate_n.calculate_n(params['n'][0])
            if new_n:
                new_params['n'] = new_n
                new_params['ratebypass'] = ['yes']
            else:
                self.log.error('nsig handling failed')
                self._calculate_n = False

        if 'lmt' in params:
            snippet = (self.yt_item or {}).get('snippet')
            if snippet and 'publishedAt' not in snippet:
                try:
                    modified = fromtimestamp(int(params['lmt'][0]) // 1000000)
                except (OSError, OverflowError, ValueError):
                    modified = None
                snippet['publishedAt'] = modified

        if headers:
            if visitor_data is not False:
                headers.setdefault(
                    'X-Goog-Visitor-Id',
                    visitor_data or self._visitor_data[self._visitor_data_key],
                )
            if referrer is not False:
                headers.setdefault(
                    'Referer',
                    referrer
                    or 'https://www.youtube.com/watch?v=%s' % self.video_id,
                )

        if stream_proxy:
            new_params['__id'] = self.video_id
            new_params['__method'] = method
            new_params['__host'] = [parts.hostname]
            new_params['__path'] = parts.path
            new_params['__headers'] = urlsafe_b64encode(
                json_dumps(headers or {}).encode('utf-8')
            )

            if 'mn' in params and 'fvip' in params:
                fvip = params['fvip'][0]
                primary, _, secondary = params['mn'][0].partition(',')
                prefix, separator, server = parts.hostname.partition('---')
                if primary and secondary:
                    new_params['__host'].append(separator.join((
                        digits_re.sub(fvip, prefix),
                        server.replace(primary, secondary),
                    )))

            if cpn is not False:
                new_params['cpn'] = cpn or self._generate_cpn()

            parts = parts._replace(
                scheme='http',
                netloc=get_connect_address(self._context, as_netloc=True),
                path=PATHS.STREAM_PROXY,
            )

        elif mpd_manifest:
            if 'mpd_version' in params:
                new_params['mpd_version'] = ['7']
            else:
                parts = parts._replace(
                    path=re_sub(
                        r'/mpd_version/\d+|/?$',
                        '/mpd_version/7',
                        parts.path,
                    ),
                )

        elif 'ratebypass' not in params and 'range' not in params:
            content_length = params.get('clen', [''])[0]
            new_params['range'] = '0-{0}'.format(content_length)

        if new_params:
            params.update(new_params)
            query_str = urlencode(params, doseq=True)
            parts = parts._replace(query=query_str)

        return parts.geturl()

    def _process_captions(self, subtitles, responses):
        all_subs = SUBTITLE_SELECTIONS['all']
        default_lang = None
        subs_data = None

        for client_name, response in responses.items():
            captions = response['captions']
            client = response['client']
            use_subtitles = client.get('_use_subtitles')

            if (not captions
                    or not use_subtitles
                    or (use_subtitles is not True
                        and subtitles.sub_selection == all_subs)):
                continue

            subtitles.load(captions, client['headers'].copy())
            default_lang = subtitles.get_lang_details()
            subs_data = subtitles.get_subtitles()
            if subs_data or subs_data is False:
                return default_lang, subs_data

        video_id = self.video_id
        client_data = {
            'json': {
                'videoId': video_id,
            },
            'url': self.V1_API_URL,
            'method': 'POST',
            '_endpoint': 'player',
            '_visitor_data': self._visitor_data[self._visitor_data_key],
        }

        for client_name in ('tv_unplugged', 'web'):
            client = self.build_client(client_name, client_data)
            if not client:
                continue
            result = self.request(
                response_hook=self._response_hook_json,
                error_title='Caption player request failed',
                error_hook=self._player_error_hook,
                video_id=video_id,
                client_name=client_name,
                has_auth=client.get('_has_auth'),
                cache=False,
                **client
            )

            if result is None:
                continue
            captions = result.get('captions')
            if captions:
                subtitles.load(captions, client['headers'])
                default_lang = subtitles.get_lang_details()
                subs_data = subtitles.get_subtitles()
                if subs_data or subs_data is False:
                    return default_lang, subs_data

        return default_lang, subs_data

    def _get_error_details(self,
                           playability_status,
                           details=('errorScreen', (
                                   ('playerErrorMessageRenderer',
                                    'reason'),
                                   ('confirmDialogRenderer',
                                    'title'),
                                   ('playerCaptchaViewModel',
                                    'accessibility',
                                    'accessibilityData',
                                    'label'),
                           ))):
        if not playability_status:
            return None

        result = self.json_traverse(playability_status, details)
        if not result or not isinstance(result, dict) or 'runs' not in result:
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

    def load_stream_info(self,
                         video_id,
                         ask_for_quality=None,
                         audio_only=None,
                         incognito=None,
                         use_mpd=None):
        self.video_id = video_id

        if ask_for_quality is None:
            ask_for_quality = self._ask_for_quality
        else:
            self._ask_for_quality = ask_for_quality

        if audio_only is None:
            audio_only = self._audio_only
        else:
            self._audio_only = audio_only

        if incognito is None:
            incognito = self._context.get_param(INCOGNITO, False)
        if incognito:
            visitor_data_key = self._visitor_data_key = INCOGNITO
            self._visitor_data[visitor_data_key] = None
        else:
            visitor_data_key = self._visitor_data_key = 'current'

        if use_mpd is None:
            use_mpd = self._use_mpd
        else:
            self._use_mpd = use_mpd

        context = self._context
        settings = context.get_settings()
        age_gate_enabled = settings.age_gate()
        use_remote_history = settings.use_remote_history()

        _client_name = None
        _client = None
        _has_auth = None
        _result = None
        _video_details = None
        _microformat = None
        _streaming_data = None
        _playability = None
        _status = None
        _reason = None

        auth_client = None
        visitor_data = self._visitor_data[visitor_data_key]
        video_details = {}
        microformat = {}
        responses = {}
        stream_list = {}

        fail = self.FAILURE_REASONS
        abort = False

        logged_in = self.logged_in
        client_data = {
            'json': {
                'videoId': video_id,
            },
            'url': self.V1_API_URL,
            'method': 'POST',
            '_access_tokens': {
                'user': (self._access_tokens.get('user')
                         if (self._configs.get('user', {})
                             .get('token-allowed', True)) else
                         None),
                'tv': self._access_tokens.get('tv'),
                'vr': self._access_tokens.get('vr'),
            },
            '_endpoint': 'player',
            '_cpn': None,
            '_visitor_data': visitor_data,
        }
        if use_remote_history:
            client_data['_auth_type'] = 'user'
            client_data['_auth_requested'] = True

        for name, clients in self._client_groups:
            if not clients:
                continue
            if name == 'mpd' and not use_mpd:
                continue
            if name == 'ask' and use_mpd and not ask_for_quality:
                continue
            if name.startswith('auth_enabled|initial_request'):
                if visitor_data and not logged_in:
                    continue
                allow_skip = False
                client_data['_auth_requested'] = True
            else:
                allow_skip = True

            exclude_retry = set()
            restart = None
            while 1:
                for _client_name in clients:
                    if _client_name in exclude_retry:
                        continue
                    client_data['_cpn'] = self._generate_cpn()
                    _client = self.build_client(_client_name, client_data)
                    if _client:
                        _has_auth = _client.get('_has_auth')
                        if _has_auth or _has_auth is False:
                            exclude_retry.add(_client_name)
                    else:
                        _has_auth = None
                        _result = None
                        _video_details = None
                        _microformat = None
                        _streaming_data = None
                        _playability = None
                        _status = None
                        _reason = None
                        continue

                    _result = self.request(
                        response_hook=self._response_hook_json,
                        error_title='Player request failed',
                        error_hook=self._player_error_hook,
                        video_id=video_id,
                        client_name=_client_name,
                        has_auth=_has_auth,
                        cache=False,
                        pass_data=True,
                        raise_exc=False,
                        **_client
                    ) or {}

                    if not visitor_data:
                        visitor_data = self.json_traverse(
                            _result,
                            (
                                'responseContext',
                                (
                                    (
                                        'visitorData',
                                    ),
                                    (
                                        'serviceTrackingParams',
                                        0,
                                        'params',
                                        {
                                            'name': 'key',
                                            'match': ('visitor_data',
                                                      'visitorData'),
                                            'out': 'value',
                                        },
                                    ),
                                ),
                            )
                        )
                        if visitor_data:
                            client_data['_visitor_data'] = visitor_data
                            self._visitor_data[visitor_data_key] = visitor_data
                    _video_details = _result.get('videoDetails', {})
                    _microformat = (_result
                                    .get('microformat', {})
                                    .get('playerMicroformatRenderer'))
                    _streaming_data = _result.get('streamingData', {})
                    _playability = _result.get('playabilityStatus', {})
                    if _playability:
                        _status = _playability.get('status', 'ERROR').upper()
                        _reason = _playability.get('reason', 'UNKNOWN')
                    else:
                        _error = _result.get('error', {})
                        _status = _error.get('status', 'ERROR').upper()
                        _reason = _error.get('message', 'UNKNOWN')

                    if (_video_details
                            and video_id != _video_details.get('videoId')):
                        _status = 'CONTENT_NOT_AVAILABLE_IN_THIS_APP'
                        _reason = 'Watch on the latest version of YouTube'

                    if (age_gate_enabled
                            and _playability.get('desktopLegacyAgeGateReason')):
                        abort = True
                        break
                    elif _status == 'LIVE_STREAM_OFFLINE':
                        abort = True
                        break
                    elif _status == 'OK':
                        break
                    elif not _playability or _status in {
                        'AGE_CHECK_REQUIRED',
                        'AGE_VERIFICATION_REQUIRED',
                        'CONTENT_CHECK_REQUIRED',
                        'LOGIN_REQUIRED',
                        'CONTENT_NOT_AVAILABLE_IN_THIS_APP',
                        'ERROR',
                        'UNPLAYABLE',
                    }:
                        self.log.warning(('Failed to retrieve video info',
                                          'Status:   {status}',
                                          'Reason:   {reason}',
                                          'video_id: {video_id!r}',
                                          'Client:   {client!r}',
                                          'Auth:     {has_auth!r}'),
                                         status=_status,
                                         reason=_reason or 'UNKNOWN',
                                         video_id=video_id,
                                         client=_client_name,
                                         has_auth=_has_auth)
                        fail_reason = _reason.lower()
                        if any(why in fail_reason for why in fail['auth']):
                            if _has_auth:
                                restart = False
                            elif restart is None and logged_in:
                                client_data['_auth_requested'] = True
                                restart = True
                            else:
                                continue
                            break
                        elif any(why in fail_reason for why in fail['reauth']):
                            if _client.get('_auth_required') == 'ignore_fail':
                                continue
                            elif client_data.get('_auth_required'):
                                restart = False
                                abort = True
                            elif restart is None and logged_in:
                                client_data['_auth_required'] = True
                                restart = True
                            break
                        elif any(why in fail_reason for why in fail['abort']):
                            abort = True
                            break
                        elif any(why in fail_reason for why in fail['skip']):
                            if allow_skip:
                                break
                        elif any(why in fail_reason for why in fail['retry']):
                            continue
                    else:
                        self.log.warning('Unknown playabilityStatus: {status!r}',
                                         status=_playability)
                else:
                    break
                if not restart:
                    break
                restart = False

            if abort:
                break

            if _status == 'OK':
                self.log.debug(('Retrieved video info:',
                                'video_id: {video_id!r}',
                                'Client:   {client!r}',
                                'Auth:     {has_auth!r}'),
                               video_id=video_id,
                               client=_client_name,
                               has_auth=_has_auth)

                video_details = merge_dicts(
                    _video_details,
                    video_details,
                    compare_str=True,
                )

                microformat = merge_dicts(
                    _microformat,
                    microformat,
                    compare_str=True,
                )

                if not auth_client and _has_auth:
                    auth_client = {
                        'client': _client.copy(),
                        'result': _result,
                    }
                    client_data['_auth_requested'] = False

                responses[_client_name] = {
                    'client': _client,
                    'progressive_fmts': _streaming_data.get('formats'),
                    'adaptive_fmts': _streaming_data.get('adaptiveFormats'),
                    'mpd_manifest': _streaming_data.get('dashManifestUrl'),
                    'hls_manifest': _streaming_data.get('hlsManifestUrl'),
                    'captions': _result.get('captions'),
                }

                if (not client_data.get('_auth_required')
                        and video_details.get('isPrivate')):
                    client_data['_auth_required'] = True

        if not responses:
            if _status == 'LIVE_STREAM_OFFLINE':
                if not _reason:
                    _reason = self._get_error_details(
                        _playability,
                        details=(
                            'liveStreamability',
                            'liveStreamabilityRenderer',
                            'offlineSlate',
                            'liveStreamOfflineSlateRenderer',
                            'mainText'
                        )
                    )
            elif not _reason:
                _reason = self._get_error_details(_playability)
            raise YouTubeException(_reason or 'UNKNOWN')

        self.yt_item = yt_item = {
            'id': video_id,
            'snippet': {
                'title': video_details.get('title'),
                'description': video_details.get('shortDescription'),
                'channelId': video_details.get('channelId'),
                'channelTitle': video_details.get('author'),
                'thumbnails': (video_details
                               .get('thumbnail', {})
                               .get('thumbnails', [])),
            },
            'contentDetails': {
                'duration': 'P' + video_details.get('lengthSeconds', '0') + 'S',
            },
            'statistics': {
                'viewCount': video_details.get('viewCount', '0'),
            },
            '_partial': True,
        }
        is_live = video_details.get('isLiveContent') or video_details.get('hasLiveStreamingData')
        if is_live:
            is_live = video_details.get('isLive', False)
            live_dvr = video_details.get('isLiveDvrEnabled', False)
            thumb_suffix = '_live' if is_live else ''
        else:
            live_dvr = False
            thumb_suffix = ''

        meta_info = {
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
            'channel': {
                'id': video_details.get('channelId', ''),
                'author': unescape(video_details.get('author', '')
                                   .encode('raw_unicode_escape')
                                   .decode('raw_unicode_escape')),
            },
            'thumbnails': {
                thumb_type: {
                    'url': THUMB_URL.format(
                        video_id, thumb['name'], thumb_suffix
                    ),
                    'size': thumb['size'],
                    'ratio': thumb['ratio'],
                    'unverified': True,
                }
                for thumb_type, thumb in THUMB_TYPES.items()
            },
            'subtitles': None,
        }

        if use_remote_history and auth_client:
            playback_stats = {
                'playback_url': 'videostatsPlaybackUrl',
                'watchtime_url': 'videostatsWatchtimeUrl',
            }
            playback_tracking = (auth_client
                                 .get('result', {})
                                 .get('playbackTracking', {}))
            cpn = auth_client.get('_cpn') or self._generate_cpn()

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

        if is_live or live_dvr or ask_for_quality or not use_mpd:
            self._process_hls(
                stream_list=stream_list,
                responses=responses,
                is_live=is_live,
                meta_info=meta_info,
                playback_stats=playback_stats,
            )

        if not is_live or live_dvr:
            subtitles = Subtitles(context, video_id, use_mpd=use_mpd)
            default_lang, subs_data = self._process_captions(
                subtitles=subtitles,
                responses=responses,
            )
            if subs_data and not subtitles.use_isa:
                meta_info['subtitles'] = [
                    subtitle['url'] for subtitle in subs_data.values()
                    if 'url' in subtitle
                ]
                subs_data = None
        else:
            default_lang = None
            subs_data = None

        if not default_lang:
            default_lang = {
                'default': 'und',
                'original': 'und',
                'is_asr': False,
            }

        # extract adaptive streams and create MPEG-DASH manifest
        if use_mpd and not audio_only:
            self._process_mpd(
                stream_list=stream_list,
                responses=responses,
                meta_info=meta_info,
                playback_stats=playback_stats,
            )
            video_data, audio_data = self._process_adaptive_streams(
                responses=responses,
                default_lang_code=(default_lang['default']
                                   if default_lang['original'] == 'und' else
                                   default_lang['original']),
            )
            manifest_url, main_stream = self._generate_mpd_manifest(
                video_data, audio_data, subs_data,
            )

            if main_stream:
                yt_format = self._get_stream_format(
                    itag='9999',
                    info=main_stream,
                    title='',
                    url=manifest_url,
                    meta=meta_info,
                    headers={
                        'User-Agent': 'youtube/0.1 ({0})'.format(self.video_id),
                    },
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

                localize = context.localize
                for _prop in ('multi_language', 'multi_audio'):
                    if not main_stream.get(_prop):
                        continue
                    _prop = 'stream.' + _prop
                    title.extend((' [', localize(_prop), ']'))

                if len(title) > 1:
                    yt_format['title'] = ''.join(title)

                stream_list['9999'] = yt_format

        # extract non-adaptive streams
        if audio_only or ask_for_quality or not use_mpd:
            self._process_progressive_streams(
                stream_list=stream_list,
                responses=responses,
                is_live=is_live,
                use_adaptive=use_mpd,
                meta_info=meta_info,
                playback_stats=playback_stats,
            )

        if stream_list:
            self.log.debug(('Media details:',
                            'Status: {status!r}',
                            'Item:   {item!r}'),
                           status=meta_info['status'],
                           item=yt_item)
        else:
            raise YouTubeException('No streams found')

        return stream_list.values(), yt_item

    def _process_adaptive_streams(self,
                                  responses,
                                  default_lang_code='und',
                                  codec_re=re_compile(
                                      r'codecs='
                                      r'"((?P<codec>.+?)\.(?P<props>.+))"'
                                  )):
        context = self._context
        settings = context.get_settings()
        audio_only = self._audio_only
        qualities = settings.mpd_video_qualities()
        isa_capabilities = context.inputstream_adaptive_capabilities()
        stream_features = settings.stream_features()
        allow_3d = '3d' in stream_features
        allow_hdr = 'hdr' in stream_features
        allow_hfr = 'hfr' in stream_features
        disable_hfr_max = 'no_hfr_max' in stream_features
        allow_spa = 'spa' in stream_features
        allow_ssa = 'ssa' in stream_features
        allow_vr = 'vr' in stream_features
        prefer_dub = 'prefer_dub' in stream_features
        prefer_auto_dub = 'prefer_auto_dub' in stream_features
        fps_map = (self.INTEGER_FPS_SCALE
                   if 'no_frac_fr_hint' in stream_features else
                   self.FRACTIONAL_FPS_SCALE)
        quality_factor_map = self.QUALITY_FACTOR
        stream_select = settings.stream_select()
        localize = context.localize

        debugging = self.log.debugging
        sep = {'__sep__': '   '}

        audio_data = {}
        video_data = {}
        preferred_audio = {
            'language_code': None,
            'role_id': None,
            'role_order': None,
            'fallback': True,
        }
        default_lang = self._language_base
        prefer_default_lang = self._language_prefer_default
        lang_role_details = self.LANG_ROLE_DETAILS

        for client_name, response in responses.items():
            client = response['client']
            if not client.get('_use_adaptive', True):
                continue

            stream_data = response['adaptive_fmts']
            if not stream_data:
                continue

            log_client = debugging
            log_audio_header = None
            log_video_header = None

            for stream in stream_data:
                mime_type = stream.get('mimeType')
                if not mime_type:
                    continue

                itag_id = itag = str(stream.get('itag'))
                if not itag:
                    continue

                index_range = stream.get('indexRange')
                if not index_range:
                    continue

                init_range = stream.get('initRange')
                if not init_range:
                    continue

                url = stream.get('url')
                if not url and 'signatureCipher' in stream:
                    url = self._process_signature_cipher(stream)
                if not url:
                    continue

                mime_type, codecs = unquote(mime_type).split('; ')
                codecs = codec_re.match(codecs)
                if codecs:
                    codec = codecs.group('codec')
                    codec_properties = codecs.group('props')
                    codecs = codecs.group(1)
                    if codec.startswith(('vp9', 'vp09')):
                        codec = 'vp9'
                        preferred_codec = codec in stream_features
                        if codec_properties.startswith(('2', '02.')):
                            codec = 'vp9.2'
                    else:
                        if codec.startswith('dts'):
                            codec = 'dts'
                        preferred_codec = codec in stream_features
                    if codec not in isa_capabilities:
                        continue
                else:
                    continue
                media_type, container = mime_type.split('/')
                bitrate = stream.get('bitrate', 0)

                if media_type == 'audio':
                    data = audio_data
                    channels = stream.get('audioChannels', 2)
                    if channels > 2 and not allow_ssa:
                        continue

                    is_spa = stream.get('spatialAudioType', '')
                    if is_spa and not allow_spa:
                        continue

                    if 'audioTrack' in stream:
                        audio_track = stream['audioTrack']

                        language = audio_track.get('id', default_lang_code)
                        if '.' in language:
                            language_code, role_id = language.split('.')
                        else:
                            language_code = language
                            role_id = '4'
                    else:
                        language_code = default_lang_code
                        role_id = '-1'

                    role_details = lang_role_details.get(role_id)
                    # Unsure of what other audio types are available
                    # Role set to "alternate" as default fallback
                    if not role_details:
                        role_details = lang_role_details[0]
                    role_type, role, role_order = role_details

                    preferred_order = preferred_audio['role_order']
                    language_fallback = preferred_audio['fallback']

                    if (default_lang
                            and language_code.startswith(default_lang)):
                        is_fallback = role != 'main'
                        if role_type == 'dub.auto':
                            if prefer_auto_dub:
                                role = 'main'
                                role_order = 0
                        elif role_type == 'dub':
                            if prefer_dub:
                                role = 'main'
                                role_order = 0
                        elif prefer_default_lang:
                            role = 'main'
                            role_order = 0
                        lang_match = (
                                (language_fallback and not is_fallback)
                                or preferred_order is None
                                or role_order > preferred_order
                        )
                        language_fallback = is_fallback
                    else:
                        lang_match = (
                                language_fallback
                                and (preferred_order is None
                                     or role_order > preferred_order)
                        )
                        language_fallback = True

                    if lang_match:
                        preferred_audio = {
                            'language_code': language_code,
                            'role_id': role_id,
                            'role_order': role_order,
                            'fallback': language_fallback,
                        }
                    language = context.get_language_name(language_code)

                    sample_rate = int(stream.get('audioSampleRate', '0'), 10)

                    is_drc = stream.get('isDrc', False)
                    if is_drc:
                        itag += '.drc'

                    mime_group = (
                        mime_type,
                        language_code,
                        role_id,
                    )

                    label = '{0} ({1} kbps)'.format(
                        localize('stream.{0}'.format(role_type)),
                        bitrate // 1000,
                    )
                    if channels > 2 or 'auto' not in stream_select:
                        quality_group = (
                            container,
                            codec,
                            language_code,
                            role_id,
                        )
                    else:
                        quality_group = mime_group

                    height = width = fps = frame_rate = None
                    is_hdr = is_vr = is_3d = None

                    log_audio = debugging
                    log_video = False
                    if log_audio_header is None:
                        log_audio_header = debugging
                elif audio_only:
                    continue
                else:
                    data = video_data
                    # Could use "zxx" language code for
                    # "Non-Linguistic, Not Applicable" but that is too verbose
                    language_code = ''

                    fps = stream.get('fps', 0)
                    if fps > 30 and not allow_hfr:
                        continue

                    if 'colorInfo' in stream:
                        is_hdr = not any(
                            value.endswith('BT709')
                            for value in stream['colorInfo'].values()
                        )
                    else:
                        is_hdr = 'HDR' in stream.get('qualityLabel', '')
                    if is_hdr and not allow_hdr:
                        continue

                    is_3d = stream.get('stereoLayout', '')
                    if is_3d and not allow_3d:
                        continue

                    is_vr = stream.get('projectionType', '')
                    if is_vr:
                        if is_vr == 'RECTANGULAR':
                            is_vr = ''
                        elif not allow_vr:
                            continue

                    height = stream.get('height')
                    width = stream.get('width')
                    if height > width:
                        compare_width = height
                        compare_height = width
                    else:
                        compare_width = width
                        compare_height = height
                    # Compare video stream width against pre-computed quality
                    # selection width based on approximate aspect ratio.
                    # 1.69 ~= 0.95 * 16 / 9
                    if width / height > 1.69:
                        nom_width = 'width_16:9'
                    else:
                        nom_width = 'width_4:3'

                    bound = None
                    _disable_hfr_max = disable_hfr_max
                    for quality in qualities:
                        if compare_width > quality[nom_width]:
                            if bound:
                                if compare_height >= bound['min_height']:
                                    quality = bound
                                elif compare_height < quality['min_height']:
                                    quality = qualities[-1]
                                if fps > 30 and _disable_hfr_max:
                                    bound = None
                            break
                        _disable_hfr_max = _disable_hfr_max and not bound
                        bound = quality
                    if not bound:
                        continue

                    # map frame rates to a more common representation to lessen
                    # the chance of double refresh changes
                    if fps:
                        frame_rate = fps_map.get(fps) or fps_map[0].format(fps)
                    else:
                        frame_rate = None

                    mime_group = (
                        mime_type,
                        codec,
                        is_hdr,
                        is_vr,
                    )

                    label = quality['label'].format(
                        quality['nom_height'] or compare_height,
                        fps if fps > 30 else '',
                        ' HDR' if is_hdr else '',
                        ' 3D' if is_3d else '',
                        ' VR' if is_vr else '',
                    )
                    quality_group = (
                        container,
                        codec,
                        label,
                    )

                    channels = sample_rate = is_drc = is_spa = None
                    language = role = role_order = role_type = None

                    log_audio = False
                    log_video = debugging
                    if log_video_header is None:
                        log_video_header = debugging

                urls = self._process_url_params(
                    unquote(url),
                    stream_proxy=True,
                    headers=client['headers'],
                    cpn=client.get('_cpn'),
                )
                if not urls:
                    continue

                details = {
                    'mimeType': mime_type,
                    'baseUrl': entity_escape(urls),
                    'mediaType': media_type,
                    'container': container,
                    'codecs': codecs,
                    'codec': codec,
                    'preferred_codec': preferred_codec,
                    'id': itag,
                    'width': width,
                    'height': height,
                    'label': label,
                    'bitrate': bitrate,
                    'biasedBitrate': bitrate * quality_factor_map.get(codec, 1),
                    # integer round up
                    'duration': -(-int(stream.get('approxDurationMs', 0))
                                  // 1000),
                    'fps': fps,
                    'frameRate': frame_rate,
                    'hdr': is_hdr,
                    'projection': is_vr,
                    'stereoLayout': is_3d,
                    'indexRange': '{start}-{end}'.format(**index_range),
                    'initRange': '{start}-{end}'.format(**init_range),
                    'langCode': language_code,
                    'langName': language,
                    'role': role,
                    'roleOrder': role_order,
                    'sampleRate': sample_rate,
                    'channels': channels,
                    'drc': is_drc,
                    'spatial': is_spa,
                }
                mime_group = data.setdefault(mime_group, {})
                quality_group = data.setdefault(quality_group, {})
                mime_group[itag] = quality_group[itag] = details

                if log_client:
                    self.log.debug('{_:{_}^100}', _='=', extra=sep)
                    self.log.debug('Streams found for %r client:',
                                   client_name,
                                   extra=sep)
                    log_client = False
                if log_audio:
                    if log_audio_header:
                        self.log.debug('{_:{_}^100}', _='-', extra=sep)
                        self.log.debug('{itag:^3}'
                                       ' | {container:^4}'
                                       ' | {channels:^5}'
                                       ' | {bitrate:^8}'
                                       ' | {sample_rate:^9}'
                                       ' | {drc:^3}'
                                       ' | {codecs:^19}'
                                       ' | {info}',
                                       itag='ID',
                                       container='TYPE',
                                       channels='CH',
                                       bitrate='ABR',
                                       sample_rate='ASR',
                                       drc='DRC',
                                       codecs='CODECS',
                                       info='INFO',
                                       extra=sep)
                        self.log.debug('{_:{_}^100}', _='-', extra=sep)
                        log_audio_header = False
                    self.log.debug('{itag:3}'
                                   ' | {container:4}'
                                   ' | {channels:2} ch'
                                   ' | {bitrate:3} kbps'
                                   ' | {sample_rate:<5.2f} kHz'
                                   ' | {drc:^3}'
                                   ' | {codecs:19}'
                                   ' | {language}'
                                   ' {role_type}',
                                   itag=itag_id,
                                   container=container,
                                   channels=channels,
                                   bitrate=bitrate // 1000,
                                   sample_rate=sample_rate / 1000,
                                   drc='Y' if is_drc else '-',
                                   codecs='%s (%s)' % (codec, codecs),
                                   language=language,
                                   role_type=role_type,
                                   extra=sep)
                elif log_video:
                    if log_video_header:
                        self.log.debug('{_:{_}^100}', _='-', extra=sep)
                        self.log.debug('{itag:^3}'
                                       ' | {container:^4}'
                                       ' | {width:>4} x {height:<4}'
                                       ' | {fps:^6}'
                                       ' | {hdr:^3}'
                                       ' | {s3d:^3}'
                                       ' | {vr:^3}'
                                       ' | {bitrate:^11}'
                                       ' | {codecs}',
                                       itag='ID',
                                       container='TYPE',
                                       width='W',
                                       height='H',
                                       fps='FPS',
                                       hdr='HDR',
                                       s3d='3D',
                                       vr='VR',
                                       bitrate='VBR',
                                       codecs='CODECS',
                                       extra=sep)
                        self.log.debug('{_:{_}^100}', _='-', extra=sep)
                        log_video_header = False
                    self.log.debug('{itag:3}'
                                   ' | {container:4}'
                                   ' | {width:>4} x {height:<4}'
                                   ' | {fps:2} fps'
                                   ' | {hdr:^3}'
                                   ' | {s3d:^3}'
                                   ' | {vr:^3}'
                                   ' | {bitrate:6,} kbps'
                                   ' | {codecs}',
                                   itag=itag_id,
                                   container=container,
                                   width=width,
                                   height=height,
                                   fps=fps,
                                   hdr='Y' if is_hdr else '-',
                                   s3d='Y' if is_3d else '-',
                                   vr='Y' if is_vr else '-',
                                   bitrate=bitrate // 1000,
                                   codecs='%s (%s)' % (codec, codecs),
                                   extra=sep)

        if not video_data and not audio_only:
            self.log.debug('No video mime-types found')
            return None, None

        def _stream_sort(stream, alt_sort=('alt_sort' in stream_features)):
            if not stream:
                return (1,)

            preferred = stream['preferred_codec']
            return (
                - preferred,
                - stream['height']
                if preferred or not alt_sort else
                stream['height'],
                not stream['projection'],
                not stream['stereoLayout'],
                - stream['fps'],
                - stream['hdr'],
                - stream['biasedBitrate'],
            ) if stream['mediaType'] == 'video' else (
                - preferred,
                not stream['spatial'],
                - stream['channels'],
                - stream['biasedBitrate'],
                stream['drc'],
            )

        def _group_sort(item):
            group, streams = item
            main_stream = streams[0]

            key = (
                group[0] != main_stream['mimeType'],
            ) if main_stream['mediaType'] == 'video' else (
                group[0] != main_stream['mimeType'],
                group[-2] != preferred_audio['language_code'],
                group[-1] != preferred_audio['role_id'],
                main_stream['langName'],
                - main_stream['roleOrder'],
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
                               subs_data):
        # Following line can be uncommented if needed to use mpd for audio only
        # if (not video_data and not self._audio_only) or not audio_data:
        if not video_data or not audio_data:
            return None, None

        if not self.BASE_PATH:
            self.log.error_trace('Unable to access temp directory')
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

            if previous_group[0] == previous_stream['mimeType']:
                if new_group[0] == new_stream['container']:
                    return not skip_group

                skip_group = (
                    new_stream['height'] <= previous_stream['height']
                    if media_type == 'video' else
                    new_stream['channels'] <= previous_stream['channels']
                )
            else:
                if new_group[0] == new_stream['mimeType']:
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

        context = self._context
        settings = context.get_settings()
        stream_features = settings.stream_features()
        do_filter = 'filter' in stream_features
        frame_rate_hint = 'no_fr_hint' not in stream_features
        stream_select = settings.stream_select()
        localize = context.localize

        main_stream = {
            'audio': audio_data[0][1][0],
            'multi_audio': False,
            'multi_language': False,
        }
        if video_data:
            main_stream['video'] = video_data[0][1][0]
            duration = main_stream['video']['duration']
        else:
            duration = main_stream['audio']['duration']

        output = [
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<MPD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
                ' xmlns="urn:mpeg:dash:schema:mpd:2011"'
                ' xmlns:xlink="http://www.w3.org/1999/xlink"'
                ' xsi:schemaLocation="urn:mpeg:dash:schema:mpd:2011 http://standards.iso.org/ittf/PubliclyAvailableStandards/MPEG-DASH_schema_files/DASH-MPD.xsd"'
                ' minBufferTime="PT1.5S"'
                ' mediaPresentationDuration="PT', str(duration), 'S"'
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

            if group[0] == mime_type and 'auto' in stream_select:
                label = '{0} [{1}]'.format(
                    stream['langName']
                    or localize('stream.automatic'),
                    stream['label']
                )
                if stream == main_stream[media_type]:
                    default = True
                    role = 'main'
            elif group[0] == container and 'list' in stream_select:
                if 'auto' in stream_select or media_type == 'video':
                    label = stream['label']
                else:
                    label = ' '.join((
                        stream['langName'],
                        stream['label'],
                    )).strip()
                    if stream == main_stream[media_type]:
                        default = True
                        role = 'main'
            else:
                continue

            if role == 'main':
                if not default:
                    role = 'alternate'
                if media_type == 'audio':
                    original = stream['role'] == 'main'
                else:
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
                    ' original="', VALUE_TO_STR[original], '"'
                    ' default="', VALUE_TO_STR[default], '"'
                    ' impaired="', VALUE_TO_STR[impaired], '"'
                    '>\n'
                # AdaptationSet Label element not currently used by ISA
                '\t\t\t<Label>', label, '</Label>\n'
                '\t\t\t<Role'
                    ' schemeIdUri="urn:mpeg:dash:role:2011"'
                    ' value="', role, '"'
                    '/>\n'
            ))

            num_streams = len(streams)
            if media_type == 'audio':
                output.extend([(
                    '\t\t\t<Representation'
                        ' id="{id}"'
                        ' codecs="{codecs}"'
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
                    '\t\t\t\t<BaseURL>{baseUrl}</BaseURL>\n'
                    # '\t\t\t\t<BaseURL>{url}</BaseURL>\n'
                    # + ''.join([''.join([
                    # '\t\t\t\t<BaseURL>', entity_escape(url), '</BaseURL>\n',
                    # ]) for url in stream['baseUrl'] if url]) +
                    '\t\t\t\t<SegmentBase indexRange="{indexRange}" timescale="1000">\n'
                    '\t\t\t\t\t<Initialization range="{initRange}"/>\n'
                    '\t\t\t\t</SegmentBase>\n'
                    '\t\t\t</Representation>\n'
                ).format(
                    quality=(idx + 1),
                    priority=(num_streams - idx),
                    # url=entity_escape(url),
                    **stream
                )
                    for idx, stream in enumerate(streams)
                    # for url in stream['baseUrl']
                    # if url
                ])

            elif media_type == 'video':
                output.extend([(
                    '\t\t\t<Representation'
                        ' id="{id}"'
                        ' codecs="{codecs}"'
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
                    '\t\t\t\t<BaseURL>{baseUrl}</BaseURL>\n'
                    # '\t\t\t\t<BaseURL>{url}</BaseURL>\n'
                    # + ''.join([''.join([
                    # '\t\t\t\t<BaseURL>', entity_escape(url), '</BaseURL>\n',
                    # ]) for url in stream['baseUrl'] if url]) +
                    '\t\t\t\t<SegmentBase indexRange="{indexRange}">\n'
                    '\t\t\t\t\t<Initialization range="{initRange}"/>\n'
                    '\t\t\t\t</SegmentBase>\n'
                    '\t\t\t</Representation>\n'
                ).format(
                    quality=(idx + 1),
                    priority=(num_streams - idx),
                    # url=entity_escape(url),
                    **stream
                )
                    for idx, stream in enumerate(streams)
                    # for url in stream['baseUrl']
                    # if url
                ])

            output.append('\t\t</AdaptationSet>\n')
            set_id += 1

        if subs_data:
            headers = subs_data.pop('_headers', None)
            for lang_id, subtitle in subs_data.items():
                lang_code = subtitle['lang']
                label = language = subtitle['language']
                kind = subtitle['kind']
                if kind == 'translation':
                    label = localize('subtitles.translation.x', language)
                    kind = '_'.join((lang_code, kind))
                else:
                    kind = lang_id

                url = entity_escape(unquote(self._process_url_params(
                    subtitle['url'],
                    stream_proxy=True,
                    headers=headers,
                )))
                if not url:
                    continue

                output.extend((
                    '\t\t<AdaptationSet'
                        ' id="', str(set_id), '"'
                        ' contentType="text"'
                        ' mimeType="', subtitle['mime_type'], '"'
                        ' lang="', lang_code, '"'
                        # name attribute is ISA specific and does not exist in
                        # the MPD spec. Should be a child Label element instead
                        ' name="[B]', label, '[/B]"'
                        # original / default are ISA specific attributes
                        ' original="', VALUE_TO_STR[subtitle['original']], '"'
                        ' default="', VALUE_TO_STR[subtitle['default']], '"'
                        '>\n'
                    # AdaptationSet Label element not currently used by ISA
                    '\t\t\t<Label>', label, '</Label>\n'
                    '\t\t\t<Role'
                        ' schemeIdUri="urn:mpeg:dash:role:2011"'
                        ' value="subtitle"'
                        '/>\n'
                    '\t\t\t<Representation'
                        ' id="subs_', kind, '"'
                        ' codecs="', subtitle['codec'], '"'
                        ' mimeType="', subtitle['mime_type'], '"'
                        # unsure about what value to use for bandwidth
                        # ' bandwidth="0"'
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
            main_stream['multi_language'] = True
        if roles.difference({'', 'main', 'dub'}):
            main_stream['multi_audio'] = True

        filename = '.'.join((self.video_id, 'mpd'))
        filepath = os_path.join(self.BASE_PATH, filename)
        try:
            with xbmcvfs.File(filepath, 'w') as mpd_file:
                success = mpd_file.write(output)
        except (IOError, OSError):
            self.log.exception(('File write failed', 'File: %s'), filepath)
            success = False
        if success:
            return urlunsplit((
                'http',
                get_connect_address(context, as_netloc=True),
                PATHS.MPD,
                urlencode({'file': filename}),
                '',
            )), main_stream
        return None, None
