# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from base64 import b64decode, b64encode

from .json_store import JSONStore
from .. import logging
from ..constants import DEVELOPER_CONFIGS
from ... import key_sets


class APIKeyStore(JSONStore):
    log = logging.getLogger(__name__)

    DOMAIN_SUFFIX = '.apps.googleusercontent.com'

    def __init__(self, context):
        super(APIKeyStore, self).__init__('api_keys.json', context)

    def set_defaults(self, reset=False):
        data = {} if reset else self.get_data()

        if 'keys' not in data:
            data = {
                'keys': {
                    'user': {
                        'api_key': '',
                        'client_id': '',
                        'client_secret': '',
                    },
                    'developer': {},
                },
            }
        else:
            keys = data['keys'] or {}
            if 'user' not in keys:
                keys['user'] = keys.pop('personal', {
                    'api_key': '',
                    'client_id': '',
                    'client_secret': '',
                })
            if 'developer' not in keys:
                keys['developer'] = {}
            data['keys'] = keys

        self.save(data)

    @staticmethod
    def get_current_switch():
        return 'user'

    def has_user_api_keys(self):
        api_data = self.get_data()
        try:
            return (api_data['keys']['user']['api_key']
                    and api_data['keys']['user']['client_id']
                    and api_data['keys']['user']['client_secret'])
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

        elif switch == 'youtube-vr':
            system = 'YouTube VR'
            key_set_details = key_sets[switch]

        elif switch.startswith('user'):
            decode = False
            system = 'All'
            key_set_details = api_data['keys']['user']

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
        if switch.startswith('user'):
            client_id = key_set['id'].replace(self.DOMAIN_SUFFIX, '')
            if switch == 'user_old':
                client_id += self.DOMAIN_SUFFIX
            key_set['id'] = client_id
        return key_set

    def strip_details(self, api_key, client_id, client_secret):
        stripped_key = ''.join(api_key.split())
        stripped_id = ''.join(client_id.replace(self.DOMAIN_SUFFIX, '').split())
        stripped_secret = ''.join(client_secret.split())

        if api_key != stripped_key:
            if stripped_key not in api_key:
                self.log.debug('Personal API key'
                               ' - skipped (mangled by stripping)')
                return_key = api_key
            else:
                self.log.debug('Personal API key'
                               ' - whitespace removed')
                return_key = stripped_key
        else:
            return_key = api_key

        if client_id != stripped_id:
            if stripped_id not in client_id:
                self.log.debug('Personal API client ID'
                               ' - skipped (mangled by stripping)')
                return_id = client_id
            elif self.DOMAIN_SUFFIX in client_id:
                self.log.debug('Personal API client ID'
                               ' - whitespace and domain removed')
                return_id = stripped_id
            else:
                self.log.debug('Personal API client ID'
                               ' - whitespace removed')
                return_id = stripped_id
        else:
            return_id = client_id

        if client_secret != stripped_secret:
            if stripped_secret not in client_secret:
                self.log.debug('Personal API client secret'
                               ' - skipped (mangled by stripping)')
                return_secret = client_secret
            else:
                self.log.debug('Personal API client secret'
                               ' - whitespace removed')
                return_secret = stripped_secret
        else:
            return_secret = client_secret

        return return_key, return_id, return_secret

    def get_configs(self):
        return {
            'tv': self.get_api_keys('youtube-tv'),
            'user': self.get_api_keys(self.get_current_switch()),
            'vr': self.get_api_keys('youtube-vr'),
            'dev': self.get_api_keys('developer'),
        }

    def get_developer_config(self, developer_id):
        context = self._context

        developer_configs = self.get_api_keys('developer')
        if developer_id and developer_configs:
            config = developer_configs.get(developer_id)
        else:
            config = context.get_ui().pop_property(DEVELOPER_CONFIGS)
            if config:
                self.log.warning('Storing developer keys in window property'
                                 ' has been deprecated. Please use the'
                                 ' youtube_registration module instead')
                config = self.load_data(config)

        if not config:
            return {}

        if not context.get_settings().allow_dev_keys():
            self.log.debug('Developer config ignored')
            return {}

        origin = config.get('origin', developer_id)
        key_details = config.get(origin)
        required_details = {'key', 'id', 'secret'}
        if (not origin
                or not key_details
                or not required_details.issubset(key_details)):
            self.log.error_trace(('Invalid developer config: {config!r}',
                                  'Expected: {{',
                                  '    "origin": ADDON_ID,',
                                  '    ADDON_ID: {{',
                                  '        "system": SYSTEM_NAME,',
                                  '        "key": API_KEY,',
                                  '        "id": CLIENT_ID,',
                                  '        "secret": CLIENT_SECRET',
                                  '    }},',
                                  '}}'),
                                 config=config)
            return {}

        key_system = key_details.get('system')
        if key_system == 'JSONStore':
            for key in required_details:
                key_details[key] = b64decode(key_details[key]).decode('utf-8')

        self.log.debug(('Using developer config',
                        'Origin: {origin!r}',
                        'System: {system!r}'),
                       origin=origin,
                       system=key_system)

        return {
            'origin': origin,
            origin: {
                'system': key_system,
                'key': key_details['key'],
                'id': key_details['id'],
                'secret': key_details['secret'],
            }
        }

    def update_developer_config(self,
                                developer_id,
                                api_key,
                                client_id,
                                client_secret):
        data = self.get_data()
        existing_config = data['keys']['developer'].get(developer_id, {})

        new_config = {
            'origin': developer_id,
            developer_id: {
                'system': 'JSONStore',
                'key': b64encode(
                    bytes(api_key, 'utf-8')
                ).decode('ascii'),
                'id': b64encode(
                    bytes(client_id, 'utf-8')
                ).decode('ascii'),
                'secret': b64encode(
                    bytes(client_secret, 'utf-8')
                ).decode('ascii'),
            }
        }

        if existing_config and existing_config == new_config:
            return False
        data['keys']['developer'][developer_id] = new_config
        return self.save(data)

    def sync(self):
        api_data = self.get_data()
        settings = self._context.get_settings()

        update_saved_values = False
        update_settings_values = False

        saved_details = (
            api_data['keys']['user'].get('api_key', ''),
            api_data['keys']['user'].get('client_id', ''),
            api_data['keys']['user'].get('client_secret', ''),
        )
        if all(saved_details):
            update_settings_values = True
            # users are now pasting keys into api_keys.json
            # try stripping whitespace and domain suffix from API details
            # and save the results if they differ
            stripped_details = self.strip_details(*saved_details)
            if all(stripped_details) and saved_details != stripped_details:
                saved_details = stripped_details
                api_data['keys']['user'] = {
                    'api_key': saved_details[0],
                    'client_id': saved_details[1],
                    'client_secret': saved_details[2],
                }
                update_saved_values = True

        setting_details = (
            settings.api_key(),
            settings.api_id(),
            settings.api_secret(),
        )
        if all(setting_details):
            update_settings_values = False
            stripped_details = self.strip_details(*setting_details)
            if all(stripped_details) and setting_details != stripped_details:
                setting_details = (
                    settings.api_key(stripped_details[0]),
                    settings.api_id(stripped_details[1]),
                    settings.api_secret(stripped_details[2]),
                )

            if saved_details != setting_details:
                api_data['keys']['user'] = {
                    'api_key': setting_details[0],
                    'client_id': setting_details[1],
                    'client_secret': setting_details[2],
                }
                update_saved_values = True

        if update_settings_values:
            settings.api_key(saved_details[0])
            settings.api_id(saved_details[1])
            settings.api_secret(saved_details[2])

        if update_saved_values:
            self.save(api_data)
            return True
        return False

    def update(self):
        context = self._context
        localize = context.localize
        settings = context.get_settings()
        ui = context.get_ui()

        params = context.get_params()
        api_key = params.get('api_key')
        client_id = params.get('client_id')
        client_secret = params.get('client_secret')
        enable = params.get('enable')

        updated_list = []
        log_list = []

        if api_key:
            settings.api_key(api_key)
            updated_list.append(localize('api.key'))
            log_list.append('api_key')
        if client_id:
            settings.api_id(client_id)
            updated_list.append(localize('api.id'))
            log_list.append('client_id')
        if client_secret:
            settings.api_secret(client_secret)
            updated_list.append(localize('api.secret'))
            log_list.append('client_secret')
        if updated_list:
            ui.show_notification(localize('updated.x', ', '.join(updated_list)))
        self.log.debug('Updated API details: %s', log_list)

        client_id = settings.api_id()
        client_secret = settings.api_secret()
        api_key = settings.api_key
        missing_list = []
        log_list = []

        if enable and client_id and client_secret and api_key:
            ui.show_notification(localize('api.personal.enabled'))
            self.log.debug('Personal API keys enabled')
        elif enable:
            if not api_key:
                missing_list.append(localize('api.key'))
                log_list.append('api_key')
            if not client_id:
                missing_list.append(localize('api.id'))
                log_list.append('client_id')
            if not client_secret:
                missing_list.append(localize('api.secret'))
                log_list.append('client_secret')
            ui.show_notification(localize('api.personal.failed',
                                          ', '.join(missing_list)))
            self.log.error_trace(('Failed to enable personal API keys',
                                  'Missing: %s'),
                                 log_list)
