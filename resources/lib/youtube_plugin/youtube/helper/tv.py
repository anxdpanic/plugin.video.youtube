# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..helper import utils
from ...kodion.items import DirectoryItem, NextPageItem, VideoItem


def my_subscriptions_to_items(provider, context, json_data, do_filter=False):
    result = []
    video_id_dict = {}

    filter_list = []
    black_list = False
    if do_filter:
        black_list = context.get_settings().get_bool('youtube.filter.my_subscriptions_filtered.blacklist', False)
        filter_list = context.get_settings().get_string('youtube.filter.my_subscriptions_filtered.list', '')
        filter_list = filter_list.replace(', ', ',')
        filter_list = filter_list.split(',')
        filter_list = [x.lower() for x in filter_list]

    item_params = {'video_id': None}
    incognito = context.get_param('incognito', False)
    if incognito:
        item_params['incognito'] = incognito

    items = json_data.get('items', [])
    for item in items:
        channel = item['channel'].lower()
        channel = channel.replace(',', '')
        if (not do_filter
                or (black_list and channel not in filter_list)
                or (not black_list and channel in filter_list)):
            video_id = item['id']
            item_params['video_id'] = video_id
            item_uri = context.create_uri(('play',), item_params)
            video_item = VideoItem(item['title'], uri=item_uri)
            if incognito:
                video_item.set_play_count(0)
            result.append(video_item)

            video_id_dict[video_id] = video_item

    use_play_data = not incognito and context.get_settings().use_local_history()

    channel_item_dict = {}
    utils.update_video_infos(provider,
                             context,
                             video_id_dict,
                             channel_items_dict=channel_item_dict,
                             use_play_data=use_play_data)
    utils.update_fanarts(provider, context, channel_item_dict)

    if context.get_settings().hide_short_videos():
        result = utils.filter_short_videos(result)

    # next page
    next_page_token = json_data.get('next_page_token', '')
    if next_page_token or json_data.get('continue', False):
        new_params = dict(context.get_params(),
                          next_page_token=next_page_token,
                          offset=int(json_data.get('offset', 0)))
        new_context = context.clone(new_params=new_params)
        current_page = new_context.get_param('page', 1)
        next_page_item = NextPageItem(new_context, current_page)
        result.append(next_page_item)

    return result


def tv_videos_to_items(provider, context, json_data):
    result = []
    video_id_dict = {}

    item_params = {'video_id': None}
    incognito = context.get_param('incognito', False)
    if incognito:
        item_params['incognito'] = incognito

    items = json_data.get('items', [])
    for item in items:
        video_id = item['id']
        item_params['video_id'] = video_id
        item_uri = context.create_uri(('play',), item_params)
        video_item = VideoItem(item['title'], uri=item_uri)
        if incognito:
            video_item.set_play_count(0)

        result.append(video_item)

        video_id_dict[video_id] = video_item

    use_play_data = not incognito and context.get_settings().use_local_history()

    channel_item_dict = {}
    utils.update_video_infos(provider,
                             context,
                             video_id_dict,
                             channel_items_dict=channel_item_dict,
                             use_play_data=use_play_data)
    utils.update_fanarts(provider, context, channel_item_dict)

    if context.get_settings().hide_short_videos():
        result = utils.filter_short_videos(result)

    # next page
    next_page_token = json_data.get('next_page_token', '')
    if next_page_token or json_data.get('continue', False):
        new_params = dict(context.get_params(),
                          next_page_token=next_page_token,
                          offset=int(json_data.get('offset', 0)))
        new_context = context.clone(new_params=new_params)
        current_page = new_context.get_param('page', 1)
        next_page_item = NextPageItem(new_context, current_page)
        result.append(next_page_item)

    return result


def saved_playlists_to_items(provider, context, json_data):
    result = []
    playlist_id_dict = {}

    thumb_size = context.get_settings().use_thumbnail_size()
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
    next_page_token = json_data.get('next_page_token', '')
    if next_page_token or json_data.get('continue', False):
        new_params = dict(context.get_params(),
                          next_page_token=next_page_token,
                          offset=int(json_data.get('offset', 0)))
        new_context = context.clone(new_params=new_params)
        current_page = new_context.get_param('page', 1)
        next_page_item = NextPageItem(new_context, current_page)
        result.append(next_page_item)

    return result
