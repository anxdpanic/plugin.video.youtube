# -*- coding: utf-8 -*-
"""

    Copyright (C) 2017-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from base64 import b64decode
from hashlib import md5
from ...kodion.json_store import APIKeyStore, LoginTokenStore
from ...kodion import Context as __Context
from ... import key_sets

DEFAULT_SWITCH = 1

__context = __Context(plugin_id='plugin.video.youtube')
__settings = __context.get_settings()


class APICheck(object):

    def __init__(self, context, settings):
        self._context = context
        self._settings = settings
        self._ui = context.get_ui()
        self._api_jstore = APIKeyStore()
        self._json_api = self._api_jstore.get_data()
        self._am_jstore = LoginTokenStore()
        self._json_am = self._am_jstore.get_data()
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
            if stripped_key and stripped_id and stripped_secret:
                if (j_key != stripped_key) or (j_id != stripped_id) or (j_secret != stripped_secret):
                    self._json_api['keys']['personal'] = {'api_key': stripped_key, 'client_id': stripped_id, 'client_secret': stripped_secret}
                    self._api_jstore.save(self._json_api)

        original_key = self._settings.get_string('youtube.api.key')
        original_id = self._settings.get_string('youtube.api.id')
        original_secret = self._settings.get_string('youtube.api.secret')
        if original_key and original_id and original_secret:
            own_key, own_id, own_secret = self._strip_api_keys(original_key, original_id, original_secret)
            if own_key and own_id and own_secret:
                if (original_key != own_key) or (original_id != own_id) or (original_secret != own_secret):
                    self._settings.set_string('youtube.api.key', own_key)
                    self._settings.set_string('youtube.api.id', own_id)
                    self._settings.set_string('youtube.api.secret', own_secret)

                if (j_key != own_key) or (j_id != own_id) or (j_secret != own_secret):
                    self._json_api['keys']['personal'] = {'api_key': own_key, 'client_id': own_id, 'client_secret': own_secret}
                    self._api_jstore.save(self._json_api)

                self._json_api = self._api_jstore.get_data()
                j_key = self._json_api['keys']['personal'].get('api_key', '')
                j_id = self._json_api['keys']['personal'].get('client_id', '')
                j_secret = self._json_api['keys']['personal'].get('client_secret', '')

        if not original_key or not original_id or not original_secret and (j_key and j_secret and j_id):
            self._settings.set_string('youtube.api.key', j_key)
            self._settings.set_string('youtube.api.id', j_id)
            self._settings.set_string('youtube.api.secret', j_secret)

        switch = self.get_current_switch()
        user = self.get_current_user()

        access_token = self._settings.get_string('kodion.access_token', '')
        refresh_token = self._settings.get_string('kodion.refresh_token', '')
        token_expires = self._settings.get_int('kodion.access_token.expires', -1)
        last_hash = self._settings.get_string('youtube.api.last.hash', '')
        if not self._json_am['access_manager']['users'].get(user, {}).get('access_token') or \
                not self._json_am['access_manager']['users'].get(user, {}).get('refresh_token'):
            if access_token and refresh_token:
                self._json_am['access_manager']['users'][user]['access_token'] = access_token
                self._json_am['access_manager']['users'][user]['refresh_token'] = refresh_token
                self._json_am['access_manager']['users'][user]['token_expires'] = token_expires
                if switch == 'own':
                    own_key_hash = self._get_key_set_hash('own')
                    if last_hash == self._get_key_set_hash('own', True) or \
                            last_hash == own_key_hash:
                        self._json_am['access_manager']['users'][user]['last_key_hash'] = own_key_hash
                self._am_jstore.save(self._json_am)
        if access_token or refresh_token or last_hash:
            self._settings.set_string('kodion.access_token', '')
            self._settings.set_string('kodion.refresh_token', '')
            self._settings.set_int('kodion.access_token.expires', -1)
            self._settings.set_string('youtube.api.last.hash', '')

        updated_hash = self._api_keys_changed(switch)
        if updated_hash:
            self._context.log_warning('User: |%s| Switching API key set to |%s|' % (user, switch))
            self._json_am['access_manager']['users'][user]['last_key_hash'] = updated_hash
            self._am_jstore.save(self._json_am)
            self._context.log_debug('API key set changed: Signing out')
            self._context.execute('RunPlugin(plugin://plugin.video.youtube/sign/out/?confirmed=true)')
        else:
            self._context.log_debug('User: |%s| Using API key set: |%s|' % (user, switch))

    def get_current_switch(self):
        return 'own'

    def get_current_user(self):
        self._json_am = self._am_jstore.get_data()
        return self._json_am['access_manager'].get('current_user', '0')

    def has_own_api_keys(self):
        self._json_api = self._api_jstore.get_data()
        own_key = self._json_api['keys']['personal']['api_key']
        own_id = self._json_api['keys']['personal']['client_id']
        own_secret = self._json_api['keys']['personal']['client_secret']
        return False if not own_key or \
                        not own_id or \
                        not own_secret else True

    def get_api_keys(self, switch):
        self._json_api = self._api_jstore.get_data()
        if switch == 'youtube-tv':
            api_key = b64decode(key_sets['youtube-tv']['key']).decode('utf-8'),
            client_id = u''.join([b64decode(key_sets['youtube-tv']['id']).decode('utf-8'), u'.apps.googleusercontent.com'])
            client_secret = b64decode(key_sets['youtube-tv']['secret']).decode('utf-8')
        elif switch == 'developer':
            self._json_api = self._api_jstore.get_data()
            return self._json_api['keys']['developer']
        elif switch == 'own':
            api_key = self._json_api['keys']['personal']['api_key']
            client_id = u''.join([self._json_api['keys']['personal']['client_id'], u'.apps.googleusercontent.com'])
            client_secret = self._json_api['keys']['personal']['client_secret']
        else:
            api_key = b64decode(key_sets['provided'][switch]['key']).decode('utf-8')
            client_id = u''.join([b64decode(key_sets['provided'][switch]['id']).decode('utf-8'), u'.apps.googleusercontent.com'])
            client_secret = b64decode(key_sets['provided'][switch]['secret']).decode('utf-8')
        return api_key, client_id, client_secret

    def _api_keys_changed(self, switch):
        self._json_am = self._am_jstore.get_data()
        user = self.get_current_user()
        last_set_hash = self._json_am['access_manager']['users'].get(user, {}).get('last_key_hash', '')
        current_set_hash = self._get_key_set_hash(switch)
        if last_set_hash != current_set_hash:
            self.changed = True
            return current_set_hash
        else:
            self.changed = False
            return None

    def _get_key_set_hash(self, switch, old=False):
        api_key, client_id, client_secret = self.get_api_keys(switch)
        if old and switch == 'own':
            client_id = client_id.replace(u'.apps.googleusercontent.com', u'')
        m = md5()
        m.update(api_key.encode('utf-8'))
        m.update(client_id.encode('utf-8'))
        m.update(client_secret.encode('utf-8'))

        return m.hexdigest()

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


notification_data = {'use_httpd': (__settings.use_dash_videos() and
                                   __settings.use_dash()) or
                                  (__settings.api_config_page()),
                     'httpd_port': __settings.httpd_port(),
                     'whitelist': __settings.httpd_whitelist(),
                     'httpd_address': __settings.httpd_listen()
                     }

__context.send_notification('check_settings', notification_data)

_api_check = APICheck(__context, __settings)

keys_changed = _api_check.changed
current_user = _api_check.get_current_user()

api = dict()
youtube_tv = dict()

_current_switch = _api_check.get_current_switch()

api['key'], api['id'], api['secret'] = _api_check.get_api_keys(_current_switch)

youtube_tv['key'], youtube_tv['id'], youtube_tv['secret'] = _api_check.get_api_keys('youtube-tv')

developer_keys = _api_check.get_api_keys('developer')
