__author__ = 'bromix'

import urllib
import urlparse
import re

from resources.lib.kodion import simple_requests as requests
from ..youtube_exceptions import YouTubeException
from .signature.cipher import Cipher


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
                'title': 'Live@72p',
                'sort': [72, 0],
                'video': {'height': 72, 'encoding': 'h.264'},
                'audio': {'bitrate': 24, 'encoding': 'aac'}},
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
                'dash/audio': True,
                'audio': {'bitrate': 48, 'encoding': 'aac'}},
        '140': {'container': 'mp4',
                'dash/audio': True,
                'audio': {'bitrate': 128, 'encoding': 'aac'}},
        '141': {'container': 'mp4',
                'dash/audio': True,
                'audio': {'bitrate': 256, 'encoding': 'aac'}},
        '171': {'container': 'webm',
                'dash/audio': True,
                'audio': {'bitrate': 128, 'encoding': 'vorbis'}},
        '172': {'container': 'webm',
                'dash/audio': True,
                'audio': {'bitrate': 192, 'encoding': 'vorbis'}},
        '249': {'container': 'webm',
                'dash/audio': True,
                'audio': {'bitrate': 50, 'encoding': 'opus'}},
        '250': {'container': 'webm',
                'dash/audio': True,
                'audio': {'bitrate': 70, 'encoding': 'opus'}},
        '251': {'container': 'webm',
                'dash/audio': True,
                'audio': {'bitrate': 160, 'encoding': 'opus'}},
    }

    def __init__(self, context, access_token='', language='en-US'):
        self._context = context
        self._language = language.replace('-', '_')
        self._access_token = access_token
        pass

    def load_stream_infos(self, video_id):
        return self._method_get_video_info(video_id)

    def _method_watch(self, video_id, reason=u''):
        stream_list = []

        headers = {'Host': 'www.youtube.com',
                   'Connection': 'keep-alive',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

        params = {'v': video_id}

        url = 'https://www.youtube.com/watch'

        result = requests.get(url, params=params, headers=headers, verify=False, allow_redirects=True)
        html = result.text

        """
        This will almost double the speed for the regular expressions, because we only must match
        a small portion of the whole html. And only if we find positions, we cut down the html.

        """
        pos = html.find('ytplayer.config')
        if pos >= 0:
            html2 = html[pos:]
            pos = html2.find('</script>')
            if pos:
                html = html2[:pos]
                pass
            pass

        """
        itag_map = {}
        itag_map.update(self.DEFAULT_ITAG_MAP)
        re_match = re.match('.+\"fmt_list\": \"(?P<fmt_list>.+?)\".+', html)
        if re_match:
            fmt_list = re_match.group('fmt_list')
            fmt_list = fmt_list.split(',')

            for value in fmt_list:
                value = value.replace('\/', '|')

                try:
                    attr = value.split('|')
                    sizes = attr[1].split('x')
                    itag_map[attr[0]] = {'width': int(sizes[0]),
                                         'height': int(sizes[1])}
                except:
                    # do nothing
                    pass
                pass
            pass
        """

        re_match_js = re.search(r'\"js\"[^:]*:[^"]*\"(?P<js>.+?)\"', html)
        js = ''
        cipher = None
        if re_match_js:
            js = re_match_js.group('js').replace('\\', '').strip('//')
            cipher = Cipher(self._context, java_script_url=js)
            pass

        re_match_hlsvp = re.search(r'\"hlsvp\"[^:]*:[^"]*\"(?P<hlsvp>[^"]*\")', html)
        if re_match_hlsvp:
            hlsvp = urllib.unquote(re_match_hlsvp.group('hlsvp')).replace('\/', '/')
            return self._load_manifest(hlsvp, video_id)

        re_match = re.search(r'\"url_encoded_fmt_stream_map\"[^:]*:[^"]*\"(?P<url_encoded_fmt_stream_map>[^"]*\")',
                             html)
        if re_match:
            url_encoded_fmt_stream_map = re_match.group('url_encoded_fmt_stream_map')
            url_encoded_fmt_stream_map = url_encoded_fmt_stream_map.split(',')

            for value in url_encoded_fmt_stream_map:
                value = value.replace('\\u0026', '&')
                attr = dict(urlparse.parse_qsl(value))

                try:
                    url = attr.get('url', None)
                    conn = attr.get('conn', None)
                    if url:
                        url = urllib.unquote(attr['url'])

                        signature = ''
                        if attr.get('s', ''):
                            signature = cipher.get_signature(attr['s'])
                            pass
                        elif attr.get('sig', ''):
                            signature = attr.get('sig', '')
                            pass

                        if signature:
                            url += '&signature=%s' % signature
                            pass

                        itag = attr['itag']
                        yt_format = self.FORMAT.get(itag, None)

                        if not yt_format:
                            raise Exception('unknown yt_format for itag "%s"' % itag)

                        # this format is discontinued
                        if yt_format.get('discontinued', False):
                            continue
                            pass

                        video_stream = {'url': url}
                        video_stream.update(yt_format)

                        stream_list.append(video_stream)
                        pass
                    elif conn:  # rtmpe
                        url = '%s?%s' % (conn, urllib.unquote(attr['stream']))
                        itag = attr['itag']
                        yt_format = self.FORMAT.get(itag, None)
                        yt_format['rtmpe'] = True
                        if not yt_format:
                            raise Exception('unknown yt_format for itag "%s"' % itag)
                        video_stream = {'url': url}
                        video_stream.update(yt_format)

                        stream_list.append(video_stream)
                        pass
                except Exception, ex:
                    x = 0
                    pass
                pass
            pass

        # try to find the reason of this page if we've only got 'UNKNOWN'
        if len(stream_list) == 0 and reason.lower() == 'unknown':
            reason_match = re.search(r'<h1[^>]*>(?P<reason>[^<]+)', html)
            if reason_match:
                reason = reason_match.group('reason').strip()
                pass
            pass

        # this is a reason from get_video_info. We should at least display the reason why the video couldn't be loaded
        if len(stream_list) == 0 and reason:
            raise YouTubeException(reason)

        return stream_list

    def _load_manifest(self, url, video_id):
        headers = {'Host': 'manifest.googlevideo.com',
                   'Connection': 'keep-alive',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com/watch?v=%s' % video_id,
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}
        result = requests.get(url, headers=headers, verify=False, allow_redirects=True)
        lines = result.text.splitlines()
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
                        raise Exception('unknown yt_format for itag "%s"' % itag)

                    width = int(re_match.group('width'))
                    height = int(re_match.group('height'))
                    video_stream = {'url': line}
                    video_stream.update(yt_format)
                    streams.append(video_stream)
                    pass
                pass
            pass
        return streams

    def _method_get_video_info(self, video_id):
        headers = {'Host': 'www.youtube.com',
                   'Connection': 'keep-alive',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com/tv',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}
        params = {'video_id': video_id,
                  'hl': self._language,
                  'ps': 'leanback',
                  'el': 'leanback',
                  'width': '1920',
                  'height': '1080',
                  'ssl_stream': '1',
                  'c': 'TVHTML5',
                  'cver': '4',
                  'cplayer': 'UNIPLAYER',
                  'cbr': 'Chrome',
                  'cbrver': '40.0.2214.115',
                  'cos': 'Windows',
                  'cosver': '6.1'}
        if self._access_token:
            params['access_token'] = self._access_token
            pass

        url = 'https://www.youtube.com/get_video_info'

        result = requests.get(url, params=params, headers=headers, verify=False, allow_redirects=True)

        stream_list = []

        data = result.text
        params = dict(urlparse.parse_qsl(data))

        if params.get('status', '') == 'fail':
            return self._method_watch(video_id, reason=params.get('reason', 'UNKNOWN'))

        if params.get('live_playback', '0') == '1':
            url = params.get('hlsvp', '')
            if url:
                return self._load_manifest(url, video_id)
            pass

        meta_info = {'video': {},
                     'channel': {},
                     'images': {}}
        meta_info['video']['id'] = params.get('vid', params.get('video_id', ''))
        meta_info['video']['title'] = params.get('title', '').decode('utf-8')
        meta_info['channel']['author'] = params.get('author', '').decode('utf-8')
        meta_info['channel']['id'] = 'UC%s' % params.get('uid', '')
        image_data_list = [
            {'from': 'iurlhq', 'to': 'high'},
            {'from': 'iurlmq', 'to': 'medium'},
            {'from': 'iurlsd', 'to': 'standard'},
            {'from': 'thumbnail_url', 'to': 'default'}]
        for image_data in image_data_list:
            image_url = params.get(image_data['from'], '')
            if image_url:
                meta_info['images'][image_data['to']] = image_url
                pass
            pass

        """
        fmt_list = params.get('fmt_list', '')
        if fmt_list:
            fmt_list = fmt_list.split(',')
            for item in fmt_list:
                data = item.split('/')
                size = data[1].split('x')
                pass
            pass
        """

        # read adaptive_fmts
        """
        adaptive_fmts = params['adaptive_fmts']
        adaptive_fmts = adaptive_fmts.split(',')
        for item in adaptive_fmts:
            stream_map = dict(urlparse.parse_qsl(item))

            if stream_map['itag'] != '140' and stream_map['itag'] != '171':
                video_stream = {'url': stream_map['url'],
                                'yt_format': itag_map[stream_map['itag']]}
                stream_list.append(video_stream)
                pass
            pass
        """

        # extract streams from map
        url_encoded_fmt_stream_map = params.get('url_encoded_fmt_stream_map', '')
        if url_encoded_fmt_stream_map:
            url_encoded_fmt_stream_map = url_encoded_fmt_stream_map.split(',')
            for item in url_encoded_fmt_stream_map:
                stream_map = dict(urlparse.parse_qsl(item))

                url = stream_map.get('url', None)
                conn = stream_map.get('conn', None)
                if url:
                    if 'sig' in stream_map:
                        url += '&signature=%s' % stream_map['sig']
                    elif 's' in stream_map:
                        # fuck!!! in this case we must call the web page
                        return self._method_watch(video_id)

                    itag = stream_map['itag']
                    yt_format = self.FORMAT.get(itag, None)
                    if not yt_format:
                        raise Exception('unknown yt_format for itag "%s"' % itag)

                    if yt_format.get('discontinued', False):
                        continue
                        pass

                    video_stream = {'url': url,
                                    'meta': meta_info}
                    video_stream.update(yt_format)
                    stream_list.append(video_stream)
                    pass
                elif conn:
                    url = '%s?%s' % (conn, urllib.unquote(stream_map['stream']))
                    itag = stream_map['itag']
                    yt_format = self.FORMAT.get(itag, None)
                    if not yt_format:
                        raise Exception('unknown yt_format for itag "%s"' % itag)
                    yt_format['video']['rtmpe'] = True
                    video_stream = {'url': url,
                                    'meta': meta_info}
                    video_stream.update(yt_format)
                    stream_list.append(video_stream)
                    pass
                pass
            pass

        # last fallback
        if not stream_list:
            return self._method_watch(video_id)

        return stream_list

    pass
