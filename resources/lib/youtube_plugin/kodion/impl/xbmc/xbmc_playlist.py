# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import xbmc
from ..abstract_playlist import AbstractPlaylist
from . import xbmc_items


class XbmcPlaylist(AbstractPlaylist):
    def __init__(self, playlist_type, context):
        AbstractPlaylist.__init__(self)

        self._context = context
        self._playlist = None
        if playlist_type == 'video':
            self._playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        elif playlist_type == 'audio':
            self._playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

    def clear(self):
        self._playlist.clear()

    def add(self, base_item):
        item = xbmc_items.to_video_item(self._context, base_item)
        if item:
            self._playlist.add(base_item.get_uri(), listitem=item)

    def shuffle(self):
        self._playlist.shuffle()

    def unshuffle(self):
        self._playlist.unshuffle()
