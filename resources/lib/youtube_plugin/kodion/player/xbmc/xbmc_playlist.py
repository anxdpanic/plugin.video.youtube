# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json

from ..abstract_playlist import AbstractPlaylist
from ...compatibility import xbmc
from ...items import VideoItem, video_listitem
from ...utils.methods import jsonrpc, wait


class XbmcPlaylist(AbstractPlaylist):
    def __init__(self, playlist_type, context):
        super(XbmcPlaylist, self).__init__()

        self._context = context
        self._playlist = None
        if playlist_type == 'video':
            self._playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        elif playlist_type == 'audio':
            self._playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)

    def clear(self):
        self._playlist.clear()

    def add(self, base_item):
        uri, item, _ = video_listitem(self._context, base_item)
        if item:
            self._playlist.add(uri, listitem=item)

    def shuffle(self):
        self._playlist.shuffle()

    def unshuffle(self):
        self._playlist.unshuffle()

    def size(self):
        return self._playlist.size()

    def get_items(self, properties=None, dumps=False):
        if properties is None:
            properties = ('title', 'file')
        response = jsonrpc(method='Playlist.GetItems',
                           params={
                               'properties': properties,
                               'playlistid': self._playlist.getPlayListId(),
                           })

        try:
            result = response['result']['items']
            return json.dumps(result, ensure_ascii=False) if dumps else result
        except KeyError:
            error = response.get('error', {})
            self._context.log_error('XbmcPlaylist.get_items error - |{0}: {1}|'
                                    .format(error.get('code', 'unknown'),
                                            error.get('message', 'unknown')))
        return '[]' if dumps else []

    def add_items(self, items, loads=False):
        if loads:
            items = json.loads(items)

        # Playlist.GetItems allows retrieving full playlist item details, but
        # Playlist.Add only allows for file/path/id etc.
        # Have to add items individually rather than using JSON-RPC

        for item in items:
            self.add(VideoItem(item.get('title', ''), item['file']))

        # jsonrpc(method='Playlist.Add',
        #         params={
        #             'playlistid': self._playlist.getPlayListId(),
        #             'item': items,
        #         },
        #         no_response=True)
