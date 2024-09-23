# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import re
import threading

from ..compatibility import xbmc
from ..constants import (
    BUSY_FLAG,
    PATHS,
    PLAYBACK_STARTED,
    PLAYBACK_STOPPED,
    PLAYER_DATA,
    PLAY_WITH,
    REFRESH_CONTAINER,
)


class PlayerMonitorThread(threading.Thread):
    def __init__(self, player, provider, context, monitor, playback_data):
        super(PlayerMonitorThread, self).__init__()

        self._stopped = threading.Event()
        self._ended = threading.Event()

        self._player = player
        self._provider = provider
        self._context = context
        self._monitor = monitor

        self.playback_data = playback_data
        self.video_id = playback_data.get('video_id')
        self.channel_id = playback_data.get('channel_id')
        self.video_status = playback_data.get('video_status')

        self.current_time = 0.0
        self.total_time = 0.0
        self.progress = 0

        self.daemon = True
        self.start()

    def abort_now(self):
        return (not self._player.isPlaying()
                or self._context.abort_requested()
                or self.stopped())

    def run(self):
        playing_file = self.playback_data.get('playing_file')
        play_count = self.playback_data.get('play_count', 0)
        use_remote_history = self.playback_data.get('use_remote_history', False)
        use_local_history = self.playback_data.get('use_local_history', False)
        playback_stats = self.playback_data.get('playback_stats', {})
        refresh_only = self.playback_data.get('refresh_only', False)
        clip = self.playback_data.get('clip', False)

        self._context.log_debug('PlayerMonitorThread[{0}]: Starting'
                                .format(self.video_id))

        player = self._player

        timeout_period = 5
        waited = 0
        wait_interval = 0.5
        while not player.isPlaying():
            if self._context.abort_requested():
                break
            if waited >= timeout_period:
                self.end()
                return

            self._context.log_debug('Waiting for playback to start')
            self._monitor.waitForAbort(wait_interval)
            waited += wait_interval
        else:
            self._context.send_notification(PLAYBACK_STARTED, {
                'video_id': self.video_id,
                'channel_id': self.channel_id,
                'status': self.video_status,
            })

        client = self._provider.get_client(self._context)
        logged_in = self._provider.is_logged_in()
        report_url = use_remote_history and playback_stats.get('playback_url')
        state = 'playing'

        if report_url:
            client.update_watch_history(
                self._context,
                self.video_id,
                report_url,
            )

        access_manager = self._context.get_access_manager()
        settings = self._context.get_settings()

        video_id_param = 'video_id=%s' % self.video_id
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
                    self._context.is_plugin_path(current_file, PATHS.PLAY)
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
                        client = self._provider.get_client(self._context)
                        logged_in = self._provider.is_logged_in()

                        if logged_in:
                            client.update_watch_history(
                                self._context,
                                self.video_id,
                                report_url,
                                status=(played_time,
                                        segment_start,
                                        segment_end,
                                        state),
                            )

                    segment_start = segment_end

            self._monitor.waitForAbort(wait_interval)
            waited += wait_interval

        self.current_time = player.current_time
        self.total_time = player.total_time
        if self.total_time > 0:
            self.progress = int(100 * self.current_time / self.total_time)

        if logged_in:
            client = self._provider.get_client(self._context)
            logged_in = self._provider.is_logged_in()

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
        self.playback_data['play_data'] = play_data

        if logged_in and report_url:
            client.update_watch_history(
                self._context,
                self.video_id,
                report_url,
                status=(segment_end, segment_end, segment_end, 'stopped'),
            )
        if use_local_history:
            self._context.get_playback_history().set_item(self.video_id,
                                                          play_data)

        self._context.send_notification(PLAYBACK_STOPPED, self.playback_data)
        self._context.log_debug('Playback stopped [{video_id}]:'
                                ' {played_time:.3f} secs of {total_time:.3f}'
                                ' @ {played_percent}%,'
                                ' played {play_count} time(s)'
                                .format(video_id=self.video_id, **play_data))

        if refresh_only:
            pass
        elif settings.get_bool('youtube.playlist.watchlater.autoremove', True):
            watch_later_id = logged_in and access_manager.get_watch_later_id()
            if watch_later_id:
                playlist_item_id = client.get_playlist_item_id_of_video_id(
                    playlist_id=watch_later_id, video_id=self.video_id
                )
                if playlist_item_id:
                    self._provider.on_playlist_x(
                        self._provider,
                        self._context,
                        method='remove',
                        category='video',
                        playlist_id=watch_later_id,
                        video_id=playlist_item_id,
                        video_name='',
                        confirmed=True,
                    )
            else:
                self._context.get_watch_later_list().del_item(self.video_id)

        if logged_in and not refresh_only:
            history_id = access_manager.get_watch_history_id()
            if history_id:
                client.add_video_to_playlist(history_id, self.video_id)

            # rate video
            if (settings.get_bool('youtube.post.play.rate') and
                    (settings.get_bool('youtube.post.play.rate.playlists')
                     or xbmc.PlayList(xbmc.PLAYLIST_VIDEO).size() < 2)):
                json_data = client.get_video_rating(self.video_id)
                if json_data:
                    items = json_data.get('items', [{'rating': 'none'}])
                    rating = items[0].get('rating', 'none')
                    if rating == 'none':
                        rating_match = re.search(
                            r'/(?P<video_id>[^/]+)/(?P<rating>[^/]+)',
                            '/'.join(('', self.video_id, rating, ''))
                        )
                        self._provider.on_video_x(
                            self._provider,
                            self._context,
                            rating_match,
                            method='rate',
                        )

        if settings.get_bool('youtube.post.play.refresh', False):
            self._context.send_notification(REFRESH_CONTAINER)

        self.end()

    def stop(self):
        self._context.log_debug('PlayerMonitorThread[{0}]: Stop event set'
                                .format(self.video_id))
        self._stopped.set()

    def stopped(self):
        return self._stopped.is_set()

    def end(self):
        self._context.log_debug('PlayerMonitorThread[{0}]: End event set'
                                .format(self.video_id))
        self._ended.set()

    def ended(self):
        return self._ended.is_set()


class PlayerMonitor(xbmc.Player):
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
                self._context.log_debug('PlayerMonitorThread[{0}]: stopping'
                                        .format(thread.video_id))
                thread.stop()

        for thread in self.threads:
            if thread.stopped() and not thread.ended():
                try:
                    thread.join(5)
                except RuntimeError:
                    pass

    def cleanup_threads(self, only_ended=True):
        active_threads = []
        for thread in self.threads:
            if only_ended and not thread.ended():
                active_threads.append(thread)
                continue

            if thread.ended():
                self._context.log_debug('PlayerMonitorThread[{0}]: clean up'
                                        .format(thread.video_id))
            else:
                self._context.log_debug('PlayerMonitorThread[{0}]: stopping'
                                        .format(thread.video_id))
                if not thread.stopped():
                    thread.stop()
            try:
                thread.join(5)
            except RuntimeError:
                pass

        self._context.log_debug('PlayerMonitor active threads: |{0}|'.format(
            ', '.join([thread.video_id for thread in active_threads])
        ))
        self.threads = active_threads

    def onPlayBackStarted(self):
        if not self._ui.busy_dialog_active():
            self._ui.clear_property(BUSY_FLAG)

        if self._ui.get_property(PLAY_WITH):
            self._context.execute('Action(SwitchPlayer)')
            self._context.execute('Action(Stop)')

    def onAVStarted(self):
        if self._ui.get_property(PLAY_WITH):
            return

        playback_data = self._ui.pop_property(PLAYER_DATA)
        if not playback_data:
            return
        self.cleanup_threads()

        playback_data = json.loads(playback_data)
        try:
            self.seek_time = float(playback_data.get('seek_time'))
            self.start_time = float(playback_data.get('start_time'))
            self.end_time = float(playback_data.get('end_time'))
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
                                                playback_data))

    def onPlayBackEnded(self):
        if not self._ui.busy_dialog_active():
            self._ui.clear_property(BUSY_FLAG)

        self._ui.pop_property(PLAY_WITH)

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
