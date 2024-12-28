# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""


class KodionException(Exception):
    def __init__(self, message='', **kwargs):
        super(KodionException, self).__init__(message)
        attrs = self.__dict__
        for attr, value in kwargs.items():
            if attr not in attrs:
                setattr(self, attr, value)

    def get_message(self):
        return str(self)
