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
        rpc_request = json.dumps({
            'jsonrpc': '2.0',
            'method': 'Playlist.GetItems',
            'params': {
                'properties': properties if properties else ['title', 'file'],
                'playlistid': self._playlist.getPlayListId()
            },
            'id': 1
        })

        response = json.loads(xbmc.executeJSONRPC(rpc_request))

        if 'result' in response:
            if 'items' in response['result']:
                result = response['result']['items']
            else:
                result = []
            return json.dumps(result, ensure_ascii=False) if dumps else result

        if 'error' in response:
            message = response['error']['message']
            code = response['error']['code']
            error = 'Requested |%s| received error |%s| and code: |%s|' % (rpc_request, message, code)
        else:
            error = 'Requested |%s| received error |%s|' % (rpc_request, str(response))
        self._context.log_error(error)
        return '[]' if dumps else []

    def add_items(self, items, loads=False):
        if loads:
            items = json.loads(items)

        # Playlist.GetItems allows retrieving full playlist item details, but
        # Playlist.Add only allows for file/path/id etc.
        # Have to add items individually rather than using JSON-RPC

        for item in items:
            self.add(VideoItem(item.get('title', ''), item['file']))

        # rpc_request = json.dumps({
        #     'jsonrpc': '2.0',
        #     'method': 'Playlist.Add',
        #     'params': {
        #         'playlistid': self._playlist.getPlayListId(),
        #         'item': items,
        #     },
        #     'id': 1
        # })
        # response = json.loads(xbmc.executeJSONRPC(rpc_request))
