# -*- coding: utf-8 -*-

import xbmc
import xbmcvfs


class YouTubePlayer(xbmc.Player):
    def __init__(self, *args, **kwargs):
        self.context = kwargs.get('context')
        self.ui = self.context.get_ui()
        self.reset()

    def reset(self):
        self.context.log_debug('Clearing home window property: {property}'.format(property='playing'))
        self.ui.clear_home_window_property('playing')

    def remove_temp_dir(self):
        temp_path = 'special://temp/plugin.video.youtube/'
        try:
            xbmcvfs.rmdir(temp_path, force=True)
            return True
        except:
            self.context.log_debug('Failed to remove directory: {dir}'.format(dir=temp_path))
            return False

    def onPlayBackStopped(self):
        if self.ui.get_home_window_property('playing') == 'true':
            self.remove_temp_dir()
        self.reset()

    def onPlayBackEnded(self):
        if self.ui.get_home_window_property('playing') == 'true':
            self.remove_temp_dir()
        self.reset()
