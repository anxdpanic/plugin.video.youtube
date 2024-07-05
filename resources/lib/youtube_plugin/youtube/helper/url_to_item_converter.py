# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import re

from . import utils
from ...kodion.compatibility import parse_qsl, urlsplit
from ...kodion.constants import PATHS
from ...kodion.items import DirectoryItem, UriItem, VideoItem
from ...kodion.utils import duration_to_seconds


class UrlToItemConverter(object):
    RE_PATH_ID = re.compile(r'/[^/]+/(?P<id>[^/?#]+)', re.I)
    VALID_HOSTNAMES = {
        'youtube.com',
        'www.youtube.com',
        'm.youtube.com',
    }

    def __init__(self, flatten=True):
        self._flatten = flatten

        self._video_id_dict = {}
        self._video_items = []

        self._playlist_id_dict = {}
        self._playlist_items = []
        self._playlist_ids = []

        self._channel_id_dict = {}
        self._channel_items = []
        self._channel_ids = []

    def add_url(self, url, context):
        parsed_url = urlsplit(url)
        if parsed_url.hostname.lower() not in self.VALID_HOSTNAMES:
            context.log_debug('Unknown hostname "{0}" in url "{1}"'.format(
                parsed_url.hostname, url
            ))
            return

        url_params = dict(parse_qsl(parsed_url.query))
        new_params = {
            new: process(url_params[old]) if process else url_params[old]
            for old, new, process in (
                ('end', 'end', duration_to_seconds),
                ('start', 'start', duration_to_seconds),
                ('t', 'seek', duration_to_seconds),
                ('list', 'playlist_id', False),
                ('v', 'video_id', False),
                ('live', 'live', False),
                ('clip', 'clip', False),
            )
            if old in url_params
        }

        path = parsed_url.path.rstrip('/').lower()
        if path.startswith(('/playlist', '/watch')):
            pass
        elif path.startswith('/channel/'):
            re_match = self.RE_PATH_ID.match(parsed_url.path)
            new_params['channel_id'] = re_match.group('id')
            if ('live' not in new_params
                    and path.endswith(('/live', '/streams'))):
                new_params['live'] = 1
        elif path.startswith(('/clip/', '/embed/', '/live/', '/shorts/')):
            re_match = self.RE_PATH_ID.match(parsed_url.path)
            new_params['video_id'] = re_match.group('id')
        else:
            context.log_debug('Unknown path "{0}" in url "{1}"'.format(
                parsed_url.path, url
            ))
            return

        if 'video_id' in new_params:
            video_id = new_params['video_id']

            video_item = VideoItem(
                '', context.create_uri((PATHS.PLAY,), new_params)
            )
            self._video_id_dict[video_id] = video_item

        elif 'playlist_id' in new_params:
            playlist_id = new_params['playlist_id']

            if self._flatten:
                self._playlist_ids.append(playlist_id)
                return

            playlist_item = DirectoryItem(
                '', context.create_uri(('playlist', playlist_id,), new_params),
            )
            self._playlist_id_dict[playlist_id] = playlist_item

        elif 'channel_id' in new_params:
            channel_id = new_params['channel_id']
            live = new_params.get('live')

            if not live and self._flatten:
                self._channel_ids.append(channel_id)
                return

            channel_item = VideoItem(
                '', context.create_uri((PATHS.PLAY,), new_params)
            ) if live else DirectoryItem(
                '', context.create_uri(('channel', channel_id,), new_params)
            )
            self._channel_id_dict[channel_id] = channel_item

        else:
            context.log_debug('No items found in url "{0}"'.format(url))

    def add_urls(self, urls, context):
        for url in urls:
            self.add_url(url, context)

    def get_items(self, provider, context, skip_title=False):
        result = []

        if self._channel_ids:
            # remove duplicates
            self._channel_ids = list(set(self._channel_ids))

            item_label = context.localize('channels')
            channels_item = DirectoryItem(
                context.get_ui().bold(item_label),
                context.create_uri(
                    ('special', 'description_links',),
                    {
                        'channel_ids': ','.join(self._channel_ids),
                    },
                ),
                image='{media}/playlist.png',
                category_label=item_label,
            )
            result.append(channels_item)

        if self._playlist_ids:
            # remove duplicates
            self._playlist_ids = list(set(self._playlist_ids))

            if context.get_param('uri'):
                playlists_item = UriItem(
                    context.create_uri(
                        (PATHS.PLAY,),
                        {
                            'playlist_ids': ','.join(self._playlist_ids),
                            'play': True,
                            'order': 'default',
                        },
                    ),
                    playable=True,
                )
            else:
                item_label = context.localize('playlists')
                playlists_item = DirectoryItem(
                    context.get_ui().bold(item_label),
                    context.create_uri(
                        ('special', 'description_links',),
                        {
                            'playlist_ids': ','.join(self._playlist_ids),
                        },
                    ),
                    image='{media}/playlist.png',
                    category_label=item_label,
                )
            result.append(playlists_item)

        if self._channel_id_dict:
            result += self.get_channel_items(provider, context, skip_title)

        if self._playlist_id_dict:
            result += self.get_playlist_items(provider, context, skip_title)

        if self._video_id_dict:
            result += self.get_video_items(provider, context, skip_title)

        return result

    def get_video_items(self, provider, context, skip_title=False):
        if self._video_items:
            return self._video_items

        use_play_data = not context.get_param('incognito', False)

        channel_id_dict = {}
        utils.update_video_infos(provider, context, self._video_id_dict,
                                 channel_items_dict=channel_id_dict,
                                 use_play_data=use_play_data)
        utils.update_fanarts(provider, context, channel_id_dict)

        self._video_items = [
            video_item
            for video_item in self._video_id_dict.values()
            if skip_title or video_item.get_title()
        ]
        return self._video_items

    def get_playlist_items(self, provider, context, skip_title=False):
        if self._playlist_items:
            return self._playlist_items

        channel_id_dict = {}
        utils.update_playlist_infos(provider, context,
                                    self._playlist_id_dict,
                                    channel_items_dict=channel_id_dict)
        utils.update_fanarts(provider, context, channel_id_dict)

        self._playlist_items = [
            playlist_item
            for playlist_item in self._playlist_id_dict.values()
            if skip_title or playlist_item.get_title()
        ]
        return self._playlist_items

    def get_channel_items(self, provider, context, skip_title=False):
        if self._channel_items:
            return self._channel_items

        channel_id_dict = {}
        utils.update_fanarts(provider, context, channel_id_dict)

        self._channel_items = [
            channel_item
            for channel_item in self._channel_id_dict.values()
            if skip_title or channel_item.get_title()
        ]
        return self._channel_items
