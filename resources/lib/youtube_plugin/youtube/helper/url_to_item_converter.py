# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from re import (
    IGNORECASE,
    compile as re_compile,
)

from . import utils
from ...kodion import logging
from ...kodion.compatibility import parse_qsl, urlsplit
from ...kodion.constants import PATHS
from ...kodion.items import DirectoryItem, UriItem, VideoItem
from ...kodion.utils.convert_format import duration_to_seconds


class UrlToItemConverter(object):
    log = logging.getLogger(__name__)

    RE_PATH_ID = re_compile(r'/[^/]*?[/@](?P<id>[^/?#]+)', IGNORECASE)
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
        self._channel_items_dict = {}

        self._new_params = None

    def add_url(self, url):
        parsed_url = urlsplit(url)
        if (not parsed_url.hostname
                or parsed_url.hostname.lower() not in self.VALID_HOSTNAMES):
            self.log.debug('Unknown hostname "{hostname}" in url "{url}"',
                           hostname=parsed_url.hostname,
                           url=url)
            return False

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
                ('video_ids', 'video_ids', False),
            )
            if old in url_params
        }

        path = parsed_url.path.rstrip('/').lower()
        if path.startswith(('/playlist', '/watch')):
            pass
        elif path.startswith(('/c/', '/channel/', '/u/', '/user/', '/@')):
            re_match = self.RE_PATH_ID.match(parsed_url.path)
            new_params['channel_id'] = re_match.group('id')
            if ('live' not in new_params
                    and path.endswith(('/live', '/streams'))):
                new_params['live'] = 1
        elif path.startswith(('/clip/', '/embed/', '/live/', '/shorts/')):
            re_match = self.RE_PATH_ID.match(parsed_url.path)
            new_params['video_id'] = re_match.group('id')
        else:
            self.log.debug('Unknown path "{path}" in url "{url}"',
                           path=parsed_url.path,
                           url=url)
            self._new_params = None
            return False
        self._new_params = new_params
        return True

    def create_item(self, context, as_uri=False):
        new_params = self._new_params
        item = None

        if 'video_ids' in new_params:
            item_uri = context.create_uri(PATHS.PLAY, new_params)
            if as_uri:
                return item_uri

            for video_id in new_params['video_ids'].split(','):
                item = VideoItem(
                    name='',
                    uri=context.create_uri(
                        PATHS.PLAY,
                        dict(new_params, video_id=video_id),
                    ),
                    video_id=video_id,
                )
                items = self._video_id_dict.setdefault(video_id, [])
                items.append(item)

        elif 'video_id' in new_params:
            item_uri = context.create_uri(PATHS.PLAY, new_params)
            if as_uri:
                return item_uri

            video_id = new_params['video_id']

            item = VideoItem(
                name='',
                uri=item_uri,
                video_id=video_id,
            )
            items = self._video_id_dict.setdefault(video_id, [])
            items.append(item)

        if 'playlist_id' in new_params:
            playlist_id = new_params['playlist_id']

            item_uri = context.create_uri(('playlist', playlist_id), new_params)
            if as_uri:
                return item_uri

            if self._flatten:
                self._playlist_ids.append(playlist_id)
                return playlist_id

            item = DirectoryItem(
                name='',
                uri=item_uri,
                playlist_id=playlist_id,
            )
            items = self._playlist_id_dict.setdefault(playlist_id, [])
            items.append(item)

        if 'channel_id' in new_params:
            channel_id = new_params['channel_id']
            live = new_params.get('live')

            item_uri = context.create_uri(
                PATHS.PLAY if live else ('channel', channel_id),
                new_params
            )
            if as_uri:
                return item_uri

            if not live and self._flatten:
                self._channel_ids.append(channel_id)
                return channel_id

            item = VideoItem(
                name='',
                uri=item_uri,
                channel_id=channel_id,
            ) if live else DirectoryItem(
                name='',
                uri=item_uri,
                channel_id=channel_id,
            )
            items = self._channel_id_dict.setdefault(channel_id, [])
            items.append(item)

        return item

    def process_url(self, url, context, as_uri=False):
        if not self.add_url(url):
            return False
        item = self.create_item(context, as_uri=as_uri)
        if not item:
            self.log.debug('No items found in url "%s"', url)
        return item

    def process_urls(self, urls, context):
        for url in urls:
            self.process_url(url, context)

    def get_items(self, provider, context, skip_title=False):
        result = []
        query = context.get_param('q')

        if self._channel_ids:
            item_label = context.localize('channels')
            channels_item = DirectoryItem(
                context.get_ui().bold(item_label),
                context.create_uri(
                    (PATHS.SEARCH, 'links',),
                    {
                        'channel_ids': ','.join(self._channel_ids),
                        'q': query,
                    },
                ) if query else context.create_uri(
                    (PATHS.DESCRIPTION_LINKS,),
                    {
                        'channel_ids': ','.join(self._channel_ids),
                    },
                ),
                image='{media}/channels.png',
                category_label=item_label,
            )
            result.append(channels_item)

        if self._playlist_ids:
            if context.get_param('uri'):
                playlists_item = UriItem(
                    context.create_uri(
                        (PATHS.PLAY,),
                        {
                            'playlist_ids': ','.join(self._playlist_ids),
                            'order': 'normal',
                        },
                    ),
                    playable=True,
                )
            else:
                item_label = context.localize('playlists')
                playlists_item = DirectoryItem(
                    context.get_ui().bold(item_label),
                    context.create_uri(
                        (PATHS.SEARCH, 'links',),
                        {
                            'playlist_ids': ','.join(self._playlist_ids),
                            'q': query,
                        },
                    ) if query else context.create_uri(
                        (PATHS.DESCRIPTION_LINKS,),
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

        utils.update_video_items(
            provider,
            context,
            self._video_id_dict,
            channel_items_dict=self._channel_items_dict,
        )
        utils.update_channel_info(provider, context, self._channel_items_dict)

        self._video_items = [
            video_item
            for video_items in self._video_id_dict.values()
            for video_item in video_items
            if skip_title or video_item.get_name()
        ]
        return self._video_items

    def get_playlist_items(self, provider, context, skip_title=False):
        if self._playlist_items:
            return self._playlist_items

        utils.update_playlist_items(
            provider,
            context,
            self._playlist_id_dict,
            channel_items_dict=self._channel_items_dict,
        )
        utils.update_channel_info(provider, context, self._channel_items_dict)

        self._playlist_items = [
            playlist_item
            for playlist_items in self._playlist_id_dict.values()
            for playlist_item in playlist_items
            if skip_title or playlist_item.get_name()
        ]
        return self._playlist_items

    def get_channel_items(self, provider, context, skip_title=False):
        if self._channel_items:
            return self._channel_items

        utils.update_channel_items(
            provider,
            context,
            self._channel_id_dict,
            channel_items_dict=self._channel_items_dict,
        )
        utils.update_channel_info(provider, context, self._channel_items_dict)

        self._channel_items = [
            channel_item
            for channel_items in self._channel_id_dict.values()
            for channel_item in channel_items
            if skip_title or channel_item.get_name()
        ]
        return self._channel_items
