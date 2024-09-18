# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import threading

from .utils import (
    THUMB_TYPES,
    filter_videos,
    get_thumbnail,
    make_comment_item,
    update_channel_infos,
    update_fanarts,
    update_playlist_infos,
    update_video_infos,
)
from ...kodion import KodionException
from ...kodion.constants import PATHS
from ...kodion.items import CommandItem, DirectoryItem, NextPageItem, VideoItem


def _process_list_response(provider, context, json_data, item_filter):
    yt_items = json_data.get('items', [])
    if not yt_items:
        context.log_warning('v3 response: Items list is empty')
        return [
            CommandItem(
                context.localize('page.back'),
                'Action(ParentDir)',
                context,
                image='DefaultFolderBack.png',
                plot=context.localize('page.empty'),
            )
        ]

    video_id_dict = {}
    channel_id_dict = {}
    playlist_id_dict = {}
    playlist_item_id_dict = {}
    subscription_id_dict = {}

    result = []

    new_params = {}
    params = context.get_params()
    incognito = params.get('incognito', False)
    if incognito:
        new_params['incognito'] = incognito
    addon_id = params.get('addon_id', '')
    if addon_id:
        new_params['addon_id'] = addon_id

    settings = context.get_settings()
    use_play_data = not incognito and settings.use_local_history()

    thumb_size = settings.get_thumbnail_size()
    fanart_type = params.get('fanart_type')
    if fanart_type is None:
        fanart_type = settings.fanart_selection()
    if fanart_type == settings.FANART_THUMBNAIL:
        fanart_type = settings.get_thumbnail_size(settings.THUMB_SIZE_BEST)
    else:
        fanart_type = False

    for yt_item in yt_items:
        kind, is_youtube, is_plugin, kind_type = _parse_kind(yt_item)
        if not (is_youtube or is_plugin) or not kind_type:
            context.log_debug('v3 item discarded: |%s|' % kind)
            continue

        item_params = yt_item.get('_params', {})
        item_params.update(new_params)

        if is_youtube:
            item_id = yt_item.get('id')
            snippet = yt_item.get('snippet', {})
            title = snippet.get('title', context.localize('untitled'))

            thumbnails = snippet.get('thumbnails')
            if not thumbnails and yt_item.get('_partial'):
                thumbnails = {
                    thumb_type: {
                        'url': thumb['url'].format(item_id, ''),
                        'size': thumb['size'],
                        'ratio': thumb['ratio'],
                    }
                    for thumb_type, thumb in THUMB_TYPES.items()
                }
            image = get_thumbnail(thumb_size, thumbnails)
            if fanart_type:
                fanart = get_thumbnail(fanart_type, thumbnails)
            else:
                fanart = None

        if kind_type == 'searchresult':
            kind, _, _, kind_type = _parse_kind(item_id)
            if kind_type == 'video' and 'videoId' in item_id:
                item_id = item_id['videoId']
            elif kind_type == 'playlist' and 'playlistId' in item_id:
                item_id = item_id['playlistId']
            elif kind_type == 'channel' and 'channelId' in item_id:
                item_id = item_id['channelId']
            else:
                item_id = None
            if not item_id:
                context.log_debug('v3 searchResult discarded: |%s|' % kind)
                continue

        if kind_type == 'video':
            item_params['video_id'] = item_id
            item_uri = context.create_uri(
                (PATHS.PLAY,),
                item_params,
            )
            item = VideoItem(title, item_uri, image=image, fanart=fanart)
            video_id_dict[item_id] = item

        elif kind_type == 'channel':
            item_uri = context.create_uri(
                ('channel', item_id),
                item_params,
            )
            item = DirectoryItem(title,
                                 item_uri,
                                 image=image,
                                 fanart=fanart,
                                 channel_id=item_id)
            channel_id_dict[item_id] = item

        elif kind_type == 'guidecategory':
            item_params['guide_id'] = item_id
            item_uri = context.create_uri(
                ('special', 'browse_channels'),
                item_params,
            )
            item = DirectoryItem(title, item_uri)

        elif kind_type == 'subscription':
            subscription_id = item_id
            item_id = snippet['resourceId']['channelId']
            # map channel id with subscription id - needed to unsubscribe
            subscription_id_dict[item_id] = subscription_id

            item_uri = context.create_uri(
                ('channel', item_id),
                item_params
            )
            item = DirectoryItem(title,
                                 item_uri,
                                 image=image,
                                 fanart=fanart,
                                 channel_id=item_id,
                                 subscription_id=subscription_id)
            channel_id_dict[item_id] = item

        elif kind_type == 'playlist':
            # set channel id to 'mine' if the path is for a playlist of our own
            channel_id = snippet.get('channelId')
            if context.get_path().startswith(PATHS.MY_PLAYLISTS):
                uri_channel_id = 'mine'
            else:
                uri_channel_id = channel_id
            if uri_channel_id:
                item_uri = context.create_uri(
                    ('channel', uri_channel_id, 'playlist', item_id),
                    item_params,
                )
            else:
                item_uri = context.create_uri(
                    ('playlist', item_id),
                    item_params,
                )
            item = DirectoryItem(title,
                                 item_uri,
                                 image=image,
                                 fanart=fanart,
                                 channel_id=channel_id,
                                 playlist_id=item_id)
            playlist_id_dict[item_id] = item

        elif kind_type == 'playlistitem':
            playlistitem_id = item_id
            item_id = snippet['resourceId']['videoId']
            # store the id of the playlistItem - needed for deleting item
            playlist_item_id_dict[item_id] = playlistitem_id

            item_params['video_id'] = item_id
            item_uri = context.create_uri(
                (PATHS.PLAY,),
                item_params,
            )
            item = VideoItem(title, item_uri, image=image, fanart=fanart)
            video_id_dict[item_id] = item

        elif kind_type == 'activity':
            details = yt_item['contentDetails']
            activity_type = snippet['type']
            if activity_type == 'recommendation':
                item_id = details['recommendation']['resourceId']['videoId']
            elif activity_type == 'upload':
                item_id = details['upload']['videoId']
            else:
                continue

            item_params['video_id'] = item_id
            item_uri = context.create_uri(
                (PATHS.PLAY,),
                item_params,
            )
            item = VideoItem(title, item_uri, image=image, fanart=fanart)
            video_id_dict[item_id] = item

        elif kind_type == 'commentthread':
            total_replies = snippet['totalReplyCount']
            snippet = snippet['topLevelComment']['snippet']
            if total_replies:
                item_uri = context.create_uri(
                    ('special', 'child_comments'),
                    {'parent_id': item_id}
                )
            else:
                item_uri = ''
            item = make_comment_item(context, snippet, item_uri, total_replies)

        elif kind_type == 'comment':
            item = make_comment_item(context, snippet, uri='')

        elif kind_type == 'pluginitem':
            item = DirectoryItem(**item_params)

        elif kind_type == 'commanditem':
            item = CommandItem(context=context, **item_params)

        else:
            item = None
            raise KodionException('Unknown kind: %s' % kind)

        if not item:
            continue

        if '_context_menu' in yt_item:
            item.add_context_menu(**yt_item['_context_menu'])

        if isinstance(item, VideoItem):
            item.video_id = item_id
            if incognito:
                item.set_play_count(0)
            # Set track number from playlist, or set to current list length to
            # match "Default" (unsorted) sort order
            position = snippet.get('position') or len(result)
            item.set_track_number(position + 1)

        if '_callback' in yt_item:
            yt_item['_callback'](item)

        result.append(item)

    # this will also update the channel_id_dict with the correct channel_id
    # for each video.
    channel_items_dict = {}

    resource_manager = provider.get_resource_manager(context)
    resources = {
        1: {
            'fetcher': resource_manager.get_videos,
            'args': (video_id_dict,),
            'kwargs': {
                'live_details': True,
                'suppress_errors': True,
                'defer_cache': True,
            },
            'thread': None,
            'updater': update_video_infos,
            'upd_args': (
                provider,
                context,
                video_id_dict,
                playlist_item_id_dict,
                channel_items_dict,
            ),
            'upd_kwargs': {
                'data': None,
                'live_details': True,
                'use_play_data': use_play_data,
                'item_filter': item_filter,
            },
            'complete': False,
            'defer': False,
        },
        2: {
            'fetcher': resource_manager.get_playlists,
            'args': (playlist_id_dict,),
            'kwargs': {'defer_cache': True},
            'thread': None,
            'updater': update_playlist_infos,
            'upd_args': (
                provider,
                context,
                playlist_id_dict,
                channel_items_dict,
            ),
            'upd_kwargs': {'data': None},
            'complete': False,
            'defer': False,
        },
        3: {
            'fetcher': resource_manager.get_channels,
            'args': (channel_id_dict,),
            'kwargs': {'defer_cache': True},
            'thread': None,
            'updater': update_channel_infos,
            'upd_args': (
                provider,
                context,
                channel_id_dict,
                subscription_id_dict,
                channel_items_dict,
            ),
            'upd_kwargs': {'data': None},
            'complete': False,
            'defer': False,
        },
        4: {
            'fetcher': resource_manager.get_fanarts,
            'args': (channel_items_dict,),
            'kwargs': {
                'force': bool(channel_id_dict or playlist_id_dict),
                'defer_cache': True,
            },
            'thread': None,
            'updater': update_fanarts,
            'upd_args': (
                provider,
                context,
                channel_items_dict,
            ),
            'upd_kwargs': {'data': None},
            'complete': False,
            'defer': True,
        },
        5: {
            'fetcher': resource_manager.cache_data,
            'args': (),
            'kwargs': {},
            'thread': None,
            'updater': None,
            'upd_args': (),
            'upd_kwargs': {},
            'complete': False,
            'defer': 4,
        },
    }

    def _fetch(resource):
        data = resource['fetcher'](
            *resource['args'], **resource['kwargs']
        )
        if data and resource['updater']:
            resource['upd_kwargs']['data'] = data
            resource['updater'](*resource['upd_args'], **resource['upd_kwargs'])
        resource['complete'] = True
        threads['current'].discard(resource['thread'])
        threads['loop'].set()

    threads = {
        'current': set(),
        'loop': threading.Event(),
    }

    remaining = len(resources)
    deferred = sum(1 for resource in resources.values() if resource['defer'])
    completed = []
    iterator = iter(resources)
    threads['loop'].set()
    while threads['loop'].wait():
        try:
            resource_id = next(iterator)
        except StopIteration:
            if not remaining and not threads['current']:
                break
            if threads['current']:
                threads['loop'].clear()
            for resource_id in completed:
                del resources[resource_id]
            completed = []
            iterator = iter(resources)
            continue

        resource = resources[resource_id]
        if resource['complete']:
            remaining -= 1
            completed.append(resource_id)
            continue

        defer = resource['defer']
        if defer:
            if remaining > deferred:
                continue
            if defer in resources and not resources[defer]['complete']:
                continue
            resource['defer'] = False

        args = resource['args']
        if args and not args[0]:
            resource['complete'] = True
            continue

        if not resource['thread']:
            new_thread = threading.Thread(target=_fetch, args=(resource,))
            new_thread.daemon = True
            threads['current'].add(new_thread)
            resource['thread'] = new_thread
            new_thread.start()

    return result


_KNOWN_RESPONSE_KINDS = {
    'activitylistresponse',
    'channellistresponse',
    'commentlistresponse',
    'commentthreadlistresponse',
    'guidecategorylistresponse',
    'playlistitemlistresponse',
    'playlistlistresponse',
    'searchlistresponse',
    'subscriptionlistresponse',
    'videolistresponse',
    # plugin kinds
    'pluginlistresponse',
}


def response_to_items(provider,
                      context,
                      json_data,
                      sort=None,
                      reverse=False,
                      process_next_page=True,
                      item_filter=None):
    kind, is_youtube, is_plugin, kind_type = _parse_kind(json_data)
    if not is_youtube and not is_plugin:
        context.log_debug('v3 response discarded: |%s|' % kind)
        return []

    params = context.get_params()

    if kind_type in _KNOWN_RESPONSE_KINDS:
        item_filter = context.get_settings().item_filter(
            update=item_filter,
            override=params.get('item_filter'),
        )
        result = _process_list_response(
            provider, context, json_data, item_filter
        )
    else:
        raise KodionException('Unknown kind: %s' % kind)

    if item_filter:
        result = filter_videos(result, **item_filter)

    if sort is not None:
        result.sort(key=sort, reverse=reverse)

    # no processing of next page item
    if not result or not process_next_page or params.get('hide_next_page'):
        return result

    # next page
    """
    This will try to prevent the issue 7163
    https://code.google.com/p/gdata-issues/issues/detail?id=7163
    Somehow the APIv3 is missing the token for the next page.
    We implemented our own calculation for the token into the YouTube client
    This should work for up to ~2000 entries.
    """
    current_page = params.get('page')
    next_page = current_page + 1 if current_page else 2
    new_params = dict(params, page=next_page)

    yt_next_page_token = json_data.get('nextPageToken')
    if yt_next_page_token == next_page:
        new_params['page_token'] = ''
    elif yt_next_page_token:
        new_params['page_token'] = yt_next_page_token
    else:
        if 'page_token' in new_params:
            del new_params['page_token']
        elif current_page:
            new_params['page_token'] = ''
        else:
            return result

        page_info = json_data.get('pageInfo', {})
        yt_total_results = int(page_info.get('totalResults', 0))
        yt_results_per_page = int(page_info.get('resultsPerPage', 50))

        if current_page * yt_results_per_page < yt_total_results:
            new_params['items_per_page'] = yt_results_per_page
        elif context.is_plugin_path(
                context.get_infolabel('Container.FolderPath'),
                partial=True,
        ):
            next_page = 1
            new_params['page'] = 1
        else:
            return result

    yt_visitor_data = json_data.get('visitorData')
    if yt_visitor_data:
        new_params['visitor'] = yt_visitor_data

    if next_page > 1:
        yt_click_tracking = json_data.get('clickTracking')
        if yt_click_tracking:
            new_params['click_tracking'] = yt_click_tracking

        offset = json_data.get('offset')
        if offset:
            new_params['offset'] = offset

    next_page_item = NextPageItem(context, new_params)
    result.append(next_page_item)

    return result


def _parse_kind(item):
    kind = item.get('kind', '')
    parts = kind.split('#')
    is_youtube = parts[0] == 'youtube'
    is_plugin = parts[0] == 'plugin'
    kind_type = parts[1 if len(parts) > 1 else 0].lower()
    return kind, is_youtube, is_plugin, kind_type
