# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .constants import (
    ABORT_FLAG,
    PLUGIN_SLEEPING,
    TEMP_PATH,
    VIDEO_ID,
)
from .context import XbmcContext
from .monitors import PlayerMonitor, ServiceMonitor
from .utils import rm_dir
from ..youtube.provider import Provider


__all__ = ('run',)


def run():
    context = XbmcContext()
    provider = Provider()

    system_version = context.get_system_version()
    context.log_notice('Service: Starting v{version}'
                       '\n\tKodi:   v{kodi}'
                       '\n\tPython: v{python}'
                       .format(version=context.get_version(),
                               kodi=str(system_version),
                               python=system_version.get_python_version()))

    get_listitem_info = context.get_listitem_info
    get_listitem_property = context.get_listitem_property

    ui = context.get_ui()
    clear_property = ui.clear_property
    set_property = ui.set_property

    clear_property(ABORT_FLAG)

    monitor = ServiceMonitor(context=context)
    player = PlayerMonitor(provider=provider,
                           context=context,
                           monitor=monitor)

    # wipe add-on temp folder on updates/restarts (subtitles, and mpd files)
    rm_dir(TEMP_PATH)

    loop_period = 10
    loop_period_ms = loop_period * 1000

    httpd_idle_time_ms = 0
    httpd_idle_timeout_ms = 30000
    httpd_ping_period_ms = 60000
    httpd_restart_attempts = 0
    httpd_max_restarts = 5

    plugin_is_idle = False
    plugin_idle_time_ms = 0
    plugin_idle_timeout_ms = 30000

    active_interval_ms = 100
    idle_interval_ms = 1000

    video_id = None
    container = monitor.is_plugin_container()

    while not monitor.abortRequested():
        is_idle = monitor.system_idle or monitor.get_idle_time() >= loop_period
        is_asleep = monitor.system_sleep

        if is_asleep:
            plugin_idle_time_ms = 0
            if not plugin_is_idle:
                plugin_is_idle = set_property(PLUGIN_SLEEPING)
        elif is_idle:
            if plugin_idle_time_ms >= plugin_idle_timeout_ms:
                plugin_idle_time_ms = 0
                if not plugin_is_idle:
                    plugin_is_idle = set_property(PLUGIN_SLEEPING)
        else:
            plugin_idle_time_ms = 0
            if plugin_is_idle:
                plugin_is_idle = clear_property(PLUGIN_SLEEPING)

        if not monitor.httpd:
            httpd_idle_time_ms = 0
        elif is_asleep:
            httpd_idle_time_ms = 0
            monitor.shutdown_httpd(on_idle=True, player=player)
        elif is_idle:
            if monitor.httpd_sleep_allowed:
                if httpd_idle_time_ms >= httpd_idle_timeout_ms:
                    httpd_idle_time_ms = 0
                    monitor.shutdown_httpd(on_idle=True, player=player)
            elif monitor.httpd_sleep_allowed is None:
                monitor.httpd_sleep_allowed = True
                httpd_idle_time_ms = 0
        else:
            if httpd_idle_time_ms >= httpd_ping_period_ms:
                httpd_idle_time_ms = 0
                if monitor.ping_httpd():
                    httpd_restart_attempts = 0
                elif httpd_restart_attempts < httpd_max_restarts:
                    monitor.restart_httpd()
                    httpd_restart_attempts += 1
                else:
                    monitor.shutdown_httpd(terminate=True)

        check_item = not plugin_is_idle and container['is_plugin']
        if check_item:
            wait_interval_ms = active_interval_ms
        else:
            wait_interval_ms = idle_interval_ms
        wait_interval = wait_interval_ms / 1000
        wait_time_ms = 0

        while not monitor.abortRequested():
            if (not monitor.httpd
                    and not monitor.system_sleep
                    and not (monitor.system_idle
                             or monitor.get_idle_time() >= loop_period)):
                monitor.system_idle = False
                monitor.system_sleep = False
                monitor.interrupt = True

            if monitor.refresh and all(container.values()):
                monitor.refresh_container(force=True)
                monitor.refresh = False
                break

            if monitor.interrupt:
                monitor.interrupt = False
                container = monitor.is_plugin_container()
                if check_item != container['is_plugin']:
                    check_item = not check_item
                    if check_item:
                        wait_interval_ms = active_interval_ms
                    else:
                        wait_interval_ms = idle_interval_ms
                    wait_interval = wait_interval_ms / 1000

            if check_item:
                new_video_id = get_listitem_property(VIDEO_ID)
                if new_video_id:
                    if video_id != new_video_id:
                        video_id = new_video_id
                        set_property(VIDEO_ID, video_id)
                elif video_id and get_listitem_info('Label'):
                    video_id = None
                    clear_property(VIDEO_ID)
            elif not plugin_is_idle and not container['is_plugin']:
                plugin_is_idle = set_property(PLUGIN_SLEEPING)

            monitor.waitForAbort(wait_interval)
            wait_time_ms += wait_interval_ms
            httpd_idle_time_ms += wait_interval_ms
            plugin_idle_time_ms += wait_interval_ms

            if wait_time_ms >= loop_period_ms:
                break
        else:
            break

    set_property(ABORT_FLAG)

    # clean up any/all playback monitoring threads
    player.cleanup_threads(only_ended=False)

    # shutdown http server
    if monitor.httpd:
        monitor.shutdown_httpd(terminate=True)

    provider.tear_down()
    context.tear_down()
