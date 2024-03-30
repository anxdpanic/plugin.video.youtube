# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .xbmc_progress_dialog import XbmcProgressDialog, XbmcProgressDialogBG
from ..abstract_context_ui import AbstractContextUI
from ...compatibility import xbmc, xbmcgui
from ...constants import ADDON_ID
from ...utils import to_unicode


class XbmcContextUI(AbstractContextUI):
    def __init__(self, xbmc_addon, context):
        super(XbmcContextUI, self).__init__()

        self._xbmc_addon = xbmc_addon

        self._context = context

    def create_progress_dialog(self, heading, text=None, background=False):
        if background:
            return XbmcProgressDialogBG(heading, text)

        return XbmcProgressDialog(heading, text)


    def on_keyboard_input(self, title, default='', hidden=False):
        # Starting with Gotham (13.X > ...)
        dialog = xbmcgui.Dialog()
        result = dialog.input(title, to_unicode(default), type=xbmcgui.INPUT_ALPHANUM)
        if result:
            text = to_unicode(result)
            return True, text

        return False, ''

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

    def on_remove_content(self, name):
        return self.on_yes_no_input(
            self._context.localize('content.remove.confirm'),
            self._context.localize('content.remove') % to_unicode(name),
        )

    def on_delete_content(self, name):
        return self.on_yes_no_input(
            self._context.localize('content.delete.confirm'),
            self._context.localize('content.delete') % to_unicode(name),
        )

    def on_clear_content(self, name):
        return self.on_yes_no_input(
            self._context.localize('content.clear.confirm'),
            self._context.localize('content.clear') % to_unicode(name),
        )

    def on_select(self, title, items=None, preselect=-1, use_details=False):
        if items is None:
            items = []

        result_map = {}
        dialog_items = []
        for idx, item in enumerate(items):
            if isinstance(item, (list, tuple)):
                num_details = len(item)
                if num_details > 2:
                    list_item = xbmcgui.ListItem(label=item[0],
                                                 label2=item[1],
                                                 offscreen=True)
                    if num_details > 3:
                        use_details = True
                        icon = item[3]
                        list_item.setArt({'icon': icon, 'thumb': icon})
                        if num_details > 4 and item[4]:
                            preselect = idx
                    result_map[idx] = item[2]
                    dialog_items.append(list_item)
                else:
                    result_map[idx] = item[1]
                    dialog_items.append(item[0])
            else:
                result_map[idx] = idx
                dialog_items.append(item)

        dialog = xbmcgui.Dialog()
        result = dialog.select(title,
                               dialog_items,
                               preselect=preselect,
                               useDetails=use_details)
        return result_map.get(result, -1)

    def show_notification(self,
                          message,
                          header='',
                          image_uri='',
                          time_ms=5000,
                          audible=True):
        _header = header
        if not _header:
            _header = self._context.get_name()

        _image = image_uri
        if not _image:
            _image = self._context.get_icon()

        _message = message.replace(',', ' ').replace('\n', ' ')

        xbmcgui.Dialog().notification(_header,
                                      _message,
                                      _image,
                                      time_ms,
                                      audible)

    def open_settings(self):
        self._xbmc_addon.openSettings()

    @staticmethod
    def refresh_container():
        # TODO: find out why the RunScript call is required
        # xbmc.executebuiltin("Container.Refresh")
        xbmc.executebuiltin('RunScript({addon_id},action/refresh)'.format(
            addon_id=ADDON_ID
        ))

    def reload_container(self, path=None):
        context = self._context
        xbmc.executebuiltin('ReplaceWindow(Videos, {0})'.format(
            context.create_uri(
                path or context.get_path(),
                dict(context.get_params(), refresh=True),
            )
        ))

    @staticmethod
    def set_property(property_id, value):
        property_id = '-'.join((ADDON_ID, property_id))
        xbmcgui.Window(10000).setProperty(property_id, value)

    @staticmethod
    def get_property(property_id):
        property_id = '-'.join((ADDON_ID, property_id))
        return xbmcgui.Window(10000).getProperty(property_id)

    @staticmethod
    def clear_property(property_id):
        property_id = '-'.join((ADDON_ID, property_id))
        xbmcgui.Window(10000).clearProperty(property_id)

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
        list_id = xbmcgui.Window(xbmcgui.getCurrentWindowId()).getFocusId()
        try:
            position = xbmc.getInfoLabel('Container.Position')
            next_position = int(position) + 1
            self._context.execute('SetFocus({list_id},{position})'.format(
                list_id=list_id, position=next_position
            ))
        except ValueError:
            pass

    @staticmethod
    def busy_dialog_active():
        dialog_id = xbmcgui.getCurrentWindowDialogId()
        if dialog_id == 10160 or dialog_id == 10138:
            return dialog_id
        return False
