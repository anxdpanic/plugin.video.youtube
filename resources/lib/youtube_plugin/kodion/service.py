# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import time
from datetime import datetime

from .context import Context
from .constants import TEMP_PATH
from .utils import PlayerMonitor, ServiceMonitor, rm_dir
from ..youtube.provider import Provider


def strptime(stamp, stamp_fmt):
    # noinspection PyUnresolvedReferences
    import _strptime
    try:
        time.strptime('01 01 2012', '%d %m %Y')  # dummy call
    except:
        pass
    return time.strptime(stamp, stamp_fmt)


def get_stamp_diff(current_stamp):
    stamp_format = '%Y-%m-%d %H:%M:%S.%f'
    current_datetime = datetime.now()
    if not current_stamp:
        return 86400  # 24 hrs
    try:
        stamp_datetime = datetime(*(strptime(current_stamp, stamp_format)[0:6]))
    except ValueError:  # current_stamp has no microseconds
        stamp_format = '%Y-%m-%d %H:%M:%S'
        stamp_datetime = datetime(*(strptime(current_stamp, stamp_format)[0:6]))

    time_delta = current_datetime - stamp_datetime
    if time_delta:
        return time_delta.total_seconds()
    return 0


def run():
    sleep_time = 10
    ping_delay_time = 60
    ping_timestamp = None
    first_run = True

    context = Context()

    context.log_debug('YouTube service initialization...')

    monitor = ServiceMonitor()
    player = PlayerMonitor(provider=Provider(), context=context)

    # wipe add-on temp folder on updates/restarts (subtitles, and mpd files)
    rm_dir(TEMP_PATH)

    # wipe function cache on updates/restarts (fix cipher related issues on update, valid for one day otherwise)
    try:
        context.get_function_cache().clear()
    except:
        # prevent service to failing due to cache related issues
        pass

    context.get_ui().clear_property('abort_requested')

    while not monitor.abortRequested():

        ping_diff = get_stamp_diff(ping_timestamp)

        if (ping_timestamp is None) or (ping_diff >= ping_delay_time):
            ping_timestamp = str(datetime.now())

            if monitor.httpd and not monitor.ping_httpd():
                monitor.restart_httpd()

        if first_run:
            first_run = False

        if monitor.waitForAbort(sleep_time):
            break

    context.get_ui().set_property('abort_requested', 'true')

    player.cleanup_threads(only_ended=False)  # clean up any/all playback monitoring threads

    if monitor.httpd:
        monitor.shutdown_httpd()  # shutdown http server
