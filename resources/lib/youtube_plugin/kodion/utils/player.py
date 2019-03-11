# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from six.moves import cPickle as pickle

import re
import threading

import xbmc


class PlaybackMonitorThread(threading.Thread):
    def __init__(self, provider, context, playback_dict):
        super(PlaybackMonitorThread, self).__init__()

        self._stopped = threading.Event()
        self._ended = threading.Event()

        self.context = context
        self.provider = provider
        self.ui = self.context.get_ui()

        self.playback_dict = playback_dict
        self.video_id = self.playback_dict.get('video_id')

        self.daemon = True
        self.start()

    def run(self):
        playing_file = self.playback_dict.get('playing_file')
        play_count = self.playback_dict.get('play_count', 0)
        use_history = self.playback_dict.get('use_history', False)
        playback_stats = self.playback_dict.get('playback_stats')
        seek_time = self.playback_dict.get('seek_time')
        refresh_only = self.playback_dict.get('refresh_only', False)

        player = xbmc.Player()

        self.context.log_debug('PlaybackMonitorThread[%s]: Starting...' % self.video_id)
        access_manager = self.context.get_access_manager()

        settings = self.context.get_settings()

        if playback_stats is None:
            playback_stats = {}

        play_count = str(play_count)

        total_time = 0.0
        current_time = 0.0
        segment_start = 0.0
        played_time = -1.0
        percent_complete = 0

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

        if is_logged_in and report_url:
            client.update_watch_history(self.video_id, report_url)
            self.context.log_debug('Playback start reported: |%s|' % self.video_id)

        report_url = playback_stats.get('watchtime_url', '')

        plugin_play_path = 'plugin://plugin.video.youtube/play/'
        video_id_param = 'video_id=%s' % self.video_id

        while player.isPlaying() and not self.context.abort_requested() and not self.stopped():

            try:
                current_file = player.getPlayingFile()
                if (current_file != playing_file and
                    not (current_file.startswith(plugin_play_path) and
                         video_id_param in current_file)) or self.stopped():
                    self.stop()
                    break
            except RuntimeError:
                pass

            try:
                current_time = float(player.getTime())
                total_time = float(player.getTotalTime())
            except RuntimeError:
                pass

            if current_time < 0.0:
                current_time = 0.0

            try:
                percent_complete = int(float(current_time) / float(total_time) * 100)
            except ZeroDivisionError:
                percent_complete = 0

            if seek_time and seek_time != '0.0':
                try:
                    player.seekTime(float(seek_time))
                    current_time = float(seek_time)
                except ValueError:
                    pass
                seek_time = None

            if p_waited >= report_interval:
                if is_logged_in:
                    self.provider.reset_client()  # refresh client, tokens may need refreshing
                    client = self.provider.get_client(self.context)
                    is_logged_in = self.provider.is_logged_in()

                if current_time == played_time:
                    last_state = state
                    state = 'paused'
                else:
                    last_state = state
                    state = 'playing'

                played_time = current_time

            if is_logged_in and report_url:
                if first_report or (p_waited >= report_interval):
                    first_report = False
                    p_waited = 0.0

                    if state == 'playing':
                        segment_end = current_time
                    else:
                        segment_end = segment_start

                    if segment_start > segment_end:
                        segment_start = segment_end - 10.0
                        if segment_start < 0.0:
                            segment_start = 0.0

                    if segment_end > float(total_time):
                        segment_end = float(total_time)

                    if state == 'playing' or last_state == 'playing':  # only report state='paused' once
                        client.update_watch_history(self.video_id, report_url
                                                    .format(st=format(segment_start, '.3f'),
                                                            et=format(segment_end, '.3f'),
                                                            state=state))
                        self.context.log_debug(
                            'Playback reported [%s]: %s segment start, %s segment end @ %s%% state=%s' %
                            (self.video_id,
                             format(segment_start, '.3f'),
                             format(segment_end, '.3f'),
                             percent_complete, state))

                    segment_start = segment_end

            xbmc.sleep(int(p_wait_time * 1000))

            p_waited += p_wait_time

        if is_logged_in and report_url:
            client.update_watch_history(self.video_id, report_url
                                        .format(st=format(segment_start, '.3f'),
                                                et=format(current_time, '.3f'),
                                                state=state))
            self.context.log_debug('Playback reported [%s]: %s segment start, %s segment end @ %s%% state=%s' %
                                   (self.video_id,
                                    format(segment_start, '.3f'),
                                    format(current_time, '.3f'),
                                    percent_complete, state))

        self.context.log_debug('Playback stopped [%s]: %s secs of %s @ %s%%' %
                               (self.video_id, format(current_time, '.3f'),
                                format(total_time, '.3f'), percent_complete))

        state = 'stopped'
        if is_logged_in:
            self.provider.reset_client()  # refresh client, tokens may need refreshing
            client = self.provider.get_client(self.context)
            is_logged_in = self.provider.is_logged_in()

        if percent_complete >= settings.get_play_count_min_percent():
            play_count = '1'
            current_time = 0.0
            if is_logged_in and report_url:
                client.update_watch_history(self.video_id, report_url
                                            .format(st=format(total_time, '.3f'),
                                                    et=format(total_time, '.3f'),
                                                    state=state))
                self.context.log_debug('Playback reported [%s] @ 100%% state=%s' % (self.video_id, state))

        else:
            if is_logged_in and report_url:
                client.update_watch_history(self.video_id, report_url
                                            .format(st=format(current_time, '.3f'),
                                                    et=format(current_time, '.3f'),
                                                    state=state))
                self.context.log_debug('Playback reported [%s]: %s segment start, %s segment end @ %s%% state=%s' %
                                       (self.video_id, format(current_time, '.3f'),
                                        format(current_time, '.3f'),
                                        percent_complete, state))

            refresh_only = True

        if use_history:
            self.context.get_playback_history().update(self.video_id, play_count, total_time,
                                                       current_time, percent_complete)

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

    def reset(self):
        properties = ['playback_dict']
        for prop in properties:
            if self.ui.get_home_window_property(prop) is not None:
                self.context.log_debug('Clearing home window property: {property}'.format(property=prop))
                self.ui.clear_home_window_property(prop)

        self.thread_clean_up()

    def thread_clean_up(self, only_ended=True):
        active_threads = []
        for thread in self.threads:
            if only_ended and not thread.ended():
                active_threads.append(thread)
                continue

            if thread.ended():
                self.context.log_debug('PlaybackMonitorThread[%s]: clean up...' % thread.video_id)
            else:
                self.context.log_debug('PlaybackMonitorThread[%s]: stopping...' % thread.video_id)
                thread.stop()
            try:
                thread.join()
            except RuntimeError:
                pass

        self.context.log_debug('PlaybackMonitor active threads: |%s|' %
                               ', '.join([thread.video_id for thread in active_threads]))
        self.threads = active_threads

    def onPlayBackStarted(self):
        if self.ui.get_home_window_property('playback_dict'):
            playback_dict = pickle.loads(self.ui.get_home_window_property('playback_dict'))
            self.threads.append(PlaybackMonitorThread(self.provider, self.context, playback_dict))
            self.reset()

    def onAVChange(self):
        self.reset()

    def onPlayBackEnded(self):
        self.onAVChange()

    def onPlayBackStopped(self):
        self.onAVChange()

    def onPlayBackError(self):
        self.onAVChange()
