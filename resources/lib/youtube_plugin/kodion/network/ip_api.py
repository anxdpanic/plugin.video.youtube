# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .requests import BaseRequestsClass
from .. import logging


class Locator(BaseRequestsClass):
    log = logging.getLogger(__name__)

    def __init__(self, context):
        self._base_url = 'http://ip-api.com'
        self._response = {}

        super(Locator, self).__init__(context=context)

    def response(self):
        return self._response

    def locate_requester(self):
        request_url = '/'.join((self._base_url, 'json'))
        response = self.request(request_url)
        if response is None:
            self._response = {}
            return
        with response:
            self._response = response.json()

    def success(self):
        response = self.response()
        successful = response.get('status', 'fail') == 'success'
        if successful:
            self.log.debug('Request successful')
        else:
            self.log.error(('Request failed', 'Message: %s'),
                           response.get('message', 'Unknown'))
        return successful

    def coordinates(self):
        lat = None
        lon = None
        if self.success():
            lat = self._response.get('lat')
            lon = self._response.get('lon')
        if lat is None or lon is None:
            self.log.error('No coordinates returned')
            return None
        self.log.debug('Coordinates found')
        return {'lat': lat, 'lon': lon}
