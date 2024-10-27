# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .requests import BaseRequestsClass


class Locator(BaseRequestsClass):

    def __init__(self, context):
        self._base_url = 'http://ip-api.com'
        self._response = {}

        super(Locator, self).__init__(context=context)

    def response(self):
        return self._response

    def locate_requester(self):
        request_url = '/'.join((self._base_url, 'json'))
        response = self.request(request_url)
        self._response = response and response.json() or {}

    def success(self):
        successful = self.response().get('status', 'fail') == 'success'
        if successful:
            self.log_debug('Location request was successful')
        else:
            msg = 'Location request failed with no error message'
            self.log_error(self.response().get('message') or msg)
        return successful

    def coordinates(self):
        lat = None
        lon = None
        if self.success():
            lat = self._response.get('lat')
            lon = self._response.get('lon')
        if lat is None or lon is None:
            self.log_error('No coordinates returned')
            return None
        self.log_debug('Coordinates found')
        return {'lat': lat, 'lon': lon}
