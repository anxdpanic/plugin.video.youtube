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
    def __init__(self,
                 dialog,
                 heading,
                 message='',
                 total=None,
                 message_template=None):
        self._dialog = dialog()
        self._dialog.create(heading, message)

        self._position = None
        self._total = int(total) if total else 100

        self._message = message
        self._message_template = message_template
        self._template_params = {}

        # simple reset because KODI won't do it :(
        self.update(position=0)

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

    def reset_total(self, new_total, **kwargs):
        self._total = int(new_total)
        self.update(position=0, **kwargs)

    def update_total(self, new_total, **kwargs):
        self._total = int(new_total)
        self.update(steps=0, **kwargs)

    def grow_total(self, new_total):
        total = int(new_total)
        if total > self._total:
            self._total = total
        return self._total

    def update(self, steps=1, position=None, message=None, **template_params):
        if position is None:
            self._position += steps

            if not self._total:
                position = 0
            elif self._position >= self._total:
                position = 100
            else:
                position = int(100 * self._position / self._total)
        else:
            self._position = position

        if isinstance(message, string_type):
            self._message = message
        elif template_params and self._message_template:
            self._template_params.update(template_params)
            message = self._message_template.format(**self._template_params)
            self._message = message

        # Kodi 18 renamed XbmcProgressDialog.update argument line1 to message.
        # Only use positional arguments to maintain compatibility
        self._dialog.update(position, self._message)

    def is_aborted(self):
        raise NotImplementedError()
