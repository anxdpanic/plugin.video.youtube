__author__ = 'bromix'

import xbmcaddon
import time
import urlparse

from random import randint
from resources.lib.kodion import simple_requests as requests
from resources.lib.youtube.youtube_exceptions import LoginException
from resources.lib.youtube.helper.yt_change_api import Change_API

addon = xbmcaddon.Addon()
api = Change_API()
if addon.getSetting('youtube.api.lastused.last_login') == '':
    api.new_login()
    pass

api_last_login = addon.getSetting('youtube.api.lastused.last_login')
api_error = addon.getSetting('youtube.api.lastused.error')
api_secret = api.get_api_secret(api_error, api_last_login)
api_key = api.get_api_key(api_error, api_last_login)
api_id = api.get_api_id(api_error, api_last_login)

# Kodi 17 support by Uukrul

class LoginClient(object):
    CONFIGS = {
         'youtube-tv': {
            'system': 'All',
            'key': 'AIzaSyAd-YEOqZz9nXVzGtn3KWzYLbLaajhqIDA',
            'id': '861556708454-d6dlm3lh05idd8npek18k6be8ba3oc68.apps.googleusercontent.com',
            'secret': 'SboVhoG9s0rNafixCSGGKXAT'
        },
        # API KEY for search and channel infos. These should work most of the time without login to safe some quota
        'youtube-for-kodi-quota': {
            'token-allowed': False,
            'system': 'All',
            'key': '%s' % api_key,
            'id': '%s.apps.googleusercontent.com' % api_id,
            'secret': '%s' % api_secret
        },
        'youtube-for-kodi-fallback': {
            'token-allowed': False,
            'system': 'Fallback!',
            'key': '%s' % api_key,
            'id': '%s.apps.googleusercontent.com' % api_id,
            'secret': '%s' % api_secret
        },
        'youtube-for-kodi-12': {
            'system': 'Frodo',
            'key': '%s' % api_key,
            'id': '%s.apps.googleusercontent.com' % api_id,
            'secret': '%s' % api_secret
        },
        'youtube-for-kodi-13': {
            'system': 'Gotham',
            'key': '%s' % api_key,
            'id': '%s.apps.googleusercontent.com' % api_id,
            'secret': '%s' % api_secret
        },
        'youtube-for-kodi-14': {
            'system': 'Helix',
            'key': '%s' % api_key,
            'id': '%s.apps.googleusercontent.com' % api_id,
            'secret': '%s' % api_secret
        },
        'youtube-for-kodi-15': {
            'system': 'Isengard',
            'key': '%s' % api_key,
            'id': '%s.apps.googleusercontent.com' % api_id,
            'secret': '%s' % api_secret
        },
        'youtube-for-kodi-16': {
            'system': 'Jarvis',
            'key': '%s' % api_key,
            'id': '%s.apps.googleusercontent.com' % api_id,
            'secret': '%s' % api_secret
        },
            'youtube-for-kodi-17': {
            'system': 'Krypton',
            'key': '%s' % api_key,
            'id': '%s.apps.googleusercontent.com' % api_id,
            'secret': '%s' % api_secret
        }
    }
    
    def __init__(self, config={}, language='en-US', region='', access_token='', access_token_tv=''):
       
        if not config:
            config = self.CONFIGS['youtube-for-kodi-fallback']
            pass

        self._config = config
        self._config_tv = self.CONFIGS['youtube-tv']

        # the default language is always en_US (like YouTube on the WEB)
        if not language:
            language = 'en_US'
            pass

        language = language.replace('-', '_')

        self._language = language
        self._region = region
        self._access_token = access_token
        self._access_token_tv = access_token_tv
        self._log_error_callback = None
        pass

    def set_log_error(self, callback):
        self._log_error_callback = callback
        pass

    def log_error(self, text):
        if self._log_error_callback:
            self._log_error_callback(text)
            pass
        else:
            print text
            pass
        pass

    def revoke(self, refresh_token, context):
        headers = {'Host': 'www.youtube.com',
                   'Connection': 'keep-alive',
                   'Origin': 'https://www.youtube.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.28 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com/tv',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

        post_data = {'token': refresh_token}

        # url
        url = 'https://www.youtube.com/o/oauth2/revoke'

        result = requests.post(url, data=post_data, headers=headers, verify=False)
        if result.status_code != requests.codes.ok:
            context.log_debug('Request answer: %s' % result.text)
            raise LoginException('Logout Failed')

        pass

    def refresh_token_tv(self, refresh_token, grant_type=''):
        client_id = self.CONFIGS['youtube-tv']['id']
        client_secret = self.CONFIGS['youtube-tv']['secret']
        return self.refresh_token(refresh_token, client_id=client_id, client_secret=client_secret,
                                  grant_type=grant_type)

    def refresh_token(self, refresh_token, client_id='', client_secret='', grant_type=''):
        headers = {'Host': 'www.youtube.com',
                   'Connection': 'keep-alive',
                   'Origin': 'https://www.youtube.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.28 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com/tv',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

        _client_id = client_id
        if not client_id:
            _client_id = self._config['id']
            pass
        _client_secret = client_secret
        if not _client_secret:
            _client_secret = self._config['secret']
            pass
        post_data = {'client_id': _client_id,
                     'client_secret': _client_secret,
                     'refresh_token': refresh_token,
                     'grant_type': 'refresh_token'}

        # url
        url = 'https://www.youtube.com/o/oauth2/token'

        result = requests.post(url, data=post_data, headers=headers, verify=False)
        if result.status_code != requests.codes.ok:
            raise LoginException('Login Failed')

        if result.headers.get('content-type', '').startswith('application/json'):
            json_data = result.json()
            access_token = json_data['access_token']
            expires_in = time.time() + int(json_data.get('expires_in', 3600))
            return access_token, expires_in

        return '', ''

    def get_device_token_tv(self, code, context, client_id='', client_secret='', grant_type=''):
        client_id = self.CONFIGS['youtube-tv']['id']
        client_secret = self.CONFIGS['youtube-tv']['secret']
        return self.get_device_token(code, context, client_id=client_id, client_secret=client_secret, grant_type=grant_type)

    def get_device_token(self, code, context, client_id='', client_secret='', grant_type=''):
        headers = {'Host': 'www.youtube.com',
                   'Connection': 'keep-alive',
                   'Origin': 'https://www.youtube.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.28 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com/tv',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

        _client_id = client_id
        if not client_id:
            _client_id = self._config['id']
            pass
        _client_secret = client_secret
        if not _client_secret:
            _client_secret = self._config['secret']
            pass
        post_data = {'client_id': _client_id,
                     'client_secret': _client_secret,
                     'code': code,
                     'grant_type': 'http://oauth.net/grant_type/device/1.0'}

        # url
        url = 'https://www.youtube.com/o/oauth2/token'

        result = requests.post(url, data=post_data, headers=headers, verify=False)
        if result.status_code != requests.codes.ok:
            context.log_debug('Request answer: %s' % result.text)
            raise LoginException('Login Failed')

        if result.headers.get('content-type', '').startswith('application/json'):
            return result.json()

        return None

    def generate_user_code_tv(self, context):
        client_id = self.CONFIGS['youtube-tv']['id']
        return self.generate_user_code(context, client_id=client_id)

    def generate_user_code(self, context, client_id=''):
        headers = {'Host': 'www.youtube.com',
                   'Connection': 'keep-alive',
                   'Origin': 'https://www.youtube.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.28 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                   'Accept': '*/*',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com/tv',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

        _client_id = client_id
        if not client_id:
            _client_id = self._config['id']
        post_data = {'client_id': _client_id,
                     'scope': 'https://www.googleapis.com/auth/youtube'}
        # 'scope': 'http://gdata.youtube.com https://www.googleapis.com/auth/youtube-paid-content'}

        # url
        url = 'https://www.youtube.com/o/oauth2/device/code'

        result = requests.post(url, data=post_data, headers=headers, verify=False)
        if result.status_code != requests.codes.ok:
            context.log_debug('Request answer: %s' % result.text)
            raise LoginException('Login Failed')

        if result.headers.get('content-type', '').startswith('application/json'):
            return result.json()

        return None

    def get_access_token(self):
        return self._access_token

    def authenticate(self, username, password):
        headers = {'device': '38c6ee9a82b8b10a',
                   'app': 'com.google.android.youtube',
                   'User-Agent': 'GoogleAuth/1.4 (GT-I9100 KTU84Q)',
                   'content-type': 'application/x-www-form-urlencoded',
                   'Host': 'android.clients.google.com',
                   'Connection': 'Keep-Alive',
                   'Accept-Encoding': 'gzip'}

        post_data = {'device_country': self._region.lower(),
                     'operatorCountry': self._region.lower(),
                     'lang': self._language.replace('-', '_'),
                     'sdk_version': '19',
                     # 'google_play_services_version': '6188034',
                     'accountType': 'HOSTED_OR_GOOGLE',
                     'Email': username.encode('utf-8'),
                     'service': 'oauth2:https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtube.force-ssl https://www.googleapis.com/auth/plus.me https://www.googleapis.com/auth/emeraldsea.mobileapps.doritos.cookie https://www.googleapis.com/auth/plus.stream.read https://www.googleapis.com/auth/plus.stream.write https://www.googleapis.com/auth/plus.pages.manage https://www.googleapis.com/auth/identity.plus.page.impersonation',
                     'source': 'android',
                     'androidId': '38c6ee9a82b8b10a',
                     'app': 'com.google.android.youtube',
                     # 'client_sig': '24bb24c05e47e0aefa68a58a766179d9b613a600',
                     'callerPkg': 'com.google.android.youtube',
                     # 'callerSig': '24bb24c05e47e0aefa68a58a766179d9b613a600',
                     'Passwd': password.encode('utf-8')}

        # url
        url = 'https://android.clients.google.com/auth'

        result = requests.post(url, data=post_data, headers=headers, verify=False)
        if result.status_code != requests.codes.ok:
            raise LoginException('Login Failed')

        lines = result.text.replace('\n', '&')
        params = dict(urlparse.parse_qsl(lines))
        token = params.get('Auth', '')
        expires = int(params.get('Expiry', -1))
        if not token or expires == -1:
            raise LoginException('Failed to get token')

        return token, expires

    pass
