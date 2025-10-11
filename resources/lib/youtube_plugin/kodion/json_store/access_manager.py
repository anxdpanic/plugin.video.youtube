# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import time
import uuid

from .json_store import JSONStore
from ..compatibility import string_type
from ..constants import ADDON_ID
from ..utils.methods import generate_hash


class AccessManager(JSONStore):
    DEFAULT_NEW_USER = {
        'access_token': '',
        'refresh_token': '',
        'token_expires': -1,
        'last_key_hash': '',
        'name': 'Default',
        'id': None,
        'watch_later': 'WL',
        'watch_history': 'HL'
    }
    DEFAULT_NEW_DEVELOPER = {
        'access_token': '',
        'refresh_token': '',
        'token_expires': -1,
        'last_key_hash': ''
    }

    def __init__(self, context):
        self._user = None
        self._last_origin = None
        super(AccessManager, self).__init__('access_manager.json', context)

    def init(self):
        super(AccessManager, self).init()
        access_manager_data = self._data['access_manager']
        self._user = access_manager_data.get('current_user', 0)
        self._last_origin = access_manager_data.get('last_origin', ADDON_ID)

    def set_defaults(self, reset=False):
        data = {} if reset else self.get_data()

        access_manager = data.get('access_manager')
        if not access_manager or not isinstance(access_manager, dict):
            users = {
                0: self.DEFAULT_NEW_USER.copy(),
            }
            access_manager = {
                'users': users,
                'current_user': 0,
                'last_origin': ADDON_ID,
                'developers': {},
            }
        else:
            users = access_manager.get('users')
            if not users or not isinstance(users, dict):
                users = {
                    0: self.DEFAULT_NEW_USER.copy(),
                }
            elif any(not isinstance(user_id, int) for user_id in users):
                new_users = {}
                old_users = {}
                for user_id, user in users.items():
                    if isinstance(user_id, int):
                        new_users[user_id] = user
                    else:
                        try:
                            user_id = int(user_id)
                            if user_id in users:
                                raise ValueError
                            new_users[user_id] = user
                        except (TypeError, ValueError):
                            old_users[user_id] = user
                if new_users:
                    users = new_users
                if old_users:
                    new_user_id = max(users) + 1 if users else 0
                    for user in old_users.values():
                        users[new_user_id] = user
                        new_user_id += 1
            access_manager['users'] = users

            current_id = access_manager.get('current_user')
            if (not current_id
                    or current_id == 'default'
                    or current_id not in users):
                current_id = min(users)
            else:
                if not isinstance(current_id, int):
                    try:
                        current_id = int(current_id)
                        if current_id not in users:
                            raise ValueError
                    except (TypeError, ValueError):
                        current_id = min(users)
            access_manager['current_user'] = current_id
            current_user = users[current_id]
            current_user.setdefault('watch_later', 'WL')
            current_user.setdefault('watch_history', 'HL')

            if 'default' in access_manager:
                default_user = access_manager['default']
                if (isinstance(default_user, dict)
                        and (default_user.get('access_token')
                             or default_user.get('refresh_token'))
                        and not current_user.get('access_token')
                        and not current_user.get('refresh_token')):
                    default_user.setdefault('name', 'Default')
                    users[current_id] = default_user
                del access_manager['default']

            if 'access_token' in access_manager:
                del access_manager['access_token']

            if 'refresh_token' in access_manager:
                del access_manager['refresh_token']

            if 'token_expires' in access_manager:
                del access_manager['token_expires']

            last_origin = access_manager.get('last_origin')
            if not last_origin or not isinstance(last_origin, string_type):
                access_manager['last_origin'] = ADDON_ID

            developers = access_manager.get('developers')
            if not developers or not isinstance(developers, dict):
                access_manager['developers'] = {}
        data['access_manager'] = access_manager

        # ensure all users have uuid
        uuids = set()
        for user in users.values():
            user_uuid = user.get('id')
            if user_uuid:
                if user_uuid in uuids:
                    user['old_id'] = user_uuid
                    user_uuid = None
                else:
                    uuids.add(user_uuid)
                    continue
            while not user_uuid or user_uuid in uuids:
                user_uuid = uuid.uuid4().hex
            uuids.add(user_uuid)
            user['id'] = user_uuid
        # end uuid check

        return self.save(data)

    @staticmethod
    def _process_data(data):
        output = {}
        for key, value in data:
            if key in output:
                continue
            if key == 'current_user':
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    value = 0
            else:
                try:
                    key = int(key)
                except (TypeError, ValueError):
                    pass
            output[key] = value
        return output

    def get_current_user_details(self, addon_id=None):
        """
        :return: current user
        """
        if addon_id and addon_id != ADDON_ID:
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
        return dict(self.DEFAULT_NEW_USER,
                    name=username,
                    id=new_uuid)

    def get_users(self):
        """
        Returns users
        :return: users
        """
        data = self._data if self._loaded else self.get_data()
        return data['access_manager'].get('users', {})

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
        current_id = self.get_current_user_details().get('watch_later', '')
        current_id = current_id.strip()
        current_id_lower = current_id.lower()

        settings = self._context.get_settings()
        settings_id = settings.get_watch_later_playlist()
        settings_id_lower = settings_id.lower()

        if settings_id_lower == 'local':
            current_id = self.set_watch_later_id(None)
        elif settings_id and settings_id_lower != current_id_lower:
            current_id = self.set_watch_later_id(settings_id)
        elif current_id_lower == 'local':
            current_id = ''

        if settings_id:
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

        current_id = self.get_current_user_details().get('watch_history', '')
        current_id = current_id.strip()
        current_id_lower = current_id.lower()

        settings = self._context.get_settings()
        settings_id = settings.get_history_playlist()
        settings_id_lower = settings_id.lower()

        if settings_id_lower == 'local':
            current_id = self.set_watch_history_id(None)
        elif settings_id and settings_id_lower != current_id_lower:
            current_id = self.set_watch_history_id(settings_id)
        elif current_id_lower == 'local':
            current_id = ''

        if settings_id:
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

    def get_refresh_tokens(self, addon_id=None):
        """
        Returns a tuple containing a list of refresh tokens and the number of
        valid refresh tokens
        :return:
        """
        details = self.get_current_user_details(addon_id)
        refresh_tokens = details.get('refresh_token', '').split('|')
        num_refresh_tokens = len([1 for token in refresh_tokens if token])
        return refresh_tokens, num_refresh_tokens

    def get_access_tokens(self, addon_id=None):
        """
        Returns a tuple containing a list of access tokens, the number of valid
        access tokens, and the token expiry timestamp.
        :return:
        """
        details = self.get_current_user_details(addon_id)
        access_tokens = details.get('access_token').split('|')
        expiry_timestamp = int(details.get('token_expires', -1))
        if expiry_timestamp > int(time.time()):
            num_access_tokens = len([1 for token in access_tokens if token])
        else:
            access_tokens = [None, None, None, None]
            num_access_tokens = 0
        return access_tokens, num_access_tokens, expiry_timestamp

    def update_access_token(self,
                            addon_id,
                            access_token=None,
                            expiry=None,
                            refresh_token=None):
        """
        Updates the old access token with the new one.
        :param addon_id:
        :param access_token:
        :param expiry:
        :param refresh_token:
        :return:
        """
        details = {
            'access_token': (
                '|'.join([token or '' for token in access_token])
                if isinstance(access_token, (list, tuple)) else
                access_token
                if access_token else
                ''
            )
        }

        if expiry is not None:
            if isinstance(expiry, (list, tuple)):
                expiry = [val for val in expiry if val]
                expiry = min(map(int, expiry)) if expiry else -1
            else:
                expiry = int(expiry)
            details['token_expires'] = time.time() + expiry

        if refresh_token is not None:
            details['refresh_token'] = (
                '|'.join([token or '' for token in refresh_token])
                if isinstance(refresh_token, (list, tuple)) else
                refresh_token
            )

        data = {
            'access_manager': {
                'developers': {
                    addon_id: details,
                },
            } if addon_id and addon_id != ADDON_ID else {
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
            } if addon_id and addon_id != ADDON_ID else {
                'users': {
                    self._user: {
                        'last_key_hash': key_hash,
                    },
                },
            },
        }
        self.save(data, update=True)

    def get_developers(self):
        """
        Returns developers
        :return: dict, developers
        """
        data = self._data if self._loaded else self.get_data()
        return data['access_manager'].get('developers', {})

    def add_new_developer(self, addon_id):
        """
        Updates the developer users
        :param addon_id: str
        :return:
        """
        data = self.get_data()
        developers = data['access_manager'].get('developers', {})
        if addon_id not in developers:
            developers[addon_id] = self.DEFAULT_NEW_DEVELOPER.copy()
            data['access_manager']['developers'] = developers
            return self.save(data)
        return False

    def keys_changed(self,
                     addon_id,
                     api_key,
                     client_id,
                     client_secret,
                     update_hash=True):
        last_hash = self.get_last_key_hash(addon_id)
        current_hash = generate_hash(api_key, client_id, client_secret)

        keys_changed = False
        if not last_hash and current_hash:
            if update_hash:
                self.set_last_key_hash(current_hash, addon_id)
        elif (not current_hash and last_hash
              or last_hash != current_hash):
            if update_hash:
                self.set_last_key_hash(current_hash, addon_id)
            keys_changed = True
        return keys_changed
