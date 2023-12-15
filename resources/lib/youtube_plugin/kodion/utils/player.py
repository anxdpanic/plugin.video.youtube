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


class PlaybackMonitorThread(threading.Thread):
    def __init__(self, player, provider, context, playback_json):
        super(PlaybackMonitorThread, self).__init__()

        self._stopped = threading.Event()
        self._ended = threading.Event()

        self._context = context
        self.provider = provider
        self.ui = self._context.get_ui()

        self.player = player

        self.playback_json = playback_json
        self.video_id = self.playback_json.get('video_id')
        self.channel_id = self.playback_json.get('channel_id')
        self.video_status = self.playback_json.get('video_status')

        self.total_time = 0.0
        self.current_time = 0.0
        self.segment_start = 0.0
        self.percent_complete = 0

        self.daemon = True
        self.start()

    def update_times(self,
                     total_time,
                     current_time,
                     segment_start,
                     percent_complete):
        self.total_time = total_time
        self.current_time = current_time
        self.segment_start = segment_start
        self.percent_complete = percent_complete

    def abort_now(self):
        return (not self.player.isPlaying()
                or self._context.abort_requested()
                or self.stopped())

    def run(self):
        playing_file = self.playback_json.get('playing_file')
        play_count = self.playback_json.get('play_count', 0)
        use_remote_history = self.playback_json.get('use_remote_history', False)
        use_local_history = self.playback_json.get('use_local_history', False)
        playback_stats = self.playback_json.get('playback_stats')
        refresh_only = self.playback_json.get('refresh_only', False)
        clip = self.playback_json.get('clip', False)

        player = self.player

        self._context.log_debug('PlaybackMonitorThread[{0}]: Starting'
                                .format(self.video_id))
        access_manager = self._context.get_access_manager()

        settings = self._context.get_settings()

        if playback_stats is None:
            playback_stats = {}

        played_time = -1.0

        state = 'playing'
        last_state = 'playing'

        np_wait_time = 0.2
        np_waited = 0.0
        p_wait_time = 0.5
        p_waited = 0.0

        report_interval = 10.0
        first_report = True

        report_url = playback_stats.get('playback_url', '')

        while not player.isPlaying() and not self._context.abort_requested():
            self._context.log_debug('Waiting for playback to start')

            xbmc.sleep(int(np_wait_time * 1000))
            if np_waited >= 5:
                self.end()
                return

            np_waited += np_wait_time

        client = self.provider.get_client(self._context)
        is_logged_in = self.provider.is_logged_in()

        if is_logged_in and report_url and use_remote_history:
            client.update_watch_history(
                self._context,
                self.video_id,
                report_url,
                st=0,
                et='N/A',
                state=state
            )

        report_url = playback_stats.get('watchtime_url', '')

        plugin_play_path = 'plugin://plugin.video.youtube/play/'
        video_id_param = 'video_id=%s' % self.video_id

        notification_sent = False

        while not self.abort_now():
            if not notification_sent:
                notification_sent = True
                self._context.send_notification('PlaybackStarted', {
                    'video_id': self.video_id,
                    'channel_id': self.channel_id,
                    'status': self.video_status,
                })

            last_total_time = self.total_time
            last_current_time = self.current_time
            last_segment_start = self.segment_start
            last_percent_complete = self.percent_complete

            try:
                current_file = player.getPlayingFile()
                if (current_file != playing_file and
                    not (current_file.startswith(plugin_play_path) and
                         video_id_param in current_file)) or self.stopped():
                    self.stop()
                    break
            except RuntimeError:
                pass

            if self.abort_now():
                self.update_times(last_total_time,
                                  last_current_time,
                                  last_segment_start,
                                  last_percent_complete)
                break

            try:
                self.current_time = float(player.getTime())
                self.total_time = float(player.getTotalTime())
            except RuntimeError:
                pass

            if self.current_time < 0:
                self.current_time = 0.0

            if self.abort_now():
                self.update_times(last_total_time,
                                  last_current_time,
                                  last_segment_start,
                                  last_percent_complete)
                break

            try:
                self.percent_complete = int(100 * self.current_time
                                            / self.total_time)
            except ZeroDivisionError:
                self.percent_complete = 0

            if self.abort_now():
                self.update_times(last_total_time,
                                  last_current_time,
                                  last_segment_start,
                                  last_percent_complete)
                break

            if player.start_time or player.seek_time:
                _seek_time = player.start_time or player.seek_time
                if self.current_time < _seek_time:
                    player.seekTime(_seek_time)
                    try:
                        self.current_time = float(player.getTime())
                    except RuntimeError:
                        pass

            if player.end_time and self.current_time >= player.end_time:
                if clip and player.start_time:
                    player.seekTime(player.start_time)
                else:
                    player.stop()

            if self.abort_now():
                self.update_times(last_total_time,
                                  last_current_time,
                                  last_segment_start,
                                  last_percent_complete)
                break

            if p_waited >= report_interval:
                # refresh client, tokens may need refreshing
                if is_logged_in:
                    self.provider.reset_client()
                    client = self.provider.get_client(self._context)
                    is_logged_in = self.provider.is_logged_in()

                if self.current_time == played_time:
                    last_state = state
                    state = 'paused'
                else:
                    last_state = state
                    state = 'playing'

                played_time = self.current_time

            if self.abort_now():
                self.update_times(last_total_time,
                                  last_current_time,
                                  last_segment_start,
                                  last_percent_complete)
                break

            if (is_logged_in and report_url and use_remote_history
                    and (first_report or p_waited >= report_interval)):
                if first_report:
                    first_report = False
                    self.segment_start = 0.0
                    self.current_time = 0.0
                    self.percent_complete = 0

                p_waited = 0.0

                if self.segment_start < 0:
                    self.segment_start = 0.0

                if state == 'playing':
                    segment_end = self.current_time
                else:
                    segment_end = self.segment_start

                if segment_end > float(self.total_time):
                    segment_end = float(self.total_time)

                if self.segment_start > segment_end:
                    segment_end = self.segment_start + 10.0

                # only report state='paused' once
                if state == 'playing' or last_state == 'playing':
                    client.update_watch_history(
                        self._context,
                        self.video_id,
                        report_url,
                        st=format(self.segment_start, '.3f'),
                        et=format(segment_end, '.3f'),
                        state=state
                    )

                self.segment_start = segment_end

            if self.abort_now():
                break

            xbmc.sleep(int(p_wait_time * 1000))

            p_waited += p_wait_time

        if is_logged_in and report_url and use_remote_history:
            client.update_watch_history(
                self._context,
                self.video_id,
                report_url,
                st=format(self.segment_start, '.3f'),
                et=format(self.current_time, '.3f'),
                state=state
            )

        self._context.send_notification('PlaybackStopped', {
            'video_id': self.video_id,
            'channel_id': self.channel_id,
            'status': self.video_status,
        })
        self._context.log_debug('Playback stopped [{video_id}]:'
                                ' {current:.3f} secs of {total:.3f}'
                                ' @ {percent}%'.format(
            video_id=self.video_id,
            current=self.current_time,
            total=self.total_time,
            percent=self.percent_complete,
        ))

        state = 'stopped'
        # refresh client, tokens may need refreshing
        if is_logged_in:
            self.provider.reset_client()
            client = self.provider.get_client(self._context)
            is_logged_in = self.provider.is_logged_in()

        if self.percent_complete >= settings.get_play_count_min_percent():
            play_count += 1
            self.current_time = 0.0
            if is_logged_in and report_url and use_remote_history:
                client.update_watch_history(
                    self._context,
                    self.video_id,
                    report_url,
                    st=format(self.total_time, '.3f'),
                    et=format(self.total_time, '.3f'),
                    state=state
                )

        else:
            if is_logged_in and report_url and use_remote_history:
                client.update_watch_history(
                    self._context,
                    self.video_id,
                    report_url,
                    st=format(self.current_time, '.3f'),
                    et=format(self.current_time, '.3f'),
                    state=state
                )

            refresh_only = True

        if use_local_history:
            play_data = {
                'play_count': play_count,
                'total_time': self.total_time,
                'played_time': self.current_time,
                'played_percent': self.percent_complete,
            }
            self._context.get_playback_history().update(self.video_id,
                                                        play_data)

        if not refresh_only and is_logged_in:
            if settings.get_bool('youtube.playlist.watchlater.autoremove',
                                 True):
                watch_later_id = access_manager.get_watch_later_id()

                if watch_later_id:
                    playlist_item_id = client.get_playlist_item_id_of_video_id(
                        playlist_id=watch_later_id, video_id=self.video_id
                    )
                    if playlist_item_id:
                        json_data = client.remove_video_from_playlist(
                            watch_later_id, playlist_item_id
                        )

            history_playlist_id = access_manager.get_watch_history_id()
            if history_playlist_id and history_playlist_id != 'HL':
                json_data = client.add_video_to_playlist(history_playlist_id,
                                                         self.video_id)

            # rate video
            if settings.get_bool('youtube.post.play.rate', False):
                do_rating = True
                if not settings.get_bool('youtube.post.play.rate.playlists',
                                         False):
                    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                    do_rating = int(playlist.size()) < 2

                if do_rating:
                    json_data = client.get_video_rating(self.video_id)
                    if json_data:
                        items = json_data.get('items', [{'rating': 'none'}])
                        rating = items[0].get('rating', 'none')
                        if rating == 'none':
                            rating_match = \
                                re.search(r'/(?P<video_id>[^/]+)'
                                          r'/(?P<rating>[^/]+)',
                                          '/{0}/{1}/'.format(self.video_id,
                                                             rating))
                            self.provider.yt_video.process('rate',
                                                           self.provider,
                                                           self._context,
                                                           rating_match)

        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        do_refresh = playlist.size() < 2 or playlist.getposition() == -1
        if (do_refresh and settings.get_bool('youtube.post.play.refresh', False)
                and not xbmc.getInfoLabel('Container.FolderPath').startswith(
                    self._context.create_uri(['kodion', 'search', 'input'])
                )):
            # don't refresh search input it causes request for new input,
            # (Container.Update in abstract_provider /kodion/search/input/
            # would resolve this but doesn't work with Remotes(Yatse))
            self.ui.refresh_container()

        self.end()

    def stop(self):
        self._context.log_debug('PlaybackMonitorThread[{0}]: Stop event set'
                                .format(self.video_id))
        self._stopped.set()

    def stopped(self):
        return self._stopped.is_set()

    def end(self):
        self._context.log_debug('PlaybackMonitorThread[{0}]: End event set'
                                .format(self.video_id))
        self._ended.set()

    def ended(self):
        return self._ended.is_set()


class YouTubePlayer(xbmc.Player):
    def __init__(self, *_args, **kwargs):
        super(YouTubePlayer, self).__init__()
        self._context = kwargs.get('context')
        self.provider = kwargs.get('provider')
        self.ui = self._context.get_ui()
        self.threads = []
        self.seek_time = None
        self.start_time = None
        self.end_time = None

    def stop_threads(self):
        for thread in self.threads:
            if thread.ended():
                continue

            if not thread.stopped():
                self._context.log_debug('PlaybackMonitorThread[{0}]: stopping'
                                        .format(thread.video_id))
                thread.stop()

        for thread in self.threads:
            if thread.stopped() and not thread.ended():
                try:
                    thread.join()
                except RuntimeError:
                    pass

    def cleanup_threads(self, only_ended=True):
        active_threads = []
        for thread in self.threads:
            if only_ended and not thread.ended():
                active_threads.append(thread)
                continue

            if thread.ended():
                self._context.log_debug('PlaybackMonitorThread[{0}]: clean up'
                                        .format(thread.video_id))
            else:
                self._context.log_debug('PlaybackMonitorThread[{0}]: stopping'
                                        .format(thread.video_id))
                if not thread.stopped():
                    thread.stop()
            try:
                thread.join()
            except RuntimeError:
                pass

        self._context.log_debug('PlaybackMonitor active threads: |{0}|'.format(
            ', '.join([thread.video_id for thread in active_threads])
        ))
        self.threads = active_threads

    def onAVStarted(self):
        if not self.ui.busy_dialog_active():
            self.ui.clear_property('busy')

        playback_json = self.ui.get_property('playback_json')
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

        self.ui.clear_property('playback_json')
        self.cleanup_threads()
        self.threads.append(PlaybackMonitorThread(self,
                                                  self.provider,
                                                  self._context,
                                                  playback_json))

    def onPlayBackEnded(self):
        if not self.ui.busy_dialog_active():
            self.ui.clear_property('busy')

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
