import hashlib
import time

from .. import constants
from ..json_store import LoginTokenStore

__author__ = 'bromix'


class AccessManager(object):
    def __init__(self, context):
        self._settings = context.get_settings()
        self._jstore = LoginTokenStore()
        self._json = self._jstore.get_data()
        self._user = self._json['access_manager'].get('current_user', '')
        self._last_origin = self._json['access_manager'].get('last_origin', 'plugin.video.youtube')

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
        return self._json['access_manager'].get(self._user, {}).get('access_token', '')

    def get_refresh_token(self):
        """
        Returns the refresh token
        :return: refresh token
        """
        self._json = self._jstore.get_data()
        return self._json['access_manager'].get(self._user, {}).get('refresh_token', '')

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
        access_token = self._json['access_manager'].get(self._user, {}).get('access_token', '')
        expires = int(self._json['access_manager'].get(self._user, {}).get('token_expires', -1))

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
        self._json['access_manager'][self._user]['access_token'] = access_token

        if unix_timestamp is not None:
            self._json['access_manager'][self._user]['token_expires'] = int(unix_timestamp)

        if refresh_token is not None:
            self._json['access_manager'][self._user]['refresh_token'] = refresh_token

        self._jstore.save(self._json)
