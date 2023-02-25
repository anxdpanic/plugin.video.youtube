# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import time
from urllib.parse import parse_qsl

import requests

from ...youtube.youtube_exceptions import InvalidGrant, LoginException
from ...kodion import Context
from .__config__ import api, youtube_tv, developer_keys, keys_changed

context = Context(plugin_id='plugin.video.youtube')


class LoginClient(object):
    api_keys_changed = keys_changed

    CONFIGS = {
        'youtube-tv': {
            'system': 'YouTube TV',
            'key': youtube_tv['key'],
            'id': youtube_tv['id'],
            'secret': youtube_tv['secret']
        },
        'main': {
            'system': 'All',
            'key': api['key'],
            'id': api['id'],
            'secret': api['secret']
        },
        'developer': developer_keys
    }

    def __init__(self, config=None, language='en-US', region='', access_token='', access_token_tv=''):
        self._config = self.CONFIGS['main'] if config is None else config
        self._config_tv = self.CONFIGS['youtube-tv']
        self._verify = context.get_settings().verify_ssl()
        # the default language is always en_US (like YouTube on the WEB)
        if not language:
            language = 'en_US'

        language = language.replace('-', '_')

        self._language = language
        self._region = region
        self._access_token = access_token
        self._access_token_tv = access_token_tv
        self._log_error_callback = None

    def set_log_error(self, callback):
        self._log_error_callback = callback

    def log_error(self, text):
        if self._log_error_callback:
            self._log_error_callback(text)
        else:
            print(text)

    def verify(self):
        return self._verify

    def set_access_token(self, access_token=''):
        self._access_token = access_token

    def set_access_token_tv(self, access_token_tv=''):
        self._access_token_tv = access_token_tv

    def revoke(self, refresh_token):
        # https://developers.google.com/youtube/v3/guides/auth/devices
        headers = {'Host': 'accounts.google.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded'}

        post_data = {'token': refresh_token}

        # url
        url = 'https://accounts.google.com/o/oauth2/revoke'

        result = requests.post(url, data=post_data, headers=headers, verify=self._verify)

        try:
            json_data = result.json()
            if 'error' in json_data:
                context.log_error('Revoke failed: Code: |%s| JSON: |%s|' % (str(result.status_code), json_data))
                json_data.update({'code': str(result.status_code)})
                raise LoginException(json_data)
        except ValueError:
            json_data = None

        if result.status_code != requests.codes.ok:
            response_dump = self._get_response_dump(result, json_data)
            context.log_error('Revoke failed: Code: |%s| Response dump: |%s|' % (str(result.status_code), response_dump))
            raise LoginException('Logout Failed')

    def refresh_token_tv(self, refresh_token):
        client_id = str(self.CONFIGS['youtube-tv']['id'])
        client_secret = str(self.CONFIGS['youtube-tv']['secret'])
        return self.refresh_token(refresh_token, client_id=client_id, client_secret=client_secret)

    def refresh_token(self, refresh_token, client_id='', client_secret=''):
        # https://developers.google.com/youtube/v3/guides/auth/devices
        headers = {'Host': 'www.googleapis.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded'}

        client_id = client_id or self._config['id']
        client_secret = client_secret or self._config['secret']

        post_data = {'client_id': client_id,
                     'client_secret': client_secret,
                     'refresh_token': refresh_token,
                     'grant_type': 'refresh_token'}

        # url
        url = 'https://www.googleapis.com/oauth2/v4/token'

        config_type = self._get_config_type(client_id, client_secret)
        context.log_debug('Refresh token: Config: |%s| Client id [:5]: |%s| Client secret [:5]: |%s|' %
                          (config_type, client_id[:5], client_secret[:5]))

        result = requests.post(url, data=post_data, headers=headers, verify=self._verify)

        try:
            json_data = result.json()
            if 'error' in json_data:
                context.log_error('Refresh Failed: Code: |%s| JSON: |%s|' % (str(result.status_code), json_data))
                json_data.update({'code': str(result.status_code)})
                if json_data['error'] == 'invalid_grant' and json_data['code'] == '400':
                    raise InvalidGrant(json_data)
                raise LoginException(json_data)
        except ValueError:
            json_data = None

        if result.status_code != requests.codes.ok:
            response_dump = self._get_response_dump(result, json_data)
            context.log_error('Refresh failed: Config: |%s| Client id [:5]: |%s| Client secret [:5]: |%s| Code: |%s| Response dump |%s|' %
                              (config_type, client_id[:5], client_secret[:5], str(result.status_code), response_dump))
            raise LoginException('Login Failed')

        if result.headers.get('content-type', '').startswith('application/json'):
            if not json_data:
                json_data = result.json()
            access_token = json_data['access_token']
            expires_in = time.time() + int(json_data.get('expires_in', 3600))
            return access_token, expires_in

        return '', ''

    def request_access_token_tv(self, code, client_id='', client_secret=''):
        client_id = client_id or self.CONFIGS['youtube-tv']['id']
        client_secret = client_secret or self.CONFIGS['youtube-tv']['secret']
        return self.request_access_token(code, client_id=client_id, client_secret=client_secret)

    def request_access_token(self, code, client_id='', client_secret=''):
        # https://developers.google.com/youtube/v3/guides/auth/devices
        headers = {'Host': 'www.googleapis.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded'}

        client_id = client_id or self._config['id']
        client_secret = client_secret or self._config['secret']

        post_data = {'client_id': client_id,
                     'client_secret': client_secret,
                     'code': code,
                     'grant_type': 'http://oauth.net/grant_type/device/1.0'}

        # url
        url = 'https://www.googleapis.com/oauth2/v4/token'

        config_type = self._get_config_type(client_id, client_secret)
        context.log_debug('Requesting access token: Config: |%s| Client id [:5]: |%s| Client secret [:5]: |%s|' %
                          (config_type, client_id[:5], client_secret[:5]))

        result = requests.post(url, data=post_data, headers=headers, verify=self._verify)

        authorization_pending = False
        try:
            json_data = result.json()
            if 'error' in json_data:
                if json_data['error'] != u'authorization_pending':
                    context.log_error('Requesting access token: Code: |%s| JSON: |%s|' % (str(result.status_code), json_data))
                    json_data.update({'code': str(result.status_code)})
                    raise LoginException(json_data)
                else:
                    authorization_pending = True
        except ValueError:
            json_data = None

        if (result.status_code != requests.codes.ok) and not authorization_pending:
            response_dump = self._get_response_dump(result, json_data)
            context.log_error('Requesting access token: Config: |%s| Client id [:5]: |%s| Client secret [:5]: |%s| Code: |%s| Response dump |%s|' %
                              (config_type, client_id[:5], client_secret[:5], str(result.status_code), response_dump))
            raise LoginException('Login Failed: Code %s' % str(result.status_code))

        if result.headers.get('content-type', '').startswith('application/json'):
            if json_data:
                return json_data
            else:
                return result.json()
        else:
            response_dump = self._get_response_dump(result, json_data)
            context.log_error('Requesting access token: Config: |%s| Client id [:5]: |%s| Client secret [:5]: |%s| Code: |%s| Response dump |%s|' %
                              (config_type, client_id[:5], client_secret[:5], str(result.status_code), response_dump))
            raise LoginException('Login Failed: Unknown response')

    def request_device_and_user_code_tv(self):
        client_id = str(self.CONFIGS['youtube-tv']['id'])
        return self.request_device_and_user_code(client_id=client_id)

    def request_device_and_user_code(self, client_id=''):
        # https://developers.google.com/youtube/v3/guides/auth/devices
        headers = {'Host': 'accounts.google.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded'}

        client_id = client_id or self._config['id']

        post_data = {'client_id': client_id,
                     'scope': 'https://www.googleapis.com/auth/youtube'}

        # url
        url = 'https://accounts.google.com/o/oauth2/device/code'

        config_type = self._get_config_type(client_id)
        context.log_debug('Requesting device and user code: Config: |%s| Client id [:5]: |%s|' %
                          (config_type, client_id[:5]))

        result = requests.post(url, data=post_data, headers=headers, verify=self._verify)

        try:
            json_data = result.json()
            if 'error' in json_data:
                context.log_error('Requesting device and user code failed: Code: |%s| JSON: |%s|' % (str(result.status_code), json_data))
                json_data.update({'code': str(result.status_code)})
                raise LoginException(json_data)
        except ValueError:
            json_data = None

        if result.status_code != requests.codes.ok:
            response_dump = self._get_response_dump(result, json_data)
            context.log_error('Requesting device and user code failed: Config: |%s| Client id [:5]: |%s| Code: |%s| Response dump |%s|' %
                              (config_type, client_id[:5], str(result.status_code), response_dump))
            raise LoginException('Login Failed')

        if result.headers.get('content-type', '').startswith('application/json'):
            if json_data:
                return json_data
            else:
                return result.json()
        else:
            response_dump = self._get_response_dump(result, json_data)
            context.log_error('Requesting access token: Config: |%s| Client id [:5]: |%s| Code: |%s| Response dump |%s|' %
                              (config_type, client_id[:5], str(result.status_code), response_dump))
            raise LoginException('Login Failed: Unknown response')

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
                     'service': 'oauth2:https://www.googleapis.com/auth/youtube '
                                'https://www.googleapis.com/auth/youtube.force-ssl '
                                'https://www.googleapis.com/auth/plus.me '
                                'https://www.googleapis.com/auth/emeraldsea.mobileapps.doritos.cookie '
                                'https://www.googleapis.com/auth/plus.stream.read '
                                'https://www.googleapis.com/auth/plus.stream.write '
                                'https://www.googleapis.com/auth/plus.pages.manage '
                                'https://www.googleapis.com/auth/identity.plus.page.impersonation',
                     'source': 'android',
                     'androidId': '38c6ee9a82b8b10a',
                     'app': 'com.google.android.youtube',
                     # 'client_sig': '24bb24c05e47e0aefa68a58a766179d9b613a600',
                     'callerPkg': 'com.google.android.youtube',
                     # 'callerSig': '24bb24c05e47e0aefa68a58a766179d9b613a600',
                     'Passwd': password.encode('utf-8')}

        # url
        url = 'https://android.clients.google.com/auth'

        result = requests.post(url, data=post_data, headers=headers, verify=self._verify)
        if result.status_code != requests.codes.ok:
            raise LoginException('Login Failed')

        lines = result.text.replace('\n', '&')
        params = dict(parse_qsl(lines))
        token = params.get('Auth', '')
        expires = int(params.get('Expiry', -1))
        if not token or expires == -1:
            raise LoginException('Failed to get token')

        return token, expires

    def _get_config_type(self, client_id, client_secret=None):
        """used for logging"""
        if client_secret is None:
            using_conf_tv = (client_id == self.CONFIGS['youtube-tv'].get('id'))
            using_conf_main = (client_id == self.CONFIGS['main'].get('id'))
        else:
            using_conf_tv = ((client_id == self.CONFIGS['youtube-tv'].get('id')) and (client_secret == self.CONFIGS['youtube-tv'].get('secret')))
            using_conf_main = ((client_id == self.CONFIGS['main'].get('id')) and (client_secret == self.CONFIGS['main'].get('secret')))
        if not using_conf_main and not using_conf_tv:
            return 'None'
        elif using_conf_tv:
            return 'YouTube-TV'
        elif using_conf_main:
            return 'YouTube-Kodi'
        else:
            return 'Unknown'

    @staticmethod
    def _get_response_dump(response, json_data=None):
        if json_data:
            return json_data
        else:
            try:
                return response.json()
            except ValueError:
                try:
                    return response.text
                except:
                    return 'None'
