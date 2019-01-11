# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import xbmc
import xbmcgui

from ..abstract_context_ui import AbstractContextUI
from .xbmc_progress_dialog import XbmcProgressDialog
from .xbmc_progress_dialog_bg import XbmcProgressDialogBG
from ... import constants
from ... import utils


class XbmcContextUI(AbstractContextUI):
    def __init__(self, xbmc_addon, context):
        AbstractContextUI.__init__(self)

        self._xbmc_addon = xbmc_addon

        self._context = context
        self._view_mode = None

    def create_progress_dialog(self, heading, text=None, background=False):
        if background and self._context.get_system_version().get_version() > (12, 3):
            return XbmcProgressDialogBG(heading, text)

        return XbmcProgressDialog(heading, text)

    def get_skin_id(self):
        return xbmc.getSkinDir()

    def on_keyboard_input(self, title, default='', hidden=False):
        # fallback for Frodo
        if self._context.get_system_version().get_version() <= (12, 3):
            keyboard = xbmc.Keyboard(default, title, hidden)
            keyboard.doModal()
            if keyboard.isConfirmed() and keyboard.getText():
                text = utils.to_unicode(keyboard.getText())
                return True, text
            else:
                return False, u''

        # Starting with Gotham (13.X > ...)
        dialog = xbmcgui.Dialog()
        result = dialog.input(title, utils.to_unicode(default), type=xbmcgui.INPUT_ALPHANUM)
        if result:
            text = utils.to_unicode(result)
            return True, text

        return False, u''

    def on_numeric_input(self, title, default=''):
        dialog = xbmcgui.Dialog()
        result = dialog.input(title, str(default), type=xbmcgui.INPUT_NUMERIC)
        if result:
            return True, int(result)

        return False, None

    def on_yes_no_input(self, title, text, nolabel='', yeslabel=''):
        dialog = xbmcgui.Dialog()
        return dialog.yesno(title, text, nolabel=nolabel, yeslabel=yeslabel)

    def on_ok(self, title, text):
        dialog = xbmcgui.Dialog()
        return dialog.ok(title, text)

    def on_remove_content(self, content_name):
        text = self._context.localize(constants.localize.REMOVE_CONTENT) % utils.to_unicode(content_name)
        return self.on_yes_no_input(self._context.localize(constants.localize.CONFIRM_REMOVE), text)

    def on_delete_content(self, content_name):
        text = self._context.localize(constants.localize.DELETE_CONTENT) % utils.to_unicode(content_name)
        return self.on_yes_no_input(self._context.localize(constants.localize.CONFIRM_DELETE), text)

    def on_select(self, title, items=None):
        if items is None:
            items = []
        major_version = self._context.get_system_version().get_version()[0]
        if isinstance(items[0], tuple) and len(items[0]) == 4 and major_version <= 16:
            items = [(item[0], item[2]) for item in items]

        use_details = (isinstance(items[0], tuple) and len(items[0]) == 4 and major_version > 16)

        _dict = {}
        _items = []
        i = 0
        for item in items:
            if isinstance(item, tuple):
                if use_details:
                    new_item = xbmcgui.ListItem(label=item[0], label2=item[1])
                    new_item.setArt({'icon': item[3], 'thumb': item[3]})
                    _items.append(new_item)
                    _dict[i] = item[2]
                else:
                    _dict[i] = item[1]
                    _items.append(item[0])
            else:
                _dict[i] = i
                _items.append(item)

            i += 1

        dialog = xbmcgui.Dialog()
        if use_details:
            result = dialog.select(title, _items, useDetails=use_details)
        else:
            result = dialog.select(title, _items)

        return _dict.get(result, -1)

    def show_notification(self, message, header='', image_uri='', time_milliseconds=5000, audible=True):
        _header = header
        if not _header:
            _header = self._context.get_name()
        _header = utils.to_utf8(_header)

        _image = image_uri
        if not _image:
            _image = self._context.get_icon()

        _message = utils.to_utf8(message)
        try:
            _message = _message.replace(',', ' ')
            _message = _message.replace('\n', ' ')
        except TypeError:
            _message = _message.replace(b',', b' ')
            _message = _message.replace(b'\n', b' ')
            _message = utils.to_unicode(_message)
            _header = utils.to_unicode(_header)

        #  xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (_header, _message, time_milliseconds, _image))
        xbmcgui.Dialog().notification(_header, _message, _image, time_milliseconds, audible)

    def open_settings(self):
        self._xbmc_addon.openSettings()

    def refresh_container(self):
        script_uri = 'special://home/addons/%s/resources/lib/youtube_plugin/refresh.py' % self._context.get_id()
        xbmc.executebuiltin('RunScript(%s)' % script_uri)

    @staticmethod
    def get_info_label(value):
        return xbmc.getInfoLabel(value)

    @staticmethod
    def set_home_window_property(property_id, value):
        property_id = ''.join(['plugin.video.youtube-', property_id])
        xbmcgui.Window(10000).setProperty(property_id, value)

    @staticmethod
    def get_home_window_property(property_id):
        property_id = ''.join(['plugin.video.youtube-', property_id])
        return xbmcgui.Window(10000).getProperty(property_id) or None

    @staticmethod
    def clear_home_window_property(property_id):
        property_id = ''.join(['plugin.video.youtube-', property_id])
        xbmcgui.Window(10000).clearProperty(property_id)

    @staticmethod
    def bold(value):
        return ''.join(['[B]', value, '[/B]'])

    @staticmethod
    def uppercase(value):
        return ''.join(['[UPPERCASE]', value, '[/UPPERCASE]'])

    @staticmethod
    def color(color, value):
        return ''.join(['[COLOR=', color.lower(), ']', value, '[/COLOR]'])

    def set_focus_next_item(self):
        cid = xbmcgui.Window(xbmcgui.getCurrentWindowId()).getFocusId()
        try:
            current_position = int(self.get_info_label('Container.Position')) + 1
            self._context.execute('SetFocus(%s,%s)' % (cid, str(current_position)))
        except ValueError:
            pass
