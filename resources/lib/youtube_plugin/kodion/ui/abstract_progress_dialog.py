# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..compatibility import string_type


class AbstractProgressDialog(object):
    def __init__(self, dialog, heading, text, total=100):
        self._dialog = dialog()
        self._dialog.create(heading, text)

        # simple reset because KODI won't do it :(
        self._total = int(total)
        self._position = 1
        self.update(steps=-1)

    def __enter__(self):
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self.close()

    def get_total(self):
        return self._total

    def get_position(self):
        return self._position

    def close(self):
        if self._dialog:
            self._dialog.close()
            self._dialog = None

    def set_total(self, total):
        self._total = int(total)

    def update(self, steps=1, text=None):
        self._position += steps

        if not self._total:
            position = 0
        elif self._position >= self._total:
            position = 100
        else:
            position = int(100 * self._position / self._total)

        if isinstance(text, string_type):
            self._dialog.update(percent=position, message=text)
        else:
            self._dialog.update(percent=position)

    def is_aborted(self):
        raise NotImplementedError()
