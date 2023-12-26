# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .json_store import JSONStore


class APIKeyStore(JSONStore):
    def __init__(self):
        super(APIKeyStore, self).__init__('api_keys.json')

    def set_defaults(self, reset=False):
        data = {} if reset else self.get_data()
        if 'keys' not in data:
            data = {'keys': {'personal': {'api_key': '', 'client_id': '', 'client_secret': ''}, 'developer': {}}}
        if 'personal' not in data['keys']:
            data['keys']['personal'] = {'api_key': '', 'client_id': '', 'client_secret': ''}
        if 'developer' not in data['keys']:
            data['keys']['developer'] = {}
        self.save(data)
