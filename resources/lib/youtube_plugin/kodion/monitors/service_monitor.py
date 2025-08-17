# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
from io import open
from threading import Event, Lock, Thread

from .. import logging
from ..compatibility import urlsplit, xbmc, xbmcgui
from ..constants import (
    ADDON_ID,
    BOOL_FROM_STR,
    BUSY_FLAG,
    CHECK_SETTINGS,
    CONTAINER_FOCUS,
    FILE_READ,
    FILE_WRITE,
    MARK_AS_LABEL,
    PATHS,
    PLAYBACK_STOPPED,
    PLAYER_VIDEO_ID,
    PLAY_CANCELLED,
    PLAY_FORCED,
    PLUGIN_WAKEUP,
    REFRESH_CONTAINER,
    RELOAD_ACCESS_MANAGER,
    SERVER_WAKEUP,
    SERVICE_IPC,
    SYNC_LISTITEM,
    VIDEO_ID,
)
from ..network import get_connect_address, get_http_server, httpd_status
from ..utils.methods import jsonrpc


class ServiceMonitor(xbmc.Monitor):
    log = logging.getLogger(__name__)

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

        self.file_access = {}

        self.onSettingsChanged(force=True)

        super(ServiceMonitor, self).__init__()

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

    @staticmethod
    def is_plugin_container(url='plugin://{0}/'.format(ADDON_ID),
                            check_all=False,
                            _bool=xbmc.getCondVisibility,
                            _busy=busy_dialog_active.__func__,
                            _label=xbmc.getInfoLabel):
        if check_all:
            return (not _bool('Container.IsUpdating')
                    and not _busy()
                    and _label('Container.FolderPath').startswith(url))
        is_plugin = _label('Container.FolderPath').startswith(url)
        return {
            'is_plugin': is_plugin,
            'is_loaded': is_plugin and not _bool('Container.IsUpdating'),
            'is_active': is_plugin and not _busy(),
        }

    @staticmethod
    def send_notification(method,
                          data=True,
                          sender='.'.join((ADDON_ID, 'service'))):
        jsonrpc(method='JSONRPC.NotifyAll',
                params={'sender': sender,
                        'message': method,
                        'data': data})

    def set_property(self,
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
        self.log.debug_trace('Set property {property_id!r}: {value!r}',
                             property_id=property_id,
                             value=log_value,
                             stacklevel=stacklevel)
        _property_id = property_id if raw else '-'.join((ADDON_ID, property_id))
        if process:
            value = process(value)
        xbmcgui.Window(10000).setProperty(_property_id, value)
        return value

    def get_property(self,
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
        self.log.debug_trace('Get property {property_id!r}: {value!r}',
                             property_id=property_id,
                             value=log_value,
                             stacklevel=stacklevel)
        if process:
            value = process(value)
        return BOOL_FROM_STR.get(value, default) if as_bool else value

    def pop_property(self,
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
        self.log.debug_trace('Pop property {property_id!r}: {value!r}',
                             property_id=property_id,
                             value=log_value,
                             stacklevel=stacklevel)
        return BOOL_FROM_STR.get(value, default) if as_bool else value

    def clear_property(self, property_id, stacklevel=2, raw=False):
        self.log.debug_trace('Clear property {property_id!r}',
                             property_id=property_id,
                             stacklevel=stacklevel)
        _property_id = property_id if raw else '-'.join((ADDON_ID, property_id))
        xbmcgui.Window(10000).clearProperty(_property_id)
        return None

    def refresh_container(self, deferred=False):
        if deferred:
            self.refresh = False
            if self.get_property(REFRESH_CONTAINER) == BUSY_FLAG:
                self.set_property(REFRESH_CONTAINER)
                xbmc.executebuiltin('Container.Refresh')
        else:
            container = self.is_plugin_container()
            if all(container.values()):
                self.set_property(REFRESH_CONTAINER)
                xbmc.executebuiltin('Container.Refresh')
            elif container['is_loaded']:
                self.set_property(REFRESH_CONTAINER, BUSY_FLAG)
                self.log.debug('Plugin window not active - deferring refresh')
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
                playlist_player = context.get_playlist_player()
                item_uri = playlist_player.get_item_path(position)

                if context.is_plugin_path(item_uri):
                    path, params = context.parse_uri(item_uri)
                    if path.rstrip('/') != PATHS.PLAY:
                        self.log.warning(('Playlist.OnAdd item is not playable',
                                          'Path:   {path}',
                                          'Params: {params}'),
                                         path=path,
                                         params=params)
                        self.set_property(PLAY_FORCED)
                    elif params.get('action') == 'list':
                        playlist_player.stop()
                        playlist_player.clear()
                        self.log.warning(('Playlist.OnAdd item is a listing',
                                          'Path:   {path}',
                                          'Params: {params}'),
                                         path=path,
                                         params=params)
                        self.set_property(PLAY_CANCELLED)

            return

        if sender != ADDON_ID:
            return

        group, separator, event = method.partition('.')

        if event == SERVICE_IPC:
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
                elif state == 'ignore':
                    self._settings_collect = -1
                response = True

            elif target in {FILE_READ, FILE_WRITE}:
                response = None
                filepath = data.get('filepath')
                if filepath:
                    if filepath not in self.file_access:
                        read_access = Event()
                        read_access.set()
                        write_access = Lock()
                        self.file_access[filepath] = (read_access, write_access)
                    else:
                        read_access, write_access = self.file_access[filepath]

                    if target == FILE_READ:
                        try:
                            with open(filepath, mode='r',
                                      encoding='utf-8') as file:
                                read_access.wait()
                                self.set_property(
                                    '-'.join((FILE_READ, filepath)),
                                    file.read(),
                                    log_value='<redacted>',
                                )
                                response = True
                        except (IOError, OSError):
                            response = False
                    else:
                        with write_access:
                            content = self.pop_property(
                                '-'.join((FILE_WRITE, filepath)),
                                log_value='<redacted>',
                            )
                            response = None
                            if content:
                                read_access.clear()
                                try:
                                    with open(filepath, mode='w',
                                              encoding='utf-8') as file:
                                        file.write(content)
                                    response = True
                                except (IOError, OSError):
                                    response = False
                                finally:
                                    read_access.set()

            else:
                return

            if data.get('response_required'):
                data['response'] = response
                self.send_notification(SERVICE_IPC, data)

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

        elif event == PLAYBACK_STOPPED:
            if data:
                data = json.loads(data)
            if not data:
                return

            if data.get('play_data', {}).get('play_count'):
                self.set_property(PLAYER_VIDEO_ID, data.get('video_id'))

        elif event == SYNC_LISTITEM:
            video_ids = json.loads(data) if data else None
            if not video_ids:
                return

            context = self._context
            focused_video_id = context.get_listitem_property(VIDEO_ID)
            if not focused_video_id:
                return

            playback_history = context.get_playback_history()
            for video_id in video_ids:
                if not video_id or video_id != focused_video_id:
                    continue

                play_count = context.get_listitem_info('PlayCount')
                resumable = context.get_listitem_bool('IsResumable')

                self.set_property(MARK_AS_LABEL,
                                  context.localize('history.mark.unwatched')
                                  if play_count else
                                  context.localize('history.mark.watched'))

                item_history = playback_history.get_item(video_id)
                if item_history:
                    item_history = dict(
                        item_history,
                        play_count=int(play_count) if play_count else 0,
                    )
                    if not resumable:
                        item_history['played_time'] = 0
                        item_history['played_percent'] = 0
                    playback_history.update_item(video_id, item_history)
                else:
                    playback_history.set_item(video_id, {
                        'play_count': int(play_count) if play_count else 0,
                    })

    def onSettingsChanged(self, force=False):
        context = self._context

        if force:
            self._settings_collect = False
            self._settings_changes = 0
        else:
            self._settings_changes += 1
            if self._settings_collect:
                if self._settings_collect == -1:
                    self._settings_collect = False
                return

            total = self._settings_changes
            self.waitForAbort(1)
            if total != self._settings_changes:
                return

            self.log.debug('onSettingsChanged: %d change(s)', total)
            self._settings_changes = 0

        settings = context.get_settings(refresh=True)
        log_level = settings.log_level()
        if log_level:
            self.log.debugging = True
            if log_level & 2:
                self.log.stack_info = True
                self.log.verbose_logging = True
            else:
                self.log.stack_info = False
                self.log.verbose_logging = False
        else:
            self.log.debugging = False
            self.log.stack_info = False
            self.log.verbose_logging = False

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
        self.log.debug('HTTPServer: Starting {ip}:{port}',
                       ip=self._httpd_address,
                       port=self._httpd_port)
        self.httpd_address_sync()
        self.httpd = get_http_server(address=self._httpd_address,
                                     port=self._httpd_port,
                                     context=context)
        if not self.httpd:
            self._httpd_error = True
            return False

        self.httpd_thread = Thread(target=self.httpd.serve_forever)
        self.httpd_thread.daemon = True
        self.httpd_thread.start()

        address = self.httpd.socket.getsockname()
        self.log.debug('HTTPServer: Listening on {address[0]}:{address[1]}',
                       address=address)
        self._httpd_error = False
        return True

    def shutdown_httpd(self, on_idle=False, terminate=False, player=None):
        if (not self.httpd
                or (not (terminate or self.system_sleep)
                    and (on_idle or self.system_idle)
                    and self.httpd_required(on_idle=True, player=player))):
            return
        self.log.debug('HTTPServer: Shutting down {ip}:{port}',
                       ip=self._old_httpd_address,
                       port=self._old_httpd_port)
        self.httpd_address_sync()

        shutdown_thread = Thread(target=self.httpd.shutdown)
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
        self.log.debug('HTTPServer: Restarting'
                       ' {old_ip}:{old_port} > {ip}:{port}',
                       old_ip=self._old_httpd_address,
                       old_port=self._old_httpd_port,
                       ip=self._httpd_address,
                       port=self._httpd_port)
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
