# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .request_client import YouTubeRequestClient
from ..youtube_exceptions import InvalidGrant, LoginException
from ...kodion import logging


class LoginClient(YouTubeRequestClient):
    log = logging.getLogger(__name__)

    ANDROID_CLIENT_AUTH_URL = 'https://android.clients.google.com/auth'
    DOMAIN_SUFFIX = '.apps.googleusercontent.com'
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
        1: 'user',
        'user': 'user',
    }

    _configs = {
        'user': {},
        'tv': {},
    }
    _access_tokens = {
        'user': None,
        'tv': None,
    }
    _initialised = False
    _logged_in = False

    def __init__(self,
                 configs=None,
                 access_token=None,
                 access_token_tv=None,
                 **kwargs):
        super(LoginClient, self).__init__(exc_type=LoginException, **kwargs)
        LoginClient.init(configs=configs)
        self.set_access_token(tv=access_token_tv, user=access_token)
        self.initialised = any(self._configs.values())

    @classmethod
    def init(cls, configs=None, **_kwargs):
        if configs is not None:
            cls._configs['user'] = configs.get('main')
            cls._configs['tv'] = configs.get('youtube-tv')

    def reinit(self, **kwargs):
        super(LoginClient, self).reinit(**kwargs)
        self.__init__(**kwargs)

    def set_access_token(self, tv=None, user=None):
        cls = type(self)
        if tv is not None:
            cls._access_tokens['tv'] = tv
        if user is not None:
            cls._access_tokens['user'] = user
        self.logged_in = any(self._access_tokens.values())

    @property
    def initialised(self):
        return self._initialised

    @initialised.setter
    def initialised(self, value):
        type(self)._initialised = value

    @property
    def logged_in(self):
        return self._logged_in

    @logged_in.setter
    def logged_in(self, value):
        type(self)._logged_in = value

    @staticmethod
    def _error_hook(**kwargs):
        json_data = getattr(kwargs['exc'], 'json_data', None)
        if not json_data or 'error' not in json_data:
            return None, None, None, None, LoginException
        if json_data['error'] == 'authorization_pending':
            return None, None, None, json_data, False
        if (json_data['error'] == 'invalid_grant'
                and json_data.get('code') == 400):
            return None, None, None, json_data, InvalidGrant(json_data)
        return None, None, None, json_data, LoginException(json_data)

    def revoke(self, refresh_token):
        # https://developers.google.com/youtube/v3/guides/auth/devices
        headers = {'Host': 'accounts.google.com',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                                 ' AppleWebKit/537.36 (KHTML, like Gecko)'
                                 ' Chrome/61.0.3163.100 Safari/537.36',
                   'Content-Type': 'application/x-www-form-urlencoded'}

        post_data = {'token': refresh_token}

        self.request(
            self.REVOKE_URL,
            method='POST',
            data=post_data,
            headers=headers,
            response_hook=self._response_hook_json,
            error_hook=LoginClient._error_hook,
            error_title='Logout failed - Refresh token revocation error',
            raise_exc=True,
        )

    def refresh_token(self, token_type, refresh_token=None):
        login_type = self.TOKEN_TYPES.get(token_type)
        config = self._configs.get(login_type)
        if config:
            client_id = config.get('id')
            client_secret = config.get('secret')
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

        client_id.replace(self.DOMAIN_SUFFIX, '')
        log_info = ('Login type:    {login_type!r}',
                    'client_id:     {client_id!r}',
                    'client_secret: {client_secret!r}')
        log_params = {
            'login_type': login_type,
            'client_id': '...',
            'client_secret': '...',
        }
        if len(client_id) > 11:
            log_params['client_id'] = '...'.join((
                client_id[:3],
                client_id[-5:],
            ))
        if len(client_secret) > 9:
            log_params['client_secret'] = '...'.join((
                client_secret[:3],
                client_secret[-3:],
            ))
        self.log.debug(('Refresh token:',) + log_info, **log_params)

        json_data = self.request(
            self.TOKEN_URL,
            method='POST',
            data=post_data,
            headers=headers,
            response_hook=self._response_hook_json,
            error_hook=LoginClient._error_hook,
            error_title='Login failed - Refresh token grant error',
            error_info=log_info,
            raise_exc=True,
            **log_params
        )
        return json_data

    def request_access_token(self, token_type, code=None):
        login_type = self.TOKEN_TYPES.get(token_type)
        config = self._configs.get(login_type)
        if config:
            client_id = config.get('id')
            client_secret = config.get('secret')
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

        client_id.replace(self.DOMAIN_SUFFIX, '')
        log_info = ('Login type:    {login_type!r}',
                    'client_id:     {client_id!r}',
                    'client_secret: {client_secret!r}')
        log_params = {
            'login_type': login_type,
            'client_id': '...',
            'client_secret': '...',
        }
        if len(client_id) > 11:
            log_params['client_id'] = '...'.join((
                client_id[:3],
                client_id[-5:],
            ))
        if len(client_secret) > 9:
            log_params['client_secret'] = '...'.join((
                client_secret[:3],
                client_secret[-3:],
            ))
        self.log.debug(('Access token request:',) + log_info, **log_params)

        json_data = self.request(
            self.TOKEN_URL,
            method='POST',
            data=post_data,
            headers=headers,
            response_hook=self._response_hook_json,
            error_hook=LoginClient._error_hook,
            error_title='Login failed - Access token request error',
            error_info=log_info,
            raise_exc=True,
            **log_params
        )
        return json_data

    def request_device_and_user_code(self, token_type):
        login_type = self.TOKEN_TYPES.get(token_type)
        config = self._configs.get(login_type)
        if config:
            client_id = config.get('id')
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

        client_id.replace(self.DOMAIN_SUFFIX, '')
        log_info = ('Login type:    {login_type!r}',
                    'client_id:     {client_id!r}')
        log_params = {
            'login_type': login_type,
            'client_id': '...',
        }
        if len(client_id) > 11:
            log_params['client_id'] = '...'.join((
                client_id[:3],
                client_id[-5:],
            ))
        self.log.debug(('Device/user code request:',) + log_info, **log_params)

        json_data = self.request(
            self.DEVICE_CODE_URL,
            method='POST',
            data=post_data,
            headers=headers,
            response_hook=self._response_hook_json,
            error_hook=LoginClient._error_hook,
            error_title='Login failed - Device/user code request error',
            error_info=log_info,
            raise_exc=True,
            **log_params
        )
        return json_data
