# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from six.moves import urllib

import re
from ...kodion.items import VideoItem, DirectoryItem
from . import utils


class UrlToItemConverter(object):
    RE_CHANNEL_ID = re.compile(r'^/channel/(?P<channel_id>.+)$')

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
        url_components = urllib.parse.urlparse(url)
        if url_components.hostname.lower() == 'youtube.com' or url_components.hostname.lower() == 'www.youtube.com':
            params = dict(urllib.parse.parse_qsl(url_components.query))
            if url_components.path.lower() == '/watch':
                video_id = params.get('v', '')
                if video_id:
                    plugin_uri = context.create_uri(['play'], {'video_id': video_id})
                    video_item = VideoItem('', plugin_uri)
                    self._video_id_dict[video_id] = video_item

                playlist_id = params.get('list', '')
                if playlist_id:
                    if self._flatten:
                        self._playlist_ids.append(playlist_id)
                    else:
                        playlist_item = DirectoryItem('', context.create_uri(['playlist', playlist_id]))
                        playlist_item.set_fanart(provider.get_fanart(context))
                        self._playlist_id_dict[playlist_id] = playlist_item
            elif url_components.path.lower() == '/playlist':
                playlist_id = params.get('list', '')
                if playlist_id:
                    if self._flatten:
                        self._playlist_ids.append(playlist_id)
                    else:
                        playlist_item = DirectoryItem('', context.create_uri(['playlist', playlist_id]))
                        playlist_item.set_fanart(provider.get_fanart(context))
                        self._playlist_id_dict[playlist_id] = playlist_item
            elif self.RE_CHANNEL_ID.match(url_components.path):
                re_match = self.RE_CHANNEL_ID.match(url_components.path)
                channel_id = re_match.group('channel_id')
                if self._flatten:
                    self._channel_ids.append(channel_id)
                else:
                    channel_item = DirectoryItem('', context.create_uri(['channel', channel_id]))
                    channel_item.set_fanart(provider.get_fanart(context))
                    self._channel_id_dict[channel_id] = channel_item
            else:
                context.log_debug('Unknown path "%s"' % url_components.path)

    def add_urls(self, urls, provider, context):
        for url in urls:
            self.add_url(url, provider, context)

    def get_items(self, provider, context):
        result = []

        if self._flatten and len(self._channel_ids) > 0:
            # remove duplicates
            self._channel_ids = list(set(self._channel_ids))

            channels_item = DirectoryItem(context.get_ui().bold(context.localize(provider.LOCAL_MAP['youtube.channels'])),
                                          context.create_uri(['special', 'description_links'],
                                                             {'channel_ids': ','.join(self._channel_ids)}),
                                          context.create_resource_path('media', 'playlist.png'))
            channels_item.set_fanart(provider.get_fanart(context))
            result.append(channels_item)

        if self._flatten and len(self._playlist_ids) > 0:
            # remove duplicates
            self._playlist_ids = list(set(self._playlist_ids))

            playlists_item = DirectoryItem(context.get_ui().bold(context.localize(provider.LOCAL_MAP['youtube.playlists'])),
                                           context.create_uri(['special', 'description_links'],
                                                              {'playlist_ids': ','.join(self._playlist_ids)}),
                                           context.create_resource_path('media', 'playlist.png'))
            playlists_item.set_fanart(provider.get_fanart(context))
            result.append(playlists_item)

        if not self._flatten:
            result.extend(self.get_channel_items(provider, context))

        if not self._flatten:
            result.extend(self.get_playlist_items(provider, context))

        # add videos
        result.extend(self.get_video_items(provider, context))

        return result

    def get_video_items(self, provider, context):
        incognito = str(context.get_param('incognito', False)).lower() == 'true'
        use_play_data = not incognito

        if len(self._video_items) == 0:
            channel_id_dict = {}
            utils.update_video_infos(provider, context, self._video_id_dict, None, channel_id_dict, use_play_data=use_play_data)
            utils.update_fanarts(provider, context, channel_id_dict)

            for key in self._video_id_dict:
                video_item = self._video_id_dict[key]
                if video_item.get_title():
                    self._video_items.append(video_item)

        return self._video_items

    def get_playlist_items(self, provider, context):
        if len(self._playlist_items) == 0:
            channel_id_dict = {}
            utils.update_playlist_infos(provider, context, self._playlist_id_dict, channel_id_dict)
            utils.update_fanarts(provider, context, channel_id_dict)

            for key in self._playlist_id_dict:
                playlist_item = self._playlist_id_dict[key]
                if playlist_item.get_name():
                    self._playlist_items.append(playlist_item)

        return self._playlist_items

    def get_channel_items(self, provider, context):
        if len(self._channel_items) == 0:
            channel_id_dict = {}
            utils.update_fanarts(provider, context, channel_id_dict)

            for key in self._channel_id_dict:
                channel_item = self._channel_id_dict[key]
                if channel_item.get_name():
                    self._channel_items.append(channel_item)

        return self._channel_items
