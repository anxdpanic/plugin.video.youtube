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
    ADDON_ID,
    PLAY_COUNT,
    SLEEPING,
    TEMP_PATH,
    VIDEO_ID,
    WAKEUP,
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
    get_infolabel = context.get_infolabel
    get_listitem_detail = context.get_listitem_detail
    get_listitem_info = context.get_listitem_info

    ui = context.get_ui()
    clear_property = ui.clear_property
    get_property = ui.get_property
    set_property = ui.set_property

    clear_property(ABORT_FLAG)

    monitor = ServiceMonitor(context=context)
    player = PlayerMonitor(provider=provider,
                           context=context,
                           monitor=monitor)

    # wipe add-on temp folder on updates/restarts (subtitles, and mpd files)
    rm_dir(TEMP_PATH)

    ping_period = waited = 60
    restart_attempts = 0
    plugin_url = 'plugin://{0}/'.format(ADDON_ID)
    video_id = None
    while not monitor.abortRequested():
        if not monitor.httpd:
            if (monitor.httpd_required()
                    and not get_infobool('System.IdleTime(10)')):
                monitor.start_httpd()
                waited = 0
        elif get_infobool('System.IdleTime(10)'):
            if get_property(WAKEUP):
                clear_property(WAKEUP)
                waited = 0
            if waited >= 30:
                monitor.shutdown_httpd()
                set_property(SLEEPING)
        elif waited >= ping_period:
            waited = 0
            if monitor.ping_httpd():
                restart_attempts = 0
            elif restart_attempts < 5:
                monitor.restart_httpd()
                restart_attempts += 1
            else:
                monitor.shutdown_httpd()

        if get_infolabel('Container.FolderPath').startswith(plugin_url):
            new_video_id = get_listitem_detail('video_id')
            if not new_video_id:
                video_id = None
                if get_listitem_info('Label'):
                    clear_property(VIDEO_ID)
                    clear_property(PLAY_COUNT)
            elif video_id != new_video_id:
                video_id = new_video_id
                set_property(VIDEO_ID, video_id)
                plugin_play_count = get_listitem_detail(PLAY_COUNT)
                set_property(PLAY_COUNT, plugin_play_count)
            else:
                kodi_play_count = get_listitem_info('PlayCount')
                kodi_play_count = int(kodi_play_count or 0)
                plugin_play_count = get_property(PLAY_COUNT)
                plugin_play_count = int(plugin_play_count or 0)
                if kodi_play_count != plugin_play_count:
                    playback_history = context.get_playback_history()
                    play_data = playback_history.get_item(video_id)
                    if not play_data:
                        play_data = {'play_count': kodi_play_count}
                        playback_history.update(video_id, play_data)
                    elif play_data.get('play_count') != kodi_play_count:
                        play_data['play_count'] = kodi_play_count
                        play_data['played_time'] = 0.0
                        play_data['played_percent'] = 0
                        playback_history.update(video_id, play_data)
                    set_property(PLAY_COUNT, str(kodi_play_count))
            wait_interval = 0.1
        else:
            wait_interval = 10

        if monitor.waitForAbort(wait_interval):
            break
        waited += wait_interval

    set_property(ABORT_FLAG)

    # clean up any/all playback monitoring threads
    player.cleanup_threads(only_ended=False)

    if monitor.httpd:
        monitor.shutdown_httpd()  # shutdown http server

    provider.tear_down()
    context.tear_down()
