# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from . import UrlResolver, UrlToItemConverter, tv, utils, v3
from ...kodion import KodionException
from ...kodion.constants import CONTENT, PATHS
from ...kodion.items import DirectoryItem, UriItem
from ...kodion.utils import strip_html_from_text


def _process_related_videos(provider, context, client):
    context.set_content(CONTENT.VIDEO_CONTENT)
    function_cache = context.get_function_cache()

    params = context.get_params()
    video_id = params.get('video_id')
    refresh = params.get('refresh', 0) > 0
    if video_id:
        json_data = function_cache.run(
            client.get_related_videos,
            function_cache.ONE_HOUR,
            _refresh=refresh,
            video_id=video_id,
            page_token=params.get('page_token', ''),
            offset=params.get('offset', 0),
        )
    else:
        json_data = function_cache.run(
            client.get_related_for_home,
            function_cache.ONE_HOUR,
            _refresh=refresh,
            page_token=params.get('page_token', ''),
            refresh=refresh,
        )

    if not json_data:
        return False
    return v3.response_to_items(provider, context, json_data)


def _process_comments(provider, context, client):
    params = context.get_params()
    video_id = params.get('video_id')
    parent_id = params.get('parent_id')
    if not video_id and not parent_id:
        return False

    context.set_content(CONTENT.LIST_CONTENT,
                        sub_type='comments',
                        category_label=params.get('item_name', video_id))

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
        return False
    return v3.response_to_items(provider, context, json_data)


def _process_recommendations(provider, context, client):
    context.set_content(CONTENT.VIDEO_CONTENT)
    params = context.get_params()
    function_cache = context.get_function_cache()

    json_data = function_cache.run(
        client.get_recommended_for_home,
        function_cache.ONE_HOUR,
        _refresh=params.get('refresh', 0) > 0,
        visitor=params.get('visitor'),
        page_token=params.get('page_token'),
        click_tracking=params.get('click_tracking'),
        offset=params.get('offset'),
    )

    if json_data:
        def filler(json_data, remaining):
            page_token = json_data.get('nextPageToken')
            if not page_token:
                return None

            json_data = function_cache.run(
                client.get_recommended_for_home,
                function_cache.ONE_HOUR,
                _refresh=params.get('refresh', 0) > 0,
                visitor=json_data.get('visitorData'),
                page_token=page_token,
                click_tracking=json_data.get('clickTracking'),
                remaining=remaining,
            )
            json_data['_filler'] = filler
            return json_data

        json_data['_filler'] = filler
        return v3.response_to_items(provider, context, json_data)
    return False


def _process_trending(provider, context, client):
    context.set_content(CONTENT.VIDEO_CONTENT)

    json_data = client.get_trending_videos(
        page_token=context.get_param('page_token')
    )

    if json_data:
        def filler(json_data, _remaining):
            page_token = json_data.get('nextPageToken')
            if not page_token:
                return None

            json_data = client.get_trending_videos(
                page_token=page_token,
            )
            json_data['_filler'] = filler
            return json_data

        json_data['_filler'] = filler
        return v3.response_to_items(provider, context, json_data)
    return False


def _process_browse_channels(provider, context, client):
    context.set_content(CONTENT.LIST_CONTENT)

    params = context.get_params()
    guide_id = params.get('guide_id')
    if guide_id:
        json_data = client.get_guide_category(guide_id)
    else:
        function_cache = context.get_function_cache()
        json_data = function_cache.run(
            client.get_guide_categories,
            function_cache.ONE_MONTH,
            _refresh=params.get('refresh', 0) > 0,
        )

    if not json_data:
        return False
    return v3.response_to_items(provider, context, json_data)


def _process_disliked_videos(provider, context, client):
    context.set_content(CONTENT.VIDEO_CONTENT)

    json_data = client.get_disliked_videos(
        page_token=context.get_param('page_token', '')
    )

    if not json_data:
        return False
    return v3.response_to_items(provider, context, json_data)


def _process_live_events(provider, context, client, event_type='live'):
    context.set_content(CONTENT.VIDEO_CONTENT)

    # TODO: cache result
    json_data = client.get_live_events(
        event_type=event_type,
        order='date' if event_type == 'upcoming' else 'viewCount',
        page_token=context.get_param('page_token', ''),
        location=context.get_param('location', False),
        after={'days': 3} if event_type == 'completed' else None,
    )

    if not json_data:
        return False
    return v3.response_to_items(provider, context, json_data)


def _process_description_links(provider, context):
    params = context.get_params()
    incognito = params.get('incognito', False)
    addon_id = params.get('addon_id', '')

    def _extract_urls(video_id):
        context.set_content(CONTENT.VIDEO_CONTENT)
        url_resolver = UrlResolver(context)

        with context.get_ui().create_progress_dialog(
                heading=context.localize('please_wait'), background=False
        ) as progress_dialog:
            resource_manager = provider.get_resource_manager(context)

            video_data = resource_manager.get_videos((video_id,))
            yt_item = video_data[video_id] if video_data else None
            if not yt_item or 'snippet' not in yt_item:
                context.get_ui().on_ok(
                    title=context.localize('video.description.links'),
                    text=context.localize('video.description.links.not_found')
                )
                return False
            snippet = yt_item['snippet']
            description = strip_html_from_text(snippet['description'])

            function_cache = context.get_function_cache()
            urls = function_cache.run(
                utils.extract_urls,
                function_cache.ONE_DAY,
                _refresh=params.get('refresh', 0) > 0,
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

        if result:
            return result
        context.get_ui().on_ok(
            title=context.localize('video.description.links'),
            text=context.localize('video.description.links.not_found')
        )
        return False

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
        return [channel_item
                for channel_item in channel_id_dict.values()
                if channel_item.get_name()]

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
        return [playlist_item
                for playlist_item in playlist_id_dict.values()
                if playlist_item.get_name()]

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
    return False


def _process_saved_playlists_tv(provider, context, client):
    context.set_content(CONTENT.LIST_CONTENT)

    json_data = client.get_saved_playlists(
        page_token=context.get_param('next_page_token', 0),
        offset=context.get_param('offset', 0)
    )

    if not json_data:
        return False
    return tv.saved_playlists_to_items(provider, context, json_data)


def _process_my_subscriptions(provider, context, client, filtered=False):
    context.set_content(CONTENT.VIDEO_CONTENT)

    logged_in = provider.is_logged_in()
    params = context.get_params()
    refresh = params.get('refresh', 0) > 0

    with context.get_ui().create_progress_dialog(
            heading=context.localize('my_subscriptions.loading'),
            message=context.localize('subscriptions'),
            background=True,
    ) as progress_dialog:
        json_data = client.get_my_subscriptions(
            page_token=params.get('page', 1),
            logged_in=logged_in,
            do_filter=filtered,
            refresh=refresh,
            progress_dialog=progress_dialog,
        )

        if json_data:
            def filler(json_data, _remaining):
                page_token = json_data.get('nextPageToken')
                if not page_token:
                    return None

                json_data = client.get_my_subscriptions(
                    page_token=json_data.get('nextPageToken'),
                    logged_in=logged_in,
                    do_filter=filtered,
                    refresh=refresh,
                    use_cache=True,
                    progress_dialog=progress_dialog,
                )
                json_data['_filler'] = filler
                return json_data

            json_data['_filler'] = filler
            return v3.response_to_items(provider, context, json_data)
    return False


def process(provider, context, re_match=None, category=None):
    if re_match and category is None:
        category = re_match.group('category')

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
            provider, context, client, filtered=category.endswith('_filtered'),
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
