# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import re
from urllib.parse import parse_qsl, urlparse

from . import utils
from ...kodion.items import DirectoryItem, UriItem, VideoItem


class UrlToItemConverter(object):
    RE_PATH_ID = re.compile(r'/\w+/(?P<id>[^/?#]+)', re.I)
    RE_SEEK_TIME = re.compile(r'\d+')
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

    def add_url(self, url, provider, context):
        parsed_url = urlparse(url)
        if parsed_url.hostname.lower() not in self.VALID_HOSTNAMES:
            context.log_debug('Unknown hostname "{0}" in url "{1}"'.format(
                parsed_url.hostname, url
            ))
            return

        url_params = dict(parse_qsl(parsed_url.query))
        path = parsed_url.path.lower()

        channel_id = live = playlist_id = seek_time = video_id = None
        if path == '/watch':
            video_id = url_params.get('v')
            playlist_id = url_params.get('list')
            seek_time = url_params.get('t')
        elif path == '/playlist':
            playlist_id = url_params.get('list')
        elif path.startswith('/channel/'):
            re_match = self.RE_PATH_ID.match(parsed_url.path)
            channel_id = re_match.group('id')
            if '/live' in path:
                live = 1
        elif path.startswith(('/live/', '/shorts/')):
            re_match = self.RE_PATH_ID.match(parsed_url.path)
            video_id = re_match.group('id')
            seek_time = url_params.get('t')
        else:
            context.log_debug('Unknown path "{0}" in url "{1}"'.format(
                parsed_url.path, url
            ))
            return

        if video_id:
            plugin_params = {
                'video_id': video_id,
            }
            if seek_time:
                seek_time = sum(
                    int(number) * seconds_per_unit
                    for number, seconds_per_unit in zip(
                        reversed(re.findall(self.RE_SEEK_TIME, seek_time)),
                        (1, 60, 3600, 86400)
                    )
                    if number
                )
                plugin_params['seek'] = seek_time
            if playlist_id:
                plugin_params['playlist_id'] = playlist_id
            video_item = VideoItem(
                '', context.create_uri(['play'], plugin_params)
            )
            self._video_id_dict[video_id] = video_item

        elif playlist_id:
            if self._flatten:
                self._playlist_ids.append(playlist_id)
            else:
                playlist_item = DirectoryItem(
                    '', context.create_uri(['playlist', playlist_id])
                )
                playlist_item.set_fanart(provider.get_fanart(context))
                self._playlist_id_dict[playlist_id] = playlist_item

        elif channel_id:
            if self._flatten:
                if live:
                    context.set_param('live', live)
                self._channel_ids.append(channel_id)
            else:
                channel_item = DirectoryItem(
                    '', context.create_uri(['channel', channel_id],
                                           {'live': live} if live else None)
                )
                channel_item.set_fanart(provider.get_fanart(context))
                self._channel_id_dict[channel_id] = channel_item

        else:
            context.log_debug('No items found in url "{0}"'.format(url))

    def add_urls(self, urls, provider, context):
        for url in urls:
            self.add_url(url, provider, context)

    def get_items(self, provider, context, title_required=True):
        result = []

        if self._flatten and self._channel_ids:
            # remove duplicates
            self._channel_ids = list(set(self._channel_ids))

            channels_item = DirectoryItem(
                context.get_ui().bold(context.localize('channels')),
                context.create_uri(['special', 'description_links'], {
                    'channel_ids': ','.join(self._channel_ids),
                }),
                context.create_resource_path('media', 'playlist.png')
            )
            channels_item.set_fanart(provider.get_fanart(context))
            result.append(channels_item)

        if self._flatten and self._playlist_ids:
            # remove duplicates
            self._playlist_ids = list(set(self._playlist_ids))

            playlists_item = UriItem(
                context.create_uri(['play'], {
                    'playlist_ids': ','.join(self._playlist_ids),
                    'play': True,
                }),
                playable=True
            ) if context.get_param('uri') else DirectoryItem(
                context.get_ui().bold(context.localize('playlists')),
                context.create_uri(['special', 'description_links'], {
                    'playlist_ids': ','.join(self._playlist_ids),
                }),
                context.create_resource_path('media', 'playlist.png')
            )
            playlists_item.set_fanart(provider.get_fanart(context))
            result.append(playlists_item)

        if not self._flatten:
            result.extend(self.get_channel_items(provider, context))

        if not self._flatten:
            result.extend(self.get_playlist_items(provider, context))

        # add videos
        result.extend(self.get_video_items(provider, context, title_required))

        return result

    def get_video_items(self, provider, context, title_required=True):
        incognito = context.get_param('incognito', False)
        use_play_data = not incognito

        if not self._video_items:
            channel_id_dict = {}
            utils.update_video_infos(provider, context, self._video_id_dict,
                                     channel_items_dict=channel_id_dict,
                                     use_play_data=use_play_data)
            utils.update_fanarts(provider, context, channel_id_dict)

            self._video_items = [
                video_item
                for video_item in self._video_id_dict.values()
                if not title_required or video_item.get_title()
            ]

        return self._video_items

    def get_playlist_items(self, provider, context):
        if not self._playlist_items:
            channel_id_dict = {}
            utils.update_playlist_infos(provider, context,
                                        self._playlist_id_dict,
                                        channel_items_dict=channel_id_dict)
            utils.update_fanarts(provider, context, channel_id_dict)

            self._playlist_items = [
                playlist_item
                for playlist_item in self._playlist_id_dict.values()
                if playlist_item.get_name()
            ]

        return self._playlist_items

    def get_channel_items(self, provider, context):
        if not self._channel_items:
            channel_id_dict = {}
            utils.update_fanarts(provider, context, channel_id_dict)

            self._channel_items = [
                channel_item
                for channel_item in self._channel_id_dict.values()
                if channel_item.get_name()
            ]

        return self._channel_items
