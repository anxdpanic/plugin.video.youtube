# -*- coding: utf-8 -*-


import xbmc


class YouTubePlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        self.context = kwargs.get('context')
        self.ui = self.context.get_ui()
        self.reset()

    def reset(self):
        properties = ['playing', 'post_play', 'license_url', 'license_token']
        for prop in properties:
            if self.ui.get_home_window_property(prop) is not None:
                self.context.log_debug('Clearing home window property: {property}'.format(property=prop))
                self.ui.clear_home_window_property(prop)

    def post_play(self):
        is_playing = self.ui.get_home_window_property('playing')
        post_play_command = self.ui.get_home_window_property('post_play')
        if is_playing is not None:
            if post_play_command is not None:
                try:
                    self.context.execute(post_play_command)
                except:
                    self.context.log_debug('Failed to execute post play events.')
                    self.ui.show_notification('Failed to execute post play events.', time_milliseconds=5000)

    def onPlayBackStopped(self):
        self.post_play()
        self.reset()

    def onPlayBackEnded(self):
        self.post_play()
        self.reset()
