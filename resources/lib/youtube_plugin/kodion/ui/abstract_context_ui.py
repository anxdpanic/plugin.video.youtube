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

    def refresh_container(self, force=False, stacklevel=None):
        """
        Needs to be implemented by a mock for testing or the real deal.
        This will refresh the current container or list.
        :return:
        """
        raise NotImplementedError()

    def focus_container(self, container_id=None, position=None):
        raise NotImplementedError()

    @staticmethod
    def get_infobool(name):
        raise NotImplementedError()

    @staticmethod
    def get_infolabel(name):
        raise NotImplementedError()

    def get_container(self,
                      container_type=True,
                      check_ready=False,
                      stacklevel=None):
        raise NotImplementedError()

    @classmethod
    def get_container_id(cls, container_type=True):
        raise NotImplementedError()

    @classmethod
    def get_container_bool(cls,
                           name,
                           container_id=True,
                           strict=True,
                           stacklevel=None):
        raise NotImplementedError()

    @classmethod
    def get_container_info(cls,
                           name,
                           container_id=True,
                           strict=True,
                           stacklevel=None):
        raise NotImplementedError()

    @classmethod
    def get_listitem_bool(cls,
                          name,
                          container_id=True,
                          strict=True,
                          stacklevel=None):
        raise NotImplementedError()

    @classmethod
    def get_listitem_info(cls,
                          name,
                          container_id=True,
                          strict=True,
                          stacklevel=None):
        raise NotImplementedError()

    @classmethod
    def get_listitem_property(cls,
                              name,
                              container_id=True,
                              strict=True,
                              stacklevel=None):
        raise NotImplementedError()

    @classmethod
    def set_property(cls,
                     property_id,
                     value='true',
                     stacklevel=2,
                     process=None,
                     log_value=None,
                     log_process=None,
                     raw=False):
        raise NotImplementedError()

    @classmethod
    def get_property(cls,
                     property_id,
                     stacklevel=2,
                     process=None,
                     log_value=None,
                     log_process=None,
                     raw=False,
                     as_bool=False,
                     default=False):
        raise NotImplementedError()

    @classmethod
    def pop_property(cls,
                     property_id,
                     stacklevel=2,
                     process=None,
                     log_value=None,
                     log_process=None,
                     raw=False,
                     as_bool=False,
                     default=False):
        raise NotImplementedError()

    @classmethod
    def clear_property(cls, property_id, stacklevel=2, raw=False):
        raise NotImplementedError()

    @staticmethod
    def bold(value, cr_before=0, cr_after=0):
        return ''.join((
            '[CR]' * cr_before,
            '[B]', value, '[/B]',
            '[CR]' * cr_after,
        ))

    @staticmethod
    def uppercase(value, cr_before=0, cr_after=0):
        return ''.join((
            '[CR]' * cr_before,
            '[UPPERCASE]', value, '[/UPPERCASE]',
            '[CR]' * cr_after,
        ))

    @staticmethod
    def color(color, value, cr_before=0, cr_after=0):
        return ''.join((
            '[CR]' * cr_before,
            '[COLOR=', color.lower(), ']', value, '[/COLOR]',
            '[CR]' * cr_after,
        ))

    @staticmethod
    def light(value, cr_before=0, cr_after=0):
        return ''.join((
            '[CR]' * cr_before,
            '[LIGHT]', value, '[/LIGHT]',
            '[CR]' * cr_after,
        ))

    @staticmethod
    def italic(value, cr_before=0, cr_after=0):
        return ''.join((
            '[CR]' * cr_before,
            '[I]', value, '[/I]',
            '[CR]' * cr_after,
        ))

    @staticmethod
    def indent(number=1, value='', cr_before=0, cr_after=0):
        return ''.join((
            '[CR]' * cr_before,
            '[TABS]', str(number), '[/TABS]', value,
            '[CR]' * cr_after,
        ))

    @staticmethod
    def new_line(value=1, cr_before=0, cr_after=0):
        if isinstance(value, int):
            return '[CR]' * value
        return ''.join((
            '[CR]' * cr_before,
            value,
            '[CR]' * cr_after,
        ))

    def set_focus_next_item(self):
        raise NotImplementedError()

    @staticmethod
    def busy_dialog_active():
        raise NotImplementedError()
