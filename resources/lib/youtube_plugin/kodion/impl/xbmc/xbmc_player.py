# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import xbmc
from ..abstract_player import AbstractPlayer


class XbmcPlayer(AbstractPlayer):
    def __init__(self, player_type, context):
        AbstractPlayer.__init__(self)

        self._player_type = player_type
        if player_type == 'audio':
            self._player_type = 'music'

        self._context = context

    def play(self, playlist_index=-1):
        """
        We call the player in this way, because 'Player.play(...)' will call the addon again while the instance is
        running.  This is somehow shitty, because we couldn't release any resources and in our case we couldn't release
        the cache. So this is the solution to prevent a locked database (sqlite).
        """
        self._context.execute('Playlist.PlayOffset(%s,%d)' % (self._player_type, playlist_index))

        """
        playlist = None
        if self._player_type == 'video':
            playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        elif self._player_type == 'music':
            playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

        if playlist_index >= 0:
            xbmc.Player().play(item=playlist, startpos=playlist_index)
        else:
            xbmc.Player().play(item=playlist)
        """

    def stop(self):
        xbmc.Player().stop()

    def pause(self):
        xbmc.Player().pause()

    def is_playing(self):
        return xbmc.Player().isPlaying()
