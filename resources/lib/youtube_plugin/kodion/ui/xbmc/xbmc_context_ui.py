# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from weakref import proxy

from ..abstract_context_ui import AbstractContextUI
from ... import logging
from ...compatibility import string_type, xbmc, xbmcgui
from ...constants import (
    ADDON_ID,
    BOOL_FROM_STR,
    BUSY_FLAG,
    CONTAINER_FOCUS,
    CONTAINER_ID,
    CONTAINER_LISTITEM_INFO,
    CONTAINER_LISTITEM_PROP,
    CONTAINER_POSITION,
    CURRENT_CONTAINER_INFO,
    CURRENT_ITEM,
    HAS_FILES,
    HAS_FOLDERS,
    HAS_PARENT,
    HIDE_PROGRESS,
    LISTITEM_INFO,
    LISTITEM_PROP,
    NUM_ALL_ITEMS,
    PLUGIN_CONTAINER_INFO,
    PROPERTY,
    REFRESH_CONTAINER,
    UPDATING,
    URI,
)
from ...utils.convert_format import to_unicode


class XbmcContextUI(AbstractContextUI):
    log = logging.getLogger(__name__)

    def __init__(self, context):
        super(XbmcContextUI, self).__init__()
        self._context = context

    def create_progress_dialog(self,
                               heading,
                               message='',
                               total=None,
                               background=False,
                               message_template=None,
                               template_params=None,
                               hide_progress=None):
        if not message_template and background:
            message_template = '{_message} {_current}/{_total}'

        return XbmcProgressDialog(
            ui=proxy(self),
            dialog=(xbmcgui.DialogProgressBG
                    if background else
                    xbmcgui.DialogProgress),
            background=background,
            heading=heading,
            message=message or self._context.localize('please_wait'),
            total=int(total) if total is not None else 0,
            message_template=message_template,
            template_params=template_params,
            hide=(
                self._context.get_param(HIDE_PROGRESS)
                if hide_progress is None else
                hide_progress
            ),
        )

    @staticmethod
    def on_keyboard_input(title, default='', hidden=False):
        # Starting with Gotham (13.X > ...)
        dialog = xbmcgui.Dialog()
        result = dialog.input(title,
                              to_unicode(default),
                              type=xbmcgui.INPUT_ALPHANUM)
        if result:
            text = to_unicode(result)
            return True, text

        return False, ''

    @staticmethod
    def on_numeric_input(title, default=''):
        dialog = xbmcgui.Dialog()
        result = dialog.input(title, str(default), type=xbmcgui.INPUT_NUMERIC)
        if result:
            return True, int(result)

        return False, None

    @staticmethod
    def on_yes_no_input(title, text, nolabel='', yeslabel=''):
        dialog = xbmcgui.Dialog()
        return dialog.yesno(title, text, nolabel=nolabel, yeslabel=yeslabel)

    @staticmethod
    def on_ok(title, text):
        dialog = xbmcgui.Dialog()
        return dialog.ok(title, text)

    def on_remove_content(self, name):
        return self.on_yes_no_input(
            self._context.localize('content.remove'),
            self._context.localize('content.remove.check.x', to_unicode(name)),
        )

    def on_delete_content(self, name):
        return self.on_yes_no_input(
            self._context.localize('content.delete'),
            self._context.localize('content.delete.check.x', to_unicode(name)),
        )

    def on_clear_content(self, name):
        return self.on_yes_no_input(
            self._context.localize('content.clear'),
            self._context.localize('content.clear.check.x', to_unicode(name)),
        )

    @staticmethod
    def on_select(title, items=None, preselect=-1, use_details=False):
        if isinstance(items, (list, tuple)):
            items = enumerate(items)
        elif isinstance(items, dict):
            items = items.items()
        else:
            return -1

        result_map = {}
        dialog_items = []

        for idx, item in items:
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

    @staticmethod
    def on_busy():
        return XbmcBusyDialog()

    def refresh_container(self, force=False, stacklevel=None):
        if force:
            if self.get_property(REFRESH_CONTAINER) == BUSY_FLAG:
                self.set_property(REFRESH_CONTAINER)
                xbmc.executebuiltin('Container.Refresh')
            return True

        stacklevel = 2 if stacklevel is None else stacklevel + 1

        container = self.get_container()
        if not container['is_plugin'] or not container['is_loaded']:
            self.log.debug('No plugin container loaded - cancelling refresh',
                           stacklevel=stacklevel)
            return False

        if container['is_active']:
            self.set_property(REFRESH_CONTAINER)
            xbmc.executebuiltin('Container.Refresh')
            return True

        self.set_property(REFRESH_CONTAINER, BUSY_FLAG)
        self.log.debug('Plugin container not active - deferring refresh',
                       stacklevel=stacklevel)
        return None

    def focus_container(self, container_id=None, position=None):
        if position is None:
            return

        container = self.get_container()
        if not all(container.values()):
            return

        if container_id is None:
            container_id = container['id']
        elif not container_id:
            return

        if not isinstance(container_id, int):
            try:
                container_id = int(container_id)
            except (TypeError, ValueError):
                return

        if self.get_container_bool(HAS_PARENT, container_id):
            offset = 0
        else:
            offset = -1

        if not isinstance(position, int):
            if position == 'next':
                position = self.get_container_info(CURRENT_ITEM, container_id)
                offset += 1
            elif position == 'previous':
                position = self.get_container_info(CURRENT_ITEM, container_id)
                offset -= 1
            elif position == 'current':
                position = (
                        self.get_property(CONTAINER_POSITION)
                        or self.get_container_info(CURRENT_ITEM, container_id)
                )
            try:
                position = int(position)
            except (TypeError, ValueError):
                return

        xbmc.executebuiltin('SetFocus({0},{1},absolute)'.format(
            container_id,
            position + offset,
        ))

    @staticmethod
    def get_infobool(name, _bool=xbmc.getCondVisibility):
        return _bool(name)

    @staticmethod
    def get_infolabel(name, _label=xbmc.getInfoLabel):
        return _label(name)

    def get_container(self,
                      container_type=True,
                      check_ready=False,
                      stacklevel=None,
                      _url='plugin://{0}/'.format(ADDON_ID)):
        stacklevel = 2 if stacklevel is None else stacklevel + 1
        container_id = self.get_container_id(container_type)
        _container_id = container_id if container_type else container_type
        is_plugin = self.get_listitem_info(
            URI,
            _container_id,
            stacklevel=stacklevel,
        ).startswith(_url)
        if check_ready and container_type is True and not is_plugin:
            is_active = False
            is_loaded = False
        else:
            is_active = not self.busy_dialog_active(all_modals=True)
            is_loaded = (
                    not self.get_container_bool(
                        UPDATING,
                        _container_id,
                        stacklevel=stacklevel,
                    )
                    and (
                            self.get_container_info(
                                NUM_ALL_ITEMS,
                                _container_id,
                                stacklevel=stacklevel,
                            )
                            or
                            self.get_container_bool(
                                HAS_FOLDERS,
                                _container_id,
                                stacklevel=stacklevel
                            )
                            or
                            self.get_container_bool(
                                HAS_FILES,
                                _container_id,
                                stacklevel=stacklevel
                            )
                            or
                            self.get_container_bool(
                                HAS_PARENT,
                                _container_id,
                                stacklevel=stacklevel,
                            )
                    )
            )

        if check_ready:
            return is_active and is_loaded
        return {
            'is_plugin': is_plugin,
            'id': container_id,
            'is_active': is_active,
            'is_loaded': is_loaded,
        }

    @classmethod
    def get_container_id(cls,
                         container_type=True,
                         _label=xbmc.getInfoLabel):
        if container_type is True:
            return _label(PROPERTY % CONTAINER_ID)
        if container_type is None:
            return None
        return _label('System.CurrentControlID')

    @classmethod
    def get_container_bool(cls,
                           name,
                           container_id=True,
                           strict=True,
                           stacklevel=None,
                           _bool=xbmc.getCondVisibility,
                           _label=xbmc.getInfoLabel):
        if container_id is True:
            container_id = _label(PROPERTY % CONTAINER_ID)
        elif container_id is None:
            strict = False
        elif container_id is False:
            container_id = _label('System.CurrentControlID')
            strict = False

        stacklevel = 2 if stacklevel is None else stacklevel + 1

        if container_id:
            out = _bool(PLUGIN_CONTAINER_INFO % (container_id, name))
            log_msg = 'Container {container_id} used for {name!r}: {out!r}'
        elif strict:
            out = False
            log_msg = None
            cls.log.warning('Plugin container not found for %r', name,
                            stacklevel=stacklevel)
        else:
            out = _bool(CURRENT_CONTAINER_INFO % name)
            log_msg = 'Current container used for {name!r}: {out!r}'
        if log_msg and cls.log.verbose_logging:
            cls.log.debug(log_msg,
                          container_id=container_id,
                          name=name,
                          out=out,
                          stacklevel=stacklevel)
        return out

    @classmethod
    def get_container_info(cls,
                           name,
                           container_id=True,
                           strict=True,
                           stacklevel=None,
                           _label=xbmc.getInfoLabel):
        if container_id is True:
            container_id = _label(PROPERTY % CONTAINER_ID)
        elif container_id is None:
            strict = False
        elif container_id is False:
            container_id = _label('System.CurrentControlID')
            strict = False

        stacklevel = 2 if stacklevel is None else stacklevel + 1

        if container_id:
            out = _label(PLUGIN_CONTAINER_INFO % (container_id, name))
            log_msg = 'Container {container_id} used for {name!r}: {out!r}'
        elif strict:
            out = False
            log_msg = None
            cls.log.warning('Plugin container not found for %r', name,
                            stacklevel=stacklevel)
        else:
            out = _label(CURRENT_CONTAINER_INFO % name)
            log_msg = 'Current container used for {name!r}: {out!r}'
        if log_msg and cls.log.verbose_logging:
            cls.log.debug(log_msg,
                          container_id=container_id,
                          name=name,
                          out=out,
                          stacklevel=stacklevel)
        return out

    @classmethod
    def get_listitem_bool(cls,
                          name,
                          container_id=True,
                          strict=True,
                          stacklevel=None,
                          _bool=xbmc.getCondVisibility,
                          _label=xbmc.getInfoLabel):
        if container_id is True:
            container_id = _label(PROPERTY % CONTAINER_ID)
        elif container_id is None:
            strict = False
        elif container_id is False:
            container_id = _label('System.CurrentControlID')
            strict = False

        stacklevel = 2 if stacklevel is None else stacklevel + 1

        if container_id:
            out = _bool(CONTAINER_LISTITEM_INFO % (container_id, name))
            log_msg = 'Container {container_id} used for {name!r}: {out!r}'
        elif strict:
            out = False
            log_msg = None
            cls.log.warning('Plugin container not found for %r', name,
                            stacklevel=stacklevel)
        else:
            out = _bool(LISTITEM_INFO % name)
            log_msg = 'Current container used for {name!r}: {out!r}'
        if log_msg and cls.log.verbose_logging:
            cls.log.debug(log_msg,
                          container_id=container_id,
                          name=name,
                          out=out,
                          stacklevel=stacklevel)
        return out

    @classmethod
    def get_listitem_info(cls,
                          name,
                          container_id=True,
                          strict=True,
                          stacklevel=None,
                          _label=xbmc.getInfoLabel):
        if container_id is True:
            container_id = _label(PROPERTY % CONTAINER_ID)
        elif container_id is None:
            strict = False
        elif container_id is False:
            container_id = _label('System.CurrentControlID')
            strict = False

        stacklevel = 2 if stacklevel is None else stacklevel + 1

        if container_id:
            out = _label(CONTAINER_LISTITEM_INFO % (container_id, name))
            log_msg = 'Container {container_id} used for {name!r}: {out!r}'
        elif strict:
            out = ''
            log_msg = None
            cls.log.warning('Plugin container not found for %r', name,
                            stacklevel=stacklevel)
        else:
            out = _label(LISTITEM_INFO % name)
            log_msg = 'Current container used for {name!r}: {out!r}'
        if log_msg and cls.log.verbose_logging:
            cls.log.debug(log_msg,
                          container_id=container_id,
                          name=name,
                          out=out,
                          stacklevel=stacklevel)
        return out

    @classmethod
    def get_listitem_property(cls,
                              name,
                              container_id=True,
                              strict=True,
                              stacklevel=None,
                              _label=xbmc.getInfoLabel):
        if container_id is True:
            container_id = _label(PROPERTY % CONTAINER_ID)
        elif container_id is None:
            strict = False
        elif container_id is False:
            container_id = _label('System.CurrentControlID')
            strict = False

        stacklevel = 2 if stacklevel is None else stacklevel + 1

        if container_id:
            out = _label(CONTAINER_LISTITEM_PROP % (container_id, name))
            log_msg = 'Container {container_id} used for {name!r}: {out!r}'
        elif strict:
            out = ''
            log_msg = None
            cls.log.warning('Plugin container not found for %r', name,
                            stacklevel=stacklevel)
        else:
            out = _label(LISTITEM_PROP % name)
            log_msg = 'Current container used for {name!r}: {out!r}'
        if log_msg and cls.log.verbose_logging:
            cls.log.debug(log_msg,
                          container_id=container_id,
                          name=name,
                          out=out,
                          stacklevel=stacklevel)
        return out

    @classmethod
    def set_property(cls,
                     property_id,
                     value='true',
                     stacklevel=2,
                     process=None,
                     log_value=None,
                     log_process=None,
                     raw=False):
        if log_value is None:
            log_value = value
        if log_process:
            log_value = log_process(log_value)
        cls.log.debug_trace('Set property {property_id!r}: {value!r}',
                            property_id=property_id,
                            value=log_value,
                            stacklevel=stacklevel)
        _property_id = property_id if raw else '-'.join((ADDON_ID, property_id))
        if process:
            value = process(value)
        xbmcgui.Window(10000).setProperty(_property_id, value)
        return value

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
        _property_id = property_id if raw else '-'.join((ADDON_ID, property_id))
        value = xbmcgui.Window(10000).getProperty(_property_id)
        if log_value is None:
            log_value = value
        if log_process:
            log_value = log_process(log_value)
        cls.log.debug_trace('Get property {property_id!r}: {value!r}',
                            property_id=property_id,
                            value=log_value,
                            stacklevel=stacklevel)
        if process:
            value = process(value)
        return BOOL_FROM_STR.get(value, default) if as_bool else value

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
        _property_id = property_id if raw else '-'.join((ADDON_ID, property_id))
        window = xbmcgui.Window(10000)
        value = window.getProperty(_property_id)
        if value:
            window.clearProperty(_property_id)
            if process:
                value = process(value)
        if log_value is None:
            log_value = value
        if log_value and log_process:
            log_value = log_process(log_value)
        cls.log.debug_trace('Pop property {property_id!r}: {value!r}',
                            property_id=property_id,
                            value=log_value,
                            stacklevel=stacklevel)
        return BOOL_FROM_STR.get(value, default) if as_bool else value

    @classmethod
    def clear_property(cls, property_id, stacklevel=2, raw=False):
        cls.log.debug_trace('Clear property {property_id!r}',
                            property_id=property_id,
                            stacklevel=stacklevel)
        _property_id = property_id if raw else '-'.join((ADDON_ID, property_id))
        xbmcgui.Window(10000).clearProperty(_property_id)
        return None

    def set_focus_next_item(self):
        self._context.send_notification(method=CONTAINER_FOCUS,
                                        data={
                                            CONTAINER_POSITION: 'next',
                                        })

    @staticmethod
    def busy_dialog_active(all_modals=False, dialog_ids=frozenset((
            10100,  # WINDOW_DIALOG_YES_NO
            10101,  # WINDOW_DIALOG_PROGRESS
            10103,  # WINDOW_DIALOG_KEYBOARD
            10109,  # WINDOW_DIALOG_NUMERIC
            10138,  # WINDOW_DIALOG_BUSY
            10151,  # WINDOW_DIALOG_EXT_PROGRESS
            10160,  # WINDOW_DIALOG_BUSY_NOCANCEL
            12000,  # WINDOW_DIALOG_SELECT
            12002,  # WINDOW_DIALOG_OK
    ))):
        if all_modals and xbmc.getCondVisibility('System.HasActiveModalDialog'):
            return True
        dialog_id = xbmcgui.getCurrentWindowDialogId()
        if dialog_id in dialog_ids:
            return dialog_id
        return False


class XbmcProgressDialog(object):
    def __init__(self,
                 ui,
                 dialog,
                 background,
                 heading,
                 message='',
                 total=0,
                 message_template=None,
                 template_params=None,
                 hide=False):
        if hide:
            self._dialog = None
            self._created = False
            return

        self._ui = ui
        if ui.busy_dialog_active(all_modals=True):
            self._dialog = dialog()
            self._dialog.create(heading, message)
            self._created = True
        else:
            self._dialog = dialog()
            self._created = False

        self._background = background

        self._position = None
        self._total = total

        self._heading = heading
        self._message = message
        if message_template:
            self._message_template = message_template
            self._template_params = {
                '_message': message,
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
        if not self._dialog:
            return None
        return self._total

    def get_position(self):
        if not self._dialog:
            return None
        return self._position

    def close(self):
        if self._dialog and self._created:
            self._dialog.close()
            self._dialog = None
            self._created = False

    def is_aborted(self):
        if self._dialog and self._created:
            return getattr(self._dialog, 'iscanceled', bool)()
        return False

    def set_total(self, total):
        if not self._dialog:
            return
        self._total = int(total)

    def reset_total(self, new_total, **kwargs):
        if not self._dialog:
            return
        self._total = int(new_total)
        self.update(position=0, **kwargs)

    def update_total(self, new_total, **kwargs):
        if not self._dialog:
            return
        self._total = int(new_total)
        self.update(steps=0, **kwargs)

    def grow_total(self, new_total=None, delta=None):
        if not self._dialog:
            return None
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

        if not self._created:
            if self._ui.busy_dialog_active(all_modals=True):
                return
            self._dialog.create(self._heading, self._message)
            self._created = True

        # Kodi 18 renamed XbmcProgressDialog.update argument line1 to message.
        # Only use positional arguments to maintain compatibility
        if self._background:
            self._dialog.update(percent, self._heading, self._message)
        else:
            self._dialog.update(percent, self._message)


class XbmcBusyDialog(object):
    def __enter__(self):
        xbmc.executebuiltin('ActivateWindow(BusyDialogNoCancel)')
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self.close()
        if exc_val:
            logging.exception('Error',
                              exc_info=(exc_type, exc_val, exc_tb),
                              stacklevel=2)

    @staticmethod
    def close():
        xbmc.executebuiltin('Dialog.Close(BusyDialogNoCancel)')
