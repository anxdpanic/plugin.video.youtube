# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import time
import uuid
from hashlib import md5

from .json_store import JSONStore
from ..constants import ADDON_ID


__author__ = 'bromix'


class AccessManager(JSONStore):
    DEFAULT_NEW_USER = {
        'access_token': '',
        'refresh_token': '',
        'token_expires': -1,
        'last_key_hash': '',
        'name': 'Default',
        'watch_later': 'WL',
        'watch_history': 'HL'
    }

    def __init__(self, context):
        super(AccessManager, self).__init__('access_manager.json')
        self._context = context
        access_manager_data = self._data['access_manager']
        self._user = access_manager_data.get('current_user', 0)
        self._last_origin = access_manager_data.get('last_origin', ADDON_ID)

    def set_defaults(self, reset=False):
        data = {} if reset else self.get_data()
        if 'access_manager' not in data:
            data = {
                'access_manager': {
                    'users': {
                        0: self.DEFAULT_NEW_USER.copy()
                    }
                }
            }
        if 'users' not in data['access_manager']:
            data['access_manager']['users'] = {
                0: self.DEFAULT_NEW_USER.copy()
            }
        if 0 not in data['access_manager']['users']:
            data['access_manager']['users'][0] = self.DEFAULT_NEW_USER.copy()
        if 'current_user' not in data['access_manager']:
            data['access_manager']['current_user'] = 0
        if 'last_origin' not in data['access_manager']:
            data['access_manager']['last_origin'] = ADDON_ID
        if 'developers' not in data['access_manager']:
            data['access_manager']['developers'] = {}

        # clean up
        if data['access_manager']['current_user'] == 'default':
            data['access_manager']['current_user'] = 0
        if 'access_token' in data['access_manager']:
            del data['access_manager']['access_token']
        if 'refresh_token' in data['access_manager']:
            del data['access_manager']['refresh_token']
        if 'token_expires' in data['access_manager']:
            del data['access_manager']['token_expires']
        if 'default' in data['access_manager']:
            if ((data['access_manager']['default'].get('access_token')
                 or data['access_manager']['default'].get('refresh_token'))
                    and not data['access_manager']['users'][0].get(
                        'access_token')
                    and not data['access_manager']['users'][0].get(
                        'refresh_token')):
                if 'name' not in data['access_manager']['default']:
                    data['access_manager']['default']['name'] = 'Default'
                data['access_manager']['users'][0] = data['access_manager'][
                    'default']
            del data['access_manager']['default']
        # end clean up

        current_user = data['access_manager']['current_user']
        if 'watch_later' not in data['access_manager']['users'][current_user]:
            data['access_manager']['users'][current_user]['watch_later'] = 'WL'
        if 'watch_history' not in data['access_manager']['users'][current_user]:
            data['access_manager']['users'][current_user][
                'watch_history'] = 'HL'

        # ensure all users have uuid
        uuids = set()
        for user in data['access_manager']['users'].values():
            c_uuid = user.get('id')
            while not c_uuid or c_uuid in uuids:
                c_uuid = uuid.uuid4().hex
            uuids.add(c_uuid)
            user['id'] = c_uuid
        # end uuid check

        self.save(data)

    @staticmethod
    def _process_data(data):
        # process users, change str keys (old format) to int (current format)
        users = data['access_manager']['users']
        if '0' in users:
            data['access_manager']['users'] = {
                int(key): value
                for key, value in users.items()
            }
        current_user = data['access_manager']['current_user']
        try:
            data['access_manager']['current_user'] = int(current_user)
        except (TypeError, ValueError):
            pass
        return data

    def get_data(self, process=_process_data.__func__):
        return super(AccessManager, self).get_data(process)

    def load(self, process=_process_data.__func__):
        return super(AccessManager, self).load(process)

    def save(self, data, update=False, process=_process_data.__func__):
        return super(AccessManager, self).save(data, update, process)

    def get_current_user_details(self, addon_id=None):
        """
        :return: current user
        """
        if addon_id:
            return self.get_developers().get(addon_id, {})
        return self.get_users()[self._user]

    def get_current_user_id(self):
        """
        :return: uuid of the current user
        """
        return self.get_users()[self._user]['id']

    def get_new_user(self, username=''):
        """
        :param username: string, users name
        :return: a new user dict
        """
        uuids = [
            user.get('id')
            for user in self.get_users().values()
        ]
        new_uuid = None
        while not new_uuid or new_uuid in uuids:
            new_uuid = uuid.uuid4().hex
        return {
            'access_token': '',
            'refresh_token': '',
            'token_expires': -1,
            'last_key_hash': '',
            'name': username,
            'id': new_uuid,
            'watch_later': 'WL',
            'watch_history': 'HL'
        }

    def get_users(self):
        """
        Returns users
        :return: users
        """
        return self._data['access_manager'].get('users', {})

    def add_user(self, username='', user=None):
        """
        Add single new user to users collection
        :param username: str, chosen name of new user
        :param user: int, optional index for new user
        :return: tuple, (index, details) of newly added user
        """
        users = self.get_users()
        new_user_details = self.get_new_user(username)
        new_user = max(users) + 1 if users and user is None else user or 0
        data = {
            'access_manager': {
                'users': {
                    new_user: new_user_details,
                },
            },
        }
        self.save(data, update=True)
        return new_user, new_user_details

    def remove_user(self, user):
        """
        Remove user from collection of current users
        :param user: int, user index
        :return:
        """
        users = self.get_users()
        if user in users:
            data = {
                'access_manager': {
                    'users': {
                        user: KeyError,
                    },
                },
            }
            self.save(data, update=True)

    def set_users(self, users):
        """
        Updates all users
        :param users: dict, users
        :return:
        """
        data = self.get_data()
        data['access_manager']['users'] = users
        self.save(data)

    def set_user(self, user, switch_to=False):
        """
        Updates the user
        :param user: string, username
        :param switch_to: boolean, change current user
        :return:
        """
        try:
            user = int(user)
        except (TypeError, ValueError):
            pass

        self._user = user
        if switch_to:
            data = {
                'access_manager': {
                    'current_user': user,
                },
            }
            self.save(data, update=True)

    def get_current_user(self):
        """
        Returns the current user
        :return: user
        """
        return self._user

    def get_username(self, user=None):
        """
        Returns the username of the current or nominated user
        :return: username
        """
        if user is None:
            user = self._user
        users = self.get_users()
        if user in users:
            return users[user].get('name')
        return ''

    def set_username(self, user, username):
        """
        Sets the username of the nominated user
        :return: True if username was set, false otherwise
        """
        users = self.get_users()
        if user in users:
            data = {
                'access_manager': {
                    'users': {
                        user: {
                            'name': username,
                        },
                    },
                },
            }
            self.save(data, update=True)
            return True
        return False

    def get_watch_later_id(self):
        """
        Returns the current users watch later playlist id
        :return: the current users watch later playlist id
        """
        current_id = (self.get_current_user_details().get('watch_later')
                      or 'WL').strip()

        settings = self._context.get_settings()
        settings_id = settings.get_watch_later_playlist()

        if settings_id.lower() == 'wl':
            current_id = self.set_watch_later_id(None)
        elif settings_id and settings_id != current_id:
            current_id = self.set_watch_later_id(settings_id)
        elif current_id:
            if current_id.lower() == 'wl':
                current_id = ''
            elif settings_id:
                settings.set_watch_later_playlist('')

        return current_id

    def set_watch_later_id(self, playlist_id=None):
        """
        Sets the current users watch later playlist id
        :param playlist_id: string, watch later playlist id
        :return:
        """
        if not playlist_id:
            playlist_id = ''

        self._context.get_settings().set_watch_later_playlist('')

        playlists = {
            'watch_later': playlist_id,
        }
        current_id = self.get_current_user_details().get('watch_later')
        if current_id:
            playlists['watch_later_old'] = current_id

        data = {
            'access_manager': {
                'users': {
                    self._user: playlists,
                },
            },
        }
        self.save(data, update=True)
        return playlist_id

    def get_watch_history_id(self):
        """
        Returns the current users watch history playlist id
        :return: the current users watch history playlist id
        """
        current_id = (self.get_current_user_details().get('watch_history')
                      or 'HL').strip()

        settings = self._context.get_settings()
        settings_id = settings.get_history_playlist()

        if settings_id.lower() == 'hl':
            current_id = self.set_watch_history_id(None)
        elif settings_id and settings_id != current_id:
            current_id = self.set_watch_history_id(settings_id)
        elif current_id:
            if current_id.lower() == 'hl':
                current_id = ''
            elif settings_id:
                settings.set_history_playlist('')

        return current_id

    def set_watch_history_id(self, playlist_id=None):
        """
        Sets the current users watch history playlist id
        :param playlist_id: string, watch history playlist id
        :return:
        """
        if not playlist_id:
            playlist_id = ''

        self._context.get_settings().set_history_playlist('')

        playlists = {
            'watch_history': playlist_id,
        }
        current_id = self.get_current_user_details().get('watch_history')
        if current_id:
            playlists['watch_history_old'] = current_id

        data = {
            'access_manager': {
                'users': {
                    self._user: playlists,
                },
            },
        }
        self.save(data, update=True)
        return playlist_id

    def set_last_origin(self, origin):
        """
        Updates the origin
        :param origin: string, origin
        :return:
        """
        self._last_origin = origin
        data = {
            'access_manager': {
                'last_origin': origin,
            },
        }
        self.save(data, update=True)

    def get_last_origin(self):
        """
        Returns the last origin
        :return:
        """
        return self._last_origin

    def get_access_token(self, addon_id=None):
        """
        Returns the access token for some API
        :return: access_token
        """
        details = self.get_current_user_details(addon_id)
        return details.get('access_token', '').split('|')

    def get_refresh_token(self, addon_id=None):
        """
        Returns the refresh token
        :return: refresh token
        """
        details = self.get_current_user_details(addon_id)
        return details.get('refresh_token', '').split('|')

    def is_access_token_expired(self, addon_id=None):
        """
        Returns True if the access_token is expired otherwise False.
        If no expiration date was provided and an access_token exists
        this method will always return True
        :return:
        """
        details = self.get_current_user_details(addon_id)
        access_token = details.get('access_token', '')
        expires = int(details.get('token_expires', -1))

        if access_token and expires <= int(time.time()):
            return True
        return False

    def update_access_token(self,
                            addon_id,
                            access_token=None,
                            unix_timestamp=None,
                            refresh_token=None):
        """
        Updates the old access token with the new one.
        :param access_token:
        :param unix_timestamp:
        :param refresh_token:
        :return:
        """
        details = {
            'access_token': (
                '|'.join(access_token)
                if isinstance(access_token, (list, tuple)) else
                access_token
                if access_token else
                ''
            )
        }

        if unix_timestamp is not None:
            details['token_expires'] = (
                min(map(int, unix_timestamp))
                if isinstance(unix_timestamp, (list, tuple)) else
                int(unix_timestamp)
            )

        if refresh_token is not None:
            details['refresh_token'] = (
                '|'.join(refresh_token)
                if isinstance(refresh_token, (list, tuple)) else
                refresh_token
            )

        data = {
            'access_manager': {
                'developers': {
                    addon_id: details,
                },
            } if addon_id else {
                'users': {
                    self._user: details,
                },
            },
        }
        self.save(data, update=True)

    def get_last_key_hash(self, addon_id=None):
        details = self.get_current_user_details(addon_id)
        return details.get('last_key_hash', '')

    def set_last_key_hash(self, key_hash, addon_id=None):
        data = {
            'access_manager': {
                'developers': {
                    addon_id: {
                        'last_key_hash': key_hash,
                    },
                },
            } if addon_id else {
                'users': {
                    self._user: {
                        'last_key_hash': key_hash,
                    },
                },
            },
        }
        self.save(data, update=True)

    @staticmethod
    def get_new_developer():
        """
        :return: a new developer dict
        """
        return {
            'access_token': '',
            'refresh_token': '',
            'token_expires': -1,
            'last_key_hash': ''
        }

    def get_developers(self):
        """
        Returns developers
        :return: dict, developers
        """
        return self._data['access_manager'].get('developers', {})

    def set_developers(self, developers):
        """
        Updates the users
        :param developers: dict, developers
        :return:
        """
        data = self.get_data()
        data['access_manager']['developers'] = developers
        self.save(data)

    def dev_keys_changed(self, addon_id, api_key, client_id, client_secret):
        last_hash = self.get_last_key_hash(addon_id)
        current_hash = self.calc_key_hash(api_key, client_id, client_secret)

        if not last_hash and current_hash:
            self.set_last_key_hash(current_hash, addon_id)
            return False

        if last_hash != current_hash:
            self.set_last_key_hash(current_hash, addon_id)
            return True

        return False

    @staticmethod
    def calc_key_hash(key, id, secret, **_kwargs):
        return md5(''.join((key, id, secret)).encode('utf-8')).hexdigest()
