# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .requests import BaseRequestsClass
from .. import logger


class Locator(BaseRequestsClass):

    def __init__(self):
        self._base_url = 'http://ip-api.com'
        self._response = {}

        super(Locator, self).__init__()

    def response(self):
        return self._response

    def locate_requester(self):
        request_url = '/'.join((self._base_url, 'json'))
        response = self.request(request_url)
        self._response = response and response.json() or {}

    def success(self):
        successful = self.response().get('status', 'fail') == 'success'
        if successful:
            logger.log_debug('Location request was successful')
        else:
            logger.log_error(self.response().get('message', 'Location request failed with no error message'))
        return successful

    def coordinates(self):
        lat = None
        lon = None
        if self.success():
            lat = self._response.get('lat')
            lon = self._response.get('lon')
        if lat is None or lon is None:
            logger.log_error('No coordinates returned')
            return None
        logger.log_debug('Coordinates found')
        return {'lat': lat, 'lon': lon}
