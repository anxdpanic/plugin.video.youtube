import uuid
import time

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

    def get_new_user(self, user_name):
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
        if settings_playlist_id and (current_playlist_id != settings_playlist_id):
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
        :param user: string, origin
        :param switch_to: boolean, change last origin
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
        :return:
        """
        self._json = self._jstore.get_data()
        self._json['access_manager']['users'][self._user]['access_token'] = access_token

        if unix_timestamp is not None:
            self._json['access_manager']['users'][self._user]['token_expires'] = int(unix_timestamp)

        if refresh_token is not None:
            self._json['access_manager']['users'][self._user]['refresh_token'] = refresh_token

        self._jstore.save(self._json)
