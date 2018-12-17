# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""


class KodionException(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)
        self._message = message

    def get_message(self):
        return self._message
