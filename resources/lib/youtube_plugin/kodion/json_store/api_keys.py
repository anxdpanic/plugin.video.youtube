# -*- coding: utf-8 -*-
"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

from . import JSONStore


class APIKeyStore(JSONStore):
    def __init__(self):
        JSONStore.__init__(self, 'api_keys.json')

    def set_defaults(self):
        data = self.get_data()
        if 'keys' not in data:
            data = {'keys': {'personal': {'api_key': '', 'client_id': '', 'client_secret': ''}, 'developer': {}}}
        if 'personal' not in data['keys']:
            data['keys']['personal'] = {'api_key': '', 'client_id': '', 'client_secret': ''}
        if 'developer' not in data['keys']:
            data['keys']['developer'] = {}
        self.save(data)
