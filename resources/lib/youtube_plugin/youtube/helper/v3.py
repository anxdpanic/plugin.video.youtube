# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import threading
from collections import deque
from operator import methodcaller
from re import compile as re_compile

from .utils import (
    THUMB_TYPES,
    THUMB_URL,
    filter_videos,
    get_thumbnail,
    make_comment_item,
    update_channel_items,
    update_playlist_items,
    update_video_items,
)
from ...kodion import KodionException, logging
from ...kodion.constants import (
    CHANNEL_ID,
    FANART_TYPE,
    FOLDER_URI,
    HIDE_LIVE,
    HIDE_MEMBERS,
    HIDE_NEXT_PAGE,
    HIDE_PLAYLISTS,
    HIDE_SEARCH,
    HIDE_SHORTS,
    HIDE_VIDEOS,
    INHERITED_PARAMS,
    ITEM_FILTER,
    PAGE,
    PATHS,
    PLAYLIST_ID,
    VIDEO_ID,
)
from ...kodion.items import (
    BookmarkItem,
    CommandItem,
    DirectoryItem,
    MediaItem,
    NewSearchItem,
    NextPageItem,
    VideoItem,
    menu_items,
)
from ...kodion.utils.convert_format import strip_html_from_text
from ...kodion.utils.datetime import parse_to_dt, utc_to_local


_log = logging.getLogger(__name__)


def _process_list_response(provider,
                           context,
                           json_data,
                           allow_duplicates=True,
                           item_filter=None,
                           progress_dialog=None,
                           video_id_dict=None,
                           channel_id_dict=None,
                           playlist_id_dict=None,
                           subscription_id_dict=None,
                           log=_log):
    yt_items = json_data.get('items')
    if not yt_items:
        log.warning('Items list is empty')
        return None

    yt_items_dict = {}
    new_video_id_dict = {}
    new_playlist_id_dict = {}
    new_channel_id_dict = {}
    if subscription_id_dict is None:
        subscription_id_dict = {}
    channel_items_dict = {}

    items = []
    position = 0
    do_callbacks = False

    params = context.get_params()
    new_params = {
        param: params[param]
        for param in INHERITED_PARAMS
        if param in params
    }

    settings = context.get_settings()
    thumb_re = re_compile(r'[^/._]+(?=[^/.]*?\.(?:jpg|webp))')
    thumb_size = settings.get_thumbnail_size()
    fanart_type = params.get(FANART_TYPE)
    if fanart_type is None:
        fanart_type = settings.fanart_selection()
    if fanart_type == settings.FANART_THUMBNAIL:
        fanart_type = settings.get_thumbnail_size(settings.THUMB_SIZE_BEST)
    else:
        fanart_type = False
    ui = context.get_ui()
    untitled = context.localize('untitled')

    for yt_item in yt_items:
        if not yt_item:
            continue
        kind, is_youtube, is_plugin, kind_type = _parse_kind(yt_item)
        if not (is_youtube or is_plugin) or not kind_type:
            log.debug('Item discarded: %r', kind)
            continue

        item_params = yt_item.get('_params') or {}
        item_params.update(new_params)

        item_id = yt_item.get('id')
        snippet = yt_item.get('snippet', {})

        video_id = None
        playlist_id = None
        channel_id = None

        if is_youtube:
            localised_info = snippet.get('localized') or {}
            title = (localised_info.get('title')
                     or snippet.get('title')
                     or untitled)
            description = strip_html_from_text(localised_info.get('description')
                                               or snippet.get('description')
                                               or '')

            thumbnails = snippet.get('thumbnails')
            if not thumbnails:
                pass
            elif isinstance(thumbnails, list):
                _url = thumbnails[0].get('url')
                thumbnails.extend([
                    {
                        'url': (thumb_re.sub(thumb['name'], _url, count=1)
                                if _url else
                                THUMB_URL.format(item_id, thumb['name'], '')),
                        'size': thumb['size'],
                        'ratio': thumb['ratio'],
                        'unverified': True,
                    }
                    for thumb in THUMB_TYPES.values()
                ])
            elif isinstance(thumbnails, dict):
                _url = next(iter(thumbnails.values())).get('url')
                thumbnails.update({
                    thumb_type: {
                        'url': (thumb_re.sub(thumb['name'], _url, count=1)
                                if _url else
                                THUMB_URL.format(item_id, thumb['name'], '')),
                        'size': thumb['size'],
                        'ratio': thumb['ratio'],
                        'unverified': True,
                    }
                    for thumb_type, thumb in THUMB_TYPES.items()
                    if thumb_type not in thumbnails
                })
            else:
                thumbnails = None
            if not thumbnails:
                thumbnails = {
                    thumb_type: {
                        'url': THUMB_URL.format(item_id, thumb['name'], ''),
                        'size': thumb['size'],
                        'ratio': thumb['ratio'],
                        'unverified': True,
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
                log.debug('searchResult discarded: %r', kind)
                continue

        if item_id:
            yt_items_dict[item_id] = yt_item

        if kind_type == 'video':
            video_id = item_id
            channel_id = (snippet.get('videoOwnerChannelId')
                          or snippet.get('channelId'))
            item_params[VIDEO_ID] = video_id
            item_uri = context.create_uri(
                (PATHS.PLAY,),
                item_params,
            )
            item = VideoItem(title,
                             item_uri,
                             image=image,
                             fanart=fanart,
                             plot=description,
                             channel_id=channel_id,
                             **item_params)

        elif kind_type == 'channel':
            channel_id = item_id
            item_uri = context.create_uri(
                (PATHS.CHANNEL, channel_id,),
                item_params,
            )
            item = DirectoryItem(ui.bold(title),
                                 item_uri,
                                 image=image,
                                 fanart=fanart,
                                 plot=description,
                                 category_label=title,
                                 channel_id=channel_id,
                                 **item_params)

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
                                 category_label=title,
                                 **item_params)

        elif kind_type == 'subscription':
            subscription_id = item_id
            channel_id = snippet['resourceId']['channelId']
            # map channel id with subscription id - needed to unsubscribe
            subscription_id_dict[channel_id] = subscription_id
            item_uri = context.create_uri(
                (PATHS.CHANNEL, channel_id,),
                item_params
            )
            item = DirectoryItem(ui.bold(title),
                                 item_uri,
                                 image=image,
                                 fanart=fanart,
                                 plot=description,
                                 category_label=title,
                                 channel_id=channel_id,
                                 subscription_id=subscription_id,
                                 **item_params)

        elif kind_type == 'searchfolder':
            if item_filter and item_filter.get(HIDE_SEARCH):
                continue
            channel_id = item_params[CHANNEL_ID]
            item = NewSearchItem(context, **item_params)
            channel_items = channel_items_dict.setdefault(channel_id, [])
            channel_items.append(item)

        elif kind_type == 'playlistsfolder':
            if item_filter and item_filter.get(HIDE_PLAYLISTS):
                continue
            channel_id = item_params[CHANNEL_ID]
            item_params['uri'] = context.create_uri(
                (PATHS.CHANNEL, channel_id, 'playlists',),
            )
            item_params['name'] = ui.bold(item_params.pop('title', ''))
            item = DirectoryItem(**item_params)
            channel_items = channel_items_dict.setdefault(channel_id, [])
            channel_items.append(item)

        elif kind_type in {'livefolder',
                           'membersfolder',
                           'shortsfolder',
                           'videosfolder'}:
            if (item_filter and (
                    (
                            kind_type == 'livefolder'
                            and item_filter.get(HIDE_LIVE)
                    ) or (
                            kind_type == 'membersfolder'
                            and item_filter.get(HIDE_MEMBERS)
                    ) or (
                            kind_type == 'shortsfolder'
                            and item_filter.get(HIDE_SHORTS)
                    ) or (
                            kind_type == 'videosfolder'
                            and item_filter.get(HIDE_VIDEOS)
                    )
            )):
                continue
            item = DirectoryItem(**item_params)

        elif kind_type in {'playlist',
                           'playlistlivefolder',
                           'playlistmembersfolder',
                           'playlistshortsfolder'}:
            if (item_filter and (
                    (
                            kind_type == 'playlistlivefolder'
                            and item_filter.get(HIDE_LIVE)
                    ) or (
                            kind_type == 'playlistmembersfolder'
                            and item_filter.get(HIDE_MEMBERS)
                    ) or (
                            kind_type == 'playlistshortsfolder'
                            and item_filter.get(HIDE_SHORTS)
                    )
            )):
                continue
            playlist_id = item_id
            # set channel id to 'mine' if the path is for a playlist of our own
            channel_id = snippet.get('channelId')
            if context.get_path().startswith(PATHS.MY_PLAYLISTS):
                uri_channel_id = 'mine'
            else:
                uri_channel_id = channel_id
            if uri_channel_id:
                item_uri = context.create_uri(
                    (PATHS.CHANNEL, uri_channel_id, 'playlist', playlist_id,),
                    item_params,
                )
            else:
                video_id = snippet.get('resourceId', {}).get('videoId')
                if video_id:
                    item_params[VIDEO_ID] = video_id
                item_uri = context.create_uri(
                    (PATHS.PLAYLIST, playlist_id,),
                    item_params,
                )
            item = DirectoryItem(ui.bold(title),
                                 item_uri,
                                 image=image,
                                 fanart=fanart,
                                 plot=description,
                                 category_label=title,
                                 channel_id=channel_id,
                                 playlist_id=playlist_id,
                                 **item_params)
            item.available = yt_item.get('_available', False)

        elif kind_type == 'playlistitem':
            video_id = snippet.get('resourceId', {}).get('videoId')
            if video_id:
                playlist_item_id = item_id
            else:
                video_id = item_id
                playlist_item_id = None
            channel_id = (snippet.get('videoOwnerChannelId')
                          or snippet.get('channelId'))
            playlist_id = snippet.get('playlistId')
            item_params[VIDEO_ID] = video_id
            item_uri = context.create_uri(
                (PATHS.PLAY,),
                item_params,
            )
            item = VideoItem(title,
                             item_uri,
                             image=image,
                             fanart=fanart,
                             plot=description,
                             channel_id=channel_id,
                             playlist_id=playlist_id,
                             playlist_item_id=playlist_item_id,
                             **item_params)

            # date time
            published_at = snippet.get('publishedAt')
            if published_at:
                datetime = parse_to_dt(published_at)
                local_datetime = utc_to_local(datetime)
                # If item is in a playlist, then set data added to playlist
                item.set_dateadded_from_datetime(local_datetime)

        elif kind_type == 'activity':
            details = yt_item['contentDetails']
            activity_type = snippet['type']
            if activity_type == 'recommendation':
                video_id = details['recommendation']['resourceId']['videoId']
            elif activity_type == 'upload':
                video_id = details['upload']['videoId']
            else:
                continue
            item_params[VIDEO_ID] = video_id
            item_uri = context.create_uri(
                (PATHS.PLAY,),
                item_params,
            )
            item = VideoItem(title,
                             item_uri,
                             image=image,
                             fanart=fanart,
                             plot=description,
                             **item_params)

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

        elif kind_type == 'bookmarkitem':
            item = BookmarkItem(**item_params)

        elif kind_type == 'commanditem':
            item = CommandItem(context=context, **item_params)

        else:
            raise KodionException('Unknown kind: %s' % kind)

        if not item:
            continue

        if not video_id and VIDEO_ID in item_params:
            video_id = item_params[VIDEO_ID]
        if not playlist_id:
            if PLAYLIST_ID in item_params:
                playlist_id = item_params[PLAYLIST_ID]
            elif not video_id and not channel_id:
                if CHANNEL_ID in item_params:
                    channel_id = item_params[CHANNEL_ID]

        for item_id, new_dict, complete_dict, allow_types, allow_kinds in (
                (
                        video_id,
                        new_video_id_dict,
                        video_id_dict,
                        MediaItem,
                        None,
                ),
                (
                        playlist_id,
                        new_playlist_id_dict,
                        playlist_id_dict,
                        DirectoryItem,
                        None,
                ),
                (
                        channel_id,
                        new_channel_id_dict,
                        channel_id_dict,
                        DirectoryItem,
                        {'channel', 'bookmarkitem', 'subscription'},
                ),
        ):
            if (not item_id
                    or (allow_types and not isinstance(item, allow_types))
                    or (allow_kinds and kind_type not in allow_kinds)):
                continue

            if complete_dict is None:
                complete_dict = new_dict
                new_dict = None

            if item_id in complete_dict:
                if not allow_duplicates:
                    continue
                stack = complete_dict[item_id]
            else:
                stack = deque()
                complete_dict[item_id] = stack

            if new_dict is not None:
                new_dict[item_id] = stack

            if is_youtube:
                stack.append(item)
            else:
                stack.appendleft(item)

        if '_context_menu' in yt_item:
            item.add_context_menu(**yt_item['_context_menu'])

        if '_callback' in yt_item:
            item.callback = yt_item.pop('_callback')
            do_callbacks = True

        if not item.get_special_sort():
            # Set track number from playlist, or set to current list position to
            # match "Default" (unsorted) sort order
            item.set_track_number(snippet.get('position', position) + 1)
            position += 1

        items.append(item)

    if progress_dialog:
        delta = (len(new_video_id_dict)
                 + len(new_channel_id_dict)
                 + len(new_playlist_id_dict)
                 + len(subscription_id_dict))
        progress_dialog.grow_total(delta=delta)
        progress_dialog.update(steps=delta)

    resource_manager = provider.get_resource_manager(context, progress_dialog)
    resources = {
        1: {
            'fetcher': resource_manager.get_videos,
            'args': (
                new_video_id_dict,
            ),
            'kwargs': {
                'live_details': True,
                'suppress_errors': True,
                'defer_cache': True,
                'yt_items_dict': yt_items_dict,
            },
            'thread': None,
            'updater': update_video_items,
            'upd_args': (
                provider,
                context,
                new_video_id_dict,
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
                new_playlist_id_dict,
            ),
            'kwargs': {
                'defer_cache': True,
            },
            'thread': None,
            'updater': update_playlist_items,
            'upd_args': (
                provider,
                context,
                new_playlist_id_dict,
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
                new_channel_id_dict,
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
                new_channel_id_dict,
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
        active_thread_ids = threads['active_thread_ids']
        thread_id = threading.current_thread().ident
        active_thread_ids.add(thread_id)
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
        except Exception:
            log.exception('Error')
        finally:
            resource['complete'] = True
            active_thread_ids.discard(thread_id)
            threads['loop_enable'].set()

    active_thread_ids = set()
    loop_enable = threading.Event()
    threads = {
        'active_thread_ids': active_thread_ids,
        'loop_enable': loop_enable,
    }

    remaining = len(resources)
    deferred = len([
        1 for resource in resources.values() if resource['defer']
    ])
    completed = []
    iterator = iter(resources)
    loop_enable.set()
    while loop_enable.wait(1) or active_thread_ids:
        try:
            resource_id = next(iterator)
        except StopIteration:
            if active_thread_ids:
                loop_enable.clear()
            for resource_id in completed:
                del resources[resource_id]
            remaining = len(resources)
            if remaining <= 0 and not active_thread_ids:
                break
            deferred = len([
                1 for resource in resources.values() if resource['defer']
            ])
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

        if resource['thread']:
            continue
        if (not resource['kwargs'].pop('_force_run', False)
                and not any(resource['args'])):
            resource['complete'] = True
            continue

        new_thread = threading.Thread(target=_fetch, args=(resource,))
        new_thread.daemon = True
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
                      allow_duplicates=True,
                      process_next_page=True,
                      item_filter=None,
                      hide_progress=None,
                      log=_log):
    params = context.get_params()
    settings = context.get_settings()
    ui = context.get_ui()

    items_per_page = settings.items_per_page()
    item_filter_param = params.get(ITEM_FILTER)
    current_page = params.get(PAGE) or 1
    exclude_current = params.get('exclude')
    if exclude_current:
        exclude_current = exclude_current[:]
    else:
        exclude_current = []
    exclude_next = []
    page_token = None
    remaining = items_per_page
    post_fill_attempts = 5
    post_filled = False
    filtered = 0

    filtered_items = []
    video_id_dict = {}
    channel_id_dict = {}
    playlist_id_dict = {}
    subscription_id_dict = {}

    with ui.create_progress_dialog(
            heading=context.localize('loading.directory'),
            message_template=context.localize('loading.directory.progress'),
            background=True,
            hide_progress=hide_progress,
    ) as progress_dialog:
        while 1:
            kind, is_youtube, is_plugin, kind_type = _parse_kind(json_data)
            if not is_youtube and not is_plugin:
                log.debug(('Response discarded', 'Kind: %r'), kind)
                break

            if kind_type not in _KNOWN_RESPONSE_KINDS:
                log.error_trace(('Unknown kind', 'Kind: %r'), kind)
                break

            pre_filler = json_data.pop('_pre_filler', None)
            if pre_filler:
                if hasattr(pre_filler, '__nowrap__'):
                    _json_data = pre_filler(
                        json_data=json_data,
                        max_results=remaining,
                        exclude=None if allow_duplicates else exclude_current,
                    )
                else:
                    _json_data = pre_fill(
                        filler=pre_filler,
                        json_data=json_data,
                        max_results=remaining,
                        exclude=None if allow_duplicates else exclude_current,
                    )
                if _json_data:
                    json_data = _json_data

            _item_filter = settings.item_filter(
                update=(item_filter or json_data.get('_item_filter')),
                override=item_filter_param,
                params=params,
                exclude=exclude_current,
            )
            result = _process_list_response(
                provider,
                context,
                json_data,
                allow_duplicates=allow_duplicates,
                item_filter=_item_filter,
                progress_dialog=progress_dialog,
                video_id_dict=video_id_dict,
                channel_id_dict=channel_id_dict,
                playlist_id_dict=playlist_id_dict,
                subscription_id_dict=subscription_id_dict,
            )
            if result:
                items, do_callbacks = result
                callback = json_data.get('_callback')
            else:
                items = []
                do_callbacks = False
                callback = None

            if items and (_item_filter or do_callbacks or callback):
                items, filtered_out = filter_videos(
                    items,
                    callback=callback,
                    **_item_filter
                )
                if filtered_out:
                    filtered += len(filtered_out)
                    log.debugging and log.debug(
                        'Items filtered out: {items!e}',
                        items=map(methodcaller('__str_parts__', as_dict=True),
                                  filtered_out),
                    )

            post_filler = json_data.pop('_post_filler', None)
            num_items = 0
            for item in items:
                if post_filler and num_items >= remaining:
                    remaining = 0
                    break
                if isinstance(item, MediaItem):
                    exclude_next.append(item.video_id)
                filtered_items.append(item)
                num_items += 1
            else:
                page_token = json_data.get('nextPageToken') or page_token
                if num_items:
                    remaining -= num_items
                elif post_filler and post_fill_attempts > 0:
                    post_fill_attempts -= 1

            if exclude_next:
                exclude_current.extend(exclude_next)

            if remaining > 0:
                if post_filled:
                    current_page += 1
            else:
                break

            if not post_filler or post_fill_attempts <= 0:
                break

            if hasattr(post_filler, '__nowrap__'):
                _json_data = post_filler(
                    json_data=json_data,
                )
            else:
                _json_data = post_fill(
                    filler=post_filler,
                    json_data=json_data,
                )
            if not _json_data:
                break
            json_data = _json_data
            post_filled = True
        next_page = current_page + 1

        items = filtered_items
        if not items:
            return items

        if sort is not None:
            items.sort(key=sort, reverse=reverse)

    # no processing of next page item
    if not json_data or not process_next_page or params.get(HIDE_NEXT_PAGE):
        return items

    # next page
    """
    This will try to prevent the issue 7163
    https://code.google.com/p/gdata-issues/issues/detail?id=7163
    Somehow the APIv3 is missing the token for the next page.
    We implemented our own calculation for the token into the YouTube client
    This should work for up to ~2000 entries.
    """
    new_params = dict(params,
                      page=next_page,
                      filtered=filtered,
                      exclude=exclude_next)
    if post_fill_attempts <= 0:
        next_page = 1
        new_params['page'] = 1
        if 'page_token' in new_params:
            del new_params['page_token']
        elif 'page' in params:
            new_params['page_token'] = ''
    elif page_token == next_page:
        new_params['page_token'] = ''
    elif page_token:
        new_params['page_token'] = page_token
    else:
        if 'page_token' in new_params:
            del new_params['page_token']
        elif 'page' in params:
            new_params['page_token'] = ''
        else:
            return items

        page_info = json_data.get('pageInfo', {})
        yt_total_results = int(page_info.get('totalResults') or len(items))
        yt_results_per_page = int(page_info.get('resultsPerPage')
                                  or items_per_page)

        if (next_page - 1) * yt_results_per_page < yt_total_results:
            new_params['items_per_page'] = yt_results_per_page
        elif ui.get_container_info(FOLDER_URI):
            next_page = 1
            new_params['page'] = 1
        else:
            return items

    if next_page > 1:
        yt_visitor_data = json_data.get('visitorData')
        if yt_visitor_data:
            new_params['visitor'] = yt_visitor_data
        yt_click_tracking = json_data.get('clickTracking')
        if yt_click_tracking:
            new_params['click_tracking'] = yt_click_tracking

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


def pre_fill(filler, json_data, max_results, exclude=None):
    if not json_data:
        return None
    page_token = json_data.get('nextPageToken')
    if not page_token:
        json_data['_pre_filler'] = None
        json_data['_post_filler'] = None
        return None

    items = json_data.get('items') or []
    post_filler = json_data.pop('_post_filler', None)

    all_items = []
    if exclude is not None:
        exclude = set(exclude)
    pre_fill_attempts = 5
    remaining = max_results

    while 1:
        num_items = 0
        for item in items:
            if num_items >= remaining:
                json_data['nextPageToken'] = page_token
                remaining = 0
                break
            item_id = item['id']
            if exclude is None:
                pass
            elif item_id in exclude:
                continue
            else:
                exclude.add(item_id)
            all_items.append(item)
            num_items += 1
        else:
            if num_items:
                remaining -= num_items
            else:
                pre_fill_attempts -= 1

        page_token = json_data.get('nextPageToken')
        if not page_token or remaining <= 0 or pre_fill_attempts <= 0:
            break

        next_response = filler(
            page_token=page_token,
            visitor=json_data.get('visitorData'),
            click_tracking=json_data.get('clickTracking'),
        )
        if not next_response:
            break
        json_data = next_response
        items = json_data.get('items') or []

    json_data['items'] = all_items
    json_data.setdefault('_pre_filler', filler)
    if post_filler:
        json_data.setdefault('_post_filler', post_filler)
    return json_data


def post_fill(filler, json_data):
    if not json_data:
        return None
    page_token = json_data.get('nextPageToken')
    if not page_token:
        json_data['_pre_filler'] = None
        json_data['_post_filler'] = None
        return None

    pre_filler = json_data.pop('_pre_filler', None)

    json_data = filler(
        page_token=page_token,
        visitor=json_data.get('visitorData'),
        click_tracking=json_data.get('clickTracking'),
    )
    if json_data:
        json_data.setdefault('_post_filler', filler)
        if pre_filler:
            json_data.setdefault('_pre_filler', pre_filler)
    return json_data
