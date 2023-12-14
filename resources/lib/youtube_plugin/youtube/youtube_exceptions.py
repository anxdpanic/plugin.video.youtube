# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..kodion import KodionException
from ..kodion.network import InvalidJSONError


class LoginException(KodionException):
    pass


class YouTubeException(KodionException):
    pass


class InvalidGrant(KodionException):
    pass


class InvalidJSON(KodionException, InvalidJSONError):
    pass
