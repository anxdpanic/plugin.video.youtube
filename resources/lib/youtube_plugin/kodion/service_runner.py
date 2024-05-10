# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .constants import ABORT_FLAG, ADDON_ID, SLEEPING, TEMP_PATH, WAKEUP
from .context import XbmcContext
from .monitors import PlayerMonitor, ServiceMonitor
from .utils import rm_dir
from ..youtube.provider import Provider


__all__ = ('run',)


def run():
    context = XbmcContext()
    context.log_debug('YouTube service initialization...')
    ui = context.get_ui()
    ui.clear_property(ABORT_FLAG)

    monitor = ServiceMonitor()
    player = PlayerMonitor(provider=Provider(),
                           context=context,
                           monitor=monitor)

    # wipe add-on temp folder on updates/restarts (subtitles, and mpd files)
    rm_dir(TEMP_PATH)

    ping_period = waited = 60
    restart_attempts = 0
    plugin_url = 'plugin://{0}/'.format(ADDON_ID)
    while not monitor.abortRequested():
        if not monitor.httpd:
            if (monitor.httpd_required()
                    and not context.get_infobool('System.IdleTime(10)')):
                monitor.start_httpd()
                waited = 0
        elif context.get_infobool('System.IdleTime(10)'):
            if ui.get_property(WAKEUP):
                ui.clear_property(WAKEUP)
                waited = 0
            if waited >= 30:
                monitor.shutdown_httpd()
                ui.set_property(SLEEPING, 'true')
        elif waited >= ping_period:
            waited = 0
            if monitor.ping_httpd():
                restart_attempts = 0
            elif restart_attempts < 5:
                monitor.restart_httpd()
                restart_attempts += 1
            else:
                monitor.shutdown_httpd()

        if context.get_infolabel('Container.FolderPath').startswith(plugin_url):
            wait_interval = 1
        else:
            wait_interval = 10

        if monitor.waitForAbort(wait_interval):
            break
        waited += wait_interval

    ui.set_property(ABORT_FLAG, 'true')

    # clean up any/all playback monitoring threads
    player.cleanup_threads(only_ended=False)

    if monitor.httpd:
        monitor.shutdown_httpd()  # shutdown http server

    monitor.tear_down()
    context.tear_down()
