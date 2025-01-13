# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json

from ..abstract_playlist_player import AbstractPlaylistPlayer
from ...compatibility import xbmc
from ...items import VideoItem, media_listitem
from ...utils.methods import jsonrpc, wait


class XbmcPlaylistPlayer(AbstractPlaylistPlayer):
    _CACHE = {
        'player_id': None,
        'playlist_id': None
    }

    PLAYLIST_MAP = {
        0: 'music',
        1: 'video',
        'video': xbmc.PLAYLIST_VIDEO,  # 1
        'audio': xbmc.PLAYLIST_MUSIC,  # 0
    }

    def __init__(self, context, playlist_type=None, retry=None):
        super(XbmcPlaylistPlayer, self).__init__()

        self._context = context

        player = xbmc.Player()
        if retry is None:
            retry = 3 if player.isPlaying() else 0

        if playlist_type is None:
            playlist_id = self.get_playlist_id(retry=retry)
        else:
            playlist_id = self.PLAYLIST_MAP.get(playlist_type)
            if playlist_id is None:
                playlist_id = self.PLAYLIST_MAP['video']
        self.set_playlist_id(playlist_id)

        self._playlist = xbmc.PlayList(playlist_id)
        self._player = player

    def clear(self):
        self._playlist.clear()

    def add(self, base_item):
        uri, item, _ = media_listitem(self._context, base_item)
        if item:
            self._playlist.add(uri, listitem=item)

    def shuffle(self):
        self._playlist.shuffle()

    def unshuffle(self):
        self._playlist.unshuffle()

    def size(self):
        return self._playlist.size()

    def stop(self):
        return self._player.stop()

    def pause(self):
        return self._player.pause()

    def play_item(self, *args, **kwargs):
        return self._player.play(*args, **kwargs)

    def is_playing(self):
        return self._player.isPlaying()

    @classmethod
    def get_player_id(cls, retry=0):
        """Function to get active player player_id"""

        # We don't need to get player_id every time, cache and reuse instead
        player_id = cls._CACHE['player_id']
        if player_id is not None:
            return player_id

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
            cls.set_player_id(None)
            return None

        for player in result:
            if player.get('type', 'video') in cls.PLAYLIST_MAP:
                try:
                    player_id = int(player['playerid'])
                except (KeyError, TypeError, ValueError):
                    continue
                break
        else:
            # No active player
            player_id = None

        cls.set_player_id(player_id)
        return player_id

    @classmethod
    def set_player_id(cls, player_id):
        """Function to set player_id for requested player type"""

        cls._CACHE['player_id'] = player_id

    @classmethod
    def set_playlist_id(cls, playlist_id):
        """Function to set playlist_id for requested playlist type"""

        cls._CACHE['playlist_id'] = playlist_id

    @classmethod
    def get_playlist_id(cls, retry=0):
        """Function to get playlist_id of active player"""

        # We don't need to get playlist_id every time, cache and reuse instead
        playlist_id = cls._CACHE['playlist_id']
        if playlist_id is not None:
            return playlist_id

        result = jsonrpc(method='Player.GetProperties',
                         params={'playerid': cls.get_player_id(retry=retry),
                                 'properties': ['playlistid']})

        try:
            playlist_id = int(result['result']['playlistid'])
        except (KeyError, TypeError, ValueError):
            playlist_id = cls.PLAYLIST_MAP['video']

        cls.set_playlist_id(playlist_id)
        return playlist_id

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
        except (KeyError, TypeError, ValueError) as exc:
            error = response.get('error', {})
            self._context.log_error('XbmcPlaylist.get_items - Error'
                                    '\n\tException: {exc!r}'
                                    '\n\tCode:      {code}'
                                    '\n\tMessage:   {msg}'
                                    .format(exc=exc,
                                            code=error.get('code', 'Unknown'),
                                            msg=error.get('message', 'Unknown')))
        return '' if dumps else []

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
        #             'playlistid': self._playlist.getPlaylistId(),
        #             'item': items,
        #         },
        #         no_response=True)

        return len(items)

    def play_playlist_item(self, position, resume=False, defer=False):
        """
        Function to play item in playlist from a specified position, where the
        first item in the playlist is position 1
        """

        context = self._context
        playlist_id = self._playlist.getPlayListId()

        if position == 'next':
            position, _ = self.get_position(offset=1)
        if not position:
            context.log_warning('Unable to play from playlist position: {0}'
                                .format(position))
            return
        context.log_debug('Playing from playlist: {id}, position: {position}'
                          .format(id=playlist_id,
                                  position=position))

        if not resume:
            command = 'Playlist.PlayOffset({type},{position})'.format(
                type=self.PLAYLIST_MAP.get(playlist_id) or 'video',
                position=position - 1,
            )
            if defer:
                return ''.join(('command://', command))
            return self._context.execute(command)

        # JSON Player.Open can be too slow but is needed if resuming is enabled
        jsonrpc(method='Player.Open',
                params={'item': {'playlistid': playlist_id,
                                 # Convert 1 indexed to 0 indexed position
                                 'position': position - 1}},
                options={'resume': True},
                no_response=True)

    def play(self, playlist_index=-1, defer=False):
        """
        We call the player in this way, because 'Player.play(...)' will call the
        addon again while the instance is running. This is somehow shitty,
        because we couldn't release any resources and in our case we couldn't
        release the cache. So this is the solution to prevent a locked database
        (sqlite) and Kodi crashing.
        """

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

        playlist_type = self.PLAYLIST_MAP.get(self._playlist.getPlayListId())
        command = 'Playlist.PlayOffset({type},{position})'.format(
            type=playlist_type or 'video',
            position=playlist_index,
        )
        if defer:
            return ''.join(('command://', command))
        return self._context.execute(command)

    def get_position(self, offset=0):
        """
        Function to get current playlist position and number of remaining
        playlist items, where the first item in the playlist is position 1
        """

        position = self._playlist.getposition()
        # PlayList().getposition() starts from zero unless playlist not active
        if position < 0:
            return None, None
        playlist_size = self._playlist.size()
        # Use 1 based index value for playlist position
        position += (offset + 1)

        # A playlist with only one element has no next item
        if playlist_size >= 1 and position <= playlist_size:
            self._context.log_debug('playlist_id: {0}, position - {1}/{2}'
                                    .format(self.get_playlist_id(),
                                            position,
                                            playlist_size))
            return position, (playlist_size - position)
        return None, None
