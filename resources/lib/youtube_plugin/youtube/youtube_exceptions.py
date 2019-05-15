# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from .. import kodion


class LoginException(kodion.KodionException):
    pass


class YouTubeException(kodion.KodionException):
    pass


class InvalidGrant(kodion.KodionException):
    pass
