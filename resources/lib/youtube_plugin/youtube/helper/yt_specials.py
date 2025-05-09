# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from functools import partial

from . import UrlResolver, UrlToItemConverter, tv, utils, v3
from ...kodion import KodionException
from ...kodion.constants import CONTENT, PATHS
from ...kodion.items import DirectoryItem, UriItem
from ...kodion.utils import strip_html_from_text


def _process_related_videos(provider, context, client):
    function_cache = context.get_function_cache()
    refresh = context.refresh_requested()
    params = context.get_params()

    video_id = params.get('video_id')
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
    else:
        json_data = function_cache.run(
            client.get_related_for_home,
            function_cache.ONE_HOUR,
            _refresh=refresh,
        )
        if not json_data:
            return False, None

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


def _process_comments(provider, context, client):
    params = context.get_params()
    video_id = params.get('video_id')
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
            'sub_type': 'comments',
            'category_label': params.get('item_name', video_id),
        },
    }
    return result, options


def _process_recommendations(provider, context, client):
    function_cache = context.get_function_cache()
    refresh = context.refresh_requested()
    params = context.get_params()
    # source = client.get_recommended_for_home_tv
    source = client.get_recommended_for_home_vr

    json_data = function_cache.run(
        source,
        function_cache.ONE_HOUR,
        _refresh=refresh,
        visitor=params.get('visitor'),
        page_token=params.get('page_token'),
        click_tracking=params.get('click_tracking'),
    )
    if not json_data:
        return False, None

    filler = partial(
        function_cache.run,
        source,
        function_cache.ONE_HOUR,
        _refresh=refresh,
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
    function_cache = context.get_function_cache()
    refresh = context.refresh_requested()

    json_data = function_cache.run(
        client.get_trending_videos,
        function_cache.ONE_HOUR,
        _refresh=refresh,
        page_token=context.get_param('page_token'),
    )
    if not json_data:
        return False, None

    filler = partial(
        function_cache.run,
        client.get_trending_videos,
        function_cache.ONE_HOUR,
        _refresh=refresh,
    )
    json_data['_post_filler'] = filler

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
    json_data = client.get_live_events(
        event_type=event_type,
        order='date' if event_type == 'upcoming' else 'viewCount',
        page_token=context.get_param('page_token', ''),
        location=context.get_param('location', False),
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
    incognito = params.get('incognito', False)
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
                    context.log_debug('Resolving urls aborted')
                    break

            url_to_item_converter = UrlToItemConverter()
            url_to_item_converter.add_urls(res_urls, context)
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
            item_params['incognito'] = incognito
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
            channel_id_dict[channel_id] = channel_item

        utils.update_channel_items(provider, context, channel_id_dict)

        # clean up - remove empty entries
        result = [channel_item
                  for channel_item in channel_id_dict.values()
                  if channel_item.get_name()]
        if not result:
            return False, None

        options = {
            provider.CONTENT_TYPE: {
                'content_type': CONTENT.LIST_CONTENT,
                'sub_type': None,
                'category_label': None,
            },
        }
        return result, options

    def _display_playlists(playlist_ids):
        item_params = {}
        if incognito:
            item_params['incognito'] = incognito
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
            playlist_id_dict[playlist_id] = playlist_item

        channel_items_dict = {}
        utils.update_playlist_items(provider,
                                    context,
                                    playlist_id_dict,
                                    channel_items_dict=channel_items_dict)
        utils.update_channel_info(provider, context, channel_items_dict)

        # clean up - remove empty entries
        result = [playlist_item
                  for playlist_item in playlist_id_dict.values()
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

    video_id = params.get('video_id', '')
    if video_id:
        return _extract_urls(video_id)

    channel_ids = params.get('channel_ids', [])
    if channel_ids:
        return _display_channels(channel_ids)

    playlist_ids = params.get('playlist_ids', [])
    if playlist_ids:
        return _display_playlists(playlist_ids)

    context.log_error('Missing video_id or playlist_ids for description links')
    return False, None


def _process_saved_playlists_tv(provider, context, client):
    json_data = client.get_saved_playlists(
        page_token=context.get_param('next_page_token', 0),
        offset=context.get_param('offset', 0)
    )
    if not json_data:
        return False, None

    result = tv.saved_playlists_to_items(provider, context, json_data)
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
                              _feed_types={'videos', 'shorts', 'live'}):
    logged_in = provider.is_logged_in()
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
            logged_in=logged_in,
            do_filter=filtered,
            feed_type=feed_type,
            refresh=refresh,
            progress_dialog=progress_dialog,
        )
        if not json_data:
            return False, None

        filler = partial(
            client.get_my_subscriptions,
            logged_in=logged_in,
            do_filter=filtered,
            feed_type=feed_type,
            refresh=refresh,
            use_cache=True,
            progress_dialog=progress_dialog,
        )
        json_data['_post_filler'] = filler

        if filtered:
            my_subscriptions_path = PATHS.MY_SUBSCRIPTIONS_FILTERED
        else:
            my_subscriptions_path = PATHS.MY_SUBSCRIPTIONS

        params = context.get_params()
        if params.get('page', 1) == 1 and not params.get('hide_folders'):
            result = [
                DirectoryItem(
                    context.localize('my_subscriptions'),
                    context.create_uri(my_subscriptions_path),
                    image='{media}/new_uploads.png',
                )
                if feed_type != 'videos' and not params.get('hide_videos') else
                None,
                DirectoryItem(
                    context.localize('shorts'),
                    context.create_uri((my_subscriptions_path, 'shorts')),
                    image='{media}/shorts.png',
                )
                if feed_type != 'shorts' and not params.get('hide_shorts') else
                None,
                DirectoryItem(
                    context.localize('live'),
                    context.create_uri((my_subscriptions_path, 'live')),
                    image='{media}/live.png',
                )
                if feed_type != 'live' and not params.get('hide_live') else
                None,
            ]
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
                'live': False,
                'shorts': True,
                'upcoming_live': False,
            } if feed_type == 'shorts' else {
                'live': False,
                'shorts': True,
                'upcoming_live': False,
            }
        ))
        return result, options


def process(provider, context, re_match=None, category=None, sub_category=None):
    if re_match:
        if category is None:
            category = re_match.group('category')
        if sub_category is None:
            sub_category = re_match.group('sub_category')

    # required for provider.is_logged_in()
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
        if provider.is_logged_in():
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
        return _process_saved_playlists_tv(provider, context, client)

    raise KodionException('YouTube special category "%s" not found' % category)
