# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""InnerTube API access.

Browsing (guide, browse, search, next) uses the TVHTML5 client, the same client youtube.com/tv
uses, so menus and shelves match the TV app. The TVHTML5 player needs the player JavaScript to
decipher stream URLs, so streams come from clients that return direct URLs.
"""
import json
import random
import string
import time

from . import auth, http, kodi

API = 'https://www.youtube.com/youtubei/v1/'
# The same API as the mobile apps reach it. Tested 2026-11-21: 2 x 40 watch page requests at once, all
# answered in about 3 s each, where www.youtube.com answers bursts with its automated-queries page.
APPS_API = 'https://youtubei.googleapis.com/youtubei/v1/'
ABOUT_PARAMS = 'EgVhYm91dPIGBAoCEgA='  # a channel's About tab

TV = {
    'key': 'tv',
    'id': 7,
    'context': {'clientName': 'TVHTML5', 'clientVersion': '7.20260707.07.00',
                'platform': 'TV', 'clientFormFactor': 'UNKNOWN_FORM_FACTOR'},
    'ua': 'Mozilla/5.0 (ChromiumStylePlatform) Cobalt/25.lts.30.1034943-gold (unlike Gecko), '
          'Unknown_TV_Unknown_0/Unknown (Unknown, Unknown)',
    'referer': 'https://www.youtube.com/tv',
}

# Player clients tried in order. Each returned direct, non-ciphered adaptive URLs (up to
# 2160p VP9/AV1) and HLS for live streams when probed on 2026-11-19.
PLAYER_CLIENTS = [
    {
        'key': 'visionos',
        'id': 101,
        'context': {'clientName': 'VISIONOS', 'clientVersion': '1.02', 'deviceMake': 'Apple',
                    'deviceModel': 'RealityDevice17,1', 'osName': 'visionOS',
                    'osVersion': '26.5.23O471'},
        'ua': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 15_7_3) AppleWebKit/605.1.15 '
              '(KHTML, like Gecko) Version/26.0 Safari/605.1.15',
    },
    {
        'key': 'ios',
        'id': 5,
        'context': {'clientName': 'IOS', 'clientVersion': '20.20.7', 'deviceMake': 'Apple',
                    'deviceModel': 'iPhone16,2', 'osName': 'iPhone', 'osVersion': '18.5.0.22F76'},
        'ua': 'com.google.ios.youtube/20.20.7 (iPhone16,2; U; CPU iOS 18_5_0 like Mac OS X;)',
        'params': '2AMB',
    },
    {
        'key': 'android',
        'id': 3,
        'context': {'clientName': 'ANDROID', 'clientVersion': '20.10.38', 'androidSdkVersion': 32,
                    'osName': 'Android', 'osVersion': '15'},
        'ua': 'com.google.android.youtube/20.10.38 (Linux; U; Android 15) gzip',
        'params': '2AMB',
    },
]

VISITOR_TTL = 86400 * 3
RETRY_STATUSES = (0, 403, 429, 500, 502, 503, 504)
RETRY_DELAY = 1.5  # seconds


class InnerTubeError(Exception):
    """status is the HTTP status (0 when YouTube couldn't be reached, None when not an HTTP failure)."""

    def __init__(self, message, status=None, blocked=False):
        Exception.__init__(self, message)
        self.status = status
        self.blocked = blocked


class InnerTube:
    def __init__(self, priority=http.FOREGROUND):
        """priority: http.BACKGROUND for work nobody is waiting on (banners, history), which the request
        broker runs after what's on screen and drops while YouTube is holding requests back."""
        self.priority = priority
        self.hl, self.gl = kodi.language()
        self._state = kodi.load_json('state.json', {})

    # ----------------------------------------------------------------- session
    def visitor_data(self, refresh=False):
        visitor = self._state.get('visitor')
        if not refresh and visitor and time.time() - visitor.get('ts', 0) < VISITOR_TTL:
            return visitor['data']
        resp = self._post('guide', {}, TV, use_auth=False, visitor=False)
        data = resp.get('responseContext', {}).get('visitorData')
        if data:
            self._state = kodi.load_json('state.json', {})
            self._state['visitor'] = {'data': data, 'ts': time.time()}
            kodi.save_json('state.json', self._state)
        return data

    @staticmethod
    def signed_in():
        return auth.active_account()[0] is not None

    def _post(self, endpoint, body, client, use_auth=True, visitor=True, retry=True, api=API):
        context_client = dict(client['context'], hl=self.hl, gl=self.gl, userAgent=client['ua'])
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': client['ua'],
            'Origin': 'https://www.youtube.com',
            'X-YouTube-Client-Name': str(client['id']),
            'X-YouTube-Client-Version': client['context']['clientVersion'],
        }
        if client.get('referer'):
            headers['Referer'] = client['referer']
        if visitor:
            visitor_data = self.visitor_data()
            if visitor_data:
                context_client['visitorData'] = visitor_data
                headers['X-Goog-Visitor-Id'] = visitor_data
        token = None
        if use_auth:
            try:
                token = auth.access_token()
            except auth.AuthError:
                token = None
            if token:
                headers['Authorization'] = 'Bearer ' + token
        payload = dict(body)
        payload['context'] = {'client': context_client, 'user': {'lockedSafetyMode': False},
                              'request': {'useSsl': True}}
        url = api + endpoint + '?prettyPrint=false'
        kodi.log('POST %s (%s%s)' % (endpoint, client['key'], ', auth' if token else ''))
        try:
            return http.request_json(url, data=json.dumps(payload).encode('utf-8'), headers=headers,
                                     priority=self.priority)
        except http.HTTPError as exc:
            if exc.blocked:
                # Google's automated-queries page: the broker already waited out a hold and tried again.
                raise InnerTubeError('YouTube is holding requests back', exc.status, blocked=True) from exc
            if exc.status == 401 and token and retry:
                auth.access_token(force_refresh=True)
                return self._post(endpoint, body, client, use_auth, visitor, retry=False)
            if exc.status in RETRY_STATUSES and retry:
                # Google turns some requests away briefly (403/429, the odd 5xx or dropped connection);
                # the same request usually succeeds a moment later. A 403 can also mean the visitor
                # id went stale, so fetch a fresh one first.
                kodi.log('HTTP %s on %s, retrying once' % (exc.status, endpoint))
                time.sleep(RETRY_DELAY)
                if exc.status == 403 and visitor:
                    try:
                        self.visitor_data(refresh=True)
                    except InnerTubeError:
                        pass
                return self._post(endpoint, body, client, use_auth, visitor, retry=False)
            message = exc.json().get('error', {}).get('message') or str(exc)
            raise InnerTubeError(message, exc.status) from exc

    # ------------------------------------------------------------- browsing
    def guide(self):
        return self._post('guide', {}, TV)

    def browse(self, browse_id=None, params=None, continuation=None, api=API):
        body = {}
        if continuation:
            body['continuation'] = continuation
        else:
            body['browseId'] = browse_id
            if params:
                body['params'] = params
        return self._post('browse', body, TV, api=api)

    def search(self, query=None, params=None, continuation=None):
        body = {'continuation': continuation} if continuation else {'query': query}
        if params and not continuation:
            body['params'] = params
        return self._post('search', body, TV)

    def channel_about(self, channel_id):
        """A channel's About tab as the visionOS app gets it: about 15 KB with the channel's banners, where
        the TV client's channel page is 0.4-1 MB."""
        body = {'browseId': channel_id, 'params': ABOUT_PARAMS}
        return self._post('browse', body, PLAYER_CLIENTS[0], use_auth=False, api=APPS_API)

    def watch_page(self, video_id):
        """The watch page as the visionOS app gets it: unlike the TV client's, it carries the description,
        like count and subscribers, in a small response."""
        body = {'videoId': video_id, 'racyCheckOk': True, 'contentCheckOk': True}
        return self._post('next', body, PLAYER_CLIENTS[0], use_auth=False, api=APPS_API)

    def next(self, video_id=None, playlist_id=None, params=None, continuation=None):
        if continuation:
            body = {'continuation': continuation}
        else:
            body = {'racyCheckOk': True, 'contentCheckOk': True}
            if video_id:
                body['videoId'] = video_id
            if playlist_id:
                body['playlistId'] = playlist_id
            if params:
                body['params'] = params
        return self._post('next', body, TV)

    def shorts(self, params='CA8='):
        """The Shorts feed as the TV app's Shorts button opens it: [(video_id, thumb), ...]."""
        first = self._post('reel/reel_item_watch', {'params': params,
                                                    'inputType': 'REEL_WATCH_INPUT_TYPE_SEEDLESS'}, TV)
        videos = []
        replacement = first.get('replacementEndpoint', {}).get('reelWatchEndpoint', {})
        if replacement.get('videoId'):
            videos.append((replacement['videoId'], _thumb(replacement)))
        token = first.get('sequenceContinuation')
        if token:
            seq = self._post('reel/reel_watch_sequence', {'sequenceParams': token}, TV)
            for entry in seq.get('entries', []):
                endpoint = entry.get('command', {}).get('reelWatchEndpoint', {})
                if endpoint.get('videoId') and all(v[0] != endpoint['videoId'] for v in videos):
                    videos.append((endpoint['videoId'], _thumb(endpoint)))
        return videos

    def account_name(self):
        """Display name of the signed-in account (from the TV account switcher)."""
        try:
            resp = self._post('account/accounts_list', {}, TV)
        except InnerTubeError:
            return None
        names = []

        def walk(node):
            if isinstance(node, dict):
                item = node.get('accountItem') or node.get('accountItemRenderer')
                if isinstance(item, dict):
                    name = _text(item.get('accountName'))
                    handle = _text(item.get('channelHandle') or item.get('accountByline'))
                    if name:
                        names.append((item.get('isSelected', False), name, handle))
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(resp)
        if not names:
            return None
        names.sort(key=lambda x: not x[0])
        selected, name, handle = names[0]
        return '%s (%s)' % (name, handle) if handle and handle != name else name

    # -------------------------------------------------------------- player
    def player_tracking(self, video_id):
        """The TV client's player response for the signed-in account. Its streams need signature
        solving and go unused, but its stats URLs are the ones YouTube counts towards history."""
        return self._post('player', {'videoId': video_id, 'contentCheckOk': True, 'racyCheckOk': True}, TV)

    def player(self, video_id):
        """Returns (player_response, client). Raises InnerTubeError when nothing is playable."""
        cpn = ''.join(random.choice(string.ascii_letters + string.digits + '-_') for _ in range(16))
        reason = None
        for client in PLAYER_CLIENTS:
            body = {
                'videoId': video_id,
                'cpn': cpn,
                'contentCheckOk': True,
                'racyCheckOk': True,
                'playbackContext': {'contentPlaybackContext': {'html5Preference': 'HTML5_PREF_WANTS'}},
            }
            if client.get('params'):
                body['params'] = client['params']
            try:
                resp = self._post('player', body, client, use_auth=False)
            except InnerTubeError as exc:
                reason = str(exc)
                continue
            status = resp.get('playabilityStatus', {})
            data = resp.get('streamingData', {})
            direct = [f for f in data.get('adaptiveFormats', []) if f.get('url')]
            if status.get('status') == 'OK' and (direct or data.get('hlsManifestUrl')):
                kodi.log('player: %s ok (%d direct formats, hls=%s)'
                         % (client['key'], len(direct), bool(data.get('hlsManifestUrl'))))
                return resp, client
            reason = status.get('reason') or _text(
                status.get('errorScreen', {}).get('playerErrorMessageRenderer', {}).get('subreason')) \
                or status.get('status')
            kodi.log('player: %s gave %s (%s)' % (client['key'], status.get('status'), reason))
            if status.get('status') == 'LOGIN_REQUIRED' and 'bot' in (reason or ''):
                self.visitor_data(refresh=True)
        raise InnerTubeError(reason or 'unplayable')


def _thumb(endpoint):
    thumbs = endpoint.get('thumbnail', {}).get('thumbnails', [])
    if thumbs:
        return thumbs[-1].get('url', '')
    return 'https://i.ytimg.com/vi/%s/oar2.jpg' % endpoint.get('videoId')


def _text(node):
    if not node:
        return ''
    if isinstance(node, str):
        return node
    if 'simpleText' in node:
        return node['simpleText']
    if 'runs' in node:
        return ''.join(run.get('text', '') for run in node['runs'])
    if 'content' in node:
        return node['content']
    return ''
