# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""


class RegisterProviderPath(object):
    def __init__(self, re_path):
        self._kodion_re_path = re_path

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # only use a wrapper if you need extra code to be run here
            return func(*args, **kwargs)

        wrapper.kodion_re_path = self._kodion_re_path
        return wrapper
