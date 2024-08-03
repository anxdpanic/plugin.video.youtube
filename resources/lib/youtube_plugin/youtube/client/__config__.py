# -*- coding: utf-8 -*-
"""

    Copyright (C) 2017-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from base64 import b64decode

from ... import key_sets
from ...kodion.json_store import APIKeyStore, AccessManager


DEFAULT_SWITCH = 1


class APICheck(object):
    def __init__(self, context):
        self._context = context
        self._api_jstore = APIKeyStore()
        self._json_api = self._api_jstore.get_data()
        self._access_manager = AccessManager(context)

        j_key = self._json_api['keys']['personal'].get('api_key', '')
        j_id = self._json_api['keys']['personal'].get('client_id', '')
        j_secret = self._json_api['keys']['personal'].get('client_secret', '')

        if j_key and j_id and j_secret:
            # users are now pasting keys into api_keys.json
            # try stripping whitespace and .apps.googleusercontent.com from keys and saving the result if they differ
            stripped_key, stripped_id, stripped_secret = self._strip_api_keys(j_key, j_id, j_secret)
            if (stripped_key and stripped_id and stripped_secret
                    and (j_key != stripped_key or j_id != stripped_id or j_secret != stripped_secret)):
                self._json_api['keys']['personal'] = {'api_key': stripped_key, 'client_id': stripped_id, 'client_secret': stripped_secret}
                self._api_jstore.save(self._json_api)

        settings = self._context.get_settings()
        original_key = settings.api_key()
        original_id = settings.api_id()
        original_secret = settings.api_secret()
        if original_key and original_id and original_secret:
            own_key, own_id, own_secret = self._strip_api_keys(original_key, original_id, original_secret)
            if own_key and own_id and own_secret:
                if (original_key != own_key) or (original_id != own_id) or (original_secret != own_secret):
                    settings.api_key(own_key)
                    settings.api_id(own_id)
                    settings.api_secret(own_secret)

                if (j_key != own_key) or (j_id != own_id) or (j_secret != own_secret):
                    self._json_api['keys']['personal'] = {'api_key': own_key, 'client_id': own_id, 'client_secret': own_secret}
                    self._api_jstore.save(self._json_api)

                self._json_api = self._api_jstore.get_data()
                j_key = self._json_api['keys']['personal'].get('api_key', '')
                j_id = self._json_api['keys']['personal'].get('client_id', '')
                j_secret = self._json_api['keys']['personal'].get('client_secret', '')

        if ((not original_key or not original_id or not original_secret)
                and j_key and j_secret and j_id):
            settings.api_key(j_key)
            settings.api_id(j_id)
            settings.api_secret(j_secret)

        switch = self.get_current_switch()
        last_hash = self._access_manager.get_last_key_hash()
        current_hash = self._get_key_set_hash(switch)

        changed = current_hash != last_hash
        if changed and switch == 'own':
            changed = self._get_key_set_hash('own_old') != last_hash
            if not changed:
                self._access_manager.set_last_key_hash(current_hash)
        self.changed = changed

        self._context.log_debug('User: |{user}|, '
                                'Using API key set: |{switch}|'
                                .format(user=self.get_current_user(),
                                        switch=switch))
        if changed:
            self._context.log_debug('API key set changed: Signing out')
            self._context.execute(self._context.create_uri(
                ('sign', 'out'),
                {
                    'confirmed': True,
                },
                run=True,
            ))
            self._access_manager.set_last_key_hash(current_hash)

    @staticmethod
    def get_current_switch():
        return 'own'

    def get_current_user(self):
        return self._access_manager.get_current_user()

    def has_own_api_keys(self):
        json_data = self._api_jstore.get_data()
        try:
            return (json_data['keys']['personal']['api_key']
                    and json_data['keys']['personal']['client_id']
                    and json_data['keys']['personal']['client_secret'])
        except KeyError:
            return False

    def get_api_keys(self, switch):
        self._json_api = self._api_jstore.get_data()
        if switch == 'developer':
            return self._json_api['keys'][switch]

        decode = True
        if switch == 'youtube-tv':
            system = 'YouTube TV'
            key_set_details = key_sets[switch]

        elif switch.startswith('own'):
            decode = False
            system = 'All'
            key_set_details = self._json_api['keys']['personal']

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
        if not key_set['id'].endswith('.apps.googleusercontent.com'):
            key_set['id'] += '.apps.googleusercontent.com'
        return key_set

    def _get_key_set_hash(self, switch):
        key_set = self.get_api_keys(switch)
        if switch.startswith('own'):
            client_id = key_set['id'].replace('.apps.googleusercontent.com', '')
            if switch == 'own_old':
                client_id += '.apps.googleusercontent.com'
            key_set['id'] = client_id
        return self._access_manager.calc_key_hash(**key_set)

    def _strip_api_keys(self, api_key, client_id, client_secret):
        stripped_key = ''.join(api_key.split())
        stripped_id = ''.join(client_id.replace('.apps.googleusercontent.com', '').split())
        stripped_secret = ''.join(client_secret.split())

        if api_key != stripped_key:
            if stripped_key not in api_key:
                self._context.log_debug('Personal API setting: |Key| Skipped: potentially mangled by stripping')
                return_key = api_key
            else:
                self._context.log_debug('Personal API setting: |Key| had whitespace removed')
                return_key = stripped_key
        else:
            return_key = api_key

        if client_id != stripped_id:
            if stripped_id not in client_id:
                self._context.log_debug('Personal API setting: |Id| Skipped: potentially mangled by stripping')
                return_id = client_id
            else:
                googleusercontent = ''
                if '.apps.googleusercontent.com' in client_id:
                    googleusercontent = ' and .apps.googleusercontent.com'
                self._context.log_debug('Personal API setting: |Id| had whitespace%s removed' % googleusercontent)
                return_id = stripped_id
        else:
            return_id = client_id

        if client_secret != stripped_secret:
            if stripped_secret not in client_secret:
                self._context.log_debug('Personal API setting: |Secret| Skipped: potentially mangled by stripping')
                return_secret = client_secret
            else:
                self._context.log_debug('Personal API setting: |Secret| had whitespace removed')
                return_secret = stripped_secret
        else:
            return_secret = client_secret

        return return_key, return_id, return_secret

    def get_configs(self):
        return {
            'youtube-tv': self.get_api_keys('youtube-tv'),
            'main': self.get_api_keys(self.get_current_switch()),
            'developer': self.get_api_keys('developer')
        }
