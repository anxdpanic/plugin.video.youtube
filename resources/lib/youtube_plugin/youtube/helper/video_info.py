# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from six.moves import range
from six import string_types, PY2
from six.moves import urllib

import copy
import re
import json
import random

import requests
from ...kodion.utils import is_httpd_live, make_dirs
from ..youtube_exceptions import YouTubeException
from .signature.cipher import Cipher
from .subtitles import Subtitles

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
        '272': {'container': 'webm',
                'dash/video': True,
                'video': {'height': 2160, 'encoding': 'vp9'}},
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
        '400': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 1440, 'encoding': 'av1'}},
        '401': {'container': 'mp4',
                'dash/video': True,
                'fps': 60,
                'hdr': True,
                'video': {'height': 2160, 'encoding': 'av1'}},
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
        # === Dash (audio only)
        '139': {'container': 'mp4',
                'sort': [48, 0],
                'title': 'aac@48',
                'dash/audio': True,
                'audio': {'bitrate': 48, 'encoding': 'aac'}},
        '140': {'container': 'mp4',
                'sort': [129, 0],
                'title': 'aac@128',
                'dash/audio': True,
                'audio': {'bitrate': 128, 'encoding': 'aac'}},
        '141': {'container': 'mp4',
                'sort': [143, 0],
                'title': 'aac@256',
                'dash/audio': True,
                'audio': {'bitrate': 256, 'encoding': 'aac'}},
        '256': {'container': 'mp4',
                'title': 'aac/itag 256',
                'dash/audio': True,
                'unsupported': True,
                'audio': {'bitrate': 0, 'encoding': 'aac'}},
        '258': {'container': 'mp4',
                'title': 'aac/itag 258',
                'dash/audio': True,
                'unsupported': True,
                'audio': {'bitrate': 0, 'encoding': 'aac'}},
        '325': {'container': 'mp4',
                'title': 'dtse/itag 325',
                'dash/audio': True,
                'unsupported': True,
                'audio': {'bitrate': 0, 'encoding': 'aac'}},
        '328': {'container': 'mp4',
                'title': 'ec-3/itag 328',
                'dash/audio': True,
                'unsupported': True,
                'audio': {'bitrate': 0, 'encoding': 'aac'}},
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

    def __init__(self, context, access_token='', language='en-US'):
        self._context = context
        self._verify = context.get_settings().verify_ssl()
        self._language = language.replace('-', '_')
        self.language = context.get_settings().get_string('youtube.language', 'en_US').replace('-', '_')
        self.region = context.get_settings().get_string('youtube.region', 'US')
        self._access_token = access_token

    @staticmethod
    def generate_cpn():
        # https://github.com/rg3/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1381
        # LICENSE: The Unlicense
        # cpn generation algorithm is reverse engineered from base.js.
        # In fact it works even with dummy cpn.
        cpn_alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
        cpn = ''.join((cpn_alphabet[random.randint(0, 256) & 63] for _ in range(0, 16)))
        return cpn

    def load_stream_infos(self, video_id=None, player_config=None, cookies=None):
        return self._method_get_video_info(video_id, player_config, cookies)

    def get_watch_page(self, video_id):
        headers = {'Host': 'www.youtube.com',
                   'Connection': 'keep-alive',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

        params = {'v': video_id,
                  'hl': self.language,
                  'gl': self.region}

        if self._access_token:
            params['access_token'] = self._access_token

        url = 'https://www.youtube.com/watch'

        result = requests.get(url, params=params, headers=headers, verify=self._verify, allow_redirects=True)
        return {'html': result.text, 'cookies': result.cookies}

    def get_embed_page(self, video_id):
        headers = {'Host': 'www.youtube.com',
                   'Connection': 'keep-alive',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

        params = {'hl': self.language,
                  'gl': self.region}

        if self._access_token:
            params['access_token'] = self._access_token

        url = 'https://www.youtube.com/embed/{video_id}'.format(video_id=video_id)

        result = requests.get(url, params=params, headers=headers, verify=self._verify, allow_redirects=True)
        return {'html': result.text, 'cookies': result.cookies}

    @staticmethod
    def get_player_config(html):
        _player_config = '{}'

        lead = 'ytplayer.config = '
        tail = ';ytplayer.load'
        pos = html.find(lead)
        if pos >= 0:
            html2 = html[pos + len(lead):]
            pos = html2.find(tail)
            if pos >= 0:
                _player_config = html2[:pos]

        blank_config = re.search(r'var blankSwfConfig\s*=\s*(?P<player_config>{.+?});\s*var fillerData', html)
        if not blank_config:
            player_config = dict()
        else:
            try:
                player_config = json.loads(blank_config.group('player_config'))
            except TypeError:
                player_config = dict()

        try:
            player_config.update(json.loads(_player_config))
        except TypeError:
            pass

        if 'args' not in player_config:
            player_config['args'] = dict()

        player_response = player_config['args'].get('player_response', dict())
        if isinstance(player_response, string_types):
            try:
                player_response = json.loads(player_response)
            except TypeError:
                player_response = dict()

        player_config['args']['player_response'] = dict()

        result = re.search(r'window\["ytInitialPlayerResponse"\]\s*=\s*\(\s*(?P<player_response>{.+?})\s*\);', html)
        if result:
            try:
                player_config['args']['player_response'] = json.loads(result.group('player_response'))
            except TypeError:
                pass

        player_config['args']['player_response'].update(player_response)

        return player_config

    def get_player_js(self, video_id, js=''):
        if not js:
            page_result = self.get_embed_page(video_id)
            html = page_result.get('html')

            if not html:
                return ''

            _player_config = '{}'
            player_config = dict()

            lead = 'yt.setConfig({\'PLAYER_CONFIG\': '
            tail = ',\'EXPERIMENT_FLAGS\':'
            if html.find(tail) == -1:
                tail = '});'
            pos = html.find(lead)
            if pos >= 0:
                html2 = html[pos + len(lead):]
                pos = html2.find(tail)
                if pos >= 0:
                    _player_config = html2[:pos]

            try:
                player_config.update(json.loads(_player_config))
            except TypeError:
                pass
            finally:
                js = player_config.get('assets', {}).get('js', '')

        if js and not js.startswith('http'):
            js = 'https://www.youtube.com/%s' % js.lstrip('/').replace('www.youtube.com/', '')
        self._context.log_debug('Player JavaScript: |%s|' % js)
        return js

    def _load_manifest(self, url, video_id, meta_info=None, curl_headers='', playback_stats=None):
        headers = {'Host': 'manifest.googlevideo.com',
                   'Connection': 'keep-alive',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com/watch?v=%s' % video_id,
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

        if playback_stats is None:
            playback_stats = {}

        result = requests.get(url, headers=headers, verify=self._verify, allow_redirects=True)
        lines = result.text.splitlines()

        _meta_info = {'video': {},
                      'channel': {},
                      'images': {},
                      'subtitles': []}
        meta_info = meta_info if meta_info else _meta_info
        streams = []
        re_line = re.compile(r'RESOLUTION=(?P<width>\d+)x(?P<height>\d+)')
        re_itag = re.compile(r'/itag/(?P<itag>\d+)')
        for i in range(len(lines)):
            re_match = re.search(re_line, lines[i])
            if re_match:
                line = lines[i + 1]

                re_itag_match = re.search(re_itag, line)
                if re_itag_match:
                    itag = re_itag_match.group('itag')
                    yt_format = self.FORMAT.get(itag, None)
                    if not yt_format:
                        self._context.log_debug('unknown yt_format for itag "%s"' % itag)
                        continue

                    # width = int(re_match.group('width'))
                    # height = int(re_match.group('height'))
                    video_stream = {'url': line,
                                    'meta': meta_info,
                                    'headers': curl_headers,
                                    'playback_stats': playback_stats
                                    }
                    video_stream.update(yt_format)
                    streams.append(video_stream)
        return streams

    def _method_get_video_info(self, video_id=None, player_config=None, cookies=None):
        def requires_cipher(_fmts):
            fl = _fmts.split(',')
            return (len(fl) > 0) and ('s' in dict(urllib.parse.parse_qsl(fl[0])))

        headers = {'Host': 'www.youtube.com',
                   'Connection': 'keep-alive',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com/tv',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

        if self._access_token:
            headers['Authorization'] = 'Bearer %s' % self._access_token

        http_params = {'hl': self.language,
                       'gl': self.region,
                       'ssl_stream': '1',
                       'html5': '1'}

        if player_config is None:
            page_result = self.get_watch_page(video_id)
            html = page_result.get('html')
            player_config = self.get_player_config(html)
            cookies = page_result.get('cookies')

        curl_headers = ''
        if cookies:
            cookies_list = list()
            for c in cookies:
                cookies_list.append('{0}={1};'.format(c.name, c.value))
            if cookies_list:
                curl_headers = 'Cookie={cookies}' \
                    .format(cookies=urllib.parse.quote(' '.join(cookies_list)))
        else:
            cookies = dict()

        player_args = player_config.get('args', {})
        player_response = player_args.get('player_response', {})
        playability_status = player_response.get('playabilityStatus', {})

        if video_id is None:
            if 'video_id' in player_args:
                video_id = player_args['video_id']

        if video_id:
            http_params['video_id'] = video_id
            http_params['eurl'] = ''.join(['https://youtube.googleapis.com/v/', video_id])
        else:
            raise YouTubeException('_method_get_video_info: no video_id')

        http_params['sts'] = player_config.get('sts', '')
        http_params['t'] = player_args.get('t', '')
        http_params['c'] = player_args.get('c', 'WEB')
        http_params['cver'] = player_args.get('cver', '1.20170712')
        http_params['cplayer'] = player_args.get('cplayer', 'UNIPLAYER')
        http_params['cbr'] = player_args.get('cbr', 'Chrome')
        http_params['cbrver'] = player_args.get('cbrver', '53.0.2785.143')
        http_params['cos'] = player_args.get('cos', 'Windows')
        http_params['cosver'] = player_args.get('cosver', '10.0')

        video_info_url = 'https://www.youtube.com/get_video_info'
        el_values = ['detailpage', 'embedded']

        params = dict()

        for el in el_values:
            http_params['el'] = el
            result = requests.get(video_info_url, params=http_params, headers=headers, cookies=cookies, verify=self._verify, allow_redirects=True)
            data = result.text
            params = dict(urllib.parse.parse_qsl(data))
            if params.get('url_encoded_fmt_stream_map') or params.get('live_playback', '0') == '1':
                break

        if not player_response:
            player_response = json.loads(params.get('player_response', '{}'))
            playability_status = player_response.get('playabilityStatus', {})

        playback_tracking = player_response.get('playbackTracking', {})

        captions = player_response.get('captions', {})
        is_live = params.get('live_playback', '0') == '1'

        stream_list = []

        meta_info = {'video': {},
                     'channel': {},
                     'images': {},
                     'subtitles': []}
        meta_info['video']['id'] = params.get('vid', params.get('video_id', ''))
        meta_info['video']['title'] = player_args.get('title', params.get('title', ''))
        meta_info['channel']['author'] = player_args.get('author', params.get('author', ''))
        try:
            meta_info['video']['title'] = meta_info['video']['title'].encode('utf-8', 'ignore').decode('utf-8')
            meta_info['channel']['author'] = meta_info['channel']['author'].encode('utf-8', 'ignore').decode('utf-8')
        except:
            pass

        meta_info['channel']['id'] = params.get('ucid', '')
        image_data_list = [
            {'from': 'iurlhq', 'to': 'high', 'image': 'hqdefault.jpg'},
            {'from': 'iurlmq', 'to': 'medium', 'image': 'mqdefault.jpg'},
            {'from': 'iurlsd', 'to': 'standard', 'image': 'sddefault.jpg'},
            {'from': 'thumbnail_url', 'to': 'default', 'image': 'default.jpg'}]
        for image_data in image_data_list:
            image_url = params.get(image_data['from'], 'https://i.ytimg.com/vi/{video_id}/{image}'.format(video_id=video_id, image=image_data['image']))
            if image_url:
                if is_live:
                    image_url = image_url.replace('.jpg', '_live.jpg')
                meta_info['images'][image_data['to']] = image_url

        if (params.get('status', '') == 'fail') or (playability_status.get('status', 'ok').lower() != 'ok'):
            if not ((playability_status.get('desktopLegacyAgeGateReason', 0) == 1) and not self._context.get_settings().age_gate()):
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
                    reason = params.get('reason')
                    if not reason and 'errorScreen' in playability_status and 'playerErrorMessageRenderer' in playability_status['errorScreen']:
                        reason = playability_status['errorScreen']['playerErrorMessageRenderer'].get('reason', {}).get('simpleText', 'UNKNOWN')
                    if not reason:
                        reason = playability_status.get('reason')

                if not reason:
                    reason = 'UNKNOWN'

                raise YouTubeException(reason)

        meta_info['subtitles'] = Subtitles(self._context, video_id, captions).get_subtitles()

        playback_stats = {
            'playback_url': '',
            'watchtime_url': ''
        }

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

        if is_live:
            live_url = player_response.get('streamingData', {}).get('hlsManifestUrl', '') or params.get('hlsvp', '')
            if live_url:
                stream_list = self._load_manifest(live_url,
                                                  video_id,
                                                  meta_info=meta_info,
                                                  curl_headers=curl_headers,
                                                  playback_stats=playback_stats)

        httpd_is_live = self._context.get_settings().use_dash_videos() and is_httpd_live(port=self._context.get_settings().httpd_port())

        cipher = None
        s_info = dict()

        adaptive_fmts = params.get('adaptive_fmts', player_args.get('adaptive_fmts', ''))
        url_encoded_fmt_stream_map = params.get('url_encoded_fmt_stream_map', player_args.get('url_encoded_fmt_stream_map', ''))

        mpd_url = player_response.get('streamingData', {}).get('dashManifestUrl') or params.get('dashmpd', player_args.get('dashmpd'))

        license_info = {'url': None, 'proxy': None, 'token': None}
        pa_li_info = player_response.get('streamingData', {}).get('licenseInfos', [])
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

        if requires_cipher(adaptive_fmts) or requires_cipher(url_encoded_fmt_stream_map):
            js = self.get_player_js(video_id, player_config.get('assets', {}).get('js', ''))
            cipher = Cipher(self._context, javascript_url=js)

        if not license_info.get('url') and not is_live and httpd_is_live and adaptive_fmts:
            mpd_url, s_info = self.generate_mpd(video_id,
                                                adaptive_fmts,
                                                params.get('length_seconds', '0'),
                                                cipher)
        use_cipher_signature = 'True' == params.get('use_cipher_signature', None)
        if mpd_url:
            mpd_sig_deciphered = True
            if mpd_url.startswith('http'):
                if (use_cipher_signature or re.search('/s/[0-9A-F.]+', mpd_url)) and (not re.search('/signature/[0-9A-F.]+', mpd_url)):
                    mpd_sig_deciphered = False
                    if cipher:
                        sig_param = 'signature'
                        sp = re.search('/sp/(?P<sig_param>[^/]+)', mpd_url)
                        if sp:
                            sig_param = sp.group('sig_param')

                        sig = re.search('/s/(?P<sig>[0-9A-F.]+)', mpd_url)
                        if sig:
                            signature = cipher.get_signature(sig.group('sig'))
                            mpd_url = re.sub('/s/[0-9A-F.]+', ''.join(['/', sig_param, '/', signature]), mpd_url)
                            mpd_sig_deciphered = True

                    else:
                        raise YouTubeException('Cipher: Not Found')
            if mpd_sig_deciphered:
                video_stream = {'url': mpd_url,
                                'meta': meta_info,
                                'headers': curl_headers,
                                'license_info': license_info,
                                'playback_stats': playback_stats}

                if is_live:
                    video_stream['url'] = '&'.join([video_stream['url'], 'start_seq=$START_NUMBER$'])
                    video_stream.update(self.FORMAT.get('9998'))
                else:
                    if not s_info:
                        video_stream.update(self.FORMAT.get('9999'))
                    else:
                        has_video = (s_info['video']['codec'] != '') and (int(s_info['video']['bandwidth']) > 0)
                        if has_video:
                            video_stream.update(self.FORMAT.get('9999'))
                            video_stream['video']['height'] = s_info['video']['height']
                            video_stream['video']['encoding'] = s_info['video']['codec']
                        else:
                            video_stream.update(self.FORMAT.get('9997'))
                        video_stream['audio']['encoding'] = s_info['audio']['codec']
                        if s_info['video']['quality_label']:
                            video_stream['title'] = s_info['video']['quality_label']
                        else:
                            if has_video:
                                video_stream['title'] = '%sp%s' % (s_info['video']['height'], s_info['video']['fps'])
                            else:
                                video_stream['title'] = '%s@%s' % (s_info['audio']['codec'], str(s_info['audio'].get('bitrate', 0)))
                        if int(s_info['audio'].get('bitrate', 0)) > 0:
                            video_stream['audio']['bitrate'] = int(s_info['audio'].get('bitrate', 0))
                stream_list.append(video_stream)
            else:
                raise YouTubeException('Failed to decipher signature')

        def parse_to_stream_list(streams):
            fmts_list = streams.split(',')
            for item in fmts_list:
                stream_map = dict(urllib.parse.parse_qsl(item))

                url = stream_map.get('url', None)
                conn = stream_map.get('conn', None)
                if url:
                    sig_param = '&signature='
                    if 'sp' in stream_map:
                        sig_param = '&%s=' % stream_map['sp']

                    if 'sig' in stream_map:
                        url = ''.join([url, sig_param, stream_map['sig']])
                    elif 's' in stream_map:
                        if cipher:
                            url = ''.join([url, sig_param, cipher.get_signature(stream_map['s'])])
                        else:
                            raise YouTubeException('Cipher: Not Found')

                    itag = stream_map['itag']
                    yt_format = self.FORMAT.get(itag, None)
                    if not yt_format:
                        self._context.log_debug('unknown yt_format for itag "%s"' % itag)
                        continue

                    if yt_format.get('discontinued', False) or yt_format.get('unsupported', False) or \
                            (yt_format.get('dash/video', False) and not yt_format.get('dash/audio', False)):
                        continue

                    stream = {'url': url,
                              'meta': meta_info,
                              'headers': curl_headers,
                              'playback_stats': playback_stats}
                    stream.update(yt_format)
                    stream_list.append(stream)
                elif conn:
                    url = '%s?%s' % (conn, urllib.parse.unquote(stream_map['stream']))
                    itag = stream_map['itag']
                    yt_format = self.FORMAT.get(itag, None)
                    if not yt_format:
                        self._context.log_debug('unknown yt_format for itag "%s"' % itag)
                        continue

                    stream = {'url': url,
                              'meta': meta_info,
                              'headers': curl_headers,
                              'playback_stats': playback_stats}
                    stream.update(yt_format)
                    if stream:
                        stream_list.append(stream)

        # extract streams from map
        if url_encoded_fmt_stream_map:
            parse_to_stream_list(url_encoded_fmt_stream_map)

        if adaptive_fmts:
            parse_to_stream_list(adaptive_fmts)

        # last fallback
        if not stream_list:
            raise YouTubeException('No streams found')

        return stream_list

    def generate_mpd(self, video_id, adaptive_fmts, duration, cipher):
        discarded_streams = list()

        def get_discarded_audio(fmt, mime_type, itag, stream, reason='unsupported'):
            _discarded_stream = dict()
            _discarded_stream['audio'] = dict()
            _discarded_stream['audio']['itag'] = str(itag)
            _discarded_stream['audio']['mime'] = str(mime_type)
            _discarded_stream['audio']['codec'] = str(stream['codecs'])
            if fmt:
                audio_bitrate = int(fmt.get('audio', {}).get('bitrate', 0))
                if audio_bitrate > 0:
                    _discarded_stream['audio']['bitrate'] = audio_bitrate
            codec_match = re.search('codecs="(?P<codec>[^"]+)"', _discarded_stream['audio']['codec'])
            if codec_match:
                _discarded_stream['audio']['codec'] = codec_match.group('codec')
            _discarded_stream['audio']['bandwidth'] = int(stream['bandwidth'])
            _discarded_stream['reason'] = reason
            return _discarded_stream

        def get_discarded_video(mime_type, itag, stream, reason='unsupported'):
            _discarded_stream = dict()
            _discarded_stream['video'] = dict()
            _discarded_stream['video']['itag'] = str(itag)
            _discarded_stream['video']['width'] = str(stream['width'])
            _discarded_stream['video']['height'] = str(stream['height'])
            if stream.get('quality_label'):
                _discarded_stream['video']['quality_label'] = str(stream['quality_label'])
            _discarded_stream['video']['fps'] = str(stream['frameRate'])
            _discarded_stream['video']['codec'] = str(stream['codecs'])
            _discarded_stream['video']['mime'] = str(mime_type)
            codec_match = re.search('codecs="(?P<codec>[^"]+)"', _discarded_stream['video']['codec'])
            if codec_match:
                _discarded_stream['video']['codec'] = codec_match.group('codec')
            _discarded_stream['video']['bandwidth'] = int(stream['bandwidth'])
            _discarded_stream['reason'] = reason
            return _discarded_stream

        def filter_qualities(stream_data, mime_type, sorted_qualities):

            data_copy = copy.deepcopy(stream_data)
            itag_match = None

            if mime_type == 'video/mp4':
                discard_mime = 'video/webm'
            elif mime_type == 'video/webm':
                discard_mime = 'video/mp4'
            else:
                return None

            if discard_mime in data_copy:
                for itag in list(data_copy[discard_mime].keys()):
                    discarded_streams.append(get_discarded_video(discard_mime,
                                                                 itag,
                                                                 data_copy[discard_mime][itag],
                                                                 'filtered mime type'))
                    del data_copy[discard_mime][itag]
                del data_copy[discard_mime]

            for idx, q in enumerate(sorted_qualities):
                if any(itag for itag in list(data_copy[mime_type].keys())
                       if int(data_copy[mime_type][itag].get('height', 0)) == q):
                    itag_match = next(itag for itag in list(data_copy[mime_type].keys())
                                      if int(data_copy[mime_type][itag].get('height', 0)) == q)
                    break

                if idx != len(sorted_qualities) - 1:
                    if any(itag for itag in list(data_copy[mime_type].keys())
                           if ((int(data_copy[mime_type][itag].get('height', 0)) < q) and
                               (int(data_copy[mime_type][itag].get('height', 0)) > sorted_qualities[idx + 1]))):
                        itag_match = next(itag for itag in list(data_copy[mime_type].keys())
                                          if ((int(data_copy[mime_type][itag].get('height', 0)) < q) and
                                              (int(data_copy[mime_type][itag].get('height', 0)) > sorted_qualities[idx + 1])))
                        break

            if itag_match:
                for itag in list(data_copy[mime_type].keys()):
                    if itag != itag_match:
                        discarded_streams.append(get_discarded_video(mime_type,
                                                                     itag,
                                                                     data_copy[mime_type][itag],
                                                                     'filtered quality'))
                        del data_copy[mime_type][itag]

                return data_copy

            return None

        def filter_fps(stream_data, mime_type):
            data_copy = None
            if mime_type in stream_data:
                data_copy = copy.deepcopy(stream_data)
                if any(k for k in list(data_copy[mime_type].keys())
                       if data_copy[mime_type][k]['fps'] <= 30):
                    for k in list(data_copy[mime_type].keys()):
                        if data_copy[mime_type][k]['fps'] > 30:
                            discarded_streams.append(get_discarded_video(mime_type,
                                                                         k,
                                                                         data_copy[mime_type][k],
                                                                         'frame rate limit'))
                            del data_copy[mime_type][k]

            return data_copy

        basepath = 'special://temp/plugin.video.youtube/'
        if not make_dirs(basepath):
            self._context.log_debug('Failed to create directories: %s' % basepath)
            return None

        has_video_stream = False
        ia_capabilities = self._context.inputstream_adaptive_capabilities()

        ipaddress = self._context.get_settings().httpd_listen()
        if ipaddress == '0.0.0.0':
            ipaddress = '127.0.0.1'

        stream_info = {'video': {'height': '0', 'fps': '0', 'codec': '', 'mime': '', 'quality_label': '', 'bandwidth': 0},
                       'audio': {'bitrate': '0', 'codec': '', 'mime': '', 'bandwidth': 0}}

        fmts_list = adaptive_fmts.split(',')
        data = dict()
        for item in fmts_list:
            stream_map = dict(urllib.parse.parse_qsl(item))

            t = stream_map.get('type')
            t = urllib.parse.unquote(t)
            t = t.split(';')
            mime = t[0]
            i = stream_map.get('itag')
            if mime not in data:
                data[mime] = {}
            data[mime][i] = {}

            data[mime][i]['codecs'] = t[1][1:]
            data[mime][i]['id'] = i

            s = stream_map.get('size')
            if s:
                s = s.split('x')
                data[mime][i]['width'] = s[0]
                data[mime][i]['height'] = s[1]

            data[mime][i]['quality_label'] = str(stream_map.get('quality_label'))

            data[mime][i]['bandwidth'] = stream_map.get('bitrate')

            # map frame rates to a more common representation to lessen the chance of double refresh changes
            # sometimes 30 fps is 30 fps, more commonly it is 29.97 fps (same for all mapped frame rates)
            frame_rate = None
            fps_scale_map = {24: 1001, 30: 1001, 60: 1001}
            if 'fps' in stream_map:
                fps = int(stream_map.get('fps'))
                data[mime][i]['fps'] = fps
                scale = fps_scale_map.get(fps, 1000)
                frame_rate = '%d/%d' % (fps * 1000, scale)

            data[mime][i]['frameRate'] = frame_rate

            url = urllib.parse.unquote(stream_map.get('url'))

            sig_param = '&signature='
            if 'sp' in stream_map:
                sig_param = '&%s=' % stream_map['sp']

            if 'sig' in stream_map:
                url = ''.join([url, sig_param, stream_map['sig']])
            elif 's' in stream_map:
                if cipher:
                    url = ''.join([url, sig_param, cipher.get_signature(stream_map['s'])])
                else:
                    raise YouTubeException('Cipher: Not Found')

            url = url.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
            data[mime][i]['baseUrl'] = url

            data[mime][i]['indexRange'] = stream_map.get('index')
            data[mime][i]['init'] = stream_map.get('init')

            if (not stream_map.get('index') or not stream_map.get('init') or
                    (stream_map.get('index') == '0-0' and stream_map.get('init') == '0-0')):
                if mime.startswith('video'):
                    discarded_streams.append(get_discarded_video(mime, i, data[mime][i], 'no init or index'))
                else:
                    discarded_streams.append(get_discarded_audio(mime, i, data[mime][i], 'no init or index'))
                del data[mime][i]

        default_mime_type = 'mp4'
        supported_mime_types = ['audio/mp4', 'video/mp4']

        if ('vp9' in ia_capabilities or 'vp9.2' in ia_capabilities) and any(m for m in data if m == 'video/webm'):
            supported_mime_types.append('video/webm')

        if ('vorbis' in ia_capabilities or 'opus' in ia_capabilities) and any(m for m in data if m == 'audio/webm'):
            supported_mime_types.append('audio/webm')

        if ('video/webm' in supported_mime_types and
                (self._context.get_settings().get_mpd_quality() > 1080 or
                 self._context.get_settings().include_hdr())):
            default_mime_type = 'webm'

        apply_filters = self._context.inputstream_adaptive_auto_stream_selection()
        limit_qualities = self._context.get_settings().mpd_video_qualities()
        limit_30fps = self._context.get_settings().mpd_30fps_limit()
        self._context.log_debug('Generating MPD: Apply filters |{apply_filters}| '
                                'Quality selection |{quality}| Limit 30FPS |{limit_fps}|'
                                .format(apply_filters=str(apply_filters),
                                        quality=str(next(iter(limit_qualities), None)),
                                        limit_fps=str(limit_30fps)))

        if apply_filters:
            # filter streams only if InputStream Adaptive - Stream selection is set to Auto
            if limit_30fps:
                filtered_data = filter_fps(data, 'video/mp4')
                if filtered_data:
                    data = filtered_data

                filtered_data = filter_fps(data, 'video/webm')
                if filtered_data:
                    data = filtered_data

            if ('video/webm' in supported_mime_types and
                    'vp9.2' in ia_capabilities and
                    self._context.get_settings().include_hdr() and
                    any(k for k in list(data['video/webm'].keys()) if '"vp9.2"' in data['video/webm'][k]['codecs'])):
                # when hdr enabled and inputstream adaptive stream selection is set to automatic
                # replace vp9 streams with vp9.2 (hdr) of the same resolution
                webm_streams = {}

                for key in list(data['video/webm'].keys()):
                    if '"vp9.2"' in data['video/webm'][key]['codecs']:
                        webm_streams[key] = data['video/webm'][key]
                    elif '"vp9"' in data['video/webm'][key]['codecs']:
                        if not any(k for k in list(data['video/webm'].keys())
                                   if '"vp9.2"' in data['video/webm'][k]['codecs'] and
                                      data['video/webm'][key]['height'] == data['video/webm'][k]['height'] and
                                      data['video/webm'][key]['width'] == data['video/webm'][k]['width']):
                            webm_streams[key] = data['video/webm'][key]

                discard_webm = [data['video/webm'][i] for i in (set(data['video/webm']) - set(webm_streams))
                                if i in data['video/webm']]
                for d in discard_webm:
                    discarded_streams.append(get_discarded_video('video/webm',
                                                                 d['id'],
                                                                 data['video/webm'][d['id']],
                                                                 'replaced by hdr'))

                if webm_streams:
                    data['video/webm'] = webm_streams

            if limit_qualities:
                if default_mime_type == 'mp4':
                    filtered_data = filter_qualities(data, 'video/mp4', limit_qualities)
                    if filtered_data:
                        data = filtered_data

                elif default_mime_type == 'webm':
                    filtered_data = filter_qualities(data, 'video/webm', limit_qualities)
                    if filtered_data:
                        data = filtered_data

        out_list = ['<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<MPD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="urn:mpeg:dash:schema:mpd:2011" xmlns:xlink="http://www.w3.org/1999/xlink" '
                    'xsi:schemaLocation="urn:mpeg:dash:schema:mpd:2011 http://standards.iso.org/ittf/PubliclyAvailableStandards/MPEG-DASH_schema_files/DASH-MPD.xsd" '
                    'minBufferTime="PT1.5S" mediaPresentationDuration="PT', duration, 'S" type="static" profiles="urn:mpeg:dash:profile:isoff-main:2011">\n',
                    '\t<Period>\n']

        n = 0
        for mime in data:
            if mime in supported_mime_types:
                default = False
                if mime.endswith(default_mime_type):
                    default = True

                out_list.append(''.join(['\t\t<AdaptationSet id="', str(n), '" mimeType="', mime, '" subsegmentAlignment="true" subsegmentStartsWithSAP="1" bitstreamSwitching="true" default="', str(default).lower(), '">\n']))
                out_list.append('\t\t\t<Role schemeIdUri="urn:mpeg:DASH:role:2011" value="main"/>\n')
                for i in data[mime]:
                    stream_format = self.FORMAT.get(i, {})
                    if 'audio' in mime:
                        audio_codec = str(data[mime][i]['codecs'])
                        match = re.search('codecs="(?P<codec>[^"]+)"', audio_codec)
                        if match:
                            audio_codec = match.group('codec')

                        if 'opus' == audio_codec.lower() and 'opus' not in ia_capabilities:
                            discarded_streams.append(get_discarded_audio(stream_format, mime, i, data[mime][i]))
                            continue
                        elif 'vorbis' == audio_codec.lower() and 'vorbis' not in ia_capabilities:
                            discarded_streams.append(get_discarded_audio(stream_format, mime, i, data[mime][i]))
                            continue

                        if int(data[mime][i]['bandwidth']) > int(stream_info['audio']['bandwidth']):
                            stream_info['audio']['mime'] = str(mime)
                            if stream_format:
                                bitrate = int(stream_format.get('audio', {}).get('bitrate', 0))
                                if bitrate > 0:
                                    stream_info['audio']['bitrate'] = bitrate
                                stream_info['audio']['codec'] = stream_format.get('audio', {}).get('encoding')
                            if not stream_info['audio'].get('codec'):
                                stream_info['audio']['codec'] = audio_codec
                            stream_info['audio']['bandwidth'] = int(data[mime][i]['bandwidth'])

                        out_list.append(''.join(['\t\t\t<Representation id="',
                                                 i, '" ', data[mime][i]['codecs'],
                                                 ' bandwidth="', data[mime][i]['bandwidth'],
                                                 '">\n']))
                        out_list.append('\t\t\t\t<AudioChannelConfiguration schemeIdUri="urn:mpeg:dash:23003:3:audio_channel_configuration:2011" value="2"/>\n')
                    else:
                        video_codec = str(data[mime][i]['codecs'])
                        match = re.search('codecs="(?P<codec>[^"]+)"', video_codec)
                        if match:
                            video_codec = match.group('codec')

                        if 'vp9.2' == video_codec.lower() and ('vp9.2' not in ia_capabilities or
                                                               not self._context.get_settings().include_hdr()):
                            if not self._context.get_settings().include_hdr() and 'vp9.2' in ia_capabilities:
                                discarded_streams.append(get_discarded_video(mime, i, data[mime][i], 'hdr not selected'))
                            else:
                                discarded_streams.append(get_discarded_video(mime, i, data[mime][i]))
                            continue
                        elif 'vp9' == video_codec.lower() and 'vp9' not in ia_capabilities:
                            discarded_streams.append(get_discarded_video(mime, i, data[mime][i]))
                            continue
                        elif video_codec.lower().startswith(('av01', 'av1')) and 'av1' not in ia_capabilities:
                            discarded_streams.append(get_discarded_video(mime, i, data[mime][i]))
                            continue

                        has_video_stream = True
                        if int(data[mime][i]['bandwidth']) > int(stream_info['video']['bandwidth']):
                            stream_info['video']['height'] = str(data[mime][i]['height'])
                            stream_info['video']['fps'] = str(data[mime][i]['frameRate'])
                            stream_info['video']['mime'] = str(mime)
                            stream_info['video']['codec'] = video_codec
                            stream_info['video']['bandwidth'] = int(data[mime][i]['bandwidth'])
                            if data[mime][i].get('quality_label'):
                                stream_info['video']['quality_label'] = str(data[mime][i]['quality_label'])
                            if stream_format:
                                stream_info['video']['codec'] = stream_format.get('video', {}).get('encoding')
                            if not stream_info['video'].get('codec'):
                                stream_info['video']['codec'] = video_codec

                        video_codec = data[mime][i]['codecs']
                        out_list.append(''.join(['\t\t\t<Representation id="', i, '" ', video_codec,
                                                 ' startWithSAP="1" bandwidth="', data[mime][i]['bandwidth'],
                                                 '" width="', data[mime][i]['width'], '" height="',
                                                 data[mime][i]['height'], '" frameRate="', data[mime][i]['frameRate'],
                                                 '">\n']))

                    out_list.append(''.join(['\t\t\t\t<BaseURL>', data[mime][i]['baseUrl'], '</BaseURL>\n']))
                    out_list.append(''.join(['\t\t\t\t<SegmentBase indexRange="', data[mime][i]['indexRange'],
                                             '">\n', '\t\t\t\t\t\t<Initialization range="',
                                             data[mime][i]['init'], '" />\n', '\t\t\t\t</SegmentBase>\n']))
                    out_list.append('\t\t\t</Representation>\n')
                out_list.append('\t\t</AdaptationSet>\n')
                n = n + 1
            else:
                for i in data[mime]:
                    stream_format = self.FORMAT.get(i, {})
                    if 'audio' in mime:
                        discarded_stream = get_discarded_audio(stream_format, mime, i, data[mime][i])
                    else:
                        discarded_stream = get_discarded_video(mime, i, data[mime][i])
                    discarded_streams.append(discarded_stream)

        out_list.append('\t</Period>\n</MPD>\n')
        out = ''.join(out_list)

        self._context.log_debug('Generated MPD highest supported quality found: |%s|' % str(stream_info))
        if discarded_streams:
            discarded_streams = sorted(discarded_streams, key=lambda k: k.get('audio', k.get('video', {}))['bandwidth'], reverse=True)
            self._context.log_debug('Generated MPD discarded streams: \n%s' % '\n'.join(str(stream) for stream in discarded_streams))

        if not has_video_stream:
            self._context.log_debug('Generated MPD no supported video streams found')

        filepath = '{base_path}{video_id}.mpd'.format(base_path=basepath, video_id=video_id)
        try:
            f = xbmcvfs.File(filepath, 'w')
            if PY2:
                _ = f.write(out.encode('utf-8'))
            else:
                _ = f.write(str(out))
            f.close()
            return 'http://{ipaddress}:{port}/{video_id}.mpd'.format(
                ipaddress=ipaddress,
                port=self._context.get_settings().httpd_port(),
                video_id=video_id
            ), stream_info
        except:
            return None, None
