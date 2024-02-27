# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import threading

from ..compatibility import unquote, xbmc, xbmcaddon
from ..constants import ADDON_ID
from ..logger import log_debug
from ..network import get_http_server, is_httpd_live
from ..settings import XbmcPluginSettings


class ServiceMonitor(xbmc.Monitor):
    _settings = XbmcPluginSettings(xbmcaddon.Addon(ADDON_ID))

    def __init__(self):
        settings = self._settings
        self._whitelist = settings.httpd_whitelist()
        self._old_httpd_port = self._httpd_port = int(settings.httpd_port())
        self._use_httpd = (settings.use_mpd_videos()
                           or settings.api_config_page())
        self._old_httpd_address = self._httpd_address = settings.httpd_listen()
        self.httpd = None
        self.httpd_thread = None
        if self.use_httpd():
            self.start_httpd()
        super(ServiceMonitor, self).__init__()

    def onNotification(self, sender, method, data):
        if sender == ADDON_ID and method.endswith('.check_settings'):
            if not isinstance(data, dict):
                data = json.loads(data)
                data = json.loads(unquote(data[0]))
            log_debug('onNotification: |check_settings| -> |{data}|'
                      .format(data=data))

            _use_httpd = data.get('use_httpd')
            _httpd_port = data.get('httpd_port')
            _whitelist = data.get('whitelist')
            _httpd_address = data.get('httpd_address')

            whitelist_changed = _whitelist != self._whitelist
            port_changed = self._httpd_port != _httpd_port
            address_changed = self._httpd_address != _httpd_address

            if whitelist_changed:
                self._whitelist = _whitelist

            if self._use_httpd != _use_httpd:
                self._use_httpd = _use_httpd

            if port_changed:
                self._old_httpd_port = self._httpd_port
                self._httpd_port = _httpd_port

            if address_changed:
                self._old_httpd_address = self._httpd_address
                self._httpd_address = _httpd_address

            if not _use_httpd:
                if self.httpd:
                    self.shutdown_httpd()
            elif not self.httpd:
                self.start_httpd()
            elif port_changed or whitelist_changed or address_changed:
                if self.httpd:
                    self.restart_httpd()
                else:
                    self.start_httpd()

        elif sender == ADDON_ID:
            log_debug('onNotification: |unhandled method| -> |{method}|'
                      .format(method=method))

    def onSettingsChanged(self):
        self._settings.flush(xbmcaddon.Addon(ADDON_ID))
        if xbmc.getInfoLabel('Container.FolderPath').startswith(
            'plugin://{0}/'.format(ADDON_ID)
        ):
            xbmc.executebuiltin('Container.Refresh')

        data = {
            'use_httpd': (self._settings.use_mpd_videos()
                          or self._settings.api_config_page()),
            'httpd_port': self._settings.httpd_port(),
            'whitelist': self._settings.httpd_whitelist(),
            'httpd_address': self._settings.httpd_listen()
        }
        self.onNotification(ADDON_ID, 'Other.check_settings', data)

    def use_httpd(self):
        return self._use_httpd

    def httpd_port(self):
        return int(self._httpd_port)

    def httpd_address(self):
        return self._httpd_address

    def old_httpd_address(self):
        return self._old_httpd_address

    def old_httpd_port(self):
        return int(self._old_httpd_port)

    def httpd_port_sync(self):
        self._old_httpd_port = self._httpd_port

    def start_httpd(self):
        if self.httpd:
            return

        log_debug('HTTPServer: Starting |{ip}:{port}|'
                  .format(ip=self.httpd_address(), port=str(self.httpd_port())))
        self.httpd_port_sync()
        self.httpd = get_http_server(address=self.httpd_address(),
                                     port=self.httpd_port())
        if not self.httpd:
            return

        self.httpd_thread = threading.Thread(target=self.httpd.serve_forever)
        self.httpd_thread.daemon = True
        self.httpd_thread.start()
        sock_name = self.httpd.socket.getsockname()
        log_debug('HTTPServer: Serving on |{ip}:{port}|'.format(
            ip=str(sock_name[0]),
            port=str(sock_name[1])
        ))

    def shutdown_httpd(self):
        if self.httpd:
            log_debug('HTTPServer: Shutting down |{ip}:{port}|'
                      .format(ip=self.old_httpd_address(),
                              port=self.old_httpd_port()))
            self.httpd_port_sync()
            self.httpd.shutdown()
            self.httpd.socket.close()
            self.httpd_thread.join()
            self.httpd_thread = None
            self.httpd = None

    def restart_httpd(self):
        log_debug('HTTPServer: Restarting |{old_ip}:{old_port}| > |{ip}:{port}|'
                  .format(old_ip=self.old_httpd_address(),
                          old_port=self.old_httpd_port(),
                          ip=self.httpd_address(),
                          port=self.httpd_port()))
        self.shutdown_httpd()
        self.start_httpd()

    def ping_httpd(self):
        return is_httpd_live(port=self.httpd_port())
