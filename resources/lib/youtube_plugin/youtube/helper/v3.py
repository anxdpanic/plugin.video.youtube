# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from threading import Thread

from .utils import (
    filter_short_videos,
    get_thumbnail,
    make_comment_item,
    update_channel_infos,
    update_fanarts,
    update_playlist_infos,
    update_video_infos,
)
from ..helper import yt_context_menu
from ...kodion import KodionException
from ...kodion.items import DirectoryItem, NextPageItem, VideoItem


def _process_list_response(provider, context, json_data):
    yt_items = json_data.get('items', [])
    if not yt_items:
        context.log_warning('List of search result is empty')
        return []

    video_id_dict = {}
    channel_id_dict = {}
    playlist_id_dict = {}
    playlist_item_id_dict = {}
    subscription_id_dict = {}

    result = []

    incognito = context.get_param('incognito', False)
    addon_id = context.get_param('addon_id', '')

    settings = context.get_settings()
    thumb_size = settings.use_thumbnail_size()
    use_play_data = not incognito and settings.use_local_history()

    for yt_item in yt_items:
        is_youtube, kind = _parse_kind(yt_item)
        if not is_youtube or not kind:
            context.log_debug('v3 response: Item discarded, is_youtube=False')
            continue

        if kind == 'video':
            video_id = yt_item['id']
            snippet = yt_item['snippet']
            title = snippet.get('title', context.localize('untitled'))
            image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))
            item_params = {'video_id': video_id}
            if incognito:
                item_params['incognito'] = incognito
            if addon_id:
                item_params['addon_id'] = addon_id
            item_uri = context.create_uri(['play'], item_params)
            video_item = VideoItem(title, item_uri, image=image)
            video_item.video_id = video_id
            if incognito:
                video_item.set_play_count(0)
            video_item.set_fanart(provider.get_fanart(context))
            result.append(video_item)
            video_id_dict[video_id] = video_item
        elif kind == 'channel':
            channel_id = yt_item['id']
            snippet = yt_item['snippet']
            title = snippet.get('title', context.localize('untitled'))
            image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))
            item_params = {}
            if incognito:
                item_params['incognito'] = incognito
            if addon_id:
                item_params['addon_id'] = addon_id
            item_uri = context.create_uri(['channel', channel_id], item_params)
            channel_item = DirectoryItem(title, item_uri, image=image)
            channel_item.set_fanart(provider.get_fanart(context))

            # if logged in => provide subscribing to the channel
            if provider.is_logged_in():
                context_menu = []
                yt_context_menu.append_subscribe_to_channel(context_menu, context, channel_id)
                channel_item.set_context_menu(context_menu)
            result.append(channel_item)
            channel_id_dict[channel_id] = channel_item
        elif kind == 'guidecategory':
            guide_id = yt_item['id']
            snippet = yt_item['snippet']
            title = snippet.get('title', context.localize('untitled'))
            item_params = {'guide_id': guide_id}
            if incognito:
                item_params['incognito'] = incognito
            if addon_id:
                item_params['addon_id'] = addon_id
            item_uri = context.create_uri(['special', 'browse_channels'], item_params)
            guide_item = DirectoryItem(title, item_uri)
            guide_item.set_fanart(provider.get_fanart(context))
            result.append(guide_item)
        elif kind == 'subscription':
            snippet = yt_item['snippet']
            title = snippet.get('title', context.localize('untitled'))
            image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))
            channel_id = snippet['resourceId']['channelId']
            item_params = {}
            if incognito:
                item_params['incognito'] = incognito
            if addon_id:
                item_params['addon_id'] = addon_id
            item_uri = context.create_uri(['channel', channel_id], item_params)
            channel_item = DirectoryItem(title, item_uri, image=image)
            channel_item.set_fanart(provider.get_fanart(context))
            channel_item.set_channel_id(channel_id)
            # map channel id with subscription id - we need it for the unsubscription
            subscription_id_dict[channel_id] = yt_item['id']

            result.append(channel_item)
            channel_id_dict[channel_id] = channel_item
        elif kind == 'playlist':
            playlist_id = yt_item['id']
            snippet = yt_item['snippet']
            title = snippet.get('title', context.localize('untitled'))
            image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))

            channel_id = snippet['channelId']

            # if the path directs to a playlist of our own, we correct the channel id to 'mine'
            if context.get_path() == '/channel/mine/playlists/':
                channel_id = 'mine'
            item_params = {}
            if incognito:
                item_params['incognito'] = incognito
            if addon_id:
                item_params['addon_id'] = addon_id
            item_uri = context.create_uri(['channel', channel_id, 'playlist', playlist_id], item_params)
            playlist_item = DirectoryItem(title, item_uri, image=image)
            playlist_item.set_fanart(provider.get_fanart(context))
            result.append(playlist_item)
            playlist_id_dict[playlist_id] = playlist_item
        elif kind == 'playlistitem':
            snippet = yt_item['snippet']
            video_id = snippet['resourceId']['videoId']

            # store the id of the playlistItem - for deleting this item we need this item
            playlist_item_id_dict[video_id] = yt_item['id']

            title = snippet.get('title', context.localize('untitled'))
            image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))
            item_params = {'video_id': video_id}
            if incognito:
                item_params['incognito'] = incognito
            if addon_id:
                item_params['addon_id'] = addon_id
            item_uri = context.create_uri(['play'], item_params)
            video_item = VideoItem(title, item_uri, image=image)
            video_item.video_id = video_id
            if incognito:
                video_item.set_play_count(0)
            video_item.set_fanart(provider.get_fanart(context))
            # Get Track-ID from Playlist
            video_item.set_track_number(snippet['position'] + 1)
            result.append(video_item)
            video_id_dict[video_id] = video_item

        elif kind == 'activity':
            snippet = yt_item['snippet']
            details = yt_item['contentDetails']
            activity_type = snippet['type']

            # recommendations
            if activity_type == 'recommendation':
                video_id = details['recommendation']['resourceId']['videoId']
            elif activity_type == 'upload':
                video_id = details['upload']['videoId']
            else:
                continue

            title = snippet.get('title', context.localize('untitled'))
            image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))
            item_params = {'video_id': video_id}
            if incognito:
                item_params['incognito'] = incognito
            if addon_id:
                item_params['addon_id'] = addon_id
            item_uri = context.create_uri(['play'], item_params)
            video_item = VideoItem(title, item_uri, image=image)
            video_item.video_id = video_id
            if incognito:
                video_item.set_play_count(0)
            video_item.set_fanart(provider.get_fanart(context))
            result.append(video_item)
            video_id_dict[video_id] = video_item

        elif kind == 'commentthread':
            thread_snippet = yt_item['snippet']
            total_replies = thread_snippet['totalReplyCount']
            snippet = thread_snippet['topLevelComment']['snippet']
            item_params = {'parent_id': yt_item['id']}
            if total_replies:
                item_uri = context.create_uri(['special', 'child_comments'], item_params)
            else:
                item_uri = ''
            result.append(make_comment_item(context, snippet, item_uri, total_replies))

        elif kind == 'comment':
            result.append(make_comment_item(context, yt_item['snippet'], uri=''))

        elif kind == 'searchresult':
            _, kind = _parse_kind(yt_item.get('id', {}))

            # video
            if kind == 'video':
                video_id = yt_item['id']['videoId']
                snippet = yt_item.get('snippet', {})
                title = snippet.get('title', context.localize('untitled'))
                image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))
                item_params = {'video_id': video_id}
                if incognito:
                    item_params['incognito'] = incognito
                if addon_id:
                    item_params['addon_id'] = addon_id
                item_uri = context.create_uri(['play'], item_params)
                video_item = VideoItem(title, item_uri, image=image)
                video_item.video_id = video_id
                if incognito:
                    video_item.set_play_count(0)
                video_item.set_fanart(provider.get_fanart(context))
                result.append(video_item)
                video_id_dict[video_id] = video_item
            # playlist
            elif kind == 'playlist':
                playlist_id = yt_item['id']['playlistId']
                snippet = yt_item['snippet']
                title = snippet.get('title', context.localize('untitled'))
                image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))

                channel_id = snippet['channelId']
                # if the path directs to a playlist of our own, we correct the channel id to 'mine'
                if context.get_path() == '/channel/mine/playlists/':
                    channel_id = 'mine'
                # channel_name = snippet.get('channelTitle', '')
                item_params = {}
                if incognito:
                    item_params['incognito'] = incognito
                if addon_id:
                    item_params['addon_id'] = addon_id
                item_uri = context.create_uri(['channel', channel_id, 'playlist', playlist_id], item_params)
                playlist_item = DirectoryItem(title, item_uri, image=image)
                playlist_item.set_fanart(provider.get_fanart(context))
                result.append(playlist_item)
                playlist_id_dict[playlist_id] = playlist_item
            elif kind == 'channel':
                channel_id = yt_item['id']['channelId']
                snippet = yt_item['snippet']
                title = snippet.get('title', context.localize('untitled'))
                image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))
                item_params = {}
                if incognito:
                    item_params['incognito'] = incognito
                if addon_id:
                    item_params['addon_id'] = addon_id
                item_uri = context.create_uri(['channel', channel_id], item_params)
                channel_item = DirectoryItem(title, item_uri, image=image)
                channel_item.set_fanart(provider.get_fanart(context))
                result.append(channel_item)
                channel_id_dict[channel_id] = channel_item
            else:
                raise KodionException("Unknown kind '%s'" % kind)
        else:
            raise KodionException("Unknown kind '%s'" % kind)

    # this will also update the channel_id_dict with the correct channel_id
    # for each video.
    channel_items_dict = {}

    running = 0
    resource_manager = provider.get_resource_manager(context)
    resources = [
        {
            'fetcher': resource_manager.get_videos,
            'args': (video_id_dict.keys(), ),
            'kwargs': {'live_details': True, 'suppress_errors': True},
            'thread': None,
            'updater': update_video_infos,
            'upd_args': (provider, context, video_id_dict, playlist_item_id_dict, channel_items_dict),
            'upd_kwargs': {'data': None, 'live_details': True, 'use_play_data': use_play_data},
            'complete': False,
            'defer': False,
        },
        {
            'fetcher': resource_manager.get_playlists,
            'args': (playlist_id_dict.keys(), ),
            'kwargs': {},
            'thread': None,
            'updater': update_playlist_infos,
            'upd_args': (provider, context, playlist_id_dict, channel_items_dict),
            'upd_kwargs': {'data': None},
            'complete': False,
            'defer': False,
        },
        {
            'fetcher': resource_manager.get_channels,
            'args': (channel_id_dict.keys(), ),
            'kwargs': {},
            'thread': None,
            'updater': update_channel_infos,
            'upd_args': (provider, context, channel_id_dict, subscription_id_dict, channel_items_dict),
            'upd_kwargs': {'data': None},
            'complete': False,
            'defer': False,
        },
        {
            'fetcher': resource_manager.get_fanarts,
            'args': (channel_items_dict.keys(), ),
            'kwargs': {},
            'thread': None,
            'updater': update_fanarts,
            'upd_args': (provider, context, channel_items_dict),
            'upd_kwargs': {'data': None},
            'complete': False,
            'defer': True,
        },
    ]

    def _fetch(resource):
        data = resource['fetcher'](
            *resource['args'], **resource['kwargs']
        )
        if not data:
            return
        resource['upd_kwargs']['data'] = data
        resource['updater'](*resource['upd_args'], **resource['upd_kwargs'])

    for resource in resources:
        if resource['defer']:
            running += 1
            continue

        if not resource['args'][0]:
            resource['complete'] = True
            continue

        running += 1
        # _fetch(resource)
        thread = Thread(target=_fetch, args=(resource, ))
        thread.daemon = True
        thread.start()
        resource['thread'] = thread

    while running > 0:
        for resource in resources:
            if resource['complete']:
                continue

            thread = resource['thread']
            if thread:
                thread.join(30)
                if not thread.is_alive():
                    resource['thread'] = None
                    resource['complete'] = True
                    running -= 1
            elif resource['defer']:
                resource['defer'] = False
                # _fetch(resource)
                thread = Thread(target=_fetch, args=(resource, ))
                thread.daemon = True
                thread.start()
                resource['thread'] = thread
            else:
                running -= 1
                resource['complete'] = True

    return result


def response_to_items(provider, context, json_data, sort=None, reverse=False, process_next_page=True):
    is_youtube, kind = _parse_kind(json_data)
    if not is_youtube:
        context.log_debug('v3 response: Response discarded, is_youtube=False')
        return []

    if kind in ['searchlistresponse', 'playlistitemlistresponse', 'playlistlistresponse',
                'subscriptionlistresponse', 'guidecategorylistresponse', 'channellistresponse',
                'videolistresponse', 'activitylistresponse', 'commentthreadlistresponse',
                'commentlistresponse']:
        result = _process_list_response(provider, context, json_data)
    else:
        raise KodionException("Unknown kind '%s'" % kind)

    if sort is not None:
        result.sort(key=sort, reverse=reverse)

    if context.get_settings().hide_short_videos():
        result = filter_short_videos(result)

    # no processing of next page item
    if not process_next_page:
        return result

    # next page
    """
    This will try to prevent the issue 7163 (https://code.google.com/p/gdata-issues/issues/detail?id=7163).
    Somehow the APIv3 is missing the token for the next page. We implemented our own calculation for the token
    into the YouTube client...this should work for up to ~2000 entries.
    """
    yt_total_results = int(json_data.get('pageInfo', {}).get('totalResults', 0))
    yt_results_per_page = int(json_data.get('pageInfo', {}).get('resultsPerPage', 0))
    page = int(context.get_param('page', 1))
    yt_next_page_token = json_data.get('nextPageToken', '')
    if yt_next_page_token or (page * yt_results_per_page < yt_total_results):
        if not yt_next_page_token:
            client = provider.get_client(context)
            yt_next_page_token = client.calculate_next_page_token(page + 1, yt_results_per_page)

        new_params = {}
        new_params.update(context.get_params())
        new_params['page_token'] = yt_next_page_token

        new_context = context.clone(new_params=new_params)

        current_page = new_context.get_param('page', 1)
        next_page_item = NextPageItem(new_context, current_page, fanart=provider.get_fanart(new_context))
        result.append(next_page_item)

    return result


def _parse_kind(item):
    parts = item.get('kind', '').split('#')
    is_youtube = parts[0] == 'youtube'
    kind = parts[1 if len(parts) > 1 else 0].lower()
    return is_youtube, kind
