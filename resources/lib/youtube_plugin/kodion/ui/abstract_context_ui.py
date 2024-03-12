# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals


class AbstractContextUI(object):
    def __init__(self):
        pass

    def create_progress_dialog(self, heading, text=None, background=False):
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

    def on_remove_content(self, content_name):
        raise NotImplementedError()

    def on_select(self, title, items=None, preselect=-1, use_details=False):
        raise NotImplementedError()

    def open_settings(self):
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
