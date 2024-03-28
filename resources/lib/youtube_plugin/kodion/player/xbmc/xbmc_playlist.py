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
    _CACHE = {
        'playerid': None,
        'playlistid': None
    }

    _PLAYER_PLAYLIST = {
        'video': xbmc.PLAYLIST_VIDEO,  # 1
        'audio': xbmc.PLAYLIST_MUSIC,  # 0
    }

    def __init__(self, playlist_type, context):
        super(XbmcPlaylist, self).__init__()

        self._context = context
        self._playlist = None
        playlist_type = self._PLAYER_PLAYLIST.get(playlist_type)
        if playlist_type:
            self._playlist = xbmc.PlayList(playlist_type)
        else:
            self._playlist = xbmc.PlayList(self.get_playlistid())

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

    @classmethod
    def get_playerid(cls, retry=3):
        """Function to get active player playerid"""

        # We don't need to get playerid every time, cache and reuse instead
        if cls._CACHE['playerid'] is not None:
            return cls._CACHE['playerid']

        # Sometimes Kodi gets confused and uses a music playlist for video
        # content, so get the first active player instead, default to video
        # player. Wait 2s per retry in case of delay in getting response.
        attempts_left = 1 + retry
        while attempts_left > 0:
            result = jsonrpc(method='Player.GetActivePlayers').get('result')
            if result:
                break

            attempts_left -= 1
            if attempts_left > 0:
                wait(2)
        else:
            # No active player
            cls._CACHE['playerid'] = None
            return None

        for player in result:
            if player.get('type', 'video') in cls._PLAYER_PLAYLIST:
                playerid = player.get('playerid')
                if playerid is not None:
                    playerid = int(playerid)
                break
        else:
            # No active player
            cls._CACHE['playerid'] = None
            return None

        cls._CACHE['playerid'] = playerid
        return playerid

    @classmethod
    def get_playlistid(cls):
        """Function to get playlistid of active player"""

        # We don't need to get playlistid every time, cache and reuse instead
        if cls._CACHE['playlistid'] is not None:
            return cls._CACHE['playlistid']

        result = jsonrpc(method='Player.GetProperties',
                         params={'playerid': cls.get_playerid(),
                                 'properties': ['playlistid']})

        try:
            playlistid = int(result['result']['playlistid'])
        except (KeyError, TypeError, ValueError):
            playlistid = cls._PLAYER_PLAYLIST['video']

        cls._CACHE['playlistid'] = playlistid
        return playlistid

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
        except (KeyError, TypeError, ValueError):
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

        return len(items)

    def play_playlist_item(self, position, resume=False):
        """
        Function to play item in playlist from a specified position, where the
        first item in the playlist is position 1
        """

        if position == 'next':
            position, _ = self.get_position(offset=1)
        context = self._context
        if not position:
            context.log_warning('Unable to play from playlist position: {0}'
                                .format(position))
            return
        context.log_debug('Playing from playlist position: {0}'
                          .format(position))

        # JSON Player.Open can be too slow but is needed if resuming is enabled
        jsonrpc(method='Player.Open',
                params={'item': {'playlistid': self._playlist.getPlayListId(),
                                 # Convert 1 indexed to 0 indexed position
                                 'position': position - 1}},
                options={'resume': resume},
                no_response=True)

    def get_position(self, offset=0):
        """
        Function to get current playlist position and number of remaining
        playlist items, where the first item in the playlist is position 1
        """

        result = (None, None)

        # Use actual playlistid rather than xbmc.PLAYLIST_VIDEO as Kodi
        # sometimes plays video content in a music playlist
        playlistid = self._playlist.getPlayListId()
        if playlistid is None:
            return result

        playlist = xbmc.PlayList(playlistid)
        position = playlist.getposition()
        # PlayList().getposition() starts from zero unless playlist not active
        if position < 0:
            return result
        playlist_size = playlist.size()
        # Use 1 based index value for playlist position
        position += (offset + 1)

        # A playlist with only one element has no next item
        if playlist_size > 1 and position <= playlist_size:
            self._context.log_debug('playlistid: {0}, position - {1}/{2}'
                                    .format(playlistid,
                                            position,
                                            playlist_size))
            result = (position, (playlist_size - position))
        return result
