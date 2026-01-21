# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import threading

from .. import logging
from ..compatibility import xbmc
from ..constants import (
    BUSY_FLAG,
    CHANNEL_ID,
    PATHS,
    PLAYBACK_STARTED,
    PLAYBACK_STOPPED,
    PLAYER_DATA,
    PLAY_USING,
    REFRESH_CONTAINER,
    TRAKT_PAUSE_FLAG,
    VIDEO_ID,
)
from ..utils.redact import redact_params


class PlayerMonitorThread(object):
    def __init__(self, player, provider, context, monitor, player_data):
        self.player_data = player_data
        video_id = player_data.get(VIDEO_ID)
        self.video_id = video_id
        self.channel_id = player_data.get(CHANNEL_ID)
        self.video_status = player_data.get('video_status')

        self._stopped = threading.Event()
        self._ended = threading.Event()

        self._player = player
        self._provider = provider
        self._context = context
        self._monitor = monitor

        self.current_time = 0.0
        self.total_time = 0.0
        self.progress = 0

        name = '{class_name}[{video_id}]'.format(
            class_name=self.__class__.__name__,
            video_id=video_id,
        )
        self.name = name
        self.log = logging.getLogger(name)

        thread = threading.Thread(name=name, target=self.run)
        self._thread = thread
        thread.daemon = True
        thread.start()

    def abort_now(self):
        return (not self._player.isPlaying()
                or self._context.abort_requested()
                or self.stopped())

    def run(self):
        video_id = self.video_id
        playing_file = self.player_data.get('playing_file')
        play_count = self.player_data.get('play_count', 0)
        use_remote_history = self.player_data.get('use_remote_history', False)
        use_local_history = self.player_data.get('use_local_history', False)
        playback_stats = self.player_data.get('playback_stats', {})
        refresh_only = self.player_data.get('refresh_only', False)
        clip = self.player_data.get('clip', False)

        context = self._context
        log = self.log
        monitor = self._monitor
        player = self._player
        provider = self._provider

        log.debug('Starting')

        timeout_period = 5
        waited = 0
        wait_interval = 0.5
        while not player.isPlaying():
            if context.abort_requested():
                break
            if waited >= timeout_period:
                self.end()
                return

            log.debug('Waiting for playback to start')
            monitor.waitForAbort(wait_interval)
            waited += wait_interval
        else:
            context.send_notification(PLAYBACK_STARTED, {
                VIDEO_ID: video_id,
                CHANNEL_ID: self.channel_id,
                'status': self.video_status,
            })

        client = provider.get_client(context)
        logged_in = client.logged_in
        report_url = use_remote_history and playback_stats.get('playback_url')
        state = 'playing'

        if report_url:
            client.update_watch_history(
                video_id,
                report_url,
            )

        access_manager = context.get_access_manager()
        settings = context.get_settings()
        playlist_player = context.get_playlist_player()

        video_id_param = 'video_id=%s' % video_id
        report_url = use_remote_history and playback_stats.get('watchtime_url')

        segment_start = 0.0
        report_time = -1.0
        wait_interval = 1
        report_period = waited = 10
        while not self.abort_now():
            try:
                current_file = player.getPlayingFile()
                played_time = player.getTime()
                total_time = player.getTotalTime()
                if not player.seeking:
                    player.current_time = played_time
                    player.total_time = total_time
            except RuntimeError:
                self.stop()
                break

            if (not current_file.startswith(playing_file) and not (
                    context.is_plugin_path(current_file, PATHS.PLAY)
                    and video_id_param in current_file
            )) or total_time <= 0:
                self.stop()
                break

            _seek_time = player.start_time or player.seek_time
            if waited and _seek_time and played_time < _seek_time:
                waited = 0
                player.seekTime(_seek_time)
                continue

            if player.end_time and played_time >= player.end_time:
                if waited and clip and player.start_time:
                    waited = 0
                    player.seekTime(player.start_time)
                    continue
                if playlist_player.size() > 1:
                    playlist_player.play_playlist_item('next')
                else:
                    player.stop()

            if waited >= report_period:
                waited = 0

                last_state = state
                if played_time == report_time:
                    state = 'paused'
                else:
                    state = 'playing'
                report_time = played_time

                if logged_in and report_url:
                    if state == 'playing':
                        segment_end = played_time
                    else:
                        segment_end = segment_start

                    if segment_start > segment_end:
                        segment_end = segment_start + report_period

                    if segment_end > total_time:
                        segment_end = total_time

                    # only report state='paused' once
                    if state == 'playing' or last_state == 'playing':
                        client = provider.get_client(context)
                        logged_in = client.logged_in

                        if logged_in:
                            client.update_watch_history(
                                video_id,
                                report_url,
                                status=(
                                    played_time,
                                    segment_start,
                                    segment_end,
                                    state,
                                ),
                            )

                    segment_start = segment_end

            monitor.waitForAbort(wait_interval)
            waited += wait_interval

        self.current_time = player.current_time
        self.total_time = player.total_time
        if self.total_time > 0:
            self.progress = int(100 * self.current_time / self.total_time)

        if logged_in:
            client = provider.get_client(context)
            logged_in = client.logged_in

        if self.video_status.get('live'):
            play_count += 1
            segment_end = self.current_time
            play_data = {
                'play_count': play_count,
                'total_time': 0,
                'played_time': 0,
                'played_percent': 0,
            }
        else:
            if self.progress >= settings.get_play_count_min_percent():
                play_count += 1
                self.current_time = 0
                segment_end = self.total_time
            else:
                segment_end = self.current_time
                refresh_only = True
            play_data = {
                'play_count': play_count,
                'total_time': self.total_time,
                'played_time': self.current_time,
                'played_percent': self.progress,
            }
        self.player_data['play_data'] = play_data

        if logged_in and report_url:
            client.update_watch_history(
                video_id,
                report_url,
                status=(
                    segment_end,
                    segment_end,
                    segment_end,
                    'stopped',
                ),
            )
        if use_local_history:
            context.get_playback_history().set_item(video_id, play_data)

        context.send_notification(PLAYBACK_STOPPED, self.player_data)
        log.debug('Playback stopped:'
                  ' {played_time:.3f} secs of {total_time:.3f}'
                  ' @ {played_percent}%,'
                  ' played {play_count} time(s)',
                  **play_data)

        if refresh_only:
            pass
        elif settings.get_bool(settings.WATCH_LATER_REMOVE, True):
            watch_later_id = logged_in and access_manager.get_watch_later_id()
            if not watch_later_id:
                context.get_watch_later_list().del_item(video_id)
            elif watch_later_id.lower() == 'wl':
                provider.on_playlist_x(
                    provider,
                    context,
                    command='remove',
                    category='video',
                    playlist_id=watch_later_id,
                    video_id=video_id,
                    video_name='',
                    confirmed=True,
                )
            else:
                playlist_item_id = client.get_playlist_item_id_of_video_id(
                    playlist_id=watch_later_id,
                    video_id=video_id,
                    do_auth=True,
                )
                if playlist_item_id:
                    provider.on_playlist_x(
                        provider,
                        context,
                        command='remove',
                        category='video',
                        playlist_id=watch_later_id,
                        video_id=playlist_item_id,
                        video_name='',
                        confirmed=True,
                    )

        if logged_in and not refresh_only:
            history_id = access_manager.get_watch_history_id()
            if history_id and history_id.lower() != 'hl':
                client.add_video_to_playlist(history_id, video_id)

            # rate video
            if (settings.get_bool(settings.RATE_VIDEOS) and
                    (settings.get_bool(settings.RATE_PLAYLISTS)
                     or xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() < 2)):
                json_data = client.get_video_rating(video_id)
                if json_data:
                    items = json_data.get('items', [{'rating': 'none'}])
                    rating = items[0].get('rating', 'none')
                    if rating == 'none':
                        provider.on_video_x(
                            provider,
                            context,
                            command='rate',
                            video_id=video_id,
                            current_rating=rating,
                        )

        if settings.get_bool(settings.PLAY_REFRESH):
            context.send_notification(REFRESH_CONTAINER)

        self.end()

    def stop(self):
        self.log.debug('Stop event set')
        self._stopped.set()

    def stopped(self):
        return self._stopped.is_set()

    def end(self):
        self.log.debug('End event set')
        self._ended.set()

    def ended(self):
        return self._ended.is_set()

    def join(self, timeout=None):
        return self._thread.join(timeout)


class PlayerMonitor(xbmc.Player):
    log = logging.getLogger(__name__)

    def __init__(self, provider, context, monitor):
        super(PlayerMonitor, self).__init__()
        self._provider = provider
        self._context = context
        self._monitor = monitor
        self._ui = self._context.get_ui()
        self.threads = []
        self.seeking = False
        self.seek_time = None
        self.start_time = None
        self.end_time = None
        self.current_time = None
        self.total_time = None

    def stop_threads(self):
        for thread in self.threads:
            if thread.ended():
                continue

            if not thread.stopped():
                self.log.debug('Stopping: %s', thread.name)
                thread.stop()

        for thread in self.threads:
            if thread.stopped() and not thread.ended():
                try:
                    thread.join(5)
                except RuntimeError:
                    pass

    def cleanup_threads(self, only_ended=True):
        active_threads = []
        active_thread_names = []
        for thread in self.threads:
            if only_ended and not thread.ended():
                active_threads.append(thread)
                active_thread_names.append(thread.name)
                continue

            if thread.ended():
                self.log.debug('Clean up: %s', thread.name)
            else:
                self.log.debug('Stopping: %s', thread.name)
                if not thread.stopped():
                    thread.stop()
            try:
                thread.join(5)
            except RuntimeError:
                pass

        self.log.debug('Active threads: %s', active_thread_names)
        self.threads = active_threads

    def onPlayBackStarted(self):
        if not self._ui.busy_dialog_active():
            self._ui.clear_property(BUSY_FLAG)

        if self._ui.get_property(PLAY_USING):
            self._context.execute('Action(SwitchPlayer)')
            self._context.execute('Action(Stop)')
            return

    def onAVStarted(self):
        ui = self._ui
        if ui.get_property(PLAY_USING):
            return

        if not ui.busy_dialog_active():
            ui.clear_property(BUSY_FLAG)

        player_data = ui.pop_property(PLAYER_DATA,
                                      process=json.loads,
                                      log_process=redact_params)
        if not player_data:
            return
        self.cleanup_threads()

        try:
            self.seek_time = float(player_data.get('seek_time'))
            self.start_time = float(player_data.get('start_time'))
            self.end_time = float(player_data.get('end_time'))
            self.current_time = max(0.0, self.getTime())
            self.total_time = max(0.0, self.getTotalTime())
        except (ValueError, TypeError, RuntimeError):
            self.seek_time = None
            self.start_time = None
            self.end_time = None
            self.current_time = 0.0
            self.total_time = 0.0

        self.threads.append(PlayerMonitorThread(self,
                                                self._provider,
                                                self._context,
                                                self._monitor,
                                                player_data))

    def onPlayBackEnded(self):
        ui = self._ui
        if not ui.busy_dialog_active():
            ui.clear_property(BUSY_FLAG)

        ui.pop_property(PLAY_USING)
        ui.clear_property(TRAKT_PAUSE_FLAG, raw=True)

        self.stop_threads()
        self.cleanup_threads()

    def onPlayBackStopped(self):
        self.onPlayBackEnded()

    def onPlayBackError(self):
        self.onPlayBackEnded()

    def onPlayBackSeek(self, time, seekOffset):
        time_s = time / 1000
        self.seeking = True
        self.current_time = time_s
        self.seek_time = None
        if ((self.end_time and time_s > self.end_time + 1)
                or (self.start_time and time_s < self.start_time - 1)):
            self.start_time = None
            self.end_time = None

    def onAVChange(self):
        self.seeking = False
