# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from functools import partial

from . import UrlResolver, UrlToItemConverter, utils, v3
from ...kodion import KodionException, logging
from ...kodion.constants import (
    CHANNEL_ID,
    CHANNEL_IDS,
    CONTENT,
    HIDE_FOLDERS,
    HIDE_LIVE,
    HIDE_SHORTS,
    HIDE_VIDEOS,
    INCOGNITO,
    PAGE,
    PATHS,
    PLAYLIST_ID,
    PLAYLIST_IDS,
    VIDEO_ID,
)
from ...kodion.items import DirectoryItem, UriItem
from ...kodion.utils.convert_format import strip_html_from_text


def _process_related_videos(provider, context, client):
    function_cache = context.get_function_cache()
    refresh = context.refresh_requested()
    params = context.get_params()

    video_id = params.get(VIDEO_ID)
    if video_id:
        json_data = function_cache.run(
            client.get_related_videos,
            function_cache.ONE_HOUR,
            _refresh=refresh,
            video_id=video_id,
            page_token=params.get('page_token', ''),
        )
        if not json_data:
            return False, None

        filler = partial(
            function_cache.run,
            client.get_related_videos,
            function_cache.ONE_HOUR,
            _refresh=refresh,
            video_id=video_id,
        )
        json_data['_pre_filler'] = filler
        json_data['_post_filler'] = filler
        category_label = context.localize(
            'video.related.to.x',
            params.get('item_name') or context.localize('untitled'),
        )
    else:
        json_data = function_cache.run(
            client.get_related_for_home,
            function_cache.ONE_HOUR,
            _refresh=refresh,
        )
        if not json_data:
            return False, None
        category_label = None

    result = v3.response_to_items(
        provider,
        context,
        json_data,
        allow_duplicates=False,
    )
    options = {
        provider.CONTENT_TYPE: {
            'content_type': CONTENT.VIDEO_CONTENT,
            'sub_type': None,
            'category_label': category_label,
        },
    }
    return result, options


def _process_comments(provider, context, client):
    params = context.get_params()
    video_id = params.get(VIDEO_ID)
    parent_id = params.get('parent_id')
    if not video_id and not parent_id:
        return False, None

    if video_id:
        json_data = client.get_parent_comments(
            video_id=video_id,
            page_token=params.get('page_token', ''),
        )
    elif parent_id:
        json_data = client.get_child_comments(
            parent_id=parent_id,
            page_token=context.get_param('page_token', ''),
        )
    else:
        json_data = None
    if not json_data:
        return False, None

    result = v3.response_to_items(provider, context, json_data)
    options = {
        provider.CONTENT_TYPE: {
            'content_type': CONTENT.LIST_CONTENT,
            'sub_type': CONTENT.COMMENTS,
            'category_label': params.get('item_name', video_id),
        },
    }
    return result, options


def _process_recommendations(provider, context, client):
    function_cache = context.get_function_cache()
    refresh = context.refresh_requested()
    params = context.get_params()

    browse_id = 'FEwhat_to_watch'
    browse_client = 'tv'
    browse_paths = client.JSON_PATHS['tv_shelf_horizontal']
    # browse_client = 'android_vr'
    # browse_paths = client.JSON_PATHS['vr_shelf']

    json_data = function_cache.run(
        client.get_browse_items,
        function_cache.ONE_HOUR,
        _refresh=refresh,
        browse_id=browse_id,
        client=browse_client,
        do_auth=True,
        page_token=params.get('page_token'),
        click_tracking=params.get('click_tracking'),
        visitor=params.get('visitor'),
        json_path=browse_paths,
    )
    if not json_data:
        return False, None

    filler = partial(
        function_cache.run,
        client.get_browse_items,
        function_cache.ONE_HOUR,
        _refresh=refresh,
        browse_id=browse_id,
        client=browse_client,
        do_auth=True,
        json_path=browse_paths,
    )
    json_data['_pre_filler'] = filler
    json_data['_post_filler'] = filler

    result = v3.response_to_items(
        provider,
        context,
        json_data,
        allow_duplicates=False,
    )
    options = {
        provider.CONTENT_TYPE: {
            'content_type': CONTENT.VIDEO_CONTENT,
            'sub_type': None,
            'category_label': None,
        },
    }
    return result, options


def _process_trending(provider, context, client):
    json_data = client.get_trending_videos(
        page_token=context.get_param('page_token'),
    )
    if not json_data:
        return False, None

    json_data['_post_filler'] = client.get_trending_videos

    result = v3.response_to_items(provider, context, json_data)
    options = {
        provider.CONTENT_TYPE: {
            'content_type': CONTENT.VIDEO_CONTENT,
            'sub_type': None,
            'category_label': None,
        },
    }
    return result, options


def _process_browse_channels(provider, context, client):
    guide_id = context.get_param('guide_id')
    if guide_id:
        json_data = client.get_guide_category(guide_id)
    else:
        function_cache = context.get_function_cache()
        json_data = function_cache.run(
            client.get_guide_categories,
            function_cache.ONE_MONTH,
            _refresh=context.refresh_requested(),
        )
    if not json_data:
        return False, None

    result = v3.response_to_items(provider, context, json_data)
    options = {
        provider.CONTENT_TYPE: {
            'content_type': CONTENT.LIST_CONTENT,
            'sub_type': None,
            'category_label': None,
        },
    }
    return result, options


def _process_disliked_videos(provider, context, client):
    json_data = client.get_disliked_videos(
        page_token=context.get_param('page_token', '')
    )
    if not json_data:
        return False, None

    result = v3.response_to_items(provider, context, json_data)
    options = {
        provider.CONTENT_TYPE: {
            'content_type': CONTENT.VIDEO_CONTENT,
            'sub_type': None,
            'category_label': None,
        },
    }
    return result, options


def _process_live_events(provider, context, client, event_type='live'):
    # TODO: cache result
    params = context.get_params()
    json_data = client.get_live_events(
        event_type=event_type,
        order=params.get('order',
                         'date' if event_type == 'upcoming' else 'viewCount'),
        page_token=params.get('page_token', ''),
        location=params.get('location', False),
        after={'days': 3} if event_type == 'completed' else None,
    )
    if not json_data:
        return False, None

    result = v3.response_to_items(provider, context, json_data)
    options = {
        provider.CONTENT_TYPE: {
            'content_type': CONTENT.VIDEO_CONTENT,
            'sub_type': None,
            'category_label': None,
        },
    }
    return result, options


def _process_description_links(provider, context):
    params = context.get_params()
    incognito = params.get(INCOGNITO, False)
    addon_id = params.get('addon_id', '')

    def _extract_urls(video_id):
        url_resolver = UrlResolver(context)

        with context.get_ui().create_progress_dialog(
                heading=context.localize('please_wait'), background=False
        ) as progress_dialog:
            resource_manager = provider.get_resource_manager(context)

            video_data = resource_manager.get_videos((video_id,))
            yt_item = video_data[video_id] if video_data else None
            if not yt_item or 'snippet' not in yt_item:
                context.get_ui().on_ok(
                    title=context.localize('video.description_links'),
                    text=context.localize('video.description_links.not_found')
                )
                return False, None
            snippet = yt_item['snippet']
            description = strip_html_from_text(snippet['description'])

            function_cache = context.get_function_cache()
            urls = function_cache.run(
                utils.extract_urls,
                function_cache.ONE_DAY,
                _refresh=context.refresh_requested(),
                text=description,
            )

            progress_dialog.set_total(len(urls))

            res_urls = []
            for url in urls:
                progress_dialog.update(steps=1, text=url)
                resolved_url = url_resolver.resolve(url)
                res_urls.append(resolved_url)

                if progress_dialog.is_aborted():
                    logging.debug('Resolving urls aborted')
                    break

            url_to_item_converter = UrlToItemConverter()
            url_to_item_converter.process_urls(res_urls, context)
            result = url_to_item_converter.get_items(provider, context)

        if not result:
            context.get_ui().on_ok(
                title=context.localize('video.description_links'),
                text=context.localize('video.description_links.not_found')
            )
            return False, None

        options = {
            provider.CONTENT_TYPE: {
                'content_type': CONTENT.VIDEO_CONTENT,
                'sub_type': None,
                'category_label': None,
            },
        }
        return result, options

    def _display_channels(channel_ids):
        item_params = {}
        if incognito:
            item_params[INCOGNITO] = incognito
        if addon_id:
            item_params['addon_id'] = addon_id

        channel_id_dict = {}
        for channel_id in channel_ids:
            channel_item = DirectoryItem(
                name='',
                uri=context.create_uri(
                    (PATHS.CHANNEL, channel_id,),
                    item_params,
                ),
                channel_id=channel_id,
            )
            channel_items = channel_id_dict.setdefault(channel_id, [])
            channel_items.append(channel_item)

        utils.update_channel_items(provider, context, channel_id_dict)

        # clean up - remove empty entries
        result = [channel_item
                  for channel_items in channel_id_dict.values()
                  for channel_item in channel_items
                  if channel_item.get_name()]
        if not result:
            return False, None

        options = {
            provider.CONTENT_TYPE: {
                'content_type': CONTENT.LIST_CONTENT,
                'sub_type': None,
                'category_label': context.localize(
                    'video.description_links.from.x',
                    params.get('item_name') or context.localize('untitled'),
                ),
            },
        }
        return result, options

    def _display_playlists(playlist_ids):
        item_params = {}
        if incognito:
            item_params[INCOGNITO] = incognito
        if addon_id:
            item_params['addon_id'] = addon_id

        playlist_id_dict = {}
        for playlist_id in playlist_ids:
            playlist_item = DirectoryItem(
                name='',
                uri=context.create_uri(
                    (PATHS.PLAYLIST, playlist_id,),
                    item_params,
                ),
                playlist_id=playlist_id,
            )
            playlist_items = playlist_id_dict.setdefault(playlist_id, [])
            playlist_items.append(playlist_item)

        channel_items_dict = {}
        utils.update_playlist_items(provider,
                                    context,
                                    playlist_id_dict,
                                    channel_items_dict=channel_items_dict)
        utils.update_channel_info(provider, context, channel_items_dict)

        # clean up - remove empty entries
        result = [playlist_item
                  for playlist_items in playlist_id_dict.values()
                  for playlist_item in playlist_items
                  if playlist_item.get_name()]
        if not result:
            return False, None

        options = {
            provider.CONTENT_TYPE: {
                'content_type': CONTENT.VIDEO_CONTENT,
                'sub_type': None,
                'category_label': None,
            },
        }
        return result, options

    video_id = params.get(VIDEO_ID)
    if video_id:
        return _extract_urls(video_id)

    channel_ids = params.get(CHANNEL_IDS)
    if channel_ids:
        return _display_channels(channel_ids)

    playlist_ids = params.get(PLAYLIST_IDS)
    if playlist_ids:
        return _display_playlists(playlist_ids)

    logging.error('Missing video_id or playlist_ids for description links')
    return False, None


def _process_saved_playlists(provider, context, client):
    params = context.get_params()

    browse_id = 'FEplaylist_aggregation'
    browse_response_type = 'playlists'
    browse_client = 'tv'
    browse_paths = client.JSON_PATHS['tv_grid']

    own_channel = client.channel_id
    if own_channel:
        own_channel = (own_channel,)

    json_data = client.get_browse_items(
        browse_id=browse_id,
        client=browse_client,
        skip_ids=own_channel,
        response_type=browse_response_type,
        do_auth=True,
        page_token=params.get('page_token'),
        click_tracking=params.get('click_tracking'),
        visitor=params.get('visitor'),
        json_path=browse_paths,
    )
    if not json_data:
        return False, None

    filler = partial(
        client.get_browse_items,
        browse_id=browse_id,
        client=browse_client,
        skip_ids=own_channel,
        response_type=browse_response_type,
        do_auth=True,
        json_path=browse_paths,
    )
    json_data['_pre_filler'] = filler
    json_data['_post_filler'] = filler

    result = v3.response_to_items(
        provider,
        context,
        json_data,
        allow_duplicates=False,
    )
    options = {
        provider.CONTENT_TYPE: {
            'content_type': CONTENT.LIST_CONTENT,
            'sub_type': None,
            'category_label': None,
        },
    }
    return result, options


def _process_my_subscriptions(provider,
                              context,
                              client,
                              filtered=False,
                              feed_type=None,
                              _feed_types=frozenset((
                                      'videos', 'shorts', 'live'
                              ))):
    refresh = context.refresh_requested()

    if feed_type not in _feed_types:
        feed_type = 'videos'

    with context.get_ui().create_progress_dialog(
            heading=context.localize('my_subscriptions.loading'),
            message=context.localize('subscriptions'),
            background=True,
    ) as progress_dialog:
        json_data = client.get_my_subscriptions(
            page_token=context.get_param('page', 1),
            do_filter=filtered,
            feed_type=feed_type,
            refresh=refresh,
            force_cache=(not refresh
                         and refresh is not False
                         and refresh is not None),
            progress_dialog=progress_dialog,
        )
        if not json_data:
            return False, None

        filler = partial(
            client.get_my_subscriptions,
            do_filter=filtered,
            feed_type=feed_type,
            refresh=refresh,
            force_cache=True,
            progress_dialog=progress_dialog,
        )
        json_data['_post_filler'] = filler

        if filtered:
            my_subscriptions_path = PATHS.MY_SUBSCRIPTIONS_FILTERED
        else:
            my_subscriptions_path = PATHS.MY_SUBSCRIPTIONS

        params = context.get_params()
        if params.get(PAGE, 1) == 1 and not params.get(HIDE_FOLDERS):
            v3_response = {
                'kind': 'plugin#pluginListResponse',
                'items': [
                    None
                    if feed_type == 'videos' or params.get(HIDE_VIDEOS) else
                    {
                        'kind': 'plugin#videosFolder',
                        '_params': {
                            'name': context.localize('my_subscriptions'),
                            'uri': context.create_uri(my_subscriptions_path),
                            'image': '{media}/new_uploads.png',
                            'special_sort': 'top',
                        },
                    },
                    None
                    if feed_type == 'shorts' or params.get(HIDE_SHORTS) else
                    {
                        'kind': 'plugin#shortsFolder',
                        '_params': {
                            'name': context.localize('shorts'),
                            'uri': context.create_uri(
                                (my_subscriptions_path, 'shorts')
                            ),
                            'image': '{media}/shorts.png',
                            'special_sort': 'top',
                        },
                    },
                    None
                    if feed_type == 'live' or params.get(HIDE_LIVE) else
                    {
                        'kind': 'plugin#liveFolder',
                        '_params': {
                            'name': context.localize('live'),
                            'uri': context.create_uri(
                                (my_subscriptions_path, 'live')
                            ),
                            'image': '{media}/live.png',
                            'special_sort': 'top',
                        },
                    },
                ],
            }
            result = v3.response_to_items(provider, context, v3_response)
        else:
            result = []

        options = {
            provider.CONTENT_TYPE: {
                'content_type': CONTENT.VIDEO_CONTENT,
                'sub_type': None,
                'category_label': None,
            },
        }
        result.extend(v3.response_to_items(
            provider, context, json_data,
            item_filter={
                'live_folder': True,
                'shorts': True,
            } if feed_type == 'live' else {
                'live_folder': True,
                'shorts': True,
                'vod': True,
            },
        ))
        return result, options


def _process_virtual_list(provider, context, _client, playlist_id=None):
    params = context.get_params()

    playlist_id = playlist_id or params.get(PLAYLIST_ID)
    if not playlist_id:
        return False, None
    playlist_id = playlist_id.upper()
    context.parse_params({
        CHANNEL_ID: 'mine',
        PLAYLIST_ID: playlist_id,
    })

    resource_manager = provider.get_resource_manager(context)
    json_data = resource_manager.get_playlist_items(
        batch_id=(playlist_id, 0),
        page_token=params.get('page_token'),
    )
    if not json_data:
        return False, None

    filler = partial(
        resource_manager.get_playlist_items,
        batch_id=(playlist_id, 0),
    )
    json_data['_pre_filler'] = filler
    json_data['_post_filler'] = filler

    result = v3.response_to_items(
        provider,
        context,
        json_data,
        allow_duplicates=False,
    )
    options = {
        provider.CONTENT_TYPE: {
            'content_type': CONTENT.VIDEO_CONTENT,
            'sub_type': CONTENT.HISTORY if playlist_id == 'HL' else None,
            'category_label': None,
        },
    }
    return result, options


def process(provider, context, re_match=None, category=None, sub_category=None):
    if re_match:
        if category is None:
            category = re_match.group('category')
        if sub_category is None:
            sub_category = re_match.group('sub_category')

    client = provider.get_client(context)

    if category == 'related_videos':
        return _process_related_videos(provider, context, client)

    if category == 'popular_right_now':
        return _process_trending(provider, context, client)

    if category == 'recommendations':
        return _process_recommendations(provider, context, client)

    if category == 'browse_channels':
        return _process_browse_channels(provider, context, client)

    if category.startswith(('my_subscriptions', 'new_uploaded_videos_tv')):
        return _process_my_subscriptions(
            provider,
            context,
            client,
            filtered=category.endswith('_filtered'),
            feed_type=sub_category,
        )

    if category == 'disliked_videos':
        if client.logged_in:
            return _process_disliked_videos(provider, context, client)
        return UriItem(context.create_uri(('sign', 'in')))

    if category == 'live':
        return _process_live_events(
            provider, context, client, event_type='live'
        )

    if category == 'upcoming_live':
        return _process_live_events(
            provider, context, client, event_type='upcoming'
        )

    if category == 'completed_live':
        return _process_live_events(
            provider, context, client, event_type='completed'
        )

    if category == 'description_links':
        return _process_description_links(provider, context)

    if category.endswith('_comments'):
        return _process_comments(provider, context, client)

    if category == 'saved_playlists':
        return _process_saved_playlists(provider, context, client)

    if category == 'playlist':
        return _process_virtual_list(provider, context, client, sub_category)

    raise KodionException('YouTube special category "%s" not found' % category)
