# -*- coding: utf-8 -*-
"""

    Copyright (C) 2017-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from base64 import b64decode

from ... import key_sets
from ...kodion.context import XbmcContext
from ...kodion.json_store import APIKeyStore, AccessManager


DEFAULT_SWITCH = 1


class APICheck(object):
    def __init__(self, context):
        self._context = context
        self._settings = context.get_settings()
        self._ui = context.get_ui()
        self._api_jstore = APIKeyStore()
        self._json_api = self._api_jstore.get_data()
        self._access_manager = AccessManager(context)
        self.changed = False

        self._on_init()

    def _on_init(self):
        self._json_api = self._api_jstore.get_data()

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

        original_key = self._settings.api_key()
        original_id = self._settings.api_id()
        original_secret = self._settings.api_secret()
        if original_key and original_id and original_secret:
            own_key, own_id, own_secret = self._strip_api_keys(original_key, original_id, original_secret)
            if own_key and own_id and own_secret:
                if (original_key != own_key) or (original_id != own_id) or (original_secret != own_secret):
                    self._settings.api_key(own_key)
                    self._settings.api_id(own_id)
                    self._settings.api_secret(own_secret)

                if (j_key != own_key) or (j_id != own_id) or (j_secret != own_secret):
                    self._json_api['keys']['personal'] = {'api_key': own_key, 'client_id': own_id, 'client_secret': own_secret}
                    self._api_jstore.save(self._json_api)

                self._json_api = self._api_jstore.get_data()
                j_key = self._json_api['keys']['personal'].get('api_key', '')
                j_id = self._json_api['keys']['personal'].get('client_id', '')
                j_secret = self._json_api['keys']['personal'].get('client_secret', '')

        if (not original_key or not original_id or not original_secret
                and j_key and j_secret and j_id):
            self._settings.api_key(j_key)
            self._settings.api_id(j_id)
            self._settings.api_secret(j_secret)

        switch = self.get_current_switch()
        user_details = self._access_manager.get_current_user_details()
        last_hash = user_details.get('last_key_hash', '')
        current_set_hash = self._get_key_set_hash(switch)

        changed = current_set_hash != last_hash
        if changed and switch == 'own':
            changed = self._get_key_set_hash('own_old') != last_hash
            if not changed:
                self._access_manager.set_last_key_hash(current_set_hash)
        self.changed = changed

        self._context.log_debug('User: |{user}|, '
                                'Using API key set: |{switch}|'
                                .format(user=self.get_current_user(),
                                        switch=switch))
        if changed:
            self._context.log_debug('API key set changed: Signing out')
            self._context.execute('RunPlugin(plugin://plugin.video.youtube/'
                                  'sign/out/?confirmed=true)')
            self._access_manager.set_last_key_hash(current_set_hash)

    @staticmethod
    def get_current_switch():
        return 'own'

    def get_current_user(self):
        return self._access_manager.get_current_user()

    def has_own_api_keys(self):
        self._json_api = self._api_jstore.get_data()
        own_key = self._json_api['keys']['personal']['api_key']
        own_id = self._json_api['keys']['personal']['client_id']
        own_secret = self._json_api['keys']['personal']['client_secret']
        return own_key and own_id and own_secret

    def get_api_keys(self, switch):
        self._json_api = self._api_jstore.get_data()
        if switch == 'developer':
            return self._json_api['keys'][switch]

        decode = True
        if switch == 'youtube-tv':
            api_key = key_sets[switch]['key']
            client_id = key_sets[switch]['id']
            client_secret = key_sets[switch]['secret']

        elif switch.startswith('own'):
            decode = False
            api_key = self._json_api['keys']['personal']['api_key']
            client_id = self._json_api['keys']['personal']['client_id']
            client_secret = self._json_api['keys']['personal']['client_secret']

        else:
            api_key = key_sets['provided'][switch]['key']
            client_id = key_sets['provided'][switch]['id']
            client_secret = key_sets['provided'][switch]['secret']

        if decode:
            api_key = b64decode(api_key).decode('utf-8')
            client_id = b64decode(client_id).decode('utf-8')
            client_secret = b64decode(client_secret).decode('utf-8')

        client_id += '.apps.googleusercontent.com'
        return {'key': api_key,
                'id': client_id,
                'secret': client_secret}

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


_api_check = APICheck(XbmcContext())

keys_changed = _api_check.changed
current_user = _api_check.get_current_user()

api = _api_check.get_api_keys(_api_check.get_current_switch())
youtube_tv = _api_check.get_api_keys('youtube-tv')
developer_keys = _api_check.get_api_keys('developer')
