# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import uuid
import time

from hashlib import md5

from ..json_store import LoginTokenStore

__author__ = 'bromix'


class AccessManager(object):
    def __init__(self, context):
        self._settings = context.get_settings()
        self._jstore = LoginTokenStore()
        self._json = self._jstore.get_data()
        self._user = self._json['access_manager'].get('current_user', '0')
        self._last_origin = self._json['access_manager'].get('last_origin', 'plugin.video.youtube')

    def get_current_user_id(self):
        """

        :return: uuid of the current user
        """
        self._json = self._jstore.get_data()
        return self._json['access_manager']['users'][self.get_user()]['id']

    def get_new_user(self, user_name=''):
        """
        :param user_name: string, users name
        :return: a new user dict
        """
        uuids = list()
        new_uuid = uuid.uuid4().hex

        for k in list(self._json['access_manager']['users'].keys()):
            user_uuid = self._json['access_manager']['users'][k].get('id')
            if user_uuid:
                uuids.append(user_uuid)

        while new_uuid in uuids:
            new_uuid = uuid.uuid4().hex

        return {'access_token': '', 'refresh_token': '', 'token_expires': -1, 'last_key_hash': '',
                'name': user_name, 'id': new_uuid, 'watch_later': ' WL', 'watch_history': 'HL'}

    def get_users(self):
        """
        Returns users
        :return: users
        """
        return self._json['access_manager'].get('users', {})

    def set_users(self, users):
        """
        Updates the users
        :param users: dict, users
        :return:
        """
        self._json = self._jstore.get_data()
        self._json['access_manager']['users'] = users
        self._jstore.save(self._json)

    def set_user(self, user, switch_to=False):
        """
        Updates the user
        :param user: string, username
        :param switch_to: boolean, change current user
        :return:
        """
        self._user = user
        if switch_to:
            self._json = self._jstore.get_data()
            self._json['access_manager']['current_user'] = user
            self._jstore.save(self._json)

    def get_user(self):
        """
        Returns the current user
        :return: user
        """
        return self._user

    def get_watch_later_id(self):
        """
        Returns the current users watch later playlist id
        :return: the current users watch later playlist id
        """

        self._json = self._jstore.get_data()
        current_playlist_id = self._json['access_manager']['users'].get(self._user, {}).get('watch_later', ' WL')
        settings_playlist_id = self._settings.get_string('youtube.folder.watch_later.playlist', '').strip()
        if settings_playlist_id.lower() == 'wl':
            settings_playlist_id = ' WL'
        if settings_playlist_id:
            if current_playlist_id != settings_playlist_id:
                self._json['access_manager']['users'][self._user]['watch_later'] = settings_playlist_id
                self._jstore.save(self._json)
            self._settings.set_string('youtube.folder.watch_later.playlist', '')
        return self._json['access_manager']['users'].get(self._user, {}).get('watch_later', ' WL')

    def set_watch_later_id(self, playlist_id):
        """
        Sets the current users watch later playlist id
        :param playlist_id: string, watch later playlist id
        :return:
        """

        if playlist_id.strip().lower() == 'wl':
            playlist_id = ' WL'
        self._json = self._jstore.get_data()
        self._json['access_manager']['users'][self._user]['watch_later'] = playlist_id
        self._settings.set_string('youtube.folder.watch_later.playlist', '')
        self._jstore.save(self._json)

    def get_watch_history_id(self):
        """
        Returns the current users watch history playlist id
        :return: the current users watch history playlist id
        """

        self._json = self._jstore.get_data()
        current_playlist_id = self._json['access_manager']['users'].get(self._user, {}).get('watch_history', 'HL')
        settings_playlist_id = self._settings.get_string('youtube.folder.history.playlist', '').strip()
        if settings_playlist_id and (current_playlist_id != settings_playlist_id):
            self._json['access_manager']['users'][self._user]['watch_history'] = settings_playlist_id
            self._jstore.save(self._json)
            self._settings.set_string('youtube.folder.history.playlist', '')
        return self._json['access_manager']['users'].get(self._user, {}).get('watch_history', 'HL')

    def set_watch_history_id(self, playlist_id):
        """
        Sets the current users watch history playlist id
        :param playlist_id: string, watch history playlist id
        :return:
        """

        self._json = self._jstore.get_data()
        self._json['access_manager']['users'][self._user]['watch_history'] = playlist_id
        self._settings.set_string('youtube.folder.history.playlist', '')
        self._jstore.save(self._json)

    def set_last_origin(self, origin):
        """
        Updates the origin
        :param origin: string, origin
        :return:
        """
        self._last_origin = origin
        self._json = self._jstore.get_data()
        self._json['access_manager']['last_origin'] = origin
        self._jstore.save(self._json)

    def get_last_origin(self):
        """
        Returns the last origin
        :return:
        """
        return self._last_origin

    def get_access_token(self):
        """
        Returns the access token for some API
        :return: access_token
        """
        self._json = self._jstore.get_data()
        return self._json['access_manager']['users'].get(self._user, {}).get('access_token', '')

    def get_refresh_token(self):
        """
        Returns the refresh token
        :return: refresh token
        """
        self._json = self._jstore.get_data()
        return self._json['access_manager']['users'].get(self._user, {}).get('refresh_token', '')

    def has_refresh_token(self):
        return self.get_refresh_token() != ''

    def is_access_token_expired(self):
        """
        Returns True if the access_token is expired otherwise False.
        If no expiration date was provided and an access_token exists
        this method will always return True
        :return:
        """
        self._json = self._jstore.get_data()
        access_token = self._json['access_manager']['users'].get(self._user, {}).get('access_token', '')
        expires = int(self._json['access_manager']['users'].get(self._user, {}).get('token_expires', -1))

        # with no access_token it must be expired
        if not access_token:
            return True

        # in this case no expiration date was set
        if expires == -1:
            return False

        now = int(time.time())
        return expires <= now

    def update_access_token(self, access_token, unix_timestamp=None, refresh_token=None):
        """
        Updates the old access token with the new one.
        :param access_token:
        :param unix_timestamp:
        :param refresh_token:
        :return:
        """
        self._json = self._jstore.get_data()
        self._json['access_manager']['users'][self._user]['access_token'] = access_token

        if unix_timestamp is not None:
            self._json['access_manager']['users'][self._user]['token_expires'] = int(unix_timestamp)

        if refresh_token is not None:
            self._json['access_manager']['users'][self._user]['refresh_token'] = refresh_token

        self._jstore.save(self._json)

    @staticmethod
    def get_new_developer():
        """
        :return: a new developer dict
        """

        return {'access_token': '', 'refresh_token': '', 'token_expires': -1, 'last_key_hash': ''}

    def get_developers(self):
        """
        Returns developers
        :return: dict, developers
        """
        return self._json['access_manager'].get('developers', {})

    def set_developers(self, developers):
        """
        Updates the users
        :param developers: dict, developers
        :return:
        """
        self._json = self._jstore.get_data()
        self._json['access_manager']['developers'] = developers
        self._jstore.save(self._json)

    def get_dev_access_token(self, addon_id):
        """
        Returns the access token for some API
        :param addon_id: addon id
        :return: access_token
        """
        self._json = self._jstore.get_data()
        return self._json['access_manager']['developers'].get(addon_id, {}).get('access_token', '')

    def get_dev_refresh_token(self, addon_id):
        """
        Returns the refresh token
        :return: refresh token
        """
        self._json = self._jstore.get_data()
        return self._json['access_manager']['developers'].get(addon_id, {}).get('refresh_token', '')

    def developer_has_refresh_token(self, addon_id):
        return self.get_dev_refresh_token(addon_id) != ''

    def is_dev_access_token_expired(self, addon_id):
        """
        Returns True if the access_token is expired otherwise False.
        If no expiration date was provided and an access_token exists
        this method will always return True
        :return:
        """
        self._json = self._jstore.get_data()
        access_token = self._json['access_manager']['developers'].get(addon_id, {}).get('access_token', '')
        expires = int(self._json['access_manager']['developers'].get(addon_id, {}).get('token_expires', -1))

        # with no access_token it must be expired
        if not access_token:
            return True

        # in this case no expiration date was set
        if expires == -1:
            return False

        now = int(time.time())
        return expires <= now

    def update_dev_access_token(self, addon_id, access_token, unix_timestamp=None, refresh_token=None):
        """
        Updates the old access token with the new one.
        :param addon_id:
        :param access_token:
        :param unix_timestamp:
        :param refresh_token:
        :return:
        """
        self._json = self._jstore.get_data()
        self._json['access_manager']['developers'][addon_id]['access_token'] = access_token

        if unix_timestamp is not None:
            self._json['access_manager']['developers'][addon_id]['token_expires'] = int(unix_timestamp)

        if refresh_token is not None:
            self._json['access_manager']['developers'][addon_id]['refresh_token'] = refresh_token

        self._jstore.save(self._json)

    def get_dev_last_key_hash(self, addon_id):
        self._json = self._jstore.get_data()
        return self._json['access_manager']['developers'][addon_id]['last_key_hash']

    def set_dev_last_key_hash(self, addon_id, key_hash):
        self._json = self._jstore.get_data()
        self._json['access_manager']['developers'][addon_id]['last_key_hash'] = key_hash
        self._jstore.save(self._json)

    def dev_keys_changed(self, addon_id, api_key, client_id, client_secret):
        self._json = self._jstore.get_data()
        last_hash = self._json['access_manager']['developers'][addon_id]['last_key_hash']
        current_hash = self.__calc_key_hash(api_key, client_id, client_secret)
        if not last_hash and current_hash:
            self.set_dev_last_key_hash(addon_id, current_hash)
            return False
        if last_hash != current_hash:
            self.set_dev_last_key_hash(addon_id, current_hash)
            return True
        else:
            return False

    @staticmethod
    def __calc_key_hash(api_key, client_id, client_secret):

        m = md5()
        try:
            m.update(api_key.encode('utf-8'))
            m.update(client_id.encode('utf-8'))
            m.update(client_secret.encode('utf-8'))
        except:
            m.update(api_key)
            m.update(client_id)
            m.update(client_secret)

        return m.hexdigest()
