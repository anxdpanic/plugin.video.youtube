# -*- coding: utf-8 -*-

import math
import xbmc


class YouTubePlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        self.context = kwargs.get('context')
        self.ui = self.context.get_ui()
        self.reset()
        self.current_video_total_time = 0.0
        self.current_played_time = 0.0

    def reset(self):
        properties = ['playing', 'post_play', 'license_url', 'license_token',
                      'seek_time', 'play_count', 'playback_history', 'addon_id',
                      'prompt_for_subtitles']
        cleared = []
        for prop in properties:
            if self.ui.get_home_window_property(prop) is not None:
                cleared.append(prop)
                self.ui.clear_home_window_property(prop)
        self.context.log_debug('Cleared home window properties: {properties}'.format(properties=str(cleared)))
        self.current_video_total_time = 0.0
        self.current_played_time = 0.0

    def post_play(self):
        is_playing = self.ui.get_home_window_property('playing')
        post_play_command = self.ui.get_home_window_property('post_play')
        use_playback_history = self.ui.get_home_window_property('playback_history') == 'true'

        if is_playing is not None:
            try:
                current_played_percent = int(math.floor((self.current_played_time / self.current_video_total_time) * 100))
            except ZeroDivisionError:
                current_played_percent = 0
            self.context.log_debug('Playback: Total time: |{total_time}| Played time: |{time}| Played percent: |{percent}|'
                                   .format(total_time=self.current_video_total_time, time=self.current_played_time,
                                           percent=current_played_percent))

            play_count = self.ui.get_home_window_property('play_count')

            if current_played_percent >= self.context.get_settings().get_play_count_min_percent():
                play_count = '1'
                self.current_played_time = 0.0
                current_played_percent = 0
            else:
                if post_play_command:
                    addon_id = self.ui.get_home_window_property('addon_id')
                    if addon_id:
                        post_play_command = 'RunPlugin(%s)' % self.context.create_uri(['events', 'post_play'],
                                                                                      {'video_id': is_playing,
                                                                                       'addon_id': addon_id,
                                                                                       'refresh_only': 'true'})
                    else:
                        post_play_command = 'RunPlugin(%s)' % self.context.create_uri(['events', 'post_play'],
                                                                                      {'video_id': is_playing,
                                                                                       'refresh_only': 'true'})
                else:
                    self.ui.clear_home_window_property('video_stats_url')

            if use_playback_history and self.context.get_settings().use_playback_history():
                self.context.get_playback_history().update(is_playing, play_count, self.current_video_total_time,
                                                           self.current_played_time, current_played_percent)

            if post_play_command is not None:
                try:
                    self.context.execute(post_play_command)
                except:
                    self.context.log_debug('Failed to execute post play events.')
                    self.ui.show_notification('Failed to execute post play events.', time_milliseconds=5000)

    def onPlayBackStarted(self):
        self.current_video_total_time = self.getTotalTime()
        seek_time = self.ui.get_home_window_property('seek_time')
        while self.isPlaying():
            xbmc.sleep(500)
            if self.isPlaying():
                if self.context.get_settings().use_playback_history():
                    if seek_time and seek_time != '0.0':
                        self.seekTime(float(seek_time))
                        seek_time = None
                self.current_played_time = self.getTime()
                if self.current_video_total_time == 0.0:
                    self.current_video_total_time = self.getTotalTime()

    def onPlayBackStopped(self):
        self.post_play()
        self.reset()

    def onPlayBackEnded(self):
        self.post_play()
        self.reset()
