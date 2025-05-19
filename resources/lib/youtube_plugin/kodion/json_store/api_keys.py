# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from base64 import b64decode

from ... import key_sets
from ..constants import DEVELOPER_CONFIGS
from .json_store import JSONStore


class APIKeyStore(JSONStore):
    DOMAIN_SUFFIX = '.apps.googleusercontent.com'

    def __init__(self, context):
        super(APIKeyStore, self).__init__('api_keys.json')
        self._context = context

    def set_defaults(self, reset=False):
        data = {} if reset else self.get_data()
        if 'keys' not in data:
            data = {
                'keys': {
                    'personal': {
                        'api_key': '',
                        'client_id': '',
                        'client_secret': '',
                    },
                    'developer': {},
                },
            }
        else:
            keys = data['keys'] or {}
            if 'personal' not in keys:
                keys['personal'] = {
                    'api_key': '',
                    'client_id': '',
                    'client_secret': '',
                }
            if 'developer' not in keys:
                keys['developer'] = {}
            data['keys'] = keys
        self.save(data)

    @staticmethod
    def get_current_switch():
        return 'own'

    def has_own_api_keys(self):
        api_data = self.get_data()
        try:
            return (api_data['keys']['personal']['api_key']
                    and api_data['keys']['personal']['client_id']
                    and api_data['keys']['personal']['client_secret'])
        except KeyError:
            return False

    def get_api_keys(self, switch):
        api_data = self.get_data()
        if switch == 'developer':
            return api_data['keys'][switch]

        decode = True
        if switch == 'youtube-tv':
            system = 'YouTube TV'
            key_set_details = key_sets[switch]

        elif switch.startswith('own'):
            decode = False
            system = 'All'
            key_set_details = api_data['keys']['personal']

        else:
            system = 'All'
            if switch not in key_sets['provided']:
                switch = 0
            key_set_details = key_sets['provided'][switch]

        key_set = {
            'system': system,
            'id': '',
            'key': '',
            'secret': ''
        }
        for key, value in key_set_details.items():
            if decode:
                value = b64decode(value).decode('utf-8')
            key = key.partition('_')[-1]
            if key and key in key_set:
                key_set[key] = value
        if (key_set['id']
                and not key_set['id'].endswith(self.DOMAIN_SUFFIX)):
            key_set['id'] += self.DOMAIN_SUFFIX
        return key_set

    def get_key_set(self, switch):
        key_set = self.get_api_keys(switch)
        if switch.startswith('own'):
            client_id = key_set['id'].replace(self.DOMAIN_SUFFIX, '')
            if switch == 'own_old':
                client_id += self.DOMAIN_SUFFIX
            key_set['id'] = client_id
        return key_set

    def strip_details(self, api_key, client_id, client_secret):
        stripped_key = ''.join(api_key.split())
        stripped_id = ''.join(client_id.replace(self.DOMAIN_SUFFIX, '').split())
        stripped_secret = ''.join(client_secret.split())

        if api_key != stripped_key:
            if stripped_key not in api_key:
                self._context.log_debug('Personal API key'
                                        ' - skipped (mangled by stripping)')
                return_key = api_key
            else:
                self._context.log_debug('Personal API key'
                                        ' - whitespace removed')
                return_key = stripped_key
        else:
            return_key = api_key

        if client_id != stripped_id:
            if stripped_id not in client_id:
                self._context.log_debug('Personal API client ID'
                                        ' - skipped (mangled by stripping)')
                return_id = client_id
            elif self.DOMAIN_SUFFIX in client_id:
                self._context.log_debug('Personal API client ID'
                                        ' - whitespace and domain removed')
                return_id = stripped_id
            else:
                self._context.log_debug('Personal API client ID'
                                        ' - whitespace removed')
                return_id = stripped_id
        else:
            return_id = client_id

        if client_secret != stripped_secret:
            if stripped_secret not in client_secret:
                self._context.log_debug('Personal API client secret'
                                        ' - skipped (mangled by stripping)')
                return_secret = client_secret
            else:
                self._context.log_debug('Personal API client secret'
                                        ' - whitespace removed')
                return_secret = stripped_secret
        else:
            return_secret = client_secret

        return return_key, return_id, return_secret

    def get_configs(self):
        return {
            'youtube-tv': self.get_api_keys('youtube-tv'),
            'main': self.get_api_keys(self.get_current_switch()),
        }

    def get_developer_config(self, developer_id):
        context = self._context

        developer_configs = self.get_api_keys('developer')
        if developer_id and developer_configs:
            config = developer_configs.get(developer_id)
        else:
            config = context.get_ui().pop_property(DEVELOPER_CONFIGS)
            if config:
                context.log_warning('Storing developer keys in window property'
                                    ' has been deprecated. Please use the'
                                    ' youtube_registration module instead')
                config = self.load_data(config)

        if not config:
            return {}

        if not context.get_settings().allow_dev_keys():
            context.log_debug('Developer config ignored')
            return {}

        origin = config.get('origin', developer_id)
        key_details = config.get('main')
        required_details = {'key', 'id', 'secret'}
        if (not origin
                or not key_details
                or not required_details.issubset(key_details)):
            context.log_error('Invalid developer config: |{config}|'
                              '\n\tExpected: |{{'
                              ' "origin": ADDON_ID,'
                              ' "main": {{'
                              ' "system": SYSTEM_NAME,'
                              ' "key": API_KEY,'
                              ' "id": CLIENT_ID,'
                              ' "secret": CLIENT_SECRET'
                              '}}}}|'
                              .format(config=config))
            return {}

        key_system = key_details.get('system')
        if key_system == 'JSONStore':
            for key in required_details:
                key_details[key] = b64decode(key_details[key]).decode('utf-8')

        context.log_debug('Using developer config'
                          '\n\tOrigin: |{origin}|'
                          '\n\tSystem: |{system}|'
                          .format(origin=origin, system=key_system))

        return {
            'origin': origin,
            'main': {
                'system': key_system,
                'key': key_details['key'],
                'id': key_details['id'],
                'secret': key_details['secret'],
            }
        }
