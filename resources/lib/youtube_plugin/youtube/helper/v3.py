# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import threading
from collections import deque
from sys import exc_info
from traceback import format_stack

from .utils import (
    THUMB_TYPES,
    filter_videos,
    get_thumbnail,
    make_comment_item,
    update_channel_items,
    update_playlist_items,
    update_video_items,
)
from ...kodion import KodionException
from ...kodion.constants import (
    PATHS,
    PLAY_FORCE_AUDIO,
    PLAY_PROMPT_QUALITY,
    PLAY_PROMPT_SUBTITLES,
    PLAY_TIMESHIFT,
    PLAY_WITH,
)
from ...kodion.items import (
    CommandItem,
    DirectoryItem,
    MediaItem,
    NewSearchItem,
    NextPageItem,
    VideoItem,
    menu_items,
)
from ...kodion.utils import datetime_parser, strip_html_from_text


def _process_list_response(provider,
                           context,
                           json_data,
                           item_filter=None,
                           progress_dialog=None):
    yt_items = json_data.get('items', [])
    if not yt_items:
        context.log_warning('v3 response: Items list is empty')
        return None

    video_id_dict = {}
    channel_id_dict = {}
    playlist_id_dict = {}
    subscription_id_dict = {}

    items = []
    do_callbacks = False

    new_params = {}
    params = context.get_params()
    copy_params = {
        'addon_id',
        'incognito',
        PLAY_FORCE_AUDIO,
        PLAY_TIMESHIFT,
        PLAY_PROMPT_QUALITY,
        PLAY_PROMPT_SUBTITLES,
        PLAY_WITH,
    }.intersection(params.keys())
    for param in copy_params:
        new_params[param] = params[param]

    settings = context.get_settings()
    thumb_size = settings.get_thumbnail_size()
    fanart_type = params.get('fanart_type')
    if fanart_type is None:
        fanart_type = settings.fanart_selection()
    if fanart_type == settings.FANART_THUMBNAIL:
        fanart_type = settings.get_thumbnail_size(settings.THUMB_SIZE_BEST)
    else:
        fanart_type = False
    ui = context.get_ui()
    untitled = context.localize('untitled')

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

            localised_info = snippet.get('localized') or {}
            title = (localised_info.get('title')
                     or snippet.get('title')
                     or untitled)
            description = strip_html_from_text(localised_info.get('description')
                                               or snippet.get('description')
                                               or '')

            thumbnails = snippet.get('thumbnails')
            if not thumbnails:
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
            if item_id:
                yt_item['_context_menu'] = {
                    'context_menu': (
                        menu_items.search_sort_by(context, params, 'relevance'),
                        menu_items.search_sort_by(context, params, 'date'),
                        menu_items.search_sort_by(context, params, 'viewCount'),
                        menu_items.search_sort_by(context, params, 'rating'),
                        menu_items.search_sort_by(context, params, 'title'),
                    ),
                    'position': 0,
                }
            else:
                context.log_debug('v3 searchResult discarded: |%s|' % kind)
                continue

        if kind_type == 'video':
            item_params['video_id'] = item_id
            item_uri = context.create_uri(
                (PATHS.PLAY,),
                item_params,
            )
            item = VideoItem(title,
                             item_uri,
                             image=image,
                             fanart=fanart,
                             plot=description,
                             video_id=item_id,
                             channel_id=(snippet.get('videoOwnerChannelId')
                                         or snippet.get('channelId')))

        elif kind_type == 'channel':
            item_uri = context.create_uri(
                (PATHS.CHANNEL, item_id,),
                item_params,
            )
            item = DirectoryItem(ui.bold(title),
                                 item_uri,
                                 image=image,
                                 fanart=fanart,
                                 plot=description,
                                 category_label=title,
                                 channel_id=item_id)
            channel_id_dict[item_id] = item

        elif kind_type == 'guidecategory':
            item_params['guide_id'] = item_id
            item_uri = context.create_uri(
                ('special', 'browse_channels'),
                item_params,
            )
            item = DirectoryItem(ui.bold(title),
                                 item_uri,
                                 image=image,
                                 fanart=fanart,
                                 plot=description,
                                 category_label=title)

        elif kind_type == 'subscription':
            subscription_id = item_id
            item_id = snippet['resourceId']['channelId']
            # map channel id with subscription id - needed to unsubscribe
            subscription_id_dict[item_id] = subscription_id

            item_uri = context.create_uri(
                (PATHS.CHANNEL, item_id,),
                item_params
            )
            item = DirectoryItem(ui.bold(title),
                                 item_uri,
                                 image=image,
                                 fanart=fanart,
                                 plot=description,
                                 category_label = title,
                                 channel_id=item_id,
                                 subscription_id=subscription_id)
            channel_id_dict[item_id] = item

        elif kind_type == 'searchfolder':
            channel_id = snippet.get('channelId')
            item = NewSearchItem(context,
                                 ui.bold(title),
                                 image=image,
                                 fanart=fanart,
                                 channel_id=channel_id)

        elif kind_type == 'playlistfolder':
            # set channel id to 'mine' if the path is for a playlist of our own
            channel_id = snippet.get('channelId')
            if context.get_path().startswith(PATHS.MY_PLAYLISTS):
                uri_channel_id = 'mine'
            else:
                uri_channel_id = channel_id
            if not uri_channel_id:
                continue

            item_uri = context.create_uri(
                (PATHS.CHANNEL, uri_channel_id, item_id,),
                item_params,
            )
            item = DirectoryItem(ui.bold(title),
                                 item_uri,
                                 image=image,
                                 fanart=fanart,
                                 plot=description,
                                 category_label=title,
                                 channel_id=channel_id,
                                 playlist_id=item_id)

        elif kind_type == 'playlist':
            # set channel id to 'mine' if the path is for a playlist of our own
            channel_id = snippet.get('channelId')
            if context.get_path().startswith(PATHS.MY_PLAYLISTS):
                uri_channel_id = 'mine'
            else:
                uri_channel_id = channel_id
            if uri_channel_id:
                item_uri = context.create_uri(
                    (PATHS.CHANNEL, uri_channel_id, 'playlist', item_id,),
                    item_params,
                )
            else:
                item_uri = context.create_uri(
                    (PATHS.PLAYLIST, item_id,),
                    item_params,
                )
            item = DirectoryItem(ui.bold(title),
                                 item_uri,
                                 image=image,
                                 fanart=fanart,
                                 plot=description,
                                 category_label=title,
                                 channel_id=channel_id,
                                 playlist_id=item_id)
            playlist_id_dict[item_id] = item
            item.available = False

        elif kind_type == 'playlistitem':
            playlist_item_id = item_id
            item_id = snippet['resourceId']['videoId']

            item_params['video_id'] = item_id
            item_uri = context.create_uri(
                (PATHS.PLAY,),
                item_params,
            )
            item = VideoItem(title,
                             item_uri,
                             image=image,
                             fanart=fanart,
                             plot=description,
                             video_id=item_id,
                             channel_id=snippet.get('videoOwnerChannelId'),
                             playlist_id=snippet.get('playlistId'),
                             playlist_item_id=playlist_item_id)

            # date time
            published_at = snippet.get('publishedAt')
            if published_at:
                datetime = datetime_parser.parse(published_at)
                local_datetime = datetime_parser.utc_to_local(datetime)
                # If item is in a playlist, then set data added to playlist
                item.set_dateadded_from_datetime(local_datetime)

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
            item = VideoItem(title,
                             item_uri,
                             image=image,
                             fanart=fanart,
                             plot=description,
                             video_id=item_id)

        elif kind_type.startswith('comment'):
            if kind_type == 'commentthread':
                reply_count = snippet['totalReplyCount']
                snippet = snippet['topLevelComment']['snippet']
                if reply_count:
                    item_uri = context.create_uri(
                        PATHS.VIDEO_COMMENTS_THREAD,
                        {'parent_id': item_id}
                    )
                else:
                    item_uri = ''
            else:
                item_uri = ''
                reply_count = 0

            item = make_comment_item(context,
                                     snippet,
                                     uri=item_uri,
                                     reply_count=reply_count)
            position = snippet.get('position') or len(items)
            item.set_track_number(position + 1)

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

        if isinstance(item, MediaItem):
            # Set track number from playlist, or set to current list length to
            # match "Default" (unsorted) sort order
            position = snippet.get('position') or len(items)
            item.set_track_number(position + 1)
            item_id = item.video_id
            if item_id in video_id_dict:
                fifo_queue = video_id_dict[item_id]
            else:
                fifo_queue = deque()
                video_id_dict[item_id] = fifo_queue
            fifo_queue.appendleft(item)

        if '_callback' in yt_item:
            item.callback = yt_item['_callback']
            do_callbacks = True

        items.append(item)

    # this will also update the channel_id_dict with the correct channel_id
    # for each video.
    channel_items_dict = {}

    resource_manager = provider.get_resource_manager(context, progress_dialog)
    resources = {
        1: {
            'fetcher': resource_manager.get_videos,
            'args': (
                video_id_dict,
            ),
            'kwargs': {
                'live_details': True,
                'suppress_errors': True,
                'defer_cache': True,
                'yt_items': yt_items,
            },
            'thread': None,
            'updater': update_video_items,
            'upd_args': (
                provider,
                context,
                video_id_dict,
                channel_items_dict,
            ),
            'upd_kwargs': {
                'data': None,
                'live_details': True,
                'item_filter': item_filter,
            },
            'complete': False,
            'defer': False,
        },
        2: {
            'fetcher': resource_manager.get_playlists,
            'args': (
                playlist_id_dict,
            ),
            'kwargs': {
                'defer_cache': True,
            },
            'thread': None,
            'updater': update_playlist_items,
            'upd_args': (
                provider,
                context,
                playlist_id_dict,
                channel_items_dict,
            ),
            'upd_kwargs': {
                'data': None,
            },
            'complete': False,
            'defer': False,
        },
        3: {
            'fetcher': resource_manager.get_channels,
            'args': (
                channel_id_dict,
            ),
            'kwargs': {
                '_force_run': True,
                'defer_cache': True,
            },
            'thread': None,
            'updater': update_channel_items,
            'upd_args': (
                provider,
                context,
                channel_id_dict,
                subscription_id_dict,
                channel_items_dict,
            ),
            'upd_kwargs': {
                '_force_run': True,
                'data': None,
            },
            'complete': False,
            'defer': True,
        },
        4: {
            'fetcher': resource_manager.cache_data,
            'args': (),
            'kwargs': {
                '_force_run': True,
            },
            'thread': None,
            'updater': None,
            'upd_args': (),
            'upd_kwargs': {},
            'complete': False,
            'defer': 3,
        },
    }

    def _fetch(resource):
        try:
            data = resource['fetcher'](*resource['args'], **resource['kwargs'])

            updater = resource['updater']
            if not updater:
                return

            kwargs = resource['upd_kwargs']
            if not kwargs.pop('_force_run', False) and not data:
                return
            kwargs['data'] = data

            updater(*resource['upd_args'], **kwargs)
        except Exception as exc:
            tb_obj = exc_info()[2]
            while tb_obj:
                next_tb_obj = tb_obj.tb_next
                if next_tb_obj:
                    tb_obj = next_tb_obj
                else:
                    stack = ''.join(format_stack(f=tb_obj.tb_frame))
                    break
            else:
                stack = None

            msg = ('v3._process_list_response._fetch - Error'
                   '\n\tException: {exc!r}'
                   '\n\tStack trace (most recent call last):\n{stack}'
                   .format(exc=exc, stack=stack))
            context.log_error(msg)
        finally:
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

    if progress_dialog:
        delta = (len(video_id_dict)
                 + len(channel_id_dict)
                 + len(playlist_id_dict)
                 + len(subscription_id_dict))
        progress_dialog.grow_total(delta=delta)
        progress_dialog.update(steps=delta)

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

        if not resource['thread']:
            if (not resource['kwargs'].pop('_force_run', False)
                    and not any(resource['args'])):
                resource['complete'] = True
                continue

            new_thread = threading.Thread(target=_fetch, args=(resource,))
            new_thread.daemon = True
            threads['current'].add(new_thread)
            resource['thread'] = new_thread
            new_thread.start()

    return items, do_callbacks


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
    params = context.get_params()
    settings = context.get_settings()

    items_per_page = settings.items_per_page()
    item_filter_param = params.get('item_filter')
    current_page = params.get('page')
    next_page = None

    with context.get_ui().create_progress_dialog(
            heading=context.localize('loading.directory'),
            message_template=context.localize('loading.directory.progress'),
            background=True,
    ) as progress_dialog:
        remaining = None
        filtered_items = []
        num_original_items = 0
        while 1:
            kind, is_youtube, is_plugin, kind_type = _parse_kind(json_data)
            if not is_youtube and not is_plugin:
                context.log_debug('v3.response_to_items - Response discarded'
                                  '\n\tKind: |{kind}|'
                                  .format(kind=kind))
                break

            if kind_type not in _KNOWN_RESPONSE_KINDS:
                context.log_error('v3.response_to_items - Unknown kind'
                                  '\n\tKind: |{kind}|'
                                  .format(kind=kind))
                break

            _item_filter = settings.item_filter(
                update=(item_filter or json_data.get('_item_filter')),
                override=item_filter_param,
            )
            result = _process_list_response(
                provider,
                context,
                json_data,
                item_filter=_item_filter,
                progress_dialog=progress_dialog,
            )
            if not result:
                break

            items, do_callbacks = result
            callback = json_data.get('_callback')
            if not items:
                break
            elif not num_original_items:
                num_original_items = max(items_per_page, len(items))

            if _item_filter or do_callbacks or callback:
                items = filter_videos(items, callback=callback, **_item_filter)
            if items:
                if remaining and remaining < len(items):
                    items = items[:remaining]
                filtered_items.extend(items)

            remaining = num_original_items - len(filtered_items)
            if remaining >= 0:
                if next_page:
                    next_page += 1
                elif current_page:
                    next_page = current_page + 1
                else:
                    next_page = 2
            if remaining <= 0:
                break

            filler = json_data.get('_filler')
            if not filler:
                break

            _json_data = filler(json_data, remaining)
            if _json_data:
                json_data = _json_data
            else:
                break

        items = filtered_items
        if not items:
            return items

        if sort is not None:
            items.sort(key=sort, reverse=reverse)

    # no processing of next page item
    if not json_data or not process_next_page or params.get('hide_next_page'):
        return items

    # next page
    """
    This will try to prevent the issue 7163
    https://code.google.com/p/gdata-issues/issues/detail?id=7163
    Somehow the APIv3 is missing the token for the next page.
    We implemented our own calculation for the token into the YouTube client
    This should work for up to ~2000 entries.
    """
    new_params = dict(params, page=next_page)
    offset = json_data.get('offset')
    yt_next_page_token = json_data.get('nextPageToken')
    if yt_next_page_token == next_page:
        new_params['page_token'] = ''
    elif yt_next_page_token:
        new_params['page_token'] = yt_next_page_token
    elif offset:
        new_params['page_token'] = ''
    else:
        if 'page_token' in new_params:
            del new_params['page_token']
        elif current_page:
            new_params['page_token'] = ''
        else:
            return items

        page_info = json_data.get('pageInfo', {})
        yt_total_results = int(page_info.get('totalResults') or len(items))
        yt_results_per_page = int(page_info.get('resultsPerPage')
                                  or items_per_page)

        if (next_page - 1) * yt_results_per_page < yt_total_results:
            new_params['items_per_page'] = yt_results_per_page
        elif context.is_plugin_path(
                context.get_infolabel('Container.FolderPath'),
                partial=True,
        ):
            next_page = 1
            new_params['page'] = 1
        else:
            return items

    yt_visitor_data = json_data.get('visitorData')
    if yt_visitor_data:
        new_params['visitor'] = yt_visitor_data

    if next_page > 1:
        yt_click_tracking = json_data.get('clickTracking')
        if yt_click_tracking:
            new_params['click_tracking'] = yt_click_tracking

        if offset:
            new_params['offset'] = offset

    next_page_item = NextPageItem(context, new_params)
    items.append(next_page_item)

    return items


def _parse_kind(item):
    kind = item.get('kind', '')
    parts = kind.split('#')
    is_youtube = parts[0] == 'youtube'
    is_plugin = parts[0] == 'plugin'
    kind_type = parts[1 if len(parts) > 1 else 0].lower()
    return kind, is_youtube, is_plugin, kind_type
