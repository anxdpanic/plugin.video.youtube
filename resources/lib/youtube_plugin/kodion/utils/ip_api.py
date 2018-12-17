# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import requests


class Locator:

    def __init__(self, context):
        self._base_url = 'http://ip-api.com'
        self._response = dict()
        self._context = context

    def response(self):
        return self._response

    def locate_requester(self):
        request_url = '/'.join([self._base_url, 'json'])
        response = requests.get(request_url)
        self._response = response.json()

    def success(self):
        successful = self.response().get('status', 'fail') == 'success'
        if successful:
            self._context.log_debug('Location request was successful')
        else:
            self._context.log_error(self.response().get('message', 'Location request failed with no error message'))
        return successful

    def coordinates(self):
        lat = None
        lon = None
        if self.success():
            lat = self._response.get('lat')
            lon = self._response.get('lon')
        if lat is None or lon is None:
            self._context.log_error('No coordinates returned')
            return None
        else:
            self._context.log_debug('Coordinates found')
            return lat, lon
