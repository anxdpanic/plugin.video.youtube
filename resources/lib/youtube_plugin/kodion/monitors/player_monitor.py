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


class PlayerMonitorThread(threading.Thread):
    def __init__(self, player, provider, context, monitor, playback_json):
        super(PlayerMonitorThread, self).__init__()

        self._stopped = threading.Event()
        self._ended = threading.Event()

        self._player = player
        self._provider = provider
        self._context = context
        self._monitor = monitor

        self.playback_json = playback_json
        self.video_id = self.playback_json.get('video_id')
        self.channel_id = self.playback_json.get('channel_id')
        self.video_status = self.playback_json.get('video_status')

        self.total_time = 0.0
        self.current_time = 0.0
        self.progress = 0

        self.daemon = True
        self.start()

    def abort_now(self):
        return (not self._player.isPlaying()
                or self._context.abort_requested()
                or self.stopped())

    def run(self):
        playing_file = self.playback_json.get('playing_file')
        play_count = self.playback_json.get('play_count', 0)
        use_remote_history = self.playback_json.get('use_remote_history', False)
        use_local_history = self.playback_json.get('use_local_history', False)
        playback_stats = self.playback_json.get('playback_stats', {})
        refresh_only = self.playback_json.get('refresh_only', False)
        clip = self.playback_json.get('clip', False)

        self._context.log_debug('PlayerMonitorThread[{0}]: Starting'
                                .format(self.video_id))

        player = self._player

        timeout_period = 5
        waited = 0
        wait_interval = 0.2
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
            self._context.send_notification('PlaybackStarted', {
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

        segment_start = 0
        played_time = -1.0
        wait_interval = 0.5
        report_period = waited = 10
        while not self.abort_now():
            try:
                current_file = player.getPlayingFile()
                self.current_time = player.getTime()
                self.total_time = player.getTotalTime()
            except RuntimeError:
                self.stop()
                break

            if (current_file != playing_file and not (
                    self._context.is_plugin_path(current_file, 'play/')
                    and video_id_param in current_file)):
                self.stop()
                break

            if self.current_time < 0:
                self.current_time = 0.0

            if self.total_time <= 0:
                self.stop()
                break
            self.progress = int(100 * self.current_time / self.total_time)

            if player.start_time or player.seek_time:
                _seek_time = player.start_time or player.seek_time
                if self.current_time < _seek_time:
                    player.seekTime(_seek_time)
                    try:
                        self.current_time = player.getTime()
                    except RuntimeError:
                        self.stop()
                        break

            if player.end_time and self.current_time >= player.end_time:
                if clip and player.start_time:
                    player.seekTime(player.start_time)
                else:
                    player.stop()

            if waited >= report_period:
                waited = 0

                last_state = state
                if self.current_time == played_time:
                    state = 'paused'
                else:
                    state = 'playing'
                played_time = self.current_time

                if logged_in and report_url:
                    if state == 'playing':
                        segment_end = self.current_time
                    else:
                        segment_end = segment_start

                    if segment_start > segment_end:
                        segment_end = segment_start + report_period

                    if segment_end > self.total_time:
                        segment_end = self.total_time

                    # only report state='paused' once
                    if state == 'playing' or last_state == 'playing':
                        # refresh client, tokens may need refreshing
                        self._provider.reset_client()
                        client = self._provider.get_client(self._context)
                        logged_in = self._provider.is_logged_in()

                        if logged_in:
                            client.update_watch_history(
                                self._context,
                                self.video_id,
                                report_url,
                                status=(self.current_time,
                                        segment_start,
                                        segment_end,
                                        state),
                            )

                    segment_start = segment_end

            self._monitor.waitForAbort(wait_interval)
            waited += wait_interval

        state = 'stopped'
        self._context.send_notification('PlaybackStopped', {
            'video_id': self.video_id,
            'channel_id': self.channel_id,
            'status': self.video_status,
        })
        self._context.log_debug('Playback stopped [{video_id}]:'
                                ' {current:.3f} secs of {total:.3f}'
                                ' @ {percent}%'
                                .format(video_id=self.video_id,
                                        current=self.current_time,
                                        total=self.total_time,
                                        percent=self.progress))

        # refresh client, tokens may need refreshing
        if logged_in:
            self._provider.reset_client()
            client = self._provider.get_client(self._context)
            logged_in = self._provider.is_logged_in()

        if self.progress >= settings.get_play_count_min_percent():
            play_count += 1
            self.current_time = 0.0
            segment_end = self.total_time
        else:
            segment_end = self.current_time
            refresh_only = True

        if logged_in and report_url:
            client.update_watch_history(
                self._context,
                self.video_id,
                report_url,
                status=(segment_end,
                        segment_end,
                        segment_end,
                        state),
            )
        if use_local_history:
            play_data = {
                'play_count': play_count,
                'total_time': self.total_time,
                'played_time': self.current_time,
                'played_percent': self.progress,
            }
            self._context.get_playback_history().update(self.video_id,
                                                        play_data)

        if refresh_only:
            pass
        elif settings.get_bool('youtube.playlist.watchlater.autoremove', True):
            watch_later_id = logged_in and access_manager.get_watch_later_id()
            if watch_later_id:
                playlist_item_id = client.get_playlist_item_id_of_video_id(
                    playlist_id=watch_later_id, video_id=self.video_id
                )
                if playlist_item_id:
                    client.remove_video_from_playlist(
                        watch_later_id, playlist_item_id
                    )
            else:
                self._context.get_watch_later_list().remove(self.video_id)

        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        in_playlist = playlist.size() >= 2

        if logged_in and not refresh_only:
            history_id = access_manager.get_watch_history_id()
            if history_id:
                client.add_video_to_playlist(history_id, self.video_id)

            # rate video
            if (settings.get_bool('youtube.post.play.rate') and
                    (not in_playlist or
                     settings.get_bool('youtube.post.play.rate.playlists'))):
                json_data = client.get_video_rating(self.video_id)
                if json_data:
                    items = json_data.get('items', [{'rating': 'none'}])
                    rating = items[0].get('rating', 'none')
                    if rating == 'none':
                        rating_match = re.search(
                            r'/(?P<video_id>[^/]+)/(?P<rating>[^/]+)',
                            '/{0}/{1}/'.format(self.video_id, rating)
                        )
                        self._provider.yt_video.process('rate',
                                                        self._provider,
                                                        self._context,
                                                        rating_match)

        if ((not in_playlist or playlist.getposition() == -1)
                and settings.get_bool('youtube.post.play.refresh', False)):
            self._context.get_ui().refresh_container()

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
        self.seek_time = None
        self.start_time = None
        self.end_time = None

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

    def onAVStarted(self):
        if not self._ui.busy_dialog_active():
            self._ui.clear_property('busy')

        playback_json = self._ui.get_property('playback_json')
        if not playback_json:
            return

        playback_json = json.loads(playback_json)
        try:
            self.seek_time = float(playback_json.get('seek_time'))
            self.start_time = float(playback_json.get('start_time'))
            self.end_time = float(playback_json.get('end_time'))
        except (ValueError, TypeError):
            self.seek_time = None
            self.start_time = None
            self.end_time = None

        self._ui.clear_property('playback_json')
        self.cleanup_threads()
        self.threads.append(PlayerMonitorThread(self,
                                                self._provider,
                                                self._context,
                                                self._monitor,
                                                playback_json))

    def onPlayBackEnded(self):
        if not self._ui.busy_dialog_active():
            self._ui.clear_property('busy')

        self.stop_threads()
        self.cleanup_threads()

    def onPlayBackStopped(self):
        self.onPlayBackEnded()

    def onPlayBackError(self):
        self.onPlayBackEnded()

    def onPlayBackSeek(self, time, seekOffset):
        time_s = time / 1000
        self.seek_time = None
        if ((self.end_time and time_s > self.end_time + 1)
                or (self.start_time and time_s < self.start_time - 1)):
            self.start_time = None
            self.end_time = None
