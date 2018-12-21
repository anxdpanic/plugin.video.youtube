# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import uuid
from . import JSONStore


# noinspection PyTypeChecker
class LoginTokenStore(JSONStore):
    def __init__(self):
        JSONStore.__init__(self, 'access_manager.json')

    def set_defaults(self):
        data = self.get_data()
        if 'access_manager' not in data:
            data = {'access_manager': {'users': {'0': {'access_token': '', 'refresh_token': '', 'token_expires': -1,
                                                       'last_key_hash': '', 'name': 'Default', 'watch_later': ' WL', 'watch_history': 'HL'}}}}
        if 'users' not in data['access_manager']:
            data['access_manager']['users'] = {'0': {'access_token': '', 'refresh_token': '', 'token_expires': -1,
                                                     'last_key_hash': '', 'name': 'Default', 'watch_later': ' WL', 'watch_history': 'HL'}}
        if '0' not in data['access_manager']['users']:
            data['access_manager']['users']['0'] = {'access_token': '', 'refresh_token': '', 'token_expires': -1,
                                                    'last_key_hash': '', 'name': 'Default', 'watch_later': ' WL', 'watch_history': 'HL'}
        if 'current_user' not in data['access_manager']:
            data['access_manager']['current_user'] = '0'
        if 'last_origin' not in data['access_manager']:
            data['access_manager']['last_origin'] = 'plugin.video.youtube'
        if 'developers' not in data['access_manager']:
            data['access_manager']['developers'] = dict()

        # clean up
        if data['access_manager']['current_user'] == 'default':
            data['access_manager']['current_user'] = '0'
        if 'access_token' in data['access_manager']:
            del data['access_manager']['access_token']
        if 'refresh_token' in data['access_manager']:
            del data['access_manager']['refresh_token']
        if 'token_expires' in data['access_manager']:
            del data['access_manager']['token_expires']
        if 'default' in data['access_manager']:
            if (data['access_manager']['default'].get('access_token') or
                data['access_manager']['default'].get('refresh_token')) and \
                    (not data['access_manager']['users']['0'].get('access_token') and
                     not data['access_manager']['users']['0'].get('refresh_token')):
                if 'name' not in data['access_manager']['default']:
                    data['access_manager']['default']['name'] = 'Default'
                data['access_manager']['users']['0'] = data['access_manager']['default']
            del data['access_manager']['default']
        # end clean up

        current_user = data['access_manager']['current_user']
        if 'watch_later' not in data['access_manager']['users'][current_user]:
            data['access_manager']['users'][current_user]['watch_later'] = ' WL'
        if 'watch_history' not in data['access_manager']['users'][current_user]:
            data['access_manager']['users'][current_user]['watch_history'] = 'HL'

        # ensure all users have uuid
        uuids = list()
        uuid_update = False
        for k in list(data['access_manager']['users'].keys()):
            c_uuid = data['access_manager']['users'][k].get('id')
            if c_uuid:
                uuids.append(c_uuid)
            else:
                if not uuid_update:
                    uuid_update = True

        if uuid_update:
            for k in list(data['access_manager']['users'].keys()):
                c_uuid = data['access_manager']['users'][k].get('id')
                if not c_uuid:
                    g_uuid = uuid.uuid4().hex
                    while g_uuid in uuids:
                        g_uuid = uuid.uuid4().hex
                    data['access_manager']['users'][k]['id'] = g_uuid
        # end uuid check

        self.save(data)
