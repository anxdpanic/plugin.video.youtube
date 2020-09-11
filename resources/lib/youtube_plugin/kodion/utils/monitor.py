# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from six.moves.urllib.parse import unquote

import json
import os
import shutil
import threading

import xbmc
import xbmcaddon
import xbmcvfs

from ..utils import get_http_server, is_httpd_live
from .. import logger

try:
    xbmc.translatePath = xbmcvfs.translatePath
except AttributeError:
    pass


class YouTubeMonitor(xbmc.Monitor):

    # noinspection PyUnusedLocal,PyMissingConstructor
    def __init__(self, *args, **kwargs):
        self.addon_id = 'plugin.video.youtube'
        addon = xbmcaddon.Addon(self.addon_id)
        self._whitelist = addon.getSetting('kodion.http.ip.whitelist')
        self._httpd_port = int(addon.getSetting('kodion.mpd.proxy.port'))
        self._old_httpd_port = self._httpd_port
        self._use_httpd = (addon.getSetting('kodion.mpd.videos') == 'true' and addon.getSetting('kodion.video.quality.mpd') == 'true') or \
                          (addon.getSetting('youtube.api.config.page') == 'true')
        self._httpd_address = addon.getSetting('kodion.http.listen')
        self._old_httpd_address = self._httpd_address
        self.httpd = None
        self.httpd_thread = None
        if self.use_httpd():
            self.start_httpd()
        del addon

    def onNotification(self, sender, method, data):
        if sender == 'plugin.video.youtube' and method.endswith('.check_settings'):
            data = json.loads(data)
            data = json.loads(unquote(data[0]))
            logger.log_debug('onNotification: |check_settings| -> |%s|' % json.dumps(data))

            _use_httpd = data.get('use_httpd')
            _httpd_port = data.get('httpd_port')
            _whitelist = data.get('whitelist')
            _httpd_address = data.get('httpd_address')

            whitelist_changed = _whitelist != self._whitelist
            port_changed = self._httpd_port != _httpd_port
            address_changed = self._httpd_address != _httpd_address

            if _whitelist != self._whitelist:
                self._whitelist = _whitelist

            if self._use_httpd != _use_httpd:
                self._use_httpd = _use_httpd

            if self._httpd_port != _httpd_port:
                self._old_httpd_port = self._httpd_port
                self._httpd_port = _httpd_port

            if self._httpd_address != _httpd_address:
                self._old_httpd_address = self._httpd_address
                self._httpd_address = _httpd_address

            if self.use_httpd() and not self.httpd:
                self.start_httpd()
            elif self.use_httpd() and (port_changed or whitelist_changed or address_changed):
                if self.httpd:
                    self.restart_httpd()
                else:
                    self.start_httpd()
            elif not self.use_httpd() and self.httpd:
                self.shutdown_httpd()

        elif sender == 'plugin.video.youtube':
            logger.log_debug('onNotification: |unknown method|')

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
        if not self.httpd:
            logger.log_debug('HTTPServer: Starting |{ip}:{port}|'.format(ip=self.httpd_address(),
                                                                         port=str(self.httpd_port())))
            self.httpd_port_sync()
            self.httpd = get_http_server(address=self.httpd_address(), port=self.httpd_port())
            if self.httpd:
                self.httpd_thread = threading.Thread(target=self.httpd.serve_forever)
                self.httpd_thread.daemon = True
                self.httpd_thread.start()
                sock_name = self.httpd.socket.getsockname()
                logger.log_debug('HTTPServer: Serving on |{ip}:{port}|'.format(ip=str(sock_name[0]),
                                                                               port=str(sock_name[1])))

    def shutdown_httpd(self):
        if self.httpd:
            logger.log_debug('HTTPServer: Shutting down |{ip}:{port}|'.format(ip=self.old_httpd_address(),
                                                                              port=str(self.old_httpd_port())))
            self.httpd_port_sync()
            self.httpd.shutdown()
            self.httpd.socket.close()
            self.httpd_thread.join()
            self.httpd_thread = None
            self.httpd = None

    def restart_httpd(self):
        logger.log_debug('HTTPServer: Restarting... |{old_ip}:{old_port}| -> |{ip}:{port}|'
                         .format(old_ip=self.old_httpd_address(), old_port=str(self.old_httpd_port()),
                                 ip=self.httpd_address(), port=str(self.httpd_port())))
        self.shutdown_httpd()
        self.start_httpd()

    def ping_httpd(self):
        return is_httpd_live(port=self.httpd_port())

    def remove_temp_dir(self):
        try:
            path = xbmc.translatePath('special://temp/%s' % self.addon_id).decode('utf-8')
        except AttributeError:
            path = xbmc.translatePath('special://temp/%s' % self.addon_id)

        if os.path.isdir(path):
            try:
                xbmcvfs.rmdir(path, force=True)
            except:
                pass
        if os.path.isdir(path):
            try:
                shutil.rmtree(path)
            except:
                pass

        if os.path.isdir(path):
            logger.log_debug('Failed to remove directory: {dir}'.format(dir=path.encode('utf-8')))
            return False
        else:
            return True
