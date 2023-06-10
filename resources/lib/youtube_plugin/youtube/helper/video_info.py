# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import re
import json
import random
import traceback
from html import unescape
from urllib.parse import (parse_qs, urlsplit, urlunsplit, urlencode, urljoin,
                          quote, unquote)

import requests
from ...kodion.utils import is_httpd_live, make_dirs, DataCache
from ..youtube_exceptions import YouTubeException
from .subtitles import Subtitles
from .ratebypass import ratebypass
from .signature.cipher import Cipher

import xbmcvfs


class VideoInfo(object):
    FORMAT = {
        # === Non-DASH ===
        '5': {'container': 'flv',
              'title': '240p',
              'sort': [240, 0],
              'video': {'height': 240, 'encoding': 'h.263'},
              'audio': {'bitrate': 64, 'encoding': 'mp3'}},
        '6': {'container': 'flv',  # Discontinued
              'discontinued': True,
              'video': {'height': 270, 'encoding': 'h.263'},
              'audio': {'bitrate': 64, 'encoding': 'mp3'}},
        '13': {'container': '3gp',  # Discontinued
               'discontinued': True,
               'video': {'encoding': 'mpeg-4'},
               'audio': {'encoding': 'aac'}},
        '17': {'container': '3gp',
               'title': '144p',
               'sort': [144, -20],
               'video': {'height': 144, 'encoding': 'mpeg-4'},
               'audio': {'bitrate': 24, 'encoding': 'aac'}},
        '18': {'container': 'mp4',
               'title': '360p',
               'sort': [360, 0],
               'video': {'height': 360, 'encoding': 'h.264'},
               'audio': {'bitrate': 96, 'encoding': 'aac'}},
        '22': {'container': 'mp4',
               'title': '720p',
               'sort': [720, 0],
               'video': {'height': 720, 'encoding': 'h.264'},
               'audio': {'bitrate': 192, 'encoding': 'aac'}},
        '34': {'container': 'flv',  # Discontinued
               'discontinued': True,
               'video': {'height': 360, 'encoding': 'h.264'},
               'audio': {'bitrate': 128, 'encoding': 'aac'}},
        '35': {'container': 'flv',  # Discontinued
               'discontinued': True,
               'video': {'height': 480, 'encoding': 'h.264'},
               'audio': {'bitrate': 128, 'encoding': 'aac'}},
        '36': {'container': '3gp',
               'title': '240p',
               'sort': [240, -20],
               'video': {'height': 240, 'encoding': 'mpeg-4'},
               'audio': {'bitrate': 32, 'encoding': 'aac'}},
        '37': {'container': 'mp4',
               'title': '1080p',
               'sort': [1080, 0],
               'video': {'height': 1080, 'encoding': 'h.264'},
               'audio': {'bitrate': 192, 'encoding': 'aac'}},
        '38': {'container': 'mp4',
               'title': '3072p',
               'sort': [3072, 0],
               'video': {'height': 3072, 'encoding': 'h.264'},
               'audio': {'bitrate': 192, 'encoding': 'aac'}},
        '43': {'container': 'webm',
               'title': '360p',
               'sort': [360, -1],
               'video': {'height': 360, 'encoding': 'vp8'},
               'audio': {'bitrate': 128, 'encoding': 'vorbis'}},
        '44': {'container': 'webm',  # Discontinued
               'discontinued': True,
               'video': {'height': 480, 'encoding': 'vp8'},
               'audio': {'bitrate': 128, 'encoding': 'vorbis'}},
        '45': {'container': 'webm',  # Discontinued
               'discontinued': True,
               'video': {'height': 720, 'encoding': 'vp8'},
               'audio': {'bitrate': 192, 'encoding': 'vorbis'}},
        '46': {'container': 'webm',  # Discontinued
               'discontinued': True,
               'video': {'height': 1080, 'encoding': 'vp8'},
               'audio': {'bitrate': 192, 'encoding': 'vorbis'}},
        '59': {'container': 'mp4',
               'title': '480p',
               'sort': [480, 0],
               'video': {'height': 480, 'encoding': 'h.264'},
               'audio': {'bitrate': 96, 'encoding': 'aac'}},
        '78': {'container': 'mp4',
               'title': '360p',
               'sort': [360, 0],
               'video': {'height': 360, 'encoding': 'h.264'},
               'audio': {'bitrate': 96, 'encoding': 'aac'}},
        # === 3D ===
        '82': {'container': 'mp4',
               '3D': True,
               'title': '3D@360p',
               'sort': [360, 0],
               'video': {'height': 360, 'encoding': 'h.264'},
               'audio': {'bitrate': 96, 'encoding': 'aac'}},
        '83': {'container': 'mp4',
               '3D': True,
               'title': '3D@240p',
               'sort': [240, 0],
               'video': {'height': 240, 'encoding': 'h.264'},
               'audio': {'bitrate': 96, 'encoding': 'aac'}},
        '84': {'container': 'mp4',
               '3D': True,
               'title': '3D@720p',
               'sort': [720, 0],
               'video': {'height': 720, 'encoding': 'h.264'},
               'audio': {'bitrate': 192, 'encoding': 'aac'}},
        '85': {'container': 'mp4',
               '3D': True,
               'title': '3D@1080p',
               'sort': [1080, 0],
               'video': {'height': 1080, 'encoding': 'h.264'},
               'audio': {'bitrate': 192, 'encoding': 'aac'}},
        '100': {'container': 'webm',
                '3D': True,
                'title': '3D@360p',
                'sort': [360, -1],
                'video': {'height': 360, 'encoding': 'vp8'},
                'audio': {'bitrate': 128, 'encoding': 'vorbis'}},
        '101': {'container': 'webm',  # Discontinued
                'discontinued': True,
                '3D': True,
                'title': '3D@360p',
                'sort': [360, -1],
                'video': {'height': 360, 'encoding': 'vp8'},
                'audio': {'bitrate': 192, 'encoding': 'vorbis'}},
        '102': {'container': 'webm',  # Discontinued
                'discontinued': True,
                '3D': True,
                'video': {'height': 720, 'encoding': 'vp8'},
                'audio': {'bitrate': 192, 'encoding': 'vorbis'}},
        # === Live Streams ===
        '91': {'container': 'ts',
               'Live': True,
               'title': 'Live@144p',
               'sort': [144, 0],
               'video': {'height': 144, 'encoding': 'h.264'},
               'audio': {'bitrate': 48, 'encoding': 'aac'}},
        '92': {'container': 'ts',
               'Live': True,
               'title': 'Live@240p',
               'sort': [240, 0],
               'video': {'height': 240, 'encoding': 'h.264'},
               'audio': {'bitrate': 48, 'encoding': 'aac'}},
        '93': {'container': 'ts',
               'Live': True,
               'title': 'Live@360p',
               'sort': [360, 0],
               'video': {'height': 360, 'encoding': 'h.264'},
               'audio': {'bitrate': 128, 'encoding': 'aac'}},
        '94': {'container': 'ts',
               'Live': True,
               'title': 'Live@480p',
               'sort': [480, 0],
               'video': {'height': 480, 'encoding': 'h.264'},
               'audio': {'bitrate': 128, 'encoding': 'aac'}},
        '95': {'container': 'ts',
               'Live': True,
               'title': 'Live@720p',
               'sort': [720, 0],
               'video': {'height': 720, 'encoding': 'h.264'},
               'audio': {'bitrate': 256, 'encoding': 'aac'}},
        '96': {'container': 'ts',
               'Live': True,
               'title': 'Live@1080p',
               'sort': [1080, 0],
               'video': {'height': 1080, 'encoding': 'h.264'},
               'audio': {'bitrate': 256, 'encoding': 'aac'}},
        '120': {'container': 'flv',  # Discontinued
                'discontinued': True,
                'Live': True,
                'title': 'Live@720p',
                'sort': [720, -10],
                'video': {'height': 720, 'encoding': 'h.264'},
                'audio': {'bitrate': 128, 'encoding': 'aac'}},
        '127': {'container': 'ts',
                'Live': True,
                'audio': {'bitrate': 96, 'encoding': 'aac'}},
        '128': {'container': 'ts',
                'Live': True,
                'audio': {'bitrate': 96, 'encoding': 'aac'}},
        '132': {'container': 'ts',
                'Live': True,
                'title': 'Live@240p',
                'sort': [240, 0],
                'video': {'height': 240, 'encoding': 'h.264'},
                'audio': {'bitrate': 48, 'encoding': 'aac'}},
        '151': {'container': 'ts',
                'Live': True,
                'unsupported': True,
                'title': 'Live@72p',
                'sort': [72, 0],
                'video': {'height': 72, 'encoding': 'h.264'},
                'audio': {'bitrate': 24, 'encoding': 'aac'}},
        '300': {'container': 'ts',
                'Live': True,
                'title': 'Live@720p',
                'sort': [720, 0],
                'video': {'height': 720, 'encoding': 'h.264'},
                'audio': {'bitrate': 128, 'encoding': 'aac'}},
        '301': {'container': 'ts',
                'Live': True,
                'title': 'Live@1080p',
                'sort': [1080, 0],
                'video': {'height': 1080, 'encoding': 'h.264'},
                'audio': {'bitrate': 128, 'encoding': 'aac'}},
        # === DASH (video only)
        '133': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 240, 'encoding': 'h.264'}},
        '134': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 360, 'encoding': 'h.264'}},
        '135': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 480, 'encoding': 'h.264'}},
        '136': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 720, 'encoding': 'h.264'}},
        '137': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 1080, 'encoding': 'h.264'}},
        '138': {'container': 'mp4',  # Discontinued
                'discontinued': True,
                'dash/video': True,
                'video': {'height': 2160, 'encoding': 'h.264'}},
        '160': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 144, 'encoding': 'h.264'}},
        '167': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 360, 'encoding': 'vp8'}},
        '168': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 480, 'encoding': 'vp8'}},
        '169': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 720, 'encoding': 'vp8'}},
        '170': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 1080, 'encoding': 'vp8'}},
        '218': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 480, 'encoding': 'vp8'}},
        '219': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 480, 'encoding': 'vp8'}},
        '242': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 240, 'encoding': 'vp9'}},
        '243': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 360, 'encoding': 'vp9'}},
        '244': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 480, 'encoding': 'vp9'}},
        '247': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 720, 'encoding': 'vp9'}},
        '248': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 1080, 'encoding': 'vp9'}},
        '264': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 1440, 'encoding': 'h.264'}},
        '266': {'container': 'mp4',
                'dash/video': True,
                'video': {'height': 2160, 'encoding': 'h.264'}},
        '271': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 1440, 'encoding': 'vp9'}},
        '272': {'container': 'webm',  # was VP9 2160p30
                'dash/video': True,
                'fps': 60,
                'video': {'height': 4320, 'encoding': 'vp9'}},
        '278': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 144, 'encoding': 'vp9'}},
        '298': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'video': {'height': 720, 'encoding': 'h.264'}},
        '299': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'video': {'height': 1080, 'encoding': 'h.264'}},
        '302': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'video': {'height': 720, 'encoding': 'vp9'}},
        '303': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'video': {'height': 1080, 'encoding': 'vp9'}},
        '308': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'video': {'height': 1440, 'encoding': 'vp9'}},
        '313': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 2160, 'encoding': 'vp9'}},
        '315': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'video': {'height': 2160, 'encoding': 'vp9'}},
        '330': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 144, 'encoding': 'vp9.2'}},
        '331': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 240, 'encoding': 'vp9.2'}},
        '332': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 360, 'encoding': 'vp9.2'}},
        '333': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 480, 'encoding': 'vp9.2'}},
        '334': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 720, 'encoding': 'vp9.2'}},
        '335': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 1080, 'encoding': 'vp9.2'}},
        '336': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 1440, 'encoding': 'vp9.2'}},
        '337': {'container': 'webm',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 2160, 'encoding': 'vp9.2'}},
        '394': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 144, 'encoding': 'av1'}},
        '395': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 240, 'encoding': 'av1'}},
        '396': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 360, 'encoding': 'av1'}},
        '397': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 480, 'encoding': 'av1'}},
        '398': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 720, 'encoding': 'av1'}},
        '399': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 1080, 'encoding': 'av1'}},
        '400': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 1440, 'encoding': 'av1'}},
        '401': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 2160, 'encoding': 'av1'}},
        '402': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 4320, 'encoding': 'av1'}},
        '571': {'container': 'mp4',
                'dash/video': True,
                'fps': 30,
                'video': {'height': 4320, 'encoding': 'av1'}},
        '694': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 144, 'encoding': 'av1'}},
        '695': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 240, 'encoding': 'av1'}},
        '696': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 360, 'encoding': 'av1'}},
        '697': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 480, 'encoding': 'av1'}},
        '698': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 720, 'encoding': 'av1'}},
        '699': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 1080, 'encoding': 'av1'}},
        '700': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 1440, 'encoding': 'av1'}},
        '701': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 2160, 'encoding': 'av1'}},
        '702': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 4320, 'encoding': 'av1'}},
        # === Dash (audio only)
        '139': {'container': 'mp4',
                'sort': [48, 0],
                'title': 'he-aac@48',
                'dash/audio': True,
                'audio': {'bitrate': 48, 'encoding': 'aac'}},
        '140': {'container': 'mp4',
                'sort': [129, 0],
                'title': 'aac-lc@128',
                'dash/audio': True,
                'audio': {'bitrate': 128, 'encoding': 'aac'}},
        '141': {'container': 'mp4',
                'sort': [143, 0],
                'title': 'aac-lc@256',
                'dash/audio': True,
                'audio': {'bitrate': 256, 'encoding': 'aac'}},
        '256': {'container': 'mp4',
                'title': 'he-aac@192',
                'dash/audio': True,
                'audio': {'bitrate': 192, 'encoding': 'aac'}},
        '258': {'container': 'mp4',
                'title': 'aac-lc@384',
                'dash/audio': True,
                'audio': {'bitrate': 384, 'encoding': 'aac'}},
        '325': {'container': 'mp4',
                'title': 'dtse@384',
                'dash/audio': True,
                'audio': {'bitrate': 384, 'encoding': 'dtse'}},
        '327': {'container': 'mp4',
                'title': 'aac-lc@256',
                'dash/audio': True,
                'audio': {'bitrate': 256, 'encoding': 'aac'}},
        '328': {'container': 'mp4',
                'title': 'ec-3@384',
                'dash/audio': True,
                'audio': {'bitrate': 384, 'encoding': 'ec-3'}},
        '171': {'container': 'webm',
                'sort': [128, 0],
                'title': 'vorbis@128',
                'dash/audio': True,
                'audio': {'bitrate': 128, 'encoding': 'vorbis'}},
        '172': {'container': 'webm',
                'sort': [142, 0],
                'title': 'vorbis@192',
                'dash/audio': True,
                'audio': {'bitrate': 192, 'encoding': 'vorbis'}},
        '249': {'container': 'webm',
                'sort': [50, 0],
                'title': 'opus@50',
                'dash/audio': True,
                'audio': {'bitrate': 50, 'encoding': 'opus'}},
        '250': {'container': 'webm',
                'sort': [70, 0],
                'title': 'opus@70',
                'dash/audio': True,
                'audio': {'bitrate': 70, 'encoding': 'opus'}},
        '251': {'container': 'webm',
                'sort': [141, 0],
                'title': 'opus@160',
                'dash/audio': True,
                'audio': {'bitrate': 160, 'encoding': 'opus'}},
        '338': {'container': 'webm',
                'sort': [141, 0],
                'title': 'opus@480',
                'dash/audio': True,
                'audio': {'bitrate': 480, 'encoding': 'opus'}},
        '380': {'container': 'mp4',
                'title': 'ac-3@384',
                'dash/audio': True,
                'audio': {'bitrate': 384, 'encoding': 'ac-3'}},
        # === DASH adaptive audio only
        '9997': {'container': 'mpd',
                 'sort': [-1, 0],
                 'title': 'DASH Audio',
                 'dash/audio': True,
                 'audio': {'bitrate': 0, 'encoding': ''}},
        # === Live DASH adaptive
        '9998': {'container': 'mpd',
                 'Live': True,
                 'sort': [1080, 1],
                 'title': 'Live DASH',
                 'dash/audio': True,
                 'dash/video': True,
                 'audio': {'bitrate': 0, 'encoding': ''},
                 'video': {'height': 0, 'encoding': ''}},
        # === DASH adaptive
        '9999': {'container': 'mpd',
                 'sort': [1080, 1],
                 'title': 'DASH',
                 'dash/audio': True,
                 'dash/video': True,
                 'audio': {'bitrate': 0, 'encoding': ''},
                 'video': {'height': 0, 'encoding': ''}}
    }

    CLIENTS = {
        # 4k no VP9 HDR
        # Limited subtitle availability
        'android_testsuite': {
            'id': 30,
            'api_key': 'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',
            'details': {
                'clientName': 'ANDROID_TESTSUITE',
                'clientVersion': '1.9',
                'androidSdkVersion': '29',
                'osName': 'Android',
                'osVersion': '10',
                'platform': 'MOBILE',
            },
            'headers': {
                'User-Agent': 'com.google.android.youtube/{details[clientVersion]} (Linux; U; Android {details[osVersion]}; US) gzip',
                'X-YouTube-Client-Name': '{id}',
                'X-YouTube-Client-Version': '{details[clientVersion]}',
            },
        },
        'android': {
            'id': 3,
            'api_key': 'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',
            'details': {
                'clientName': 'ANDROID',
                'clientVersion': '17.31.35',
                'androidSdkVersion': '29',
                'osName': 'Android',
                'osVersion': '10',
                'platform': 'MOBILE',
            },
            'headers': {
                'User-Agent': 'com.google.android.youtube/{details[clientVersion]} (Linux; U; Android {details[osVersion]}; US) gzip',
                'X-YouTube-Client-Name': '{id}',
                'X-YouTube-Client-Version': '{details[clientVersion]}',
            },
            'disableDash': False,
        },
        # Only for videos that allow embedding
        # Limited to 720p on some videos
        'android_embedded': {
            'id': 55,
            'api_key': 'AIzaSyCjc_pVEDi4qsv5MtC2dMXzpIaDoRFLsxw',
            'details': {
                'clientName': 'ANDROID_EMBEDDED_PLAYER',
                'clientVersion': '17.36.4',
                'clientScreen': 'EMBED',
                'androidSdkVersion': '29',
                'osName': 'Android',
                'osVersion': '10',
                'platform': 'MOBILE',
            },
            'headers': {
                'User-Agent': 'com.google.android.youtube/{details[clientVersion]} (Linux; U; Android {details[osVersion]}; US) gzip',
                'X-YouTube-Client-Name': '{id}',
                'X-YouTube-Client-Version': '{details[clientVersion]}',
            },
        },
        # 4k with HDR
        # Some videos block this client, may also require embedding enabled
        # Limited subtitle availability
        'android_youtube_tv': {
            'id': 29,
            'api_key': 'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',
            'details': {
                'clientName': 'ANDROID_UNPLUGGED',
                'clientVersion': '6.36',
                'androidSdkVersion': '29',
                'osName': 'Android',
                'osVersion': '10',
                'platform': 'MOBILE',
            },
            'headers': {
                'User-Agent': 'com.google.android.apps.youtube.unplugged/{details[clientVersion]} (Linux; U; Android {details[osVersion]}; US) gzip',
                'X-YouTube-Client-Name': '{id}',
                'X-YouTube-Client-Version': '{details[clientVersion]}',
            },
        },
        # Used for misc api requests by default
        # Requires handling of nsig to overcome throttling (TODO)
        'web': {
            'id': 1,
            'api_key': 'AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
            'details': {
                'clientName': 'WEB',
                'clientVersion': '2.20220801.00.00',
            },
            # Headers from the "Galaxy S20 Ultra" from Chrome dev tools device emulation
            'headers': {
                'User-Agent': ('Mozilla/5.0 (Linux; Android 10; SM-G981B)'
                               ' AppleWebKit/537.36 (KHTML, like Gecko)'
                               ' Chrome/80.0.3987.162 Mobile Safari/537.36'),
            },
        },
        '_common': {
            'gl': None,
            'hl': None,
        },
        '_headers': {
            'Origin': 'https://www.youtube.com',
            'Referer': 'https://www.youtube.com/',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
        },
    }

    def __init__(self, context, access_token='', api_key='', language='en-US'):
        settings = context.get_settings()

        self.video_id = None
        self._context = context
        self._data_cache = self._context.get_data_cache()
        self._verify = settings.verify_ssl()
        self._language = settings.get_string('youtube.language', language).replace('-', '_')
        self._language_base = self._language[0:2]
        self._access_token = access_token
        self._api_key = api_key
        self._player_js = None
        self._calculate_n = True
        self._cipher = None

        self._selected_client = None
        client_selection = settings.client_selection()
        # Alternate #1
        # Will play almost all videos with available subtitles at full resolution with HDR
        # Some very small minority of videos won't show available subtitles
        if client_selection == 1:
            self._prioritised_clients = (
                self.CLIENTS['android'],
                self.CLIENTS['android_youtube_tv'],
                self.CLIENTS['android_testsuite'],
                self.CLIENTS['android_embedded'],
            )
        # Alternate #2
        # Will play almost all videos at full resolution with HDR
        # Most videos wont show available subtitles
        # Useful for testing AV1 HDR
        elif client_selection == 2:
            self._prioritised_clients = (
                self.CLIENTS['android_testsuite'],
                self.CLIENTS['android_youtube_tv'],
                self.CLIENTS['android'],
                self.CLIENTS['android_embedded'],
            )
        # Default
        # Will play almost all videos with available subtitles at full resolution with HDR
        # Some very small minority of videos may only play at 720p
        else:
            self._prioritised_clients = (
                self.CLIENTS['android'],
                self.CLIENTS['android_embedded'],
                self.CLIENTS['android_youtube_tv'],
                self.CLIENTS['android_testsuite'],
            )

        self.CLIENTS['_common']['hl'] = self._language
        self.CLIENTS['_common']['gl'] = settings.get_string('youtube.region', 'US')

    @staticmethod
    def generate_cpn():
        # https://github.com/rg3/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1381
        # LICENSE: The Unlicense
        # cpn generation algorithm is reverse engineered from base.js.
        # In fact it works even with dummy cpn.
        cpn_alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        cpn = ''.join((cpn_alphabet[random.randint(0, 256) & 63] for _ in range(0, 16)))
        return cpn

    def load_stream_infos(self, video_id):
        self.video_id = video_id
        return self._method_get_video_info()

    def get_watch_page(self):
        headers = self.CLIENTS['web']['headers'].copy()
        headers.update(self.CLIENTS['_headers'])
        if self._access_token:
            headers['Authorization'] = 'Bearer %s' % self._access_token

        url = 'https://www.youtube.com/watch?v={0}'.format(self.video_id)
        cookies = {'CONSENT': 'YES+cb.20210615-14-p0.en+FX+294'}

        result = requests.get(url, headers=headers, verify=self._verify,
                              cookies=cookies, allow_redirects=True)

        return {'url': result.url, 'html': result.text, 'cookies': result.cookies}

    def get_embed_page(self):
        headers = self.CLIENTS['web']['headers'].copy()
        headers.update(self.CLIENTS['_headers'])
        if self._access_token:
            headers['Authorization'] = 'Bearer %s' % self._access_token

        url = 'https://www.youtube.com/embed/{0}'.format(self.video_id)
        cookies = {'CONSENT': 'YES+cb.20210615-14-p0.en+FX+294'}

        result = requests.get(url, headers=headers, verify=self._verify,
                              cookies=cookies, allow_redirects=True)

        return {'url': result.url, 'html': result.text, 'cookies': result.cookies}

    @staticmethod
    def get_player_client(config):
        return config.get('INNERTUBE_CONTEXT', {}).get('client', {})

    def get_player_key(self, html):
        pattern = 'INNERTUBE_API_KEY":"'
        start_index = html.find(pattern)
        if start_index != -1:
            start_index += len(pattern)
            end_index = html.find('"', start_index)
            self._context.log_debug('Player key found')
            return html[start_index:end_index]
        return None

    @staticmethod
    def get_player_config(html):
        # pattern source is from youtube-dl
        # https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L313
        # LICENSE: The Unlicense
        found = re.search(r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;', html)

        if found:
            config = json.loads(found.group(1))
            return config
        return {}

    @staticmethod
    def get_player_response(html):
        response = {}

        found = re.search(
                r'ytInitialPlayerResponse\s*=\s*(?P<response>{.+?})\s*;\s*(?:var\s+meta|</script|\n)', html
        )
        if found:
            response = json.loads(found.group('response'))

        return response

    def get_player_js(self):
        js_url = None
        cached_url = self._data_cache.get_item(DataCache.ONE_HOUR * 4, 'player_js_url').get('url', '')
        if cached_url not in ['', 'http://', 'https://']:
            js_url = cached_url

        if not js_url:
            html = self.get_watch_page()['html']
            player_config = self.get_player_config(html)
            if not player_config:
                return ''

            if 'PLAYER_JS_URL' in player_config:
                js_url = player_config['PLAYER_JS_URL']
            elif 'WEB_PLAYER_CONTEXT_CONFIGS' in player_config:
                for configs in player_config['WEB_PLAYER_CONTEXT_CONFIGS'].values():
                    if 'jsUrl' in configs:
                        js_url = configs['jsUrl']
                        break

        if not js_url:
            return ''

        js_url = self._normalize_url(js_url)
        self._data_cache.set('player_js_url', json.dumps({'url': js_url}))
        cache_key = quote(js_url)
        cached_js = self._data_cache.get_item(DataCache.ONE_HOUR * 4, cache_key).get('js')
        if cached_js:
            return cached_js

        headers = self.CLIENTS['web']['headers'].copy()
        headers.update(self.CLIENTS['_headers'])
        result = requests.get(js_url, headers=headers, verify=self._verify, allow_redirects=True)
        javascript = result.text

        self._data_cache.set(cache_key, json.dumps({'js': javascript}))
        return javascript

    @staticmethod
    def make_curl_headers(headers, cookies=None):
        output = ''
        if cookies:
            output += 'Cookie={all_cookies}'.format(
                all_cookies=quote(
                    '; '.join('{0}={1}'.format(c.name, c.value) for c in cookies)
                )
            )
            output += '&'
        # Headers to be used in function 'to_play_item' of 'xbmc_items.py'.
        output += '&'.join('{0}={1}'.format(key, quote(headers[key]))
                           for key in headers)
        return output

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

    def _load_manifest(self, url, meta_info=None, playback_stats=None):
        headers = self.CLIENTS['web']['headers'].copy()
        headers.update(self.CLIENTS['_headers'])
        headers['Referer'] = 'https://www.youtube.com/watch?v={0}'.format(self.video_id)

        curl_headers = self.make_curl_headers(headers, cookies=None)

        if playback_stats is None:
            playback_stats = {}

        try:
            result = requests.get(url, headers=headers, verify=self._verify, allow_redirects=True)
            result.raise_for_status()
        except requests.exceptions.RequestException:
            # Failed to get the M3U8 playlist file. Add a log debug in this case?
            return ()

        _meta_info = {'video': {},
                      'channel': {},
                      'images': {},
                      'subtitles': []}
        meta_info = meta_info if meta_info else _meta_info
        streams = []
        # The playlist might include a #EXT-X-MEDIA entry, but it's usually for
        # a small default stream with itag 133 (240p) and can be ignored.
        # Capture the URL of a .m3u8 playlist and the itag value from that URL.
        re_playlist_data = re.compile(r'#EXT-X-STREAM-INF[^#]+(?P<url>http[^\s]+/itag/(?P<itag>\d+)[^\s]+)')
        for match in re_playlist_data.finditer(result.text):
            playlist_url = match.group('url')
            itag = match.group('itag')

            yt_format = self.FORMAT.get(itag, None)
            if not yt_format:
                self._context.log_debug('unknown yt_format for itag "%s"' % itag)
                continue

            video_stream = {'url': playlist_url,
                            'meta': meta_info,
                            'headers': curl_headers,
                            'playback_stats': playback_stats
                            }
            video_stream.update(yt_format)
            streams.append(video_stream)
        return streams

    def _process_signature_cipher(self, stream_map):
        signature_cipher = parse_qs(stream_map['signatureCipher'])
        url = signature_cipher.get('url', [None])[0]
        encrypted_signature = signature_cipher.get('s', [None])[0]
        query_var = signature_cipher.get('sp', ['signature'])[0]

        if not url or not encrypted_signature:
            return None

        signature = self._data_cache.get_item(DataCache.ONE_HOUR * 4, encrypted_signature).get('sig')
        if not signature:
            try:
                signature = self._cipher.get_signature(encrypted_signature)
            except Exception as error:
                self._context.log_debug('{0}: {1}\n{2}'.format(error, encrypted_signature, traceback.format_exc()))
                self._context.log_error('Stream URL unable to be extracted from signatureCipher')
                return None
            self._data_cache.set(encrypted_signature, json.dumps({'sig': signature}))

        if signature:
            url = '{0}&{1}={2}'.format(url, query_var, signature)
            return url
        return None

    def _process_url_params(self, url):
        if not url:
            return url

        parts = urlsplit(url)
        query = parse_qs(parts.query)
        new_query = {}
        update_url = False

        if 'n' in query and query.get('ratebypass', [None])[0] != 'yes' and self._calculate_n:
            self._player_js = self._player_js or self.get_player_js()
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

        if new_query:
            query.update(new_query)
        elif not update_url:
            return url

        url = urlunsplit((parts.scheme,
                          parts.netloc,
                          parts.path,
                          urlencode(query, doseq=True),
                          parts.fragment))
        return url

    @staticmethod
    def _get_error_details(playability_status, details=None):
        if ('errorScreen' not in playability_status
                or 'playerErrorMessageRenderer' not in playability_status['errorScreen']):
            return None

        status_renderer = playability_status['errorScreen']['playerErrorMessageRenderer']

        if details:
            result = status_renderer
            for key in details:
                if isinstance(result, dict) and key not in result:
                    return None
                if isinstance(result, list) and (not isinstance(key, int) or len(result) <= key):
                    return None
                result = result[key]
            return result

        status_reason = status_renderer.get('reason', {})
        status_reason_runs = status_reason.get('runs', [{}])

        status_reason_texts = [
            text['text']
            for text in status_reason_runs
            if 'text' in text and text['text']
        ]
        if status_reason_texts:
            return ''.join(status_reason_texts)
        if 'simpleText' in status_reason:
            return status_reason['simpleText']
        return None

    def _method_get_video_info(self):
        if self._access_token:
            auth_header = 'Bearer %s' % self._access_token
        else:
            auth_header = None

        video_info_url = 'https://www.youtube.com/youtubei/v1/player'

        payload = {
            'contentCheckOk': True,
            'context': {},
            'params': '8AEB',
            'playbackContext': {
                'contentPlaybackContext': {
                    'html5Preference': 'HTML5_PREF_WANTS',
                },
            },
            'racyCheckOk': True,
            'thirdParty': {
                'embedUrl': 'https://www.youtube.com/',
            },
            'user': {
                'lockedSafetyMode': False
            },
            'videoId': self.video_id,
        }

        player_response = {}
        for _ in range(2):
            for client in self._prioritised_clients:
                client['details'].update(self.CLIENTS['_common'])
                payload['context']['client'] = client['details']

                headers = (client.get('headers') or self.CLIENTS['web']['headers']).copy()
                for name, value in headers.items():
                    headers[name] = value.format(**client)
                if auth_header:
                    headers['Authorization'] = auth_header
                    params = None
                else:
                    params = {'key': client['api_key'] or self._api_key}
                headers.update(self.CLIENTS['_headers'])

                try:
                    result = requests.post(video_info_url, params=params, json=payload,
                                      headers=headers, verify=self._verify, cookies=None,
                                      allow_redirects=True)
                    result.raise_for_status()
                except requests.exceptions.RequestException as error:
                    self._context.log_debug(error.response.text)
                    error_message = 'Failed to get player response for video_id "{0}"'.format(self.video_id)
                    self._context.log_error(error_message + '\n' + traceback.format_exc())
                    raise YouTubeException(error_message) from error

                player_response = result.json()
                playability_status = player_response.get('playabilityStatus', {})
                status = playability_status.get('status', 'OK')

                if status in ('AGE_CHECK_REQUIRED', 'UNPLAYABLE', 'CONTENT_CHECK_REQUIRED',
                              'LOGIN_REQUIRED', 'AGE_VERIFICATION_REQUIRED', 'ERROR'):
                    if (status == 'UNPLAYABLE' and
                            playability_status.get('reason', '') == 'The uploader has not made this video available in your country'):
                        break
                    if status != 'ERROR':
                        continue
                    # This is used to check if a "The following content is not available on this app."
                    # error occurs. Text will vary depending on Accept-Language and client hl so
                    # Youtube support url is checked instead
                    url = self._get_error_details(playability_status,
                                                  details=['learnMore', 'runs', 0,
                                                           'navigationEndpoint',
                                                           'urlEndpoint', 'url'])
                    if url and url.startswith('//support.google.com/youtube/answer/12318250'):
                        continue
                break
            # Only attempt to remove Authorization header if clients iterable was exhausted
            # i.e. request attempted using all clients
            else:
                if auth_header:
                    auth_header = None
                    continue
            # Otherwise skip retrying clients without Authorization header
            break
        self._context.log_debug('Requested video info with client: {0} (logged {1})'.format(
            client['details']['clientName'], 'in' if auth_header else 'out'))
        self._selected_client = client

        if 'Authorization' in headers:
            del headers['Authorization']
        # Make a set of URL-quoted headers to be sent to Kodi when requesting
        # the stream during playback. The YT player doesn't seem to use any
        # cookies when doing that, so for now cookies are ignored.
        # curl_headers = self.make_curl_headers(headers, cookies)
        curl_headers = self.make_curl_headers(headers, cookies=None)

        video_details = player_response.get('videoDetails', {})
        is_live_content = video_details.get('isLiveContent') is True
        streaming_data = player_response.get('streamingData', {})

        live_url = streaming_data.get('hlsManifestUrl', '')
        is_live = is_live_content and live_url

        meta_info = {'video': {},
                     'channel': {},
                     'images': {},
                     'subtitles': []}

        meta_info['video']['id'] = video_details.get('videoId', self.video_id)

        meta_info['video']['title'] = video_details.get('title', '')
        meta_info['channel']['author'] = video_details.get('author', '')

        meta_info['video']['title'] = meta_info['video']['title'].encode('raw_unicode_escape')
        meta_info['channel']['author'] = meta_info['channel']['author'].encode('raw_unicode_escape')

        meta_info['video']['title'] = meta_info['video']['title'].decode('raw_unicode_escape')
        meta_info['channel']['author'] = meta_info['channel']['author'].decode('raw_unicode_escape')

        meta_info['video']['title'] = unescape(meta_info['video']['title'])
        meta_info['channel']['author'] = unescape(meta_info['channel']['author'])

        meta_info['channel']['id'] = video_details.get('channelId', '')
        image_data_list = [
            {'from': 'iurlhq', 'to': 'high', 'image': 'hqdefault.jpg'},
            {'from': 'iurlmq', 'to': 'medium', 'image': 'mqdefault.jpg'},
            {'from': 'iurlsd', 'to': 'standard', 'image': 'sddefault.jpg'},
            {'from': 'thumbnail_url', 'to': 'default', 'image': 'default.jpg'}]
        for image_data in image_data_list:
            image_url = 'https://i.ytimg.com/vi/{0}/{1}'.format(self.video_id, image_data['image'])
            if image_url:
                if is_live:
                    image_url = image_url.replace('.jpg', '_live.jpg')
                meta_info['images'][image_data['to']] = image_url

        microformat = player_response.get('microformat', {}).get('playerMicroformatRenderer', {})
        meta_info['video']['status'] = {
            'unlisted': microformat.get('isUnlisted', False),
            'private': video_details.get('isPrivate', False),
            'crawlable': video_details.get('isCrawlable', False),
            'family_safe': microformat.get('isFamilySafe', False),
            'live': is_live,
        }

        if (playability_status.get('status', 'ok').lower() != 'ok'
                and not ((playability_status.get('desktopLegacyAgeGateReason', 0) == 1)
                and not self._context.get_settings().age_gate())):
            reason = None
            if playability_status.get('status') == 'LIVE_STREAM_OFFLINE':
                if playability_status.get('reason'):
                    reason = playability_status.get('reason')
                else:
                    live_streamability = playability_status.get('liveStreamability', {})
                    live_streamability_renderer = live_streamability.get('liveStreamabilityRenderer', {})
                    offline_slate = live_streamability_renderer.get('offlineSlate', {})
                    live_stream_offline_slate_renderer = offline_slate.get('liveStreamOfflineSlateRenderer', {})
                    renderer_main_text = live_stream_offline_slate_renderer.get('mainText', {})
                    main_text_runs = renderer_main_text.get('runs', [{}])
                    reason_text = []
                    for text in main_text_runs:
                        reason_text.append(text.get('text', ''))
                    if reason_text:
                        reason = ''.join(reason_text)
            else:
                reason = self._get_error_details(playability_status) or playability_status.get('reason')

            if not reason:
                reason = 'UNKNOWN'

            raise YouTubeException(reason)

        captions = player_response.get('captions')
        if captions:
            headers = self.CLIENTS['web']['headers'].copy()
            headers.update(self.CLIENTS['_headers'])
            meta_info['subtitles'] = Subtitles(self._context, headers,
                                               self.video_id, captions).get_subtitles()
        else:
            meta_info['subtitles'] = []

        playback_stats = {
            'playback_url': '',
            'watchtime_url': ''
        }

        playback_tracking = player_response.get('playbackTracking', {})
        playback_url = playback_tracking.get('videostatsPlaybackUrl', {}).get('baseUrl', '')
        watchtime_url = playback_tracking.get('videostatsWatchtimeUrl', {}).get('baseUrl', '')

        if playback_url and playback_url.startswith('http'):
            playback_stats['playback_url'] = ''.join([
                playback_url,
                '&ver=2&fs=0&volume=100&muted=0',
                '&cpn={cpn}'.format(cpn=self.generate_cpn())
            ])

        if watchtime_url and watchtime_url.startswith('http'):
            playback_stats['watchtime_url'] = ''.join([
                watchtime_url,
                '&ver=2&fs=0&volume=100&muted=0',
                '&cpn={cpn}'.format(cpn=self.generate_cpn()),
                '&st={st}&et={et}&state={state}'
            ])

        stream_list = []

        if live_url:
            stream_list.extend(self._load_manifest(live_url,
                                                   meta_info=meta_info,
                                                   playback_stats=playback_stats))

        httpd_is_live = (self._context.get_settings().use_dash_videos() and
                         is_httpd_live(port=self._context.get_settings().httpd_port()))

        s_info = {}
        adaptive_fmts = streaming_data.get('adaptiveFormats', [])
        std_fmts = streaming_data.get('formats', [])
        mpd_url = streaming_data.get('dashManifestUrl', '')

        license_info = {'url': None, 'proxy': None, 'token': None}
        pa_li_info = streaming_data.get('licenseInfos', [])
        if pa_li_info and (pa_li_info != ['']) and not httpd_is_live:
            raise YouTubeException('Proxy is not running')
        for li_info in pa_li_info:
            if li_info.get('drmFamily') == 'WIDEVINE':
                license_info['url'] = li_info.get('url', None)
                if license_info['url']:
                    self._context.log_debug('Found widevine license url: |%s|' % license_info['url'])
                    li_ipaddress = self._context.get_settings().httpd_listen()
                    if li_ipaddress == '0.0.0.0':
                        li_ipaddress = '127.0.0.1'
                    proxy_addr = \
                        ['http://{ipaddress}:{port}/widevine'.format(
                            ipaddress=li_ipaddress,
                            port=self._context.get_settings().httpd_port()
                        ), '||R{SSM}|']
                    license_info['proxy'] = ''.join(proxy_addr)
                    license_info['token'] = self._access_token
                    break

        if (any((True for fmt in adaptive_fmts if fmt and 'url' not in fmt and 'signatureCipher' in fmt))
                or any((True for fmt in std_fmts if fmt and 'url' not in fmt and 'signatureCipher' in fmt))):
            self._context.log_debug('signatureCipher detected')
            self._player_js = self.get_player_js()
            self._cipher = Cipher(self._context, javascript=self._player_js)

        if not is_live and httpd_is_live and adaptive_fmts and not client.get('disableDash'):
            mpd_url, s_info = self.generate_mpd(adaptive_fmts,
                                                video_details.get('lengthSeconds', '0'),
                                                license_info.get('url'))

        if mpd_url:
            video_stream = {
                'url': mpd_url,
                'meta': meta_info,
                'headers': curl_headers,
                'license_info': license_info,
                'playback_stats': playback_stats
            }

            if is_live:
                video_stream['url'] = '&'.join([video_stream['url'], 'start_seq=$START_NUMBER$'])
                video_stream.update(self.FORMAT.get('9998'))
            elif not s_info:
                video_stream.update(self.FORMAT.get('9999'))
            else:
                video_info = s_info.get('video')
                if video_info:
                    codec = video_info['codec']
                    bitrate = video_info['bitrate']
                    height = video_info['height']

                    if codec and bitrate:
                        stream_details = self.FORMAT.get('9999').copy()
                        stream_details['video']['height'] = height
                        stream_details['video']['encoding'] = codec
                        stream_details['title'] = video_info['label'] or '{0}p{1}'.format(height, video_info['fps'])
                    else:
                        stream_details = self.FORMAT.get('9999').copy()
                else:
                    stream_details = self.FORMAT.get('9999').copy()

                audio_info = s_info.get('audio')
                if audio_info:
                    codec = audio_info.get('codec')
                    bitrate = audio_info.get('bitrate', 0) // 1000

                    if codec and bitrate:
                        stream_details['audio']['encoding'] = codec
                        stream_details['audio']['bitrate'] = bitrate
                    if not video_info:
                        stream_details['title'] = '{0}@{1}'.format(codec, bitrate)
                    if audio_info['lang'] not in {'', 'und'}:
                        stream_details['title'] += ' Multi-language'

                video_stream.update(stream_details)
            stream_list.append(video_stream)

        def parse_to_stream_list(streams):
            for stream_map in streams:
                url = stream_map.get('url')
                conn = stream_map.get('conn')

                if not url and conn:
                    url = '%s?%s' % (conn, unquote(stream_map['stream']))
                elif not url and self._cipher and 'signatureCipher' in stream_map:
                    url = self._process_signature_cipher(stream_map)

                if not url:
                    continue
                url = self._process_url_params(url)

                itag = str(stream_map['itag'])
                stream_map['itag'] = itag
                yt_format = self.FORMAT.get(itag)
                if not yt_format:
                    self._context.log_debug('unknown yt_format for itag "%s"' % itag)
                    continue
                if (yt_format.get('discontinued') or yt_format.get('unsupported')
                        or (yt_format.get('dash/video') and not yt_format.get('dash/audio'))):
                    continue

                stream = {'url': url,
                          'meta': meta_info,
                          'headers': curl_headers,
                          'playback_stats': playback_stats}
                stream.update(yt_format)
                if 'audioTrack' in stream_map:
                    stream['title'] = '{0} {1}'.format(stream['title'], stream_map['audioTrack']['displayName'])
                stream_list.append(stream)

        # extract streams from map
        if std_fmts:
            parse_to_stream_list(std_fmts)

        if adaptive_fmts:
            parse_to_stream_list(adaptive_fmts)

        # last fallback
        if not stream_list:
            raise YouTubeException('No streams found')

        return stream_list

    def generate_mpd(self, adaptive_fmts, duration, license_url):
        basepath = 'special://temp/plugin.video.youtube/'
        if not make_dirs(basepath):
            self._context.log_debug('Failed to create directories: %s' % basepath)
            return None

        ia_capabilities = self._context.inputstream_adaptive_capabilities()
        mpd_quality = self._context.get_settings().get_mpd_quality()
        quality_type = isinstance(mpd_quality, str) and mpd_quality or ''
        quality_height = isinstance(mpd_quality, int) and mpd_quality or 0
        hdr = self._context.get_settings().include_hdr() and {'vp9.2', 'av1'} & ia_capabilities
        limit_30fps = self._context.get_settings().mpd_30fps_limit()

        ipaddress = self._context.get_settings().httpd_listen()
        if ipaddress == '0.0.0.0':
            ipaddress = '127.0.0.1'

        fps_scale_map = {
            24: 1001,
            30: 1001,
            60: 1001
        }

        data = {}
        preferred_audio = {
            'id': '',
            'language_code': None,
            'audio_type': 0,
        }
        for stream_map in adaptive_fmts:
            mime_type = stream_map.get('mimeType')
            if not mime_type:
                continue

            itag = str(stream_map.get('itag', ''))
            if not itag:
                continue

            index_range = stream_map.get('indexRange')
            if not index_range:
                continue

            init_range = stream_map.get('initRange')
            if not init_range:
                continue

            url = stream_map.get('url')
            if not url and self._cipher and 'signatureCipher' in stream_map:
                url = self._process_signature_cipher(stream_map)
            if not url:
                continue

            mime_type, codecs = unquote(mime_type).split('; ')
            codec = re.match(r'codecs="([a-z0-9]+)', codecs)
            if codec:
                codec = codec.group(1)
            media_type, container = mime_type.split('/')
            if ((quality_type and container != quality_type)
                    or (mime_type == 'video/webm' and not {'vp9', 'vp9.2'} & ia_capabilities)
                    or (mime_type == 'audio/webm' and not {'vorbis', 'opus'} & ia_capabilities)
                    or (codec in {'av01', 'av1'} and 'av1' not in ia_capabilities)
                    or (codec.startswith('dts') and 'dts' not in ia_capabilities)):
                continue

            if 'audioTrack' in stream_map:
                audio_track = stream_map['audioTrack']
                language = audio_track.get('id', '')
                if '.' in language:
                    language_code, audio_type = language.split('.')
                    audio_type = int(audio_type)
                else:
                    language_code = language or 'und'
                    audio_type = 4
                label = audio_track.get('displayName', '')
                if audio_type == 4 or audio_track.get('audioIsDefault'):
                    audio_role = 'main'
                elif audio_type == 3:
                    audio_role = 'dub'
                elif audio_type == 2:
                    audio_role = 'description'
                # Unsure of what other audio types are actually available
                # Role set to "alternate" as default fallback
                else:
                    audio_role = 'alternate'
                height = None
                width = None
                key = '{0}_{1}'.format(mime_type, language)
                if (language_code == self._language_base and (
                        not preferred_audio['id']
                        or audio_role == 'main'
                        or audio_type > preferred_audio['audio_type']
                    )):
                    preferred_audio = {
                        'id': '_'+language,
                        'language_code': language_code,
                        'audio_type': audio_type,
                    }
            elif media_type == 'audio':
                language_code = 'und'
                label = stream_map.get('audioQuality', '')
                audio_role = 'main'
                height = None
                width = None
                key = mime_type
            else:
                # Could use "zxx" language code for Non-Linguistic, Not Applicable
                # but that is too verbose
                language_code = ''
                label = stream_map.get('qualityLabel', '')
                audio_role = None
                height = stream_map.get('height')
                width = stream_map.get('width')
                key = mime_type

            # map frame rates to a more common representation to lessen the chance of double refresh changes
            # sometimes 30 fps is 30 fps, more commonly it is 29.97 fps (same for all mapped frame rates)
            fps = stream_map.get('fps', 0)
            if fps:
                frame_rate = '{0}/{1}'.format(fps * 1000, fps_scale_map.get(fps, 1000))
            else:
                frame_rate = None

            if ((not hdr and 'HDR' in label) or (limit_30fps and fps > 30)
                    or (height and 0 < quality_height < height)):
                continue

            if key not in data:
                data[key] = {}

            url = unquote(url)
            url = self._process_url_params(url)
            url = url.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

            data[key][itag] = {
                'mimeType': mime_type,
                'baseUrl': url,
                'mediaType': media_type,
                'container': container,
                'codecs': codecs,
                'codec': codec,
                'id': itag,
                'width': width,
                'height': height,
                'label': label,
                'bitrate': stream_map.get('bitrate', 0),
                'fps': fps,
                'frameRate': frame_rate,
                'indexRange': '{start}-{end}'.format(**index_range),
                'initRange': '{start}-{end}'.format(**init_range),
                'lang': language_code,
                'audioRole': audio_role,
                'sampleRate': int(stream_map.get('audioSampleRate', '0'), 10),
                'channels': stream_map.get('audioChannels'),
            }

        if 'video/mp4' not in data and 'video/webm' not in data:
            self._context.log_debug('Generate MPD: No video mime-types found')
            return None, None

        def _stream_sort(stream):
            if not stream:
                return (-1, )
            return (
                stream['height'],
                stream['fps'],
                hdr and ('HDR' in stream['label']),
                # Prefer lower bitrate for video streams
                # Used to preference more advanced codecs
                -stream['bitrate'],
            ) if stream['mediaType'] == 'video' else (
                stream['channels'],
                stream['sampleRate'],
                stream['bitrate'],
            )

        data = {
            key: sorted(streams.values(), reverse=True, key=_stream_sort)
            for key, streams in data.items()
        }

        stream_info = {}
        if 'video/mp4' not in data:
            stream_info['video'] = data['video/webm'][0]
        elif 'video/webm' not in data:
            stream_info['video'] = data['video/mp4'][0]
        elif _stream_sort(data['video/mp4'][0]) > _stream_sort(data['video/webm'][0]):
            stream_info['video'] = data['video/mp4'][0]
        else:
            stream_info['video'] = data['video/webm'][0]

        mp4_audio = data.get('audio/mp4'+preferred_audio['id'], [None])[0]
        webm_audio = data.get('audio/webm'+preferred_audio['id'], [None])[0]
        if _stream_sort(mp4_audio) > _stream_sort(webm_audio):
            stream_info['audio'] = mp4_audio
        else:
            stream_info['audio'] = webm_audio

        out_list = [
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<MPD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="urn:mpeg:dash:schema:mpd:2011" xmlns:xlink="http://www.w3.org/1999/xlink"'
                ' xsi:schemaLocation="urn:mpeg:dash:schema:mpd:2011 http://standards.iso.org/ittf/PubliclyAvailableStandards/MPEG-DASH_schema_files/DASH-MPD.xsd"'
                ' minBufferTime="PT1.5S" mediaPresentationDuration="PT', duration, 'S" type="static" profiles="urn:mpeg:dash:profile:isoff-main:2011">\n'
            '\t<Period>\n'
        ]

        set_id = 0
        for streams in data.values():
            default = False
            original = False
            impaired = False
            label = ''
            main_stream = streams[0]
            media_type = main_stream['mediaType']
            if media_type == 'video':
                if stream_info[media_type] == main_stream:
                    default = True
                    role = 'main'
                else:
                    role = 'alternate'
                original = ''
            elif media_type == 'audio':
                label = main_stream['label']
                role = main_stream['audioRole']
                if role == 'main':
                    original = True
                elif role == 'description':
                    impaired = True
                if stream_info[media_type] == main_stream:
                    default = True
                # Use main audio stream with same container format as video stream
                # as fallback selection for default audio stream
                elif (not stream_info[media_type] and original
                        and main_stream['container'] == stream_info['video']['container']):
                    default = True
                    stream_info[media_type] = main_stream

            out_list.extend((
                '\t\t<AdaptationSet subsegmentAlignment="true" subsegmentStartsWithSAP="1" bitstreamSwitching="true"'
                    ' id="', str(set_id), '"'
                    ' mimeType="', main_stream['mimeType'], '"'
                    ' lang="', main_stream['lang'], '"'
                    # name attribute is ISA specific and does not exist in the MPD spec
                    # Should be a child Label element instead
                    ' name="', label, '"'
                    # original, default and impaired are ISA specific attributes
                    ' original="', str(original).lower(), '"'
                    ' default="', str(default).lower(), '"'
                    ' impaired="', str(impaired).lower(), '">\n'
                # AdaptationSet Label element not currently used by ISA
                '\t\t\t<Label>', label, '</Label>\n'
                '\t\t\t<Role schemeIdUri="urn:mpeg:dash:role:2011" value="', role, '"/>\n'
            ))

            if license_url:
                license_url = license_url.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
                out_list.extend((
                    '\t\t\t<ContentProtection schemeIdUri="http://youtube.com/drm/2012/10/10">\n'
                    '\t\t\t\t<yt:SystemURL type="widevine">', license_url, '</yt:SystemURL>\n'
                    '\t\t\t</ContentProtection>\n'
                ))

            num_streams = len(streams)
            if media_type == 'audio':
                out_list.extend(((
                    '\t\t\t<Representation id="{id}" {codecs}'
                        ' bandwidth="{bitrate}" sampleRate="{sampleRate}" numChannels="{channels}"'
                        # quality and priority attributes not currently used by ISA
                        ' qualityRanking="{quality}" selectionPriority="{priority}">\n'
                    '\t\t\t\t<AudioChannelConfiguration schemeIdUri="urn:mpeg:dash:23003:3:audio_channel_configuration:2011" value="{channels}"/>\n'
                    # Representation Label element not currently used by ISA
                    '\t\t\t\t<Label>{label}</Label>\n'
                    '\t\t\t\t<BaseURL>{baseUrl}</BaseURL>\n'
                    '\t\t\t\t<SegmentBase indexRange="{indexRange}">\n'
                    '\t\t\t\t\t<Initialization range="{initRange}"/>\n'
                    '\t\t\t\t</SegmentBase>\n'
                    '\t\t\t</Representation>\n'
                ).format(quality=(idx + 1), priority=(num_streams - idx), **stream) for idx, stream in enumerate(streams)))
            elif media_type == 'video':
                out_list.extend(((
                    '\t\t\t<Representation id="{id}" {codecs} startWithSAP="1"'
                        ' bandwidth="{bitrate}" width="{width}" height="{height}" frameRate="{frameRate}"'
                        # quality and priority attributes not currently used by ISA
                        ' qualityRanking="{quality}" selectionPriority="{priority}">\n'
                    # Representation Label element not currently used by ISA
                    '\t\t\t\t<Label>{label}</Label>\n'
                    '\t\t\t\t<BaseURL>{baseUrl}</BaseURL>\n'
                    '\t\t\t\t<SegmentBase indexRange="{indexRange}">\n'
                    '\t\t\t\t\t<Initialization range="{initRange}"/>\n'
                    '\t\t\t\t</SegmentBase>\n'
                    '\t\t\t</Representation>\n'
                ).format(quality=(idx + 1), priority=(num_streams - idx), **stream) for idx, stream in enumerate(streams)))

            out_list.append('\t\t</AdaptationSet>\n')
            set_id += 1

        out_list.append('\t</Period>\n'
                        '</MPD>\n')
        out = ''.join(out_list)

        filepath = '{0}{1}.mpd'.format(basepath, self.video_id)
        success = None
        with xbmcvfs.File(filepath, 'w') as mpd_file:
            success = mpd_file.write(str(out))
        if not success:
            return None, None
        return 'http://{0}:{1}/{2}.mpd'.format(
            ipaddress,
            self._context.get_settings().httpd_port(),
            self.video_id
        ), stream_info
