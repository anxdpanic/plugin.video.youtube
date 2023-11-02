# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""


class AbstractProgressDialog(object):
    def __init__(self, total=100):
        self._total = int(total)
        self._position = 0

    def get_total(self):
        return self._total

    def get_position(self):
        return self._position

    def close(self):
        raise NotImplementedError()

    def set_total(self, total):
        self._total = int(total)

    def update(self, steps=1, text=None):
        raise NotImplementedError()

    def is_aborted(self):
        raise NotImplementedError()
