# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals


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

    @staticmethod
    def on_keyboard_input(title, default='', hidden=False):
        raise NotImplementedError()

    @staticmethod
    def on_numeric_input(title, default=''):
        raise NotImplementedError()

    @staticmethod
    def on_yes_no_input(title, text, nolabel='', yeslabel=''):
        raise NotImplementedError()

    @staticmethod
    def on_ok(title, text):
        raise NotImplementedError()

    def on_remove_content(self, name):
        raise NotImplementedError()

    def on_delete_content(self, name):
        raise NotImplementedError()

    def on_clear_content(self, name):
        raise NotImplementedError()

    @staticmethod
    def on_select(title, items=None, preselect=-1, use_details=False):
        raise NotImplementedError()

    def show_notification(self, message, header='', image_uri='',
                          time_ms=5000, audible=True):
        raise NotImplementedError()

    @staticmethod
    def on_busy():
        raise NotImplementedError()

    @staticmethod
    def refresh_container():
        """
        Needs to be implemented by a mock for testing or the real deal.
        This will refresh the current container or list.
        :return:
        """
        raise NotImplementedError()

    @staticmethod
    def get_infobool(name):
        raise NotImplementedError()

    @staticmethod
    def get_infolabel(name):
        raise NotImplementedError()

    @classmethod
    def get_container_bool(cls,
                           name,
                           container_id=None,
                           strict=True,
                           stacklevel=2):
        raise NotImplementedError()

    @classmethod
    def get_container_info(cls,
                           name,
                           container_id=None,
                           strict=True,
                           stacklevel=2):
        raise NotImplementedError()

    @classmethod
    def get_listitem_bool(cls,
                          name,
                          container_id=None,
                          strict=True,
                          stacklevel=2):
        raise NotImplementedError()

    @classmethod
    def get_listitem_property(cls,
                              name,
                              container_id=None,
                              strict=True,
                              stacklevel=2):
        raise NotImplementedError()

    @classmethod
    def get_listitem_info(cls,
                          name,
                          container_id=None,
                          strict=True,
                          stacklevel=2):
        raise NotImplementedError()
