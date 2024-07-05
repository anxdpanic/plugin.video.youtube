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
    SERVER_POST_START,
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
    context.log_debug('YouTube service initialization...')

    provider = Provider()

    get_infobool = context.get_infobool
    get_listitem_info = context.get_listitem_info
    get_listitem_property = context.get_listitem_property

    ui = context.get_ui()
    clear_property = ui.clear_property
    pop_property = ui.pop_property
    set_property = ui.set_property

    clear_property(ABORT_FLAG)

    monitor = ServiceMonitor(context=context)
    player = PlayerMonitor(provider=provider,
                           context=context,
                           monitor=monitor)

    # wipe add-on temp folder on updates/restarts (subtitles, and mpd files)
    rm_dir(TEMP_PATH)

    plugin_sleeping = False
    plugin_sleep_timeout = httpd_sleep_timeout = 0
    ping_period = 60
    loop_num = sub_loop_num = 0
    restart_attempts = 0
    video_id = None
    container = monitor.is_plugin_container()
    while not monitor.abortRequested():
        idle = get_infobool('System.IdleTime(10)')

        if idle:
            if plugin_sleep_timeout >= 30:
                plugin_sleep_timeout = 0
                if not plugin_sleeping:
                    plugin_sleeping = set_property(PLUGIN_SLEEPING)
        else:
            plugin_sleep_timeout = 0
            if plugin_sleeping:
                plugin_sleeping = clear_property(PLUGIN_SLEEPING)

        if not monitor.httpd:
            httpd_sleep_timeout = 0
        elif idle:
            if monitor.httpd_sleep_allowed:
                if httpd_sleep_timeout >= 30:
                    monitor.shutdown_httpd(sleep=True)
            else:
                if pop_property(SERVER_POST_START):
                    monitor.httpd_sleep_allowed = True
                httpd_sleep_timeout = 0
        else:
            if httpd_sleep_timeout >= ping_period:
                httpd_sleep_timeout = 0
                if monitor.ping_httpd():
                    restart_attempts = 0
                elif restart_attempts < 5:
                    monitor.restart_httpd()
                    restart_attempts += 1
                else:
                    monitor.shutdown_httpd()

        while not monitor.abortRequested():
            if container['is_plugin']:
                wait_interval = 0.1
                if loop_num < 1:
                    loop_num = 1
                if sub_loop_num < 1:
                    sub_loop_num = 10

                if monitor.refresh and all(container.values()):
                    monitor.refresh_container(force=True)
                    monitor.refresh = False
                    break
                monitor.interrupt = False

                new_video_id = get_listitem_property(VIDEO_ID)
                if new_video_id:
                    if video_id != new_video_id:
                        video_id = new_video_id
                        set_property(VIDEO_ID, video_id)
                elif video_id and get_listitem_info('Label'):
                    video_id = None
                    clear_property(VIDEO_ID)
            else:
                wait_interval = 1
                if loop_num < 1:
                    loop_num = 2
                if sub_loop_num < 1:
                    sub_loop_num = 5

                if not plugin_sleeping:
                    plugin_sleeping = set_property(PLUGIN_SLEEPING)

            if sub_loop_num > 1:
                sub_loop_num -= 1
                if monitor.interrupt:
                    container = monitor.is_plugin_container()
                    monitor.interrupt = False
            else:
                container = monitor.is_plugin_container()
                sub_loop_num = 0
                loop_num -= 1
                if not wait_interval or container['is_plugin']:
                    wait_interval = 0.1

            if wait_interval:
                monitor.waitForAbort(wait_interval)
                httpd_sleep_timeout += wait_interval
                plugin_sleep_timeout += wait_interval

            if loop_num <= 0:
                break
        else:
            break

    set_property(ABORT_FLAG)

    # clean up any/all playback monitoring threads
    player.cleanup_threads(only_ended=False)

    # shutdown http server
    if monitor.httpd:
        monitor.shutdown_httpd()

    provider.tear_down()
    context.tear_down()
