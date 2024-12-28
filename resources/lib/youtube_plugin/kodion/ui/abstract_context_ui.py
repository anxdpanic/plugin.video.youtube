# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..compatibility import string_type


class AbstractContextUI(object):
    def __init__(self):
        pass

    def create_progress_dialog(self,
                               heading,
                               message='',
                               background=False,
                               message_template=None):
        raise NotImplementedError()

    def get_view_manager(self):
        raise NotImplementedError()

    def on_keyboard_input(self, title, default='', hidden=False):
        raise NotImplementedError()

    def on_numeric_input(self, title, default=''):
        raise NotImplementedError()

    def on_yes_no_input(self, title, text, nolabel='', yeslabel=''):
        raise NotImplementedError()

    def on_ok(self, title, text):
        raise NotImplementedError()

    def on_remove_content(self, name):
        raise NotImplementedError()

    def on_delete_content(self, name):
        raise NotImplementedError()

    def on_clear_content(self, name):
        raise NotImplementedError()

    def on_select(self, title, items=None, preselect=-1, use_details=False):
        raise NotImplementedError()

    def show_notification(self, message, header='', image_uri='',
                          time_ms=5000, audible=True):
        raise NotImplementedError()

    @staticmethod
    def refresh_container():
        """
        Needs to be implemented by a mock for testing or the real deal.
        This will refresh the current container or list.
        :return:
        """
        raise NotImplementedError()


class AbstractProgressDialog(object):
    def __init__(self,
                 dialog,
                 heading,
                 message='',
                 total=0,
                 message_template=None,
                 template_params=None):
        self._dialog = dialog()
        self._dialog.create(heading, message)

        self._position = None
        self._total = total

        self._message = message
        if message_template:
            self._message_template = message_template
            self._template_params = {
                '_progress': (0, self._total),
                '_current': 0,
                '_total': self._total,
            }
            if template_params:
                self._template_params.update(template_params)
        else:
            self._message_template = None
            self._template_params = None

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

    def is_aborted(self):
        return getattr(self._dialog, 'iscanceled', bool)()

    def set_total(self, total):
        self._total = int(total)

    def reset_total(self, new_total, **kwargs):
        self._total = int(new_total)
        self.update(position=0, **kwargs)

    def update_total(self, new_total, **kwargs):
        self._total = int(new_total)
        self.update(steps=0, **kwargs)

    def grow_total(self, new_total=None, delta=None):
        if delta:
            delta = int(delta)
            self._total += delta
        elif new_total:
            total = int(new_total)
            if total > self._total:
                self._total = total
        return self._total

    def update(self, steps=1, position=None, message=None, **template_params):
        if not self._dialog:
            return

        if position is None:
            self._position += steps
        else:
            self._position = position

        if not self._total:
            percent = 0
        elif self._position >= self._total:
            percent = 100
            self._total = self._position
        else:
            percent = int(100 * self._position / self._total)

        if isinstance(message, string_type):
            self._message = message
        elif self._message_template:
            if template_params:
                self._template_params.update(template_params)
            template_params = self._template_params
            progress = (self._position, self._total)
            template_params['_progress'] = progress
            template_params['_current'], template_params['_total'] = progress
            message = self._message_template.format(
                *template_params['_progress'],
                **template_params
            )
            self._message = message

        # Kodi 18 renamed XbmcProgressDialog.update argument line1 to message.
        # Only use positional arguments to maintain compatibility
        self._dialog.update(percent, self._message)
