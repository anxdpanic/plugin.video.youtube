# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import json
import re
import threading

import xbmc


class PlaybackMonitorThread(threading.Thread):
    def __init__(self, provider, context, playback_json):
        super(PlaybackMonitorThread, self).__init__()

        self._stopped = threading.Event()
        self._ended = threading.Event()

        self.context = context
        self.provider = provider
        self.ui = self.context.get_ui()

        self.player = xbmc.Player()

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

    def update_times(self, total_time, current_time, segment_start, percent_complete):
        self.total_time = total_time
        self.current_time = current_time
        self.segment_start = segment_start
        self.percent_complete = percent_complete

    def abort_now(self):
        return not self.player.isPlaying() or self.context.abort_requested() or self.stopped()

    def run(self):
        playing_file = self.playback_json.get('playing_file')
        play_count = self.playback_json.get('play_count', 0)
        use_history = self.playback_json.get('use_history', False)
        playback_history = self.playback_json.get('playback_history', False)
        playback_stats = self.playback_json.get('playback_stats')
        refresh_only = self.playback_json.get('refresh_only', False)
        try:
            seek_time = float(self.playback_json.get('seek_time'))
        except (ValueError, TypeError):
            seek_time = None

        player = self.player

        self.context.log_debug('PlaybackMonitorThread[%s]: Starting...' % self.video_id)
        access_manager = self.context.get_access_manager()

        settings = self.context.get_settings()

        if playback_stats is None:
            playback_stats = {}

        play_count = str(play_count)

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

        while not player.isPlaying() and not self.context.abort_requested():
            self.context.log_debug('Waiting for playback to start')

            xbmc.sleep(int(np_wait_time * 1000))
            if np_waited >= 5:
                self.end()
                return

            np_waited += np_wait_time

        client = self.provider.get_client(self.context)
        is_logged_in = self.provider.is_logged_in()

        if is_logged_in and report_url and use_history:
            client.update_watch_history(self.video_id, report_url)
            self.context.log_debug('Playback start reported: |%s|' % self.video_id)

        report_url = playback_stats.get('watchtime_url', '')

        plugin_play_path = 'plugin://plugin.video.youtube/play/'
        video_id_param = 'video_id=%s' % self.video_id

        notification_sent = False

        while player.isPlaying() and not self.context.abort_requested() and not self.stopped():
            if not notification_sent:
                notification_sent = True
                self.context.send_notification('PlaybackStarted', {
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
                self.update_times(last_total_time, last_current_time, last_segment_start, last_percent_complete)
                break

            try:
                self.current_time = float(player.getTime())
                self.total_time = float(player.getTotalTime())
            except RuntimeError:
                pass

            if self.current_time < 0.0:
                self.current_time = 0.0

            if self.abort_now():
                self.update_times(last_total_time, last_current_time, last_segment_start, last_percent_complete)
                break

            try:
                self.percent_complete = int(float(self.current_time) / float(self.total_time) * 100)
            except ZeroDivisionError:
                self.percent_complete = 0

            if self.abort_now():
                self.update_times(last_total_time, last_current_time, last_segment_start, last_percent_complete)
                break

            if seek_time and seek_time != 0.0:
                player.seekTime(seek_time)
                try:
                    self.current_time = float(player.getTime())
                except RuntimeError:
                    pass
                if self.current_time >= seek_time:
                    seek_time = None

            if self.abort_now():
                self.update_times(last_total_time, last_current_time, last_segment_start, last_percent_complete)
                break

            if p_waited >= report_interval:
                if is_logged_in:
                    self.provider.reset_client()  # refresh client, tokens may need refreshing
                    client = self.provider.get_client(self.context)
                    is_logged_in = self.provider.is_logged_in()

                if self.current_time == played_time:
                    last_state = state
                    state = 'paused'
                else:
                    last_state = state
                    state = 'playing'

                played_time = self.current_time

            if self.abort_now():
                self.update_times(last_total_time, last_current_time, last_segment_start, last_percent_complete)
                break

            if is_logged_in and report_url and use_history:
                if first_report or (p_waited >= report_interval):
                    if first_report:
                        first_report = False
                        self.segment_start = 0.0
                        self.current_time = 0.0
                        self.percent_complete = 0

                    p_waited = 0.0

                    if self.segment_start < 0.0:
                        self.segment_start = 0.0

                    if state == 'playing':
                        segment_end = self.current_time
                    else:
                        segment_end = self.segment_start

                    if segment_end > float(self.total_time):
                        segment_end = float(self.total_time)

                    if self.segment_start > segment_end:
                        segment_end = self.segment_start + 10.0

                    if state == 'playing' or last_state == 'playing':  # only report state='paused' once
                        client.update_watch_history(self.video_id, report_url
                                                    .format(st=format(self.segment_start, '.3f'),
                                                            et=format(segment_end, '.3f'),
                                                            state=state))
                        self.context.log_debug(
                            'Playback reported [%s]: %s segment start, %s segment end @ %s%% state=%s' %
                            (self.video_id,
                             format(self.segment_start, '.3f'),
                             format(segment_end, '.3f'),
                             self.percent_complete, state))

                    self.segment_start = segment_end

            if self.abort_now():
                break

            xbmc.sleep(int(p_wait_time * 1000))

            p_waited += p_wait_time

        if is_logged_in and report_url and use_history:
            client.update_watch_history(self.video_id, report_url
                                        .format(st=format(self.segment_start, '.3f'),
                                                et=format(self.current_time, '.3f'),
                                                state=state))
            self.context.log_debug('Playback reported [%s]: %s segment start, %s segment end @ %s%% state=%s' %
                                   (self.video_id,
                                    format(self.segment_start, '.3f'),
                                    format(self.current_time, '.3f'),
                                    self.percent_complete, state))

        self.context.send_notification('PlaybackStopped', {
            'video_id': self.video_id,
            'channel_id': self.channel_id,
            'status': self.video_status,
        })
        self.context.log_debug('Playback stopped [%s]: %s secs of %s @ %s%%' %
                               (self.video_id, format(self.current_time, '.3f'),
                                format(self.total_time, '.3f'), self.percent_complete))

        state = 'stopped'
        if is_logged_in:
            self.provider.reset_client()  # refresh client, tokens may need refreshing
            client = self.provider.get_client(self.context)
            is_logged_in = self.provider.is_logged_in()

        if self.percent_complete >= settings.get_play_count_min_percent():
            play_count = '1'
            self.current_time = 0.0
            if is_logged_in and report_url and use_history:
                client.update_watch_history(self.video_id, report_url
                                            .format(st=format(self.total_time, '.3f'),
                                                    et=format(self.total_time, '.3f'),
                                                    state=state))
                self.context.log_debug('Playback reported [%s] @ 100%% state=%s' % (self.video_id, state))

        else:
            if is_logged_in and report_url and use_history:
                client.update_watch_history(self.video_id, report_url
                                            .format(st=format(self.current_time, '.3f'),
                                                    et=format(self.current_time, '.3f'),
                                                    state=state))
                self.context.log_debug('Playback reported [%s]: %s segment start, %s segment end @ %s%% state=%s' %
                                       (self.video_id, format(self.current_time, '.3f'),
                                        format(self.current_time, '.3f'),
                                        self.percent_complete, state))

            refresh_only = True

        if playback_history:
            self.context.get_playback_history().update(self.video_id, play_count, self.total_time,
                                                       self.current_time, self.percent_complete)

        if not refresh_only:
            if is_logged_in:

                if settings.get_bool('youtube.playlist.watchlater.autoremove', True):
                    watch_later_id = access_manager.get_watch_later_id()

                    if watch_later_id and watch_later_id.strip().lower() != 'wl':
                        playlist_item_id = \
                            client.get_playlist_item_id_of_video_id(playlist_id=watch_later_id, video_id=self.video_id)
                        if playlist_item_id:
                            json_data = client.remove_video_from_playlist(watch_later_id, playlist_item_id)
                            _ = self.provider.v3_handle_error(self.provider, self.context, json_data)

                history_playlist_id = access_manager.get_watch_history_id()
                if history_playlist_id and history_playlist_id != 'HL':
                    json_data = client.add_video_to_playlist(history_playlist_id, self.video_id)
                    _ = self.provider.v3_handle_error(self.provider, self.context, json_data)

                # rate video
                if settings.get_bool('youtube.post.play.rate', False):
                    do_rating = True
                    if not settings.get_bool('youtube.post.play.rate.playlists', False):
                        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                        do_rating = int(playlist.size()) < 2

                    if do_rating:
                        json_data = client.get_video_rating(self.video_id)
                        success = self.provider.v3_handle_error(self.provider, self.context, json_data)
                        if success:
                            items = json_data.get('items', [{'rating': 'none'}])
                            rating = items[0].get('rating', 'none')
                            if rating == 'none':
                                rating_match = \
                                    re.search('/(?P<video_id>[^/]+)/(?P<rating>[^/]+)', '/%s/%s/' %
                                              (self.video_id, rating))
                                self.provider.yt_video.process('rate', self.provider, self.context, rating_match)

        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        do_refresh = (int(playlist.size()) < 2) or (playlist.getposition() == -1)

        if do_refresh and settings.get_bool('youtube.post.play.refresh', False) and \
                not xbmc.getInfoLabel('Container.FolderPath') \
                        .startswith(self.context.create_uri(['kodion', 'search', 'input'])):
            # don't refresh search input it causes request for new input,
            # (Container.Update in abstract_provider /kodion/search/input/
            # would resolve this but doesn't work with Remotes(Yatse))
            self.ui.refresh_container()

        self.end()

    def stop(self):
        self.context.log_debug('PlaybackMonitorThread[%s]: Stop event set...' % self.video_id)
        self._stopped.set()

    def stopped(self):
        return self._stopped.is_set()

    def end(self):
        self.context.log_debug('PlaybackMonitorThread[%s]: End event set...' % self.video_id)
        self._ended.set()

    def ended(self):
        return self._ended.is_set()


class YouTubePlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        self.context = kwargs.get('context')
        self.provider = kwargs.get('provider')
        self.ui = self.context.get_ui()
        self.threads = []

    def stop_threads(self):
        for thread in self.threads:
            if thread.ended():
                continue

            if not thread.stopped():
                self.context.log_debug('PlaybackMonitorThread[%s]: stopping...' % thread.video_id)
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
                self.context.log_debug('PlaybackMonitorThread[%s]: clean up...' % thread.video_id)
            else:
                self.context.log_debug('PlaybackMonitorThread[%s]: stopping...' % thread.video_id)
                if not thread.stopped():
                    thread.stop()
            try:
                thread.join()
            except RuntimeError:
                pass

        self.context.log_debug('PlaybackMonitor active threads: |%s|' %
                               ', '.join([thread.video_id for thread in active_threads]))
        self.threads = active_threads

    def onPlayBackStarted(self):
        if self.ui.get_home_window_property('playback_json'):
            playback_json = json.loads(self.ui.get_home_window_property('playback_json'))
            self.ui.clear_home_window_property('playback_json')
            self.cleanup_threads()
            self.threads.append(PlaybackMonitorThread(self.provider, self.context, playback_json))

    def onPlayBackEnded(self):
        self.stop_threads()
        self.cleanup_threads()

    def onPlayBackStopped(self):
        self.onPlayBackEnded()

    def onPlayBackError(self):
        self.onPlayBackEnded()
