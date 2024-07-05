# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..helper import utils
from ...kodion.constants import PATHS
from ...kodion.items import DirectoryItem, NextPageItem, VideoItem


def tv_videos_to_items(provider, context, json_data):
    incognito = context.get_param('incognito')
    settings = context.get_settings()
    use_play_data = not incognito and settings.use_local_history()
    item_filter = settings.item_filter()

    item_params = {
        'video_id': None,
    }
    if incognito:
        item_params['incognito'] = True
    video_id_dict = {}
    channel_item_dict = {}
    for item in json_data.get('items', []):
        video_id = item['id']
        item_params['video_id'] = video_id
        video_item = VideoItem(
            item['title'], context.create_uri((PATHS.PLAY,), item_params)
        )
        if incognito:
            video_item.set_play_count(0)
        video_id_dict[video_id] = video_item

    utils.update_video_infos(provider,
                             context,
                             video_id_dict,
                             channel_items_dict=channel_item_dict,
                             use_play_data=use_play_data,
                             item_filter=item_filter)
    utils.update_fanarts(provider, context, channel_item_dict)

    if item_filter:
        result = utils.filter_videos(video_id_dict.values(), **item_filter)
    else:
        result = list(video_id_dict.values())

    # next page
    next_page_token = json_data.get('next_page_token')
    if next_page_token or json_data.get('continue'):
        params = context.get_params()
        new_params = dict(params,
                          next_page_token=next_page_token,
                          offset=json_data.get('offset', 0),
                          page=params.get('page', 1) + 1)
        next_page_item = NextPageItem(context, new_params)
        result.append(next_page_item)

    return result


def saved_playlists_to_items(provider, context, json_data):
    result = []
    playlist_id_dict = {}

    thumb_size = context.get_settings().get_thumbnail_size()
    incognito = context.get_param('incognito', False)
    item_params = {}
    if incognito:
        item_params['incognito'] = incognito

    items = json_data.get('items', [])
    for item in items:
        title = item['title']
        channel_id = item['channel_id']
        playlist_id = item['id']
        image = utils.get_thumbnail(thumb_size, item.get('thumbnails', {}))

        if channel_id:
            item_uri = context.create_uri(
                ('channel', channel_id, 'playlist', playlist_id,),
                item_params,
            )
        else:
            item_uri = context.create_uri(
                ('playlist', playlist_id),
                item_params,
            )

        playlist_item = DirectoryItem(title, item_uri, image=image)
        result.append(playlist_item)
        playlist_id_dict[playlist_id] = playlist_item

    channel_items_dict = {}
    utils.update_playlist_infos(provider,
                                context,
                                playlist_id_dict,
                                channel_items_dict)
    utils.update_fanarts(provider, context, channel_items_dict)

    # next page
    next_page_token = json_data.get('next_page_token')
    if next_page_token or json_data.get('continue'):
        params = context.get_params()
        new_params = dict(params,
                          next_page_token=next_page_token,
                          offset=json_data.get('offset', 0),
                          page=params.get('page', 1) + 1)
        next_page_item = NextPageItem(context, new_params)
        result.append(next_page_item)

    return result
