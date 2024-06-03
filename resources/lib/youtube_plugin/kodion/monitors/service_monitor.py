# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import threading

from ..compatibility import xbmc, xbmcgui
from ..constants import (
    ADDON_ID,
    CHECK_SETTINGS,
    REFRESH_CONTAINER,
    RELOAD_ACCESS_MANAGER,
    WAKEUP,
)
from ..logger import log_debug
from ..network import get_connect_address, get_http_server, httpd_status


class ServiceMonitor(xbmc.Monitor):
    _settings_changes = 0
    _settings_state = None

    def __init__(self, context):
        self._context = context
        settings = context.get_settings()
        self._use_httpd = (settings.use_isa()
                           or settings.api_config_page()
                           or settings.support_alternative_player())
        address, port = get_connect_address(self._context)
        self._old_httpd_address = self._httpd_address = address
        self._old_httpd_port = self._httpd_port = port
        self._whitelist = settings.httpd_whitelist()

        self.httpd = None
        self.httpd_thread = None

        self.refresh = False
        self.interrupt = False

        if self._use_httpd:
            self.start_httpd()

        super(ServiceMonitor, self).__init__()

    @staticmethod
    def is_plugin_container(url='plugin://{0}/'.format(ADDON_ID),
                            check_all=False,
                            _bool=xbmc.getCondVisibility,
                            _label=xbmc.getInfoLabel):
        if check_all:
            return (not _bool('Container.IsUpdating')
                    and not _bool('System.HasActiveModalDialog')
                    and _label('Container.FolderPath').startswith(url))
        is_plugin = _label('Container.FolderPath').startswith(url)
        return {
            'is_plugin': is_plugin,
            'is_loaded': is_plugin and not _bool('Container.IsUpdating'),
            'is_active': is_plugin and not _bool('System.HasActiveModalDialog'),
        }

    @staticmethod
    def set_property(property_id, value='true'):
        property_id = '-'.join((ADDON_ID, property_id))
        xbmcgui.Window(10000).setProperty(property_id, value)
        return value

    def refresh_container(self, force=False):
        self.set_property(REFRESH_CONTAINER)
        if force or self.is_plugin_container(check_all=True):
            xbmc.executebuiltin('Container.Refresh')
        else:
            self.refresh = True

    def onNotification(self, sender, method, data):
        if sender != ADDON_ID:
            return
        group, separator, event = method.partition('.')
        if event == CHECK_SETTINGS:
            if not isinstance(data, dict):
                data = json.loads(data)
            log_debug('onNotification: |check_settings| -> |{data}|'
                      .format(data=data))

            if data == 'defer':
                self._settings_state = data
                return
            if data == 'process':
                self._settings_state = data
                self.onSettingsChanged()
                self._settings_state = None
                return
        elif event == WAKEUP:
            if not self.httpd and self.httpd_required():
                self.start_httpd()
            self.interrupt = True
        elif event == REFRESH_CONTAINER:
            self.refresh_container()
        elif event == RELOAD_ACCESS_MANAGER:
            self._context.reload_access_manager()
            self.refresh_container()
        else:
            log_debug('onNotification: |unhandled method| -> |{method}|'
                      .format(method=method))

    def onSettingsChanged(self):
        self._settings_changes += 1
        if self._settings_state == 'defer':
            return
        changes = self._settings_changes
        if self._settings_state != 'process':
            self.waitForAbort(1)
            if changes != self._settings_changes:
                return
        log_debug('onSettingsChanged: {0} change(s)'.format(changes))
        self._settings_changes = 0

        settings = self._context.get_settings(refresh=True)

        self.set_property(CHECK_SETTINGS)
        self.refresh_container()

        use_httpd = (settings.use_isa()
                     or settings.api_config_page()
                     or settings.support_alternative_player())
        address, port = get_connect_address(self._context)
        whitelist = settings.httpd_whitelist()

        whitelist_changed = whitelist != self._whitelist
        port_changed = port != self._httpd_port
        address_changed = address != self._httpd_address

        if whitelist_changed:
            self._whitelist = whitelist

        if self._use_httpd != use_httpd:
            self._use_httpd = use_httpd

        if port_changed:
            self._old_httpd_port = self._httpd_port
            self._httpd_port = port

        if address_changed:
            self._old_httpd_address = self._httpd_address
            self._httpd_address = address

        if not use_httpd:
            if self.httpd:
                self.shutdown_httpd()
        elif not self.httpd:
            self.start_httpd()
        elif port_changed or whitelist_changed or address_changed:
            if self.httpd:
                self.restart_httpd()
            else:
                self.start_httpd()

    def httpd_address_sync(self):
        self._old_httpd_address = self._httpd_address
        self._old_httpd_port = self._httpd_port

    def start_httpd(self):
        if self.httpd:
            return

        log_debug('HTTPServer: Starting |{ip}:{port}|'
                  .format(ip=self._httpd_address, port=self._httpd_port))
        self.httpd_address_sync()
        self.httpd = get_http_server(address=self._httpd_address,
                                     port=self._httpd_port,
                                     context=self._context)
        if not self.httpd:
            return

        self.httpd_thread = threading.Thread(target=self.httpd.serve_forever)
        self.httpd_thread.start()

        address = self.httpd.socket.getsockname()
        log_debug('HTTPServer: Serving on |{ip}:{port}|'
                  .format(ip=address[0], port=address[1]))

    def shutdown_httpd(self):
        if self.httpd:
            log_debug('HTTPServer: Shutting down |{ip}:{port}|'
                      .format(ip=self._old_httpd_address,
                              port=self._old_httpd_port))
            self.httpd_address_sync()
            self.httpd.shutdown()
            self.httpd.socket.close()
            self.httpd_thread.join()
            self.httpd_thread = None
            self.httpd = None

    def restart_httpd(self):
        log_debug('HTTPServer: Restarting |{old_ip}:{old_port}| > |{ip}:{port}|'
                  .format(old_ip=self._old_httpd_address,
                          old_port=self._old_httpd_port,
                          ip=self._httpd_address,
                          port=self._httpd_port))
        self.shutdown_httpd()
        self.start_httpd()

    def ping_httpd(self):
        return self.httpd and httpd_status(self._context)

    def httpd_required(self):
        return self._use_httpd
