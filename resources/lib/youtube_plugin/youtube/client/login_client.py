# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .request_client import YouTubeRequestClient
from ..youtube_exceptions import (
    InvalidGrant,
    InvalidJSON,
    LoginException,
)


class LoginClient(YouTubeRequestClient):
    ANDROID_CLIENT_AUTH_URL = 'https://android.clients.google.com/auth'
    DEVICE_CODE_URL = 'https://accounts.google.com/o/oauth2/device/code'
    REVOKE_URL = 'https://accounts.google.com/o/oauth2/revoke'
    SERVICE_URLS = 'oauth2:' + 'https://www.googleapis.com/auth/'.join((
        'youtube '
        'youtube.force-ssl '
        'plus.me '
        'emeraldsea.mobileapps.doritos.cookie '
        'plus.stream.read '
        'plus.stream.write '
        'plus.pages.manage '
        'identity.plus.page.impersonation',
    ))
    TOKEN_URL = 'https://www.googleapis.com/oauth2/v4/token'
    TOKEN_TYPES = {
        0: 'tv',
        'tv': 'tv',
        1: 'personal',
        'personal': 'personal',
    }

    def __init__(self,
                 configs=None,
                 access_token='',
                 access_token_tv='',
                 **kwargs):
        if not configs:
            configs = {}
        self._config = configs.get('main') or {}
        self._config_tv = configs.get('youtube-tv') or {}

        self._access_token = access_token
        self._access_token_tv = access_token_tv

        super(LoginClient, self).__init__(exc_type=LoginException, **kwargs)

    @staticmethod
    def _response_hook(**kwargs):
        response = kwargs['response']
        try:
            json_data = response.json()
            if 'error' in json_data:
                json_data.setdefault('code', response.status_code)
                raise LoginException('"error" in response JSON data',
                                     json_data=json_data,
                                     response=response)
        except ValueError as exc:
            raise InvalidJSON(exc, response=response)
        response.raise_for_status()
        return json_data

    @staticmethod
    def _error_hook(**kwargs):
        json_data = getattr(kwargs['exc'], 'json_data', None)
        if not json_data or 'error' not in json_data:
            return None, None, None, None, None, LoginException
        if json_data['error'] == 'authorization_pending':
            return None, None, None, json_data, False, False
        if (json_data['error'] == 'invalid_grant'
                and json_data.get('code') == 400):
            return None, None, None, json_data, False, InvalidGrant(json_data)
        return None, None, None, json_data, False, LoginException(json_data)

    def set_access_token(self, personal=None, tv=None):
        if personal is not None:
            self._access_token = personal
        if tv is not None:
            self._access_token_tv = tv

    def revoke(self, refresh_token):
        # https://developers.google.com/youtube/v3/guides/auth/devices
        headers = {'Host': 'accounts.google.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                                 ' AppleWebKit/537.36 (KHTML, like Gecko)'
                                 ' Chrome/61.0.3163.100 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded'}

        post_data = {'token': refresh_token}

        self.request(self.REVOKE_URL,
                     method='POST',
                     data=post_data,
                     headers=headers,
                     response_hook=LoginClient._response_hook,
                     error_hook=LoginClient._error_hook,
                     error_title='Logout Failed',
                     error_info=('Revoke - Failed'
                                 '\n\tException: {exc!r}'),
                     raise_exc=True)

    def refresh_token(self, token_type, refresh_token=None):
        login_type = self.TOKEN_TYPES.get(token_type)
        if login_type == 'tv':
            client_id = self._config_tv.get('id')
            client_secret = self._config_tv.get('secret')
        elif login_type == 'personal':
            client_id = self._config.get('id')
            client_secret = self._config.get('secret')
        else:
            return None
        if not client_id or not client_secret or not refresh_token:
            return None

        # https://developers.google.com/youtube/v3/guides/auth/devices
        headers = {'Host': 'www.googleapis.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                                 ' AppleWebKit/537.36 (KHTML, like Gecko)'
                                 ' Chrome/61.0.3163.100 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded'}

        post_data = {'client_id': client_id,
                     'client_secret': client_secret,
                     'refresh_token': refresh_token,
                     'grant_type': 'refresh_token'}

        config_type = self._get_config_type(client_id, client_secret)
        client = (('\n\tconfig_type:   |{config_type}|'
                   '\n\tclient_id:     |{id_start}...{id_end}|'
                   '\n\tclient_secret: |{secret_start}...{secret_end}|')
                  .format(config_type=config_type,
                          id_start=client_id[:3],
                          id_end=client_id[-5:],
                          secret_start=client_secret[:3],
                          secret_end=client_secret[-3:]))
        self.log_debug('Refresh token:{0}'.format(client))

        json_data = self.request(self.TOKEN_URL,
                                 method='POST',
                                 data=post_data,
                                 headers=headers,
                                 response_hook=LoginClient._response_hook,
                                 error_hook=LoginClient._error_hook,
                                 error_title='Login Failed',
                                 error_info=('Refresh token - Failed'
                                             '\n\tException: {{exc!r}}'
                                             '{client}'
                                             .format(client=client)),
                                 raise_exc=True)
        return json_data

    def request_access_token(self, token_type, code=None):
        login_type = self.TOKEN_TYPES.get(token_type)
        if login_type == 'tv':
            client_id = self._config_tv.get('id')
            client_secret = self._config_tv.get('secret')
        elif login_type == 'personal':
            client_id = self._config.get('id')
            client_secret = self._config.get('secret')
        else:
            return None
        if not client_id or not client_secret or not code:
            return None

        # https://developers.google.com/youtube/v3/guides/auth/devices
        headers = {'Host': 'www.googleapis.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                                 ' AppleWebKit/537.36 (KHTML, like Gecko)'
                                 ' Chrome/61.0.3163.100 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded'}

        post_data = {'client_id': client_id,
                     'client_secret': client_secret,
                     'code': code,
                     'grant_type': 'http://oauth.net/grant_type/device/1.0'}

        config_type = self._get_config_type(client_id, client_secret)
        client = (('\n\tconfig_type:   |{config_type}|'
                   '\n\tclient_id:     |{id_start}...{id_end}|'
                   '\n\tclient_secret: |{secret_start}...{secret_end}|')
                  .format(config_type=config_type,
                          id_start=client_id[:3],
                          id_end=client_id[-5:],
                          secret_start=client_secret[:3],
                          secret_end=client_secret[-3:]))
        self.log_debug('Requesting access token:{0}'.format(client))

        json_data = self.request(self.TOKEN_URL,
                                 method='POST',
                                 data=post_data,
                                 headers=headers,
                                 response_hook=LoginClient._response_hook,
                                 error_hook=LoginClient._error_hook,
                                 error_title='Login Failed: Unknown response',
                                 error_info=('Access token request - Failed'
                                             '\n\tException: {{exc!r}}'
                                             '{client}'
                                             .format(client=client)),
                                 raise_exc=True)
        return json_data

    def request_device_and_user_code(self, token_type):
        login_type = self.TOKEN_TYPES.get(token_type)
        if login_type == 'tv':
            client_id = self._config_tv.get('id')
        elif login_type == 'personal':
            client_id = self._config.get('id')
        else:
            return None
        if not client_id:
            return None

        # https://developers.google.com/youtube/v3/guides/auth/devices
        headers = {'Host': 'accounts.google.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                                 ' AppleWebKit/537.36 (KHTML, like Gecko)'
                                 ' Chrome/61.0.3163.100 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded'}

        post_data = {'client_id': client_id,
                     'scope': 'https://www.googleapis.com/auth/youtube'}

        config_type = self._get_config_type(client_id)
        client = (('\n\tconfig_type: |{config_type}|'
                   '\n\tclient_id:   |{id_start}...{id_end}|')
                  .format(config_type=config_type,
                          id_start=client_id[:3],
                          id_end=client_id[-5:]))
        self.log_debug('Requesting device and user code:{0}'.format(client))

        json_data = self.request(self.DEVICE_CODE_URL,
                                 method='POST',
                                 data=post_data,
                                 headers=headers,
                                 response_hook=LoginClient._response_hook,
                                 error_hook=LoginClient._error_hook,
                                 error_title='Login Failed: Unknown response',
                                 error_info=('Device/user code request - Failed'
                                             '\n\tException: {{exc!r}}'
                                             '{client}'
                                             .format(client=client)),
                                 raise_exc=True)
        return json_data

    def _get_config_type(self, client_id, client_secret=None):
        """used for logging"""
        if client_secret is None:
            config_id = self._config_tv.get('id')
            using_conf_tv = config_id and client_id == config_id
            config_id = self._config.get('id')
            using_conf_main = config_id and client_id == config_id
        else:
            config_secret = self._config_tv.get('secret')
            config_id = self._config_tv.get('id')
            using_conf_tv = (
                    config_secret and client_secret == config_secret
                    and config_id and client_id == config_id
            )
            config_secret = self._config.get('secret')
            config_id = self._config.get('id')
            using_conf_main = (
                    config_secret and client_secret == config_secret
                    and config_id and client_id == config_id
            )

        if not using_conf_main and not using_conf_tv:
            return 'None'
        if using_conf_tv:
            return 'YouTube-TV'
        if using_conf_main:
            return 'YouTube-Kodi'
        return 'Unknown'
