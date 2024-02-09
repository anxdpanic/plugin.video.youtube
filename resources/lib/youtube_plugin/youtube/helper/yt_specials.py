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
from ...kodion.constants import content
from ...kodion.items import DirectoryItem, UriItem
from ...kodion.utils import strip_html_from_text


def _process_related_videos(provider, context):
    context.set_content(content.VIDEO_CONTENT)
    function_cache = context.get_function_cache()

    params = context.get_params()
    video_id = params.get('video_id', '')
    if video_id:
        json_data = function_cache.run(
            provider.get_client(context).get_related_videos,
            function_cache.ONE_HOUR,
            _refresh=params.get('refresh'),
            video_id=video_id,
            page_token=params.get('page_token', ''),
            offset=params.get('offset', 0),
        )
    else:
        json_data = function_cache.run(
            provider.get_client(context).get_related_for_home,
            function_cache.ONE_HOUR,
            _refresh=params.get('refresh'),
            page_token=params.get('page_token', ''),
        )

    if not json_data:
        return False
    return v3.response_to_items(provider, context, json_data)


def _process_parent_comments(provider, context):
    context.set_content(content.LIST_CONTENT)

    video_id = context.get_param('video_id', '')
    if not video_id:
        return []

    json_data = provider.get_client(context).get_parent_comments(
        video_id=video_id, page_token=context.get_param('page_token', '')
    )

    if not json_data:
        return False
    return v3.response_to_items(provider, context, json_data)


def _process_child_comments(provider, context):
    context.set_content(content.LIST_CONTENT)

    parent_id = context.get_param('parent_id', '')
    if not parent_id:
        return []

    json_data = provider.get_client(context).get_child_comments(
        parent_id=parent_id, page_token=context.get_param('page_token', '')
    )

    if not json_data:
        return False
    return v3.response_to_items(provider, context, json_data)


def _process_recommendations(provider, context):
    context.set_content(content.VIDEO_CONTENT)
    params = context.get_params()
    function_cache = context.get_function_cache()

    json_data = function_cache.run(
        provider.get_client(context).get_recommended_for_home,
        function_cache.ONE_HOUR,
        _refresh=params.get('refresh'),
        visitor=params.get('visitor', ''),
        page_token=params.get('page_token', ''),
        click_tracking=params.get('click_tracking', ''),
    )

    if not json_data:
        return False
    return v3.response_to_items(provider, context, json_data)


def _process_trending(provider, context):
    context.set_content(content.VIDEO_CONTENT)

    json_data = provider.get_client(context).get_trending_videos(
        page_token=context.get_param('page_token', '')
    )

    if not json_data:
        return False
    return v3.response_to_items(provider, context, json_data)


def _process_browse_channels(provider, context):
    context.set_content(content.LIST_CONTENT)
    client = provider.get_client(context)

    guide_id = context.get_param('guide_id', '')
    if guide_id:
        json_data = client.get_guide_category(guide_id)
    else:
        function_cache = context.get_function_cache()
        json_data = function_cache.run(client.get_guide_categories,
                                       function_cache.ONE_MONTH)

    if not json_data:
        return False
    return v3.response_to_items(provider, context, json_data)


def _process_disliked_videos(provider, context):
    context.set_content(content.VIDEO_CONTENT)

    json_data = provider.get_client(context).get_disliked_videos(
        page_token=context.get_param('page_token', '')
    )

    if not json_data:
        return False
    return v3.response_to_items(provider, context, json_data)


def _process_live_events(provider, context, event_type='live'):
    def _sort(x):
        return x.get_date()

    context.set_content(content.VIDEO_CONTENT)

    # TODO: cache result
    json_data = provider.get_client(context).get_live_events(
        event_type=event_type,
        page_token=context.get_param('page_token', ''),
        location=context.get_param('location', False),
    )

    if not json_data:
        return False
    return v3.response_to_items(provider, context, json_data, sort=_sort)


def _process_description_links(provider, context):
    params = context.get_params()
    incognito = params.get('incognito', False)
    addon_id = params.get('addon_id', '')

    def _extract_urls(video_id):
        context.set_content(content.VIDEO_CONTENT)
        url_resolver = UrlResolver(context)

        with context.get_ui().create_progress_dialog(
            heading=context.localize('please_wait'), background=False
        ) as progress_dialog:
            resource_manager = provider.get_resource_manager(context)

            video_data = resource_manager.get_videos((video_id,))
            yt_item = video_data[video_id]
            if not yt_item or 'snippet' not in yt_item:
                context.get_ui().on_ok(
                    title=context.localize('video.description.links'),
                    text=context.localize('video.description.links.not_found')
                )
                return False
            snippet = yt_item['snippet']
            description = strip_html_from_text(snippet['description'])

            function_cache = context.get_function_cache()
            urls = function_cache.run(utils.extract_urls,
                                      function_cache.ONE_DAY,
                                      _refresh=params.get('refresh'),
                                      text=description)

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
                '', context.create_uri(('channel', channel_id,), item_params)
            )
            channel_id_dict[channel_id] = channel_item

        channel_item_dict = {}
        utils.update_channel_infos(provider,
                                   context,
                                   channel_id_dict,
                                   channel_items_dict=channel_item_dict)

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
                '', context.create_uri(('playlist', playlist_id,), item_params)
            )
            playlist_id_dict[playlist_id] = playlist_item

        channel_item_dict = {}
        utils.update_playlist_infos(provider,
                                    context,
                                    playlist_id_dict,
                                    channel_items_dict=channel_item_dict)
        utils.update_fanarts(provider, context, channel_item_dict)

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


def _process_saved_playlists_tv(provider, context):
    context.set_content(content.LIST_CONTENT)

    json_data = provider.get_client(context).get_saved_playlists(
        page_token=context.get_param('next_page_token', ''),
        offset=context.get_param('offset', 0)
    )

    if not json_data:
        return False
    return tv.saved_playlists_to_items(provider, context, json_data)


def _process_new_uploaded_videos_tv(provider, context, filtered=False):
    context.set_content(content.VIDEO_CONTENT)

    json_data = provider.get_client(context).get_my_subscriptions(
        page_token=context.get_param('next_page_token', ''),
        offset=context.get_param('offset', 0)
    )

    if not json_data:
        return False
    return tv.my_subscriptions_to_items(provider,
                                        context,
                                        json_data,
                                        do_filter=filtered)


def process(category, provider, context):
    _ = provider.get_client(context)  # required for provider.is_logged_in()
    if (not provider.is_logged_in()
            and category in ('new_uploaded_videos_tv',
                             'new_uploaded_videos_tv_filtered',
                             'disliked_videos')):
        return UriItem(context.create_uri(('sign', 'in')))

    if category == 'related_videos':
        return _process_related_videos(provider, context)
    if category == 'popular_right_now':
        return _process_trending(provider, context)
    if category == 'recommendations':
        return _process_recommendations(provider, context)
    if category == 'browse_channels':
        return _process_browse_channels(provider, context)
    if category == 'new_uploaded_videos_tv':
        return _process_new_uploaded_videos_tv(provider, context)
    if category == 'new_uploaded_videos_tv_filtered':
        return _process_new_uploaded_videos_tv(provider, context, filtered=True)
    if category == 'disliked_videos':
        return _process_disliked_videos(provider, context)
    if category == 'live':
        return _process_live_events(provider, context)
    if category == 'upcoming_live':
        return _process_live_events(provider, context, event_type='upcoming')
    if category == 'completed_live':
        return _process_live_events(provider, context, event_type='completed')
    if category == 'description_links':
        return _process_description_links(provider, context)
    if category == 'parent_comments':
        return _process_parent_comments(provider, context)
    if category == 'child_comments':
        return _process_child_comments(provider, context)
    if category == 'saved_playlists':
        return _process_saved_playlists_tv(provider, context)
    raise KodionException("YouTube special category '%s' not found" % category)
