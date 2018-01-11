__author__ = 'bromix'

import urllib
import urlparse
import re
import json

import requests
from ..youtube_exceptions import YouTubeException
from .signature.cipher import Cipher
from subtitles import Subtitles


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
        # === Live DASH adaptive
        '9998': {'container': 'mpd',
                 'Live': True,
                 'sort': [1080, 0],
                 'title': 'Live DASH',
                 'dash/audio': True,
                 'dash/video': True,
                 'audio': {'bitrate': 0, 'encoding': ''},
                 'video': {'height': 0, 'encoding': ''}},
        # === DASH adaptive
        '9999': {'container': 'mpd',
                 'sort': [1080, 0],
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

    def get_player_config(self, html):
        _player_config = '{}'
        lead = 'ytplayer.config = '
        tail = ';ytplayer.load'
        pos = html.find(lead)
        if pos >= 0:
            html2 = html[pos + len(lead):]
            pos = html2.find(tail)
            if pos:
                _player_config = html2[:pos]

        blank_config = re.search('var blankSwfConfig\s*=\s*(?P<player_config>{.+?});\s*var fillerData', html)
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
        if isinstance(player_response, basestring):
            try:
                player_response = json.loads(player_response)
            except TypeError:
                player_response = dict()

        player_config['args']['player_response'] = dict()

        result = re.search('window\["ytInitialPlayerResponse"\]\s*=\s*\(\s*(?P<player_response>{.+?})\s*\);', html)
        if result:
            try:
                player_config['args']['player_response'] = json.loads(result.group('player_response'))
            except TypeError:
                pass

        player_config['args']['player_response'].update(player_response)

        return player_config

    def _load_manifest(self, url, video_id, meta_info=None, curl_headers=''):
        headers = {'Host': 'manifest.googlevideo.com',
                   'Connection': 'keep-alive',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com/watch?v=%s' % video_id,
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}
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

                    width = int(re_match.group('width'))
                    height = int(re_match.group('height'))
                    video_stream = {'url': line,
                                    'meta': meta_info,
                                    'headers': curl_headers
                    }
                    video_stream.update(yt_format)
                    streams.append(video_stream)
        return streams

    def _method_get_video_info(self, video_id=None, player_config=None, cookies=None):
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

        params = {'hl': self.language,
                  'gl': self.region,
                  'ssl_stream': '1',
                  'html5': '1'}

        if player_config is None:
            watch_page_result = self.get_watch_page(video_id)
            html = watch_page_result.get('html')
            cookies = watch_page_result.get('cookies')
            player_config = self.get_player_config(html)

        curl_headers = ''
        if cookies:
            cookies_list = list()
            for c in cookies:
                cookies_list.append('{0}={1};'.format(c.name, c.value))
            if cookies_list:
                curl_headers = 'Cookie={cookies}'\
                    .format(cookies=urllib.quote(' '.join(cookies_list)))
        else:
            cookies = dict()

        player_assets = player_config.get('assets', {})
        player_args = player_config.get('args', {})
        player_response = player_args.get('player_response', {})
        playability_status = player_response.get('playabilityStatus', {})
        captions = player_response.get('captions', {})
        js = player_assets.get('js')

        if video_id is None:
            if 'video_id' in player_args:
                video_id = player_args['video_id']

        if video_id:
            params['video_id'] = video_id
            params['eurl'] = 'https://youtube.googleapis.com/v/' + video_id
        else:
            raise YouTubeException('_method_get_video_info: no video_id')

        cipher = None
        if js:
            if not js.startswith('http'):
                js = 'http://www.youtube.com/%s' % js.lstrip('/')
            self._context.log_debug('Cipher: js player: |%s|' % js)
            cipher = Cipher(self._context, java_script_url=js)

        params['sts'] = player_config.get('sts', '')

        params['c'] = player_args.get('c', 'WEB')
        params['cver'] = player_args.get('cver', '1.20170712')
        params['cplayer'] = player_args.get('cplayer', 'UNIPLAYER')
        params['cbr'] = player_args.get('cbr', 'Chrome')
        params['cbrver'] = player_args.get('cbrver', '53.0.2785.143')
        params['cos'] = player_args.get('cos', 'Windows')
        params['cosver'] = player_args.get('cosver', '10.0')

        url = 'https://www.youtube.com/get_video_info'

        result = requests.get(url, params=params, headers=headers, cookies=cookies, verify=self._verify, allow_redirects=True)

        stream_list = []

        data = result.text
        params = dict(urlparse.parse_qsl(data))

        meta_info = {'video': {},
                     'channel': {},
                     'images': {},
                     'subtitles': []}
        meta_info['video']['id'] = params.get('vid', params.get('video_id', ''))
        meta_info['video']['title'] = params.get('title', '')
        meta_info['channel']['author'] = params.get('author', '')
        try:
            meta_info['video']['title'] = meta_info['video']['title'].decode('utf-8')
            meta_info['channel']['author'] = meta_info['channel']['author'].decode('utf-8')
        except:
            pass

        meta_info['channel']['id'] = params.get('ucid', '')
        image_data_list = [
            {'from': 'iurlhq', 'to': 'high'},
            {'from': 'iurlmq', 'to': 'medium'},
            {'from': 'iurlsd', 'to': 'standard'},
            {'from': 'thumbnail_url', 'to': 'default'}]
        for image_data in image_data_list:
            image_url = params.get(image_data['from'], '')
            if image_url:
                meta_info['images'][image_data['to']] = image_url

        meta_info['subtitles'] = Subtitles(self._context, video_id, captions).get_subtitles()

        if (params.get('status', '') == 'fail') or (playability_status.get('status', 'ok').lower() != 'ok'):
            if not ((playability_status.get('desktopLegacyAgeGateReason', 0) == 1) and not self._context.get_settings().age_gate()):
                reason = params.get('reason')
                if not reason:
                    reason = playability_status.get('reason')
                    if not reason:
                        reason = 'UNKNOWN'
                        if 'errorScreen' in playability_status and 'playerErrorMessageRenderer' in playability_status['errorScreen']:
                            reason = playability_status['errorScreen']['playerErrorMessageRenderer'].get('reason', {}).get('simpleText', 'UNKNOWN')
                raise YouTubeException(reason)

        if params.get('live_playback', '0') == '1':
            url = params.get('hlsvp', '')
            if url:
                stream_list = self._load_manifest(url, video_id, meta_info=meta_info, curl_headers=curl_headers)

        mpd_url = params.get('dashmpd', player_args.get('dashmpd'))
        use_cipher_signature = 'True' == params.get('use_cipher_signature', None)
        if mpd_url:
            mpd_sig_deciphered = True
            if (use_cipher_signature or re.search('/s/[0-9A-F\.]+', mpd_url)) and (not re.search('/signature/[0-9A-F\.]+', mpd_url)):
                mpd_sig_deciphered = False
                if cipher:
                    sig = re.search('/s/(?P<sig>[0-9A-F\.]+)', mpd_url)
                    if sig:
                        signature = cipher.get_signature(sig.group('sig'))
                        mpd_url = re.sub('/s/[0-9A-F\.]+', '/signature/' + signature, mpd_url)
                        mpd_sig_deciphered = True
                else:
                    raise YouTubeException('Cipher: Not Found')
            if mpd_sig_deciphered:
                video_stream = {'url': mpd_url,
                                'meta': meta_info,
                                'headers': curl_headers}
                if params.get('live_playback', '0') == '1':
                    video_stream['url'] += '&start_seq=$START_NUMBER$'
                    video_stream.update(self.FORMAT.get('9998'))
                else:
                    video_stream.update(self.FORMAT.get('9999'))
                stream_list.append(video_stream)
            else:
                raise YouTubeException('Failed to decipher signature')

        def parse_to_stream_list(stream_map_list):
            for item in stream_map_list:
                stream_map = dict(urlparse.parse_qsl(item))

                url = stream_map.get('url', None)
                conn = stream_map.get('conn', None)
                if url:
                    if 'sig' in stream_map:
                        url += '&signature=%s' % stream_map['sig']
                    elif 's' in stream_map:
                        if cipher:
                            url += '&signature=%s' % cipher.get_signature(stream_map['s'])
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

                    video_stream = {'url': url,
                                    'meta': meta_info,
                                    'headers': curl_headers}
                    video_stream.update(yt_format)
                    stream_list.append(video_stream)
                elif conn:
                    url = '%s?%s' % (conn, urllib.unquote(stream_map['stream']))
                    itag = stream_map['itag']
                    yt_format = self.FORMAT.get(itag, None)
                    if not yt_format:
                        self._context.log_debug('unknown yt_format for itag "%s"' % itag)
                        continue

                    video_stream = {'url': url,
                                    'meta': meta_info,
                                    'headers': curl_headers}
                    video_stream.update(yt_format)
                    if video_stream:
                        stream_list.append(video_stream)

        # extract streams from map
        url_encoded_fmt_stream_map = params.get('url_encoded_fmt_stream_map', player_args.get('url_encoded_fmt_stream_map', ''))
        if url_encoded_fmt_stream_map:
            url_encoded_fmt_stream_map = url_encoded_fmt_stream_map.split(',')
            parse_to_stream_list(url_encoded_fmt_stream_map)

        adaptive_fmts = params.get('adaptive_fmts', player_args.get('adaptive_fmts', ''))
        if adaptive_fmts:
            adaptive_fmts = adaptive_fmts.split(',')
            parse_to_stream_list(adaptive_fmts)




        duration = params.get('length_seconds')
        fmts_list = params.get('adaptive_fmts').split(',')
        data = {}
        for item in fmts_list:
            stream_map = dict(urlparse.parse_qsl(item))

            t = stream_map.get('type')
            t = urllib.unquote(t).decode('utf8')
            t = t.split(';')
            mime = t[0]
            i = stream_map.get('itag')
            if not data.has_key(mime):
                data[mime] = {}
            data[mime][i] = {}

            data[mime][i]['codecs'] = t[1][1:]
            data[mime][i]['id'] = i

            s = stream_map.get('size')
            if s:
                s=s.split('x')
                data[mime][i]['width'] = s[0]
                data[mime][i]['height'] = s[1]

            data[mime][i]['bandwidth'] = stream_map.get('bitrate')
            data[mime][i]['frameRate'] = stream_map.get('fps')

            url = urllib.unquote(stream_map.get('url')).decode('utf8')
            url = url.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
            data[mime][i]['baseUrl'] = url

            data[mime][i]['indexRange'] = stream_map.get('index')
            data[mime][i]['init'] = stream_map.get('init')



        out = '<?xml version="1.0" encoding="UTF-8"?>' + \
        '<MPD xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="urn:mpeg:dash:schema:mpd:2011" xmlns:xlink="http://www.w3.org/1999/xlink" ' + \
        'xsi:schemaLocation="urn:mpeg:dash:schema:mpd:2011 http://standards.iso.org/ittf/PubliclyAvailableStandards/MPEG-DASH_schema_files/DASH-MPD.xsd" ' + \
        'minBufferTime="PT1.5S" mediaPresentationDuration="PT' + duration +'S" type="static" availabilityStartTime="2001-12-17T09:40:57Z" profiles="urn:mpeg:dash:profile:isoff-main:2011">'
        out += '<Period start="PT0S" duration="PT' + duration +'S">\n'

        n = 0
        for mime in data:
            out += '<AdaptationSet id="' + str(n) + '" mimeType="' + mime + '" subsegmentAlignment="true" subsegmentStartsWithSAP="1" bitstreamSwitching="true">\n'
            out += '<Role schemeIdUri="urn:mpeg:DASH:role:2011" value="main"/>\n'
            for i in data[mime]:
                if 'audio' in mime:
                    out += '<Representation id="' + i + '" ' + data[mime][i]['codecs'] + \
                        ' bandwidth="' + data[mime][i]['bandwidth'] + \
                        '">\n'
                    out += '<AudioChannelConfiguration schemeIdUri="urn:mpeg:dash:23003:3:audio_channel_configuration:2011" value="2"/>\n'
                else:
                    out += '<Representation id="' + i + '" ' + data[mime][i]['codecs'] + \
                        ' startWithSAP="1" bandwidth="' + data[mime][i]['bandwidth'] + \
                        '" width="' + data[mime][i]['width'] + '" height="' + data[mime][i]['height'] + \
                        '" frameRate="' + data[mime][i]['frameRate'] + '">\n'

                out += '<BaseURL>' + data[mime][i]['baseUrl'] + '</BaseURL>\n'
                out += '<SegmentBase indexRange="' + data[mime][i]['indexRange'] + '">\n' + \
                '<Initialization range="' + data[mime][i]['init'] + '" />\n' + \
                '</SegmentBase>\n'
                out += '</Representation>\n'
            out += '</AdaptationSet>\n'
            n = n + 1
        out += '</Period></MPD>\n'

        with open('out.mpd', 'w') as the_file:
            the_file.write(out)

        # last fallback
        if not stream_list:
            raise YouTubeException('No streams found')

        return stream_list
