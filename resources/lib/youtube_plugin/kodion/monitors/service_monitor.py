# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import threading

from ..compatibility import urlsplit, xbmc, xbmcgui
from ..constants import (
    ADDON_ID,
    CHECK_SETTINGS,
    CONTAINER_FOCUS,
    PATHS,
    PLAY_FORCED,
    PLUGIN_WAKEUP,
    REFRESH_CONTAINER,
    RELOAD_ACCESS_MANAGER,
    SERVER_WAKEUP,
    WAKEUP,
)
from ..network import get_connect_address, get_http_server, httpd_status


class ServiceMonitor(xbmc.Monitor):
    _settings_changes = 0
    _settings_collect = False
    get_idle_time = xbmc.getGlobalIdleTime

    def __init__(self, context):
        self._context = context

        self._httpd_address = None
        self._httpd_port = None
        self._whitelist = None
        self._old_httpd_address = None
        self._old_httpd_port = None
        self._use_httpd = None
        self._httpd_error = False

        self.httpd = None
        self.httpd_thread = None
        self.httpd_sleep_allowed = True

        self.system_idle = False
        self.system_sleep = False
        self.refresh = False
        self.interrupt = False

        self.onSettingsChanged(force=True)

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
        if sender == 'xbmc':
            if method == 'System.OnSleep':
                self.system_idle = True
                self.system_sleep = True

            elif method in {
                'GUI.OnScreensaverActivated',
                'GUI.OnDPMSActivated',
            }:
                self.system_idle = True

            elif method in {
                'GUI.OnScreensaverDeactivated',
                'GUI.OnDPMSDeactivated',
                'System.OnWake',
            }:
                self.system_idle = False
                self.system_sleep = False
                self.interrupt = True

            elif method == 'Player.OnPlay':
                player = xbmc.Player()
                try:
                    playing_file = urlsplit(player.getPlayingFile())
                    if playing_file.path in {PATHS.MPD,
                                             PATHS.PLAY,
                                             PATHS.REDIRECT}:
                        if not self.httpd:
                            self.start_httpd()
                        if self.httpd_sleep_allowed:
                            self.httpd_sleep_allowed = None
                except RuntimeError:
                    pass

            elif method == 'Playlist.OnAdd':
                context = self._context

                data = json.loads(data)
                position = data.get('position', 0)
                item_path = context.get_infolabel(
                    'Player.position({0}).FilenameAndPath'.format(position)
                )

                if context.is_plugin_path(item_path):
                    if not context.is_plugin_path(item_path, PATHS.PLAY):
                        context.log_warning('Playlist.OnAdd - non-playable path'
                                            '\n\tPath: {0}'.format(item_path))
                        self.set_property(PLAY_FORCED)

            return

        if sender != ADDON_ID:
            return

        group, separator, event = method.partition('.')

        if event == WAKEUP:
            if not isinstance(data, dict):
                data = json.loads(data)
            if not data:
                return

            target = data.get('target')

            if target == PLUGIN_WAKEUP:
                self.system_idle = False
                self.system_sleep = False
                self.interrupt = True
                response = True

            elif target == SERVER_WAKEUP:
                if not self.httpd and self.httpd_required():
                    response = self.start_httpd()
                else:
                    response = bool(self.httpd)
                if self.httpd_sleep_allowed:
                    self.httpd_sleep_allowed = None

            elif target == CHECK_SETTINGS:
                state = data.get('state')
                if state == 'defer':
                    self._settings_collect = True
                elif state == 'process':
                    self.onSettingsChanged(force=True)
                response = True

            else:
                return

            if data.get('response_required'):
                data['response'] = response
                self.set_property(WAKEUP, json.dumps(data, ensure_ascii=False))

        elif event == REFRESH_CONTAINER:
            self.refresh_container()

        elif event == CONTAINER_FOCUS:
            if data:
                data = json.loads(data)
            if not data or not self.is_plugin_container(check_all=True):
                return
            xbmc.executebuiltin('SetFocus({0},{1},absolute)'.format(*data))

        elif event == RELOAD_ACCESS_MANAGER:
            self._context.reload_access_manager()
            self.refresh_container()

    def onSettingsChanged(self, force=False):
        context = self._context

        if force:
            self._settings_collect = False
            self._settings_changes = 0
        else:
            self._settings_changes += 1
            if self._settings_collect:
                return

            total = self._settings_changes
            self.waitForAbort(1)
            if total != self._settings_changes:
                return

            context.log_debug('onSettingsChanged: {0} change(s)'.format(total))
            self._settings_changes = 0

        settings = context.get_settings(refresh=True)
        if settings.logging_enabled():
            context.debug_log(on=True)
        else:
            context.debug_log(off=True)

        self.set_property(CHECK_SETTINGS)
        self.refresh_container()

        httpd_started = bool(self.httpd)
        httpd_restart = False

        address, port = get_connect_address(context)
        if port != self._httpd_port:
            self._old_httpd_port = self._httpd_port
            self._httpd_port = port
            httpd_restart = httpd_started
        if address != self._httpd_address:
            self._old_httpd_address = self._httpd_address
            self._httpd_address = address
            httpd_restart = httpd_started

        whitelist = settings.httpd_whitelist()
        if whitelist != self._whitelist:
            self._whitelist = whitelist
            httpd_restart = httpd_started

        sleep_allowed = settings.httpd_sleep_allowed()
        if sleep_allowed is False:
            self.httpd_sleep_allowed = False

        if self.httpd_required(settings):
            if httpd_restart:
                self.restart_httpd()
            else:
                self.start_httpd()
        elif httpd_started:
            self.shutdown_httpd(terminate=True)

    def httpd_address_sync(self):
        self._old_httpd_address = self._httpd_address
        self._old_httpd_port = self._httpd_port

    def start_httpd(self):
        if self.httpd:
            self._httpd_error = False
            return True

        context = self._context
        context.log_debug('HTTPServer: Starting |{ip}:{port}|'
                          .format(ip=self._httpd_address,
                                  port=self._httpd_port))
        self.httpd_address_sync()
        self.httpd = get_http_server(address=self._httpd_address,
                                     port=self._httpd_port,
                                     context=context)
        if not self.httpd:
            self._httpd_error = True
            return False

        self.httpd_thread = threading.Thread(target=self.httpd.serve_forever)
        self.httpd_thread.daemon = True
        self.httpd_thread.start()

        address = self.httpd.socket.getsockname()
        context.log_debug('HTTPServer: Listening on |{ip}:{port}|'
                          .format(ip=address[0],
                                  port=address[1]))
        self._httpd_error = False
        return True

    def shutdown_httpd(self, on_idle=False, terminate=False, player=None):
        if (not self.httpd
                or (not (terminate or self.system_sleep)
                    and (on_idle or self.system_idle)
                    and self.httpd_required(on_idle=True, player=player))):
            return
        self._context.log_debug('HTTPServer: Shutting down |{ip}:{port}|'
                                .format(ip=self._old_httpd_address,
                                        port=self._old_httpd_port))
        self.httpd_address_sync()

        shutdown_thread = threading.Thread(target=self.httpd.shutdown)
        shutdown_thread.daemon = True
        shutdown_thread.start()

        for thread in (self.httpd_thread, shutdown_thread):
            if not thread.is_alive():
                continue
            try:
                thread.join(2)
            except RuntimeError:
                pass

        self.httpd.server_close()

        self.httpd_thread = None
        self.httpd = None

    def restart_httpd(self):
        self._context.log_debug('HTTPServer: Restarting'
                                ' |{old_ip}:{old_port}| > |{ip}:{port}|'
                                .format(old_ip=self._old_httpd_address,
                                        old_port=self._old_httpd_port,
                                        ip=self._httpd_address,
                                        port=self._httpd_port))
        self.shutdown_httpd(terminate=True)
        self.start_httpd()

    def ping_httpd(self):
        return self.httpd and httpd_status(self._context)

    def httpd_required(self, settings=None, on_idle=False, player=None):
        if settings:
            required = (settings.use_mpd_videos()
                        or settings.api_config_page()
                        or settings.support_alternative_player())
            self._use_httpd = required

        elif self._httpd_error:
            required = False

        elif on_idle:
            settings = self._context.get_settings()

            playing = player.isPlaying() if player else False
            external = player.isExternalPlayer() if playing else False

            required = ((playing and settings.use_mpd_videos())
                        or settings.api_config_page()
                        or (external and settings.support_alternative_player()))

        else:
            required = self._use_httpd

        return required
