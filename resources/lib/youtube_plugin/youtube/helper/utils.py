# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import time
from datetime import date as dt_date, datetime as dt_datetime
from math import log10
from operator import (
    contains as op_contains,
    eq as op_eq,
    ge as op_ge,
    gt as op_gt,
    le as op_le,
    lt as op_lt,
)
from re import (
    compile as re_compile,
    error as re_error,
    search as re_search,
)

from ...kodion import logging
from ...kodion.compatibility import string_type, unquote, urlsplit
from ...kodion.constants import (
    CHANNEL_ID,
    CONTENT,
    FANART_TYPE,
    PATHS,
    PLAYLIST_ID,
)
from ...kodion.items import (
    AudioItem,
    CommandItem,
    DirectoryItem,
    MediaItem,
    menu_items,
)
from ...kodion.utils.convert_format import friendly_number, strip_html_from_text
from ...kodion.utils.datetime import (
    get_scheduled_start,
    parse_to_dt,
    utc_to_local,
)


# RegExp used to match plugin playlist paths of the form:
# /channel/[CHANNEL_ID]/playlist/[PLAYLIST_ID]/
# /playlist/[PLAYLIST_ID]/
__RE_PLAYLIST = re_compile(
    r'^(/channel/(?P<channel_id>[^/]+))/playlist/(?P<playlist_id>[^/]+)/?$'
)

__RE_SEASON_EPISODE = re_compile(
    r'\b(?:Season\s*|S)(\d+)|(?:\b(?:Part|Ep.|Episode)\s*|#|E)(\d+)'
)

__RE_URL = re_compile(r'(https?://\S+)')


def extract_urls(text):
    return __RE_URL.findall(text)


def get_thumb_timestamp(minutes=15):
    seconds = minutes * 60
    return str(time.mktime(time.gmtime(
        seconds * (round(time.time() / seconds))
    )))


def make_comment_item(context, snippet, uri, reply_count=0):
    localize = context.localize
    settings = context.get_settings()
    ui = context.get_ui()

    author = snippet.get('authorDisplayName')
    if not author:
        author = urlsplit(snippet.get('authorChannelUrl', ''))
        author = unquote(author.path.rstrip('/').split('/')[-1])
    author_id = snippet.get('authorChannelId', {}).get('value', '')
    author_image = snippet.get('authorProfileImageUrl')
    if author_image:
        author_image = author_image.replace('=s48', '=s160')
    else:
        author_image = None
    body = strip_html_from_text(snippet['textOriginal'])

    label_props = []
    plot_props = []

    like_count = snippet['likeCount']
    if like_count:
        like_count, likes_value = friendly_number(like_count, as_str=False)
        color = settings.get_label_color('likeCount')
        label_likes = ui.color(color, ui.bold(like_count))
        plot_likes = ui.color(color, ui.bold(' '.join((
            like_count, localize('video.comments.likes')
        ))))
        label_props.append(label_likes)
        plot_props.append(plot_likes)

    if reply_count:
        reply_count, replies_value = friendly_number(reply_count, as_str=False)
        color = settings.get_label_color('commentCount')
        label_replies = ui.color(color, ui.bold(reply_count))
        plot_replies = ui.color(color, ui.bold(' '.join((
            reply_count, localize('video.comments.replies')
        ))))
        label_props.append(label_replies)
        plot_props.append(plot_replies)
    else:
        replies_value = 0

    published_at = snippet['publishedAt']
    updated_at = snippet['updatedAt']
    edited = published_at != updated_at
    if edited:
        label_props.append('*')
        plot_props.append(localize('video.comments.edited'))

    label = body.replace('\n', ' ')[:140]
    label_stats = ' | '.join(label_props)
    plot_stats = ' | '.join(plot_props)

    # Format the plot of the comment item.
    plot = ''.join((
        ui.bold(author, cr_after=1),
        ui.new_line(plot_stats, cr_after=1) if plot_stats else '',
        ui.new_line(body, cr_after=1) if body else ''
    ))

    datetime = parse_to_dt(published_at)
    local_datetime = utc_to_local(datetime)

    if uri:
        comment_item = DirectoryItem(
            label,
            uri,
            image=author_image,
            plot=plot,
            category_label=' - '.join(
                (author, context.format_date_short(local_datetime))
            ),
            special_sort=False,
        )
    else:
        comment_item = CommandItem(
            label,
            'Action(Info)',
            context,
            image=author_image,
            plot=plot,
        )

    comment_item.set_count(replies_value)

    comment_item.set_short_details(label_stats)
    comment_item.set_production_code(label_stats)

    comment_item.channel_id = author_id
    comment_item.add_artist(ui.bold(author))
    comment_item.add_cast(author,
                          role=localize('author'),
                          thumbnail=author_image)

    comment_item.set_added_utc(datetime)
    comment_item.set_dateadded_from_datetime(local_datetime)

    if edited:
        datetime = parse_to_dt(updated_at)
        local_datetime = utc_to_local(datetime)
    comment_item.set_date_from_datetime(local_datetime)

    return comment_item


def update_channel_items(provider, context, channel_id_dict,
                         subscription_id_dict=None,
                         channel_items_dict=None,
                         data=None):
    if not channel_id_dict and not data and not channel_items_dict:
        return

    channel_ids = list(channel_id_dict)
    if channel_ids and not data:
        resource_manager = provider.get_resource_manager(context)
        data = resource_manager.get_channels(channel_ids)

    if not data:
        if channel_items_dict:
            update_channel_info(provider,
                                context,
                                channel_items_dict=channel_items_dict)
        return

    if subscription_id_dict is None:
        subscription_id_dict = {}

    client = provider.get_client(context)
    logged_in = client.logged_in

    settings = context.get_settings()
    show_details = settings.show_detailed_description()

    localize = context.localize
    untitled = localize('untitled')

    path = context.get_path()
    ui = context.get_ui()

    if path.startswith(PATHS.SUBSCRIPTIONS):
        in_bookmarks_list = False
        in_subscription_list = True
    elif path.startswith(PATHS.BOOKMARKS):
        in_bookmarks_list = True
        in_subscription_list = False
    else:
        in_bookmarks_list = False
        in_subscription_list = False

    filters_set = None
    if in_bookmarks_list or in_subscription_list:
        if settings.subscriptions_filter_enabled():
            filter_string, filters_set, custom_filters = channel_filter_split(
                settings.subscriptions_filter()
            )

    fanart_type = context.get_param(FANART_TYPE)
    if fanart_type is None:
        fanart_type = settings.fanart_selection()
    thumb_size = settings.get_thumbnail_size()
    thumb_fanart = (
        settings.get_thumbnail_size(settings.THUMB_SIZE_BEST)
        if fanart_type == settings.FANART_THUMBNAIL else
        False
    )

    cxm_unsubscribe_from_channel = menu_items.channel_unsubscribe_from(
        context,
        subscription_id=menu_items.SUBSCRIPTION_ID_INFOLABEL,
    )
    cxm_subscribe_to_channel = (
        menu_items.channel_subscribe_to(context)
        if logged_in and not in_subscription_list else
        None
    )
    cxm_filter_remove = menu_items.my_subscriptions_filter_remove(context)
    cxm_filter_add = menu_items.my_subscriptions_filter_add(context)
    cxm_bookmark_channel = (
        None
        if in_bookmarks_list else
        menu_items.bookmark_add_channel(context)
    )

    for channel_id, yt_item in data.items():
        if not yt_item or 'snippet' not in yt_item:
            continue

        channel_items = channel_id_dict.get(channel_id)
        if channel_items:
            channel_item = channel_items[-1]
        else:
            continue

        snippet = yt_item['snippet']

        label_stats = []
        stats = []
        if 'statistics' in yt_item:
            for stat, value in yt_item['statistics'].items():
                label = context.LOCAL_MAP.get('stats.' + stat)
                if not label:
                    continue

                str_value, value = friendly_number(value, as_str=False)
                if not value:
                    continue

                color = settings.get_label_color(stat)
                label = localize(label)
                if value == 1:
                    label = label.rstrip('s')

                label_stats.append(ui.color(color, str_value))
                stats.append(ui.color(color, ui.bold(' '.join((
                    str_value, label
                )))))

            label_stats = ' | '.join(label_stats)
            stats = ' | '.join(stats)

        # Used for label2, but is poorly supported in skins
        channel_item.set_short_details(label_stats)
        # Hack to force a custom label mask containing production code,
        # activated on sort order selection, to display details
        # Refer XbmcContext.apply_content for usage
        channel_item.set_production_code(label_stats)

        # channel name and title
        localised_info = snippet.get('localized') or {}
        channel_handle = snippet.get('customUrl')
        channel_name = (localised_info.get('title')
                        or snippet.get('title')
                        or untitled)
        channel_item.set_name(channel_name)
        channel_item.add_artist(channel_handle or channel_name)

        # plot
        description = strip_html_from_text(localised_info.get('description')
                                           or snippet.get('description')
                                           or '')
        if show_details:
            description = ''.join((
                ui.bold(channel_name, cr_after=1),
                ui.new_line(stats, cr_after=1) if stats else '',
                ui.new_line(description, cr_after=1) if description else '',
                ui.new_line('--------', cr_after=1),
                'https://www.youtube.com/',
                channel_handle if channel_handle else
                channel_id if channel_id.startswith('@') else
                'channel/' + channel_id,
            ))
        channel_item.set_plot(description)

        # date time
        published_at = snippet.get('publishedAt')
        if published_at:
            datetime = parse_to_dt(published_at)
            channel_item.set_added_utc(datetime)
            local_datetime = utc_to_local(datetime)
            channel_item.set_date_from_datetime(local_datetime)

        # try to find a better resolution for the image
        image = get_thumbnail(thumb_size, snippet.get('thumbnails'))
        channel_item.set_image(image)

        # try to find a better resolution for the fanart
        if thumb_fanart:
            fanart = get_thumbnail(thumb_fanart, snippet.get('thumbnails'))
            channel_item.set_fanart(fanart)

        subscription_id = subscription_id_dict.get(channel_id, '')
        if subscription_id:
            channel_item.subscription_id = subscription_id
            context_menu = [
                cxm_unsubscribe_from_channel,
                cxm_bookmark_channel,
            ]
        else:
            context_menu = [
                cxm_subscribe_to_channel,
                cxm_bookmark_channel,
            ]

        # add/remove from filter list
        if filters_set is not None:
            context_menu.append(
                cxm_filter_remove
                if client.channel_match(channel_id, filters_set) else
                cxm_filter_add
            )

        update_duplicate_items(channel_item,
                               channel_items,
                               channel_id,
                               channel_items_dict,
                               context_menu)

    if channel_items_dict:
        update_channel_info(provider,
                            context,
                            channel_items_dict=channel_items_dict,
                            channel_data=data)


def update_playlist_items(provider, context, playlist_id_dict,
                          channel_items_dict=None,
                          data=None):
    if not playlist_id_dict and not data:
        return

    playlist_ids = list(playlist_id_dict)
    if playlist_ids and not data:
        resource_manager = provider.get_resource_manager(context)
        data = resource_manager.get_playlists(playlist_ids)

    if not data:
        return

    access_manager = context.get_access_manager()
    logged_in = provider.get_client(context).logged_in
    if logged_in:
        history_id = access_manager.get_watch_history_id()
        watch_later_id = access_manager.get_watch_later_id()
    else:
        history_id = ''
        watch_later_id = ''

    settings = context.get_settings()
    show_details = settings.show_detailed_description()
    item_count_color = settings.get_label_color('itemCount')

    params = context.get_params()
    fanart_type = params.get(FANART_TYPE)
    if fanart_type is None:
        fanart_type = settings.fanart_selection()
    thumb_size = settings.get_thumbnail_size()
    thumb_fanart = (
        settings.get_thumbnail_size(settings.THUMB_SIZE_BEST)
        if fanart_type == settings.FANART_THUMBNAIL else
        False
    )

    localize = context.localize
    episode_count_label = localize('stats.itemCount')
    video_count_label = localize('stats.videoCount')
    podcast_label = context.localize('playlist.podcast')
    untitled = localize('untitled')

    path = context.get_path()
    ui = context.get_ui()

    in_bookmarks_list = False
    in_my_playlists = False
    in_saved_playlists = False

    # if the path directs to a playlist of our own, set channel id to 'mine'
    if path.startswith(PATHS.MY_PLAYLISTS):
        in_my_playlists = True
    elif path.startswith(PATHS.BOOKMARKS):
        in_bookmarks_list = True
    elif path.startswith(PATHS.SAVED_PLAYLISTS):
        in_saved_playlists = True

    cxm_playlist_delete = menu_items.playlist_delete(context)
    cxm_playlist_rename = menu_items.playlist_rename(context)
    cxm_watch_later_unassign = menu_items.watch_later_list_unassign(context)
    cxm_watch_later_assign = menu_items.watch_later_list_assign(context)
    cxm_history_list_unassign = menu_items.history_list_unassign(context)
    cxm_history_list_assign = menu_items.history_list_assign(context)
    cxm_separator = menu_items.separator()
    cxm_play_playlist = menu_items.playlist_play(context)
    cxm_play_recently_added = menu_items.playlist_play_recently_added(context)
    cxm_view_playlist = menu_items.playlist_view(context)
    cxm_play_shuffled_playlist = menu_items.playlist_shuffle(context)
    cxm_refresh_listing = menu_items.refresh_listing(context, path, params)
    cxm_remove_saved_playlist = menu_items.playlist_remove_from_library(context)
    cxm_save_playlist = (
        menu_items.playlist_save_to_library(context)
        if logged_in and not (in_my_playlists or in_saved_playlists) else
        None
    )
    cxm_go_to_channel = (
        menu_items.channel_go_to(context)
        if not in_my_playlists else
        None
    )
    cxm_subscribe_to_channel = (
        menu_items.channel_subscribe_to(context)
        if logged_in and not in_my_playlists else
        None
    )
    cxm_bookmark_channel = (
        menu_items.bookmark_add_channel(context)
        if not in_my_playlists else
        None
    )

    for playlist_id, yt_item in data.items():
        if not yt_item or 'snippet' not in yt_item:
            continue

        playlist_items = playlist_id_dict.get(playlist_id)
        if playlist_items:
            playlist_item = playlist_items[-1]
        else:
            continue

        item_count_str, item_count = friendly_number(
            yt_item.get('contentDetails', {}).get('itemCount', 0),
            as_str=False,
        )
        if not item_count and playlist_id.startswith('UU'):
            continue

        snippet = yt_item['snippet']

        playlist_item.available = True

        is_podcast = yt_item.get('status', {}).get('podcastStatus') == 'enabled'
        count_label = episode_count_label if is_podcast else video_count_label
        label_details = ' | '.join([item for item in (
            ui.bold('((○))') if is_podcast else '',
            ui.color(item_count_color, item_count_str),
        ) if item])

        # Used for label2, but is poorly supported in skins
        playlist_item.set_short_details(label_details)
        # Hack to force a custom label mask containing production code,
        # activated on sort order selection, to display details
        # Refer XbmcContext.apply_content for usage
        playlist_item.set_production_code(label_details)

        # title
        localised_info = snippet.get('localized') or {}
        title = localised_info.get('title') or snippet.get('title') or untitled
        playlist_item.set_name(title)

        # channel name
        channel_name = snippet.get('channelTitle') or untitled
        playlist_item.add_artist(channel_name)

        # plot with channel name, podcast status and item count
        description = strip_html_from_text(localised_info.get('description')
                                           or snippet.get('description')
                                           or '')
        if show_details:
            description = ''.join((
                ui.bold(channel_name, cr_after=1),
                ui.bold(podcast_label) if is_podcast else '',
                ' | ' if is_podcast else '',
                ui.color(
                    item_count_color,
                    ui.bold(' '.join((item_count_str,
                                      count_label.rstrip('s')
                                      if item_count == 1 else
                                      count_label))),
                    cr_after=1,
                ),
                ui.new_line(description, cr_after=1) if description else '',
                ui.new_line('--------', cr_after=1),
                'https://youtube.com/playlist?list=' + playlist_id,
            ))
        playlist_item.set_plot(description)

        # date time
        published_at = snippet.get('publishedAt')
        if published_at:
            datetime = parse_to_dt(published_at)
            playlist_item.set_added_utc(datetime)
            local_datetime = utc_to_local(datetime)
            playlist_item.set_date_from_datetime(local_datetime)

        # try to find a better resolution for the image
        image = get_thumbnail(thumb_size, snippet.get('thumbnails'))
        playlist_item.set_image(image)

        # try to find a better resolution for the fanart
        if thumb_fanart:
            fanart = get_thumbnail(thumb_fanart, snippet.get('thumbnails'))
            playlist_item.set_fanart(fanart)

        # update channel mapping
        channel_id = snippet.get('channelId', '')
        playlist_item.channel_id = channel_id

        if in_my_playlists:
            context_menu = [
                # remove my playlist
                cxm_playlist_delete,
                # rename playlist
                cxm_playlist_rename,
                # remove as my custom watch later playlist
                cxm_watch_later_unassign
                if playlist_id == watch_later_id else
                # set as my custom watch later playlist
                cxm_watch_later_assign,
                # remove as custom history playlist
                cxm_history_list_unassign
                if playlist_id == history_id else
                # set as custom history playlist
                cxm_history_list_assign,
                cxm_separator,
            ]
        elif in_saved_playlists:
            context_menu = [
                cxm_remove_saved_playlist,
                cxm_separator,
            ]
        else:
            context_menu = []

        context_menu.extend((
            # play all videos of the playlist
            cxm_play_playlist,
            cxm_play_recently_added,
            cxm_view_playlist,
            cxm_play_shuffled_playlist,
            cxm_refresh_listing,
            cxm_separator,
            cxm_save_playlist,
            menu_items.bookmark_add(
                context, playlist_item
            )
            if not (in_my_playlists or in_bookmarks_list) else
            None,
            cxm_go_to_channel,
            # subscribe to the channel via the playlist item
            cxm_subscribe_to_channel,
            # bookmark channel of the playlist
            cxm_bookmark_channel,
        ))

        update_duplicate_items(playlist_item,
                               playlist_items,
                               channel_id,
                               channel_items_dict,
                               context_menu)


def update_video_items(provider, context, video_id_dict,
                       channel_items_dict=None,
                       live_details=True,
                       item_filter=None,
                       data=None,
                       yt_items_dict=None):
    if not video_id_dict and not data:
        return

    video_ids = list(video_id_dict)
    if video_ids and not data:
        resource_manager = provider.get_resource_manager(context)
        data = resource_manager.get_videos(video_ids,
                                           live_details=live_details,
                                           suppress_errors=True,
                                           yt_items_dict=yt_items_dict)

    if not data:
        return

    logged_in = provider.get_client(context).logged_in
    if logged_in:
        watch_later_id = context.get_access_manager().get_watch_later_id()
    else:
        watch_later_id = ''

    settings = context.get_settings()
    alternate_player = settings.support_alternative_player()
    default_web_urls = settings.default_player_web_urls()
    ask_quality = not default_web_urls and settings.ask_for_video_quality()
    audio_only = settings.audio_only()
    show_details = settings.show_detailed_description()
    shorts_duration = settings.shorts_duration()
    subtitles_prompt = settings.get_subtitle_selection() == 1
    use_play_data = settings.use_local_history()

    params = context.get_params()
    fanart_type = params.get(FANART_TYPE)
    if fanart_type is None:
        fanart_type = settings.fanart_selection()
    thumb_size = settings.get_thumbnail_size()
    get_better_thumbs = (settings.get_int(settings.THUMB_SIZE)
                         == settings.THUMB_SIZE_BEST)
    thumb_fanart = (
        settings.get_thumbnail_size(settings.THUMB_SIZE_BEST)
        if fanart_type == settings.FANART_THUMBNAIL else
        False
    )
    thumb_stamp = get_thumb_timestamp()

    localize = context.localize
    untitled = localize('untitled')

    path = context.get_path()
    ui = context.get_ui()

    playlist_id = None
    playlist_channel_id = None

    in_bookmarks_list = False
    in_my_subscriptions_list = False
    in_watch_history_list = False
    in_watch_later_list = False

    if path.startswith(PATHS.MY_SUBSCRIPTIONS):
        in_my_subscriptions_list = True
    elif path.startswith(PATHS.WATCH_LATER):
        in_watch_later_list = True
    elif path.startswith(PATHS.BOOKMARKS):
        in_bookmarks_list = True
    elif path.startswith(PATHS.VIRTUAL_PLAYLIST):
        playlist_id = params.get(PLAYLIST_ID)
        playlist_channel_id = 'mine'
        if playlist_id:
            playlist_id_upper = playlist_id.upper()
            if playlist_id_upper == 'WL':
                in_watch_later_list = True
            elif playlist_id_upper == 'HL':
                in_watch_history_list = True
    else:
        playlist_match = __RE_PLAYLIST.match(path)
        if playlist_match:
            playlist_id = playlist_match.group(PLAYLIST_ID)
            playlist_channel_id = playlist_match.group(CHANNEL_ID)

    cxm_remove_from_playlist = menu_items.playlist_remove_from(
        context,
        playlist_id=playlist_id,
    )
    cxm_separator = menu_items.separator()
    cxm_play = menu_items.media_play(context)
    cxm_play_with_subtitles = (
        None
        if subtitles_prompt else
        menu_items.media_play_with_subtitles(context)
    )
    cxm_play_audio_only = (
        None
        if audio_only else
        menu_items.media_play_audio_only(context)
    )
    cxm_play_ask_for_quality = (
        None
        if ask_quality else
        menu_items.media_play_ask_for_quality(context)
    )
    cxm_play_timeshift = menu_items.media_play_timeshift(context)
    cxm_play_using = (
        menu_items.media_play_using(context)
        if alternate_player else
        None
    )
    cxm_play_from = menu_items.playlist_play_from(context, playlist_id)
    cxm_queue = menu_items.media_queue(context)
    cxm_watch_later = menu_items.playlist_add_to(
        context,
        watch_later_id,
        'watch_later',
    )
    cxm_go_to_channel = menu_items.channel_go_to(context)
    cxm_unsubscribe_from_channel = menu_items.channel_unsubscribe_from(
        context,
        channel_id=menu_items.CHANNEL_ID_INFOLABEL,
    )
    cxm_subscribe_to_channel = menu_items.channel_subscribe_to(context)
    cxm_remove_bookmarked_channel = menu_items.bookmark_remove(
        context,
        menu_items.CHANNEL_ID_INFOLABEL,
        menu_items.ARTIST_INFOLABEL,
    )
    cxm_bookmark_channel = menu_items.bookmark_add_channel(context)
    cxm_mark_as = menu_items.history_local_mark_as(context)
    cxm_reset_resume = menu_items.history_local_reset_resume(context)
    cxm_refresh_listing = menu_items.refresh_listing(context)
    cxm_more = menu_items.video_more_for(
        context,
        logged_in=logged_in,
        refresh=path.startswith((PATHS.LIKED_VIDEOS, PATHS.DISLIKED_VIDEOS)),
    )

    for video_id, yt_item in data.items():
        if not yt_item:
            continue

        media_items = video_id_dict.get(video_id)
        if media_items:
            media_item = media_items[-1]
        else:
            continue

        available = True
        if 'snippet' in yt_item:
            snippet = yt_item['snippet']
        else:
            snippet = {}
            if yt_item.get('_unavailable'):
                available = False
                media_item.playable = False
                media_item.available = False

        media_item.set_mediatype(
            CONTENT.AUDIO_TYPE
            if isinstance(media_item, AudioItem) else
            CONTENT.VIDEO_TYPE
        )

        play_data = use_play_data and yt_item.get('play_data')
        if play_data and 'total_time' in play_data:
            duration = play_data['total_time']
        else:
            duration = yt_item.get('contentDetails', {}).get('duration')
            if duration:
                duration = parse_to_dt(duration)
                if duration.seconds:
                    # subtract 1s because YouTube duration is +1s too long
                    duration = duration.seconds - 1
                else:
                    duration = 0
        if duration:
            media_item.set_duration_from_seconds(duration)
            if duration <= shorts_duration:
                media_item.short = True

        broadcast_type = snippet.get('liveBroadcastContent')
        media_item.live = broadcast_type == 'live'
        media_item.upcoming = broadcast_type == 'upcoming'

        upload_status = yt_item.get('status', {}).get('uploadStatus')
        if upload_status == 'processed' and duration:
            media_item.live = False
        elif upload_status == 'uploaded' and not duration:
            media_item.live = True

        if 'liveStreamingDetails' in yt_item:
            streaming_details = yt_item['liveStreamingDetails']
            if 'actualStartTime' in streaming_details:
                start_at = streaming_details['actualStartTime']
                media_item.upcoming = False
                if 'actualEndTime' in streaming_details:
                    media_item.completed = True
            else:
                start_at = streaming_details.get('scheduledStartTime')
                media_item.upcoming = True
        else:
            media_item.completed = False
            media_item.live = False
            media_item.upcoming = False
            media_item.vod = True
            start_at = None

            if item_filter and (
                    (not item_filter['completed']
                     and media_item.completed)
                    or (not item_filter['live']
                        and media_item.live and not media_item.upcoming)
                    or (not item_filter['upcoming']
                        and media_item.upcoming)
                    or (not item_filter['premieres']
                        and media_item.upcoming and not media_item.live)
                    or (not item_filter['upcoming_live']
                        and media_item.upcoming and media_item.live)
                    or (not item_filter['vod']
                        and media_item.vod)
                    or (not item_filter['shorts']
                        and media_item.short)
            ):
                continue

        if play_data:
            if media_item.live:
                if 'play_count' in play_data:
                    media_item.set_play_count(play_data['play_count'])

                if 'last_played' in play_data:
                    media_item.set_last_played(play_data['last_played'])

                media_item.set_start_percent(0)
                media_item.set_start_time(0)
            else:
                if 'play_count' in play_data:
                    media_item.set_play_count(play_data['play_count'])

                if 'last_played' in play_data:
                    media_item.set_last_played(play_data['last_played'])

                if 'played_percent' in play_data:
                    media_item.set_start_percent(play_data['played_percent'])

                if 'played_time' in play_data:
                    media_item.set_start_time(play_data['played_time'])

        if start_at:
            datetime = parse_to_dt(start_at)
            media_item.set_scheduled_start_utc(datetime)
            local_datetime = utc_to_local(datetime)
            media_item.set_year_from_datetime(local_datetime)
            media_item.set_aired_from_datetime(local_datetime)
            media_item.set_premiered_from_datetime(local_datetime)
            media_item.set_date_from_datetime(local_datetime)
            if media_item.upcoming:
                if media_item.live:
                    type_label = localize('live.upcoming')
                else:
                    type_label = localize('upcoming')
            elif media_item.live:
                type_label = localize('live')
            else:
                type_label = localize('start')
            start_at = ' '.join((
                type_label,
                get_scheduled_start(context, local_datetime),
            ))

        label_stats = []
        stats = []
        rating = 0
        likes = 0
        views = 0
        if 'statistics' in yt_item:
            for stat, value in yt_item['statistics'].items():
                label = context.LOCAL_MAP.get('stats.' + stat)
                if not label:
                    continue

                str_value, value = friendly_number(value, as_str=False)
                if not value:
                    continue

                color = settings.get_label_color(stat)
                label = localize(label)
                if value == 1:
                    label = label.rstrip('s')

                label_stats.append(ui.color(color, str_value))
                stats.append(ui.color(color, ui.bold(' '.join((
                    str_value, label
                )))))

                if stat == 'likeCount':
                    likes = value
                elif stat == 'viewCount':
                    views = value
                    media_item.set_count(views)

            label_stats = ' | '.join(label_stats)
            stats = ' | '.join(stats)

            if 0 < likes <= views:
                if likes == views:
                    rating = 10
                else:
                    # This is a completely made up, arbitrary ranking score
                    rating = (
                            10 * (log10(views) * log10(likes))
                            / (log10(likes + views) ** 2)
                    )
                media_item.set_rating(rating)

        # Used for label2, but is poorly supported in skins
        media_item.set_short_details(label_stats)
        # Hack to force a custom label mask containing production code,
        # activated on sort order selection, to display details
        # Refer XbmcContext.apply_content for usage
        media_item.set_production_code(label_stats)

        # update and set the title
        localised_info = snippet.get('localized') or {}
        title = media_item.get_name()
        if not title or title == untitled or media_item.bookmark_id:
            title = (localised_info.get('title')
                     or snippet.get('title')
                     or untitled)
        media_item.set_name(ui.italic(title) if media_item.upcoming else title)

        """
        This is experimental. We try to get the most information out of the title of a video.
        This is not based on any language. In some cases this won't work at all.
        TODO: via language and settings provide the regex for matching episode and season.
        """
        season = episode = None
        for season_episode in __RE_SEASON_EPISODE.findall(title):
            if not season:
                value = season_episode[0]
                if value:
                    value = int(value)
                    if value < 2 ** 31:
                        season = value
                        media_item.set_season(season)

            if not episode:
                value = season_episode[1]
                if value:
                    value = int(value)
                    if value < 2 ** 31:
                        episode = value
                        media_item.set_episode(episode)

            if season and episode:
                break

        # channel name
        channel_name = snippet.get('channelTitle', '') or untitled
        media_item.add_artist(channel_name)

        # plot
        description = strip_html_from_text(localised_info.get('description')
                                           or snippet.get('description')
                                           or '')
        if show_details:
            description = ''.join((
                ui.bold(channel_name, cr_after=1),
                ui.new_line(stats, cr_after=1) if stats else '',
                (ui.italic(start_at, cr_after=1) if media_item.upcoming
                 else ui.new_line(start_at, cr_after=1)) if start_at else '',
                ui.new_line(description, cr_after=1) if description else '',
                ui.new_line('--------', cr_after=1),
                'https://youtu.be/' + video_id,
            ))
        media_item.set_plot(description)

        # date time
        published_at = snippet.get('publishedAt')
        if not published_at:
            datetime = None
        elif isinstance(published_at, string_type):
            datetime = parse_to_dt(published_at)
        else:
            datetime = published_at
        if datetime:
            media_item.set_added_utc(datetime)
            local_datetime = utc_to_local(datetime)
            # If item is in a playlist, then use date added to playlist rather
            # than date that item was published to YouTube
            if not media_item.get_dateadded():
                media_item.set_dateadded_from_datetime(local_datetime)
            if not start_at:
                media_item.set_year_from_datetime(local_datetime)
                media_item.set_aired_from_datetime(local_datetime)
                media_item.set_premiered_from_datetime(local_datetime)
                media_item.set_date_from_datetime(local_datetime)

        # try to find a better resolution for the image
        image = media_item.get_image()
        if (not image
                or get_better_thumbs
                or image.startswith(('Default', 'special://'))):
            image = get_thumbnail(thumb_size, snippet.get('thumbnails'))
        if image and media_item.live:
            if '?' in image:
                image = ''.join((image, '&ct=', thumb_stamp))
            elif image.endswith(('_live.jpg', '_live.webp')):
                image = ''.join((image, '?ct=', thumb_stamp))
        media_item.set_image(image)

        # try to find a better resolution for the fanart
        if thumb_fanart:
            fanart = get_thumbnail(thumb_fanart, snippet.get('thumbnails'))
            if fanart and media_item.live:
                if '?' in fanart:
                    fanart = ''.join((fanart, '&ct=', thumb_stamp))
                elif image.endswith(('_live.jpg', '_live.webp')):
                    fanart = ''.join((fanart, '?ct=', thumb_stamp))
            media_item.set_fanart(fanart)

        # update channel mapping
        channel_id = snippet.get('channelId') or playlist_channel_id
        media_item.channel_id = channel_id

        item_from_playlist = playlist_id or media_item.playlist_id

        # Provide 'remove' in own playlists or virtual lists, except the
        # YouTube Watch History list as that does not support direct edits
        if (not in_watch_history_list
                and item_from_playlist
                and logged_in
                and playlist_channel_id == 'mine'):
            context_menu = [
                cxm_remove_from_playlist,
                cxm_separator,
            ]
        else:
            context_menu = []

        if available:
            context_menu.extend((
                cxm_play,
                cxm_play_with_subtitles,
                cxm_play_audio_only,
                cxm_play_ask_for_quality,
                cxm_play_timeshift if media_item.live else None,
                cxm_play_using,
                cxm_play_from if item_from_playlist else None,
                cxm_queue,
            ))

        # add 'Watch Later' only if we are not in my 'Watch Later' list
        if not available or in_watch_later_list:
            pass
        elif watch_later_id:
            context_menu.append(cxm_watch_later)
        else:
            context_menu.append(
                menu_items.watch_later_local_add(
                    context, media_item
                )
            )

        if not in_bookmarks_list:
            context_menu.append(
                menu_items.bookmark_add(
                    context, media_item
                )
            )

        if channel_id:
            # got to [CHANNEL] only if we are not directly in the channel
            if context.create_path(PATHS.CHANNEL, channel_id) != path:
                media_item.channel_id = channel_id
                context_menu.append(cxm_go_to_channel)

            if logged_in:
                context_menu.append(
                    # unsubscribe from the channel of the video
                    cxm_unsubscribe_from_channel
                    if in_my_subscriptions_list else
                    # subscribe to the channel of the video
                    cxm_subscribe_to_channel
                )

            context_menu.append(
                # remove bookmarked channel of the video
                cxm_remove_bookmarked_channel
                if in_my_subscriptions_list else
                # bookmark channel of the video
                cxm_bookmark_channel
            )

        if use_play_data:
            context_menu.append(cxm_mark_as)
            if play_data and (play_data.get('played_percent', 0) > 0
                              or play_data.get('played_time', 0) > 0):
                context_menu.append(cxm_reset_resume)

        # more...
        context_menu.extend((
            cxm_refresh_listing,
            cxm_more,
        ))

        update_duplicate_items(media_item,
                               media_items,
                               channel_id,
                               channel_items_dict,
                               context_menu)


def update_play_info(provider,
                     context,
                     video_id,
                     media_item,
                     video_stream,
                     yt_item=None):
    update_video_items(
        provider,
        context,
        {video_id: [media_item]},
        yt_items_dict={video_id: yt_item},
    )

    settings = context.get_settings()

    meta_data = video_stream.get('meta')
    if meta_data:
        media_item.live = meta_data.get('status', {}).get('live', False)
        media_item.set_subtitles(meta_data.get('subtitles', None))
        image = get_thumbnail(settings.get_thumbnail_size(),
                              meta_data.get('thumbnails'))
        if image:
            if media_item.live:
                if '?' in image:
                    image = ''.join((image, '&ct=', get_thumb_timestamp()))
                elif image.endswith(('_live.jpg', '_live.webp')):
                    image = ''.join((image, '?ct=', get_thumb_timestamp()))
            media_item.set_image(image)

    if 'headers' in video_stream:
        media_item.set_headers(video_stream['headers'])

    # set _uses_isa
    if video_stream.get('adaptive'):
        if media_item.live:
            use_isa = settings.use_isa_live_streams()
        else:
            use_isa = settings.use_isa()
    else:
        use_isa = False
    media_item.set_isa(use_isa)

    if use_isa:
        drm_details = video_stream.get('drm_details')
        if drm_details:
            drm_type = drm_details.get('widevine')
            if drm_type:
                try:
                    from inputstreamhelper import Helper
                except ImportError:
                    Helper = None

                if Helper:
                    is_helper = Helper(
                        'mpd' if media_item.use_mpd() else 'hls',
                        drm=drm_type['license_type'],
                    )
                    if is_helper and is_helper.check_inputstream():
                        media_item.set_license_key('|'.join((
                            drm_type['proxy_url'],
                            drm_type['headers'],
                            drm_type['post_format'],
                            drm_type['response_format'],
                        )))


def update_channel_info(provider,
                        context,
                        channel_items_dict,
                        data=None,
                        channel_data=None):
    # at least we need one channel id
    if not channel_items_dict and not (data or channel_data):
        return

    channel_ids = list(channel_items_dict)
    if channel_ids and not data:
        resource_manager = provider.get_resource_manager(context)
        data = resource_manager.get_channel_info(channel_ids,
                                                 channel_data=channel_data,
                                                 suppress_errors=True)

    if not data:
        return

    settings = context.get_settings()
    channel_name_aliases = settings.get_channel_name_aliases()
    fanart_type = context.get_param(FANART_TYPE)
    if fanart_type is None:
        fanart_type = settings.fanart_selection()
    use_channel_fanart = fanart_type == settings.FANART_CHANNEL
    use_thumb_fanart = fanart_type == settings.FANART_THUMBNAIL

    channel_role = context.localize('channel')

    for channel_id, channel_items in channel_items_dict.items():
        channel_info = data.get(channel_id)
        if not channel_info:
            continue

        for item in channel_items:
            if (use_channel_fanart
                    or use_thumb_fanart and not item.get_fanart(default=False)):
                item.set_fanart(channel_info.get('fanart'))

            channel_name = channel_info.get('name')
            if channel_name:
                if 'cast' in channel_name_aliases:
                    item.add_cast(channel_name,
                                  role=channel_role,
                                  thumbnail=channel_info.get('image'))
                if 'studio' in channel_name_aliases:
                    item.add_studio(channel_name)


PREFER_WEBP_THUMBS = False
if PREFER_WEBP_THUMBS:
    THUMB_URL = 'https://i.ytimg.com/vi_webp/{0}/{1}{2}.webp'
else:
    THUMB_URL = 'https://i.ytimg.com/vi/{0}/{1}{2}.jpg'
RE_CUSTOM_THUMB = re_compile(r'_custom_[0-9]')
THUMB_TYPES = {
    'default': {
        'name': 'default',
        'width': 120,
        'height': 90,
        'size': 120 * 90,
        'ratio': 120 / 90,  # 4:3
    },
    'medium': {
        'name': 'mqdefault',
        'width': 320,
        'height': 180,
        'size': 320 * 180,
        'ratio': 320 / 180,  # 16:9
    },
    'high': {
        'name': 'hqdefault',
        'width': 480,
        'height': 360,
        'size': 480 * 360,
        'ratio': 480 / 360,  # 4:3
    },
    'standard': {
        'name': 'sddefault',
        'width': 640,
        'height': 480,
        'size': 640 * 480,
        'ratio': 640 / 480,  # 4:3
    },
    '720': {
        'name': 'hq720',
        'width': 1280,
        'height': 720,
        'size': 1280 * 720,
        'ratio': 1280 / 720,  # 16:9
    },
    'oar': {
        'name': 'oardefault',
        'size': 0,
        'ratio': 0,
    },
    'maxres': {
        'name': 'maxresdefault',
        'size': 0,
        'ratio': 0,
    },
}


def get_thumbnail(thumb_size, thumbnails, default_thumb=None):
    if not thumbnails:
        return default_thumb
    is_dict = isinstance(thumbnails, dict)
    size_limit = thumb_size['size']
    ratio_limit = thumb_size['ratio']

    def _sort_ratio_size(thumb):
        if is_dict:
            thumb_type, thumb = thumb
        else:
            thumb_type = None

        if 'size' in thumb:
            size = thumb['size']
            ratio = thumb['ratio']
        elif 'width' in thumb:
            width = thumb['width']
            height = thumb['height']
            size = width * height
            ratio = width / height
        elif thumb_type in THUMB_TYPES:
            thumb = THUMB_TYPES[thumb_type]
            size = thumb['size']
            ratio = thumb['ratio']
        else:
            return False, False, False
        return (
            ratio_limit and ratio_limit * 0.9 <= ratio <= ratio_limit * 1.1,
            not thumb.get('unverified', False),
            size <= size_limit and size if size_limit else size,
        )

    thumbnail = sorted(thumbnails.items() if is_dict else thumbnails,
                       key=_sort_ratio_size,
                       reverse=True)[0]
    url = (thumbnail[1] if is_dict else thumbnail).get('url')
    if not url:
        return default_thumb
    if url.startswith('//'):
        url = 'https:' + url
    if '?' in url:
        url = urlsplit(url)
        url = url._replace(
            netloc='i.ytimg.com',
            path=RE_CUSTOM_THUMB.sub('', url.path),
            query=None,
        ).geturl()
    elif PREFER_WEBP_THUMBS and '/vi_webp/' not in url:
        url = url.replace('/vi/', '/vi_webp/', 1).replace('.jpg', '.webp', 1)
    return url


def add_related_video_to_playlist(provider, context, client, v3, video_id):
    playlist_player = context.get_playlist_player()
    if playlist_player.size() > 999:
        return
    playlist_items = playlist_player.get_items()

    next_item = None
    page_token = ''
    for _ in range(2):
        json_data = client.get_related_videos(
            video_id,
            page_token=page_token,
        )
        if not json_data:
            break

        result_items = v3.response_to_items(
            provider,
            context,
            json_data,
            process_next_page=False,
        )

        try:
            next_item = next((
                item for item in result_items
                if (item
                    and isinstance(item, MediaItem)
                    and not any((
                        item.get_uri() == playlist_item.get('file')
                        or item.get_name() == playlist_item.get('title')
                        for playlist_item in playlist_items
                    )))
            ))
        except StopIteration:
            page_token = json_data.get('nextPageToken')

        if not page_token:
            break

    if next_item:
        playlist_player.add(next_item)
    else:
        context.get_ui().show_notification(
            context.localize('error.no_videos_found'),
            header=context.localize('after_watch.play_suggested'),
            time_ms=5000,
        )


def filter_videos(items,
                  exclude=None,
                  shorts=True,
                  live=True,
                  upcoming_live=True,
                  premieres=True,
                  upcoming=True,
                  completed=True,
                  vod=True,
                  custom=None,
                  callback=None,
                  **_kwargs):
    accepted = []
    rejected = []
    for item in items:
        rejected_reason = None
        if item.callback and not item.callback():
            rejected_reason = 'Item callback'
        elif callback and not callback(item):
            rejected_reason = 'Collection callback'
        elif custom and not filter_parse(item, custom):
            rejected_reason = 'Custom filter'
        elif item.playable:
            if exclude and item.video_id in exclude:
                rejected_reason = 'Is excluded'
            elif not completed and item.completed:
                rejected_reason = 'Is completed'
            elif not live and item.live and not item.upcoming:
                rejected_reason = 'Is live'
            elif not upcoming and item.upcoming:
                rejected_reason = 'Is upcoming'
            elif not premieres and item.upcoming and not item.live:
                rejected_reason = 'Is premiere'
            elif not upcoming_live and item.upcoming and item.live:
                rejected_reason = 'Is upcoming live'
            elif not vod and item.vod:
                rejected_reason = 'Is VOD'
            elif not shorts and item.short:
                rejected_reason = 'Is short'

        if rejected_reason:
            item.set_filter_reason(rejected_reason)
            rejected.append(item)
        else:
            accepted.append(item)
    return accepted, rejected


def filter_parse(item,
                 all_criteria,
                 criteria_re=re_compile(
                     r'{?{([^}]+)}{([^}]+)}{([^}]+)}}?'
                 ),
                 op_map={
                     '=': op_eq,
                     '==': op_eq,
                     '>': op_gt,
                     '>=': op_ge,
                     '<': op_lt,
                     '<=': op_le,
                     'contains': op_contains,
                     'endswith': str.endswith,
                     'startswith': str.startswith,
                     'search': re_search,
                 },
                 _none=lambda: None):
    criteria_met = False
    for idx, criteria in enumerate(all_criteria):
        if isinstance(criteria, string_type):
            criteria = criteria_re.findall(criteria)
            all_criteria[idx] = criteria
        for input_1, op_str, input_2 in criteria:
            try:
                if input_1.startswith('.'):
                    input_1 = getattr(item, input_1[1:], None)
                else:
                    input_1 = getattr(item, 'get_{0}'.format(input_1), _none)()

                if input_2.startswith('"'):
                    input_2 = unquote(input_2[1:-1])
                    if input_1 is None:
                        input_1 = ''
                    elif isinstance(input_1, (dt_date, dt_datetime)):
                        input_2 = parse_to_dt(input_2)
                else:
                    input_2 = float(input_2)
                    if input_1 is None:
                        input_1 = -1

                _, negate, op_str = op_str.rpartition('!')
                op = op_map.get(op_str)
                if not op:
                    break
                if op_str == 'search':
                    input_1, input_2 = input_2, input_1

                result = op(input_1, input_2)
                if negate:
                    result = not result
                if not result:
                    break
            except (AttributeError, TypeError, ValueError, re_error):
                logging.exception(('Error',
                                   'Criteria: {criteria!r}',
                                   'input_1:  {input_1!r}',
                                   'op:       {op_str!r}',
                                   'input_2:  {input_2!r}'),
                                  criteria=criteria,
                                  input_1=input_1,
                                  op_str=op_str,
                                  input_2=input_2)
                break
        else:
            criteria_met = True
            break
    return criteria_met


def channel_filter_split(filters_string):
    custom_filters = []
    channel_filters = {
        filter_string
        for filter_string in filters_string.split(',')
        if filter_string and custom_filter_split(filter_string, custom_filters)
    }
    return filters_string, channel_filters, custom_filters


def custom_filter_split(filter_string,
                        custom_filters,
                        criteria_re=re_compile(
                            r'{?{([^}]+)}{([^}]+)}{([^}]+)}}?'
                        )):
    criteria = criteria_re.findall(filter_string)
    if not criteria:
        return True
    custom_filters.append(criteria)
    return False


def update_duplicate_items(updated_item,
                           items,
                           channel_id=None,
                           channel_items_dict=None,
                           context_menu=None,
                           skip_keys=frozenset(('_bookmark_id',
                                                '_bookmark_timestamp',
                                                '_callback',
                                                '_context_menu',
                                                '_track_number',
                                                '_uri')),
                           skip_vals=(None, '', -1)):
    updates = {
        key: val
        for key, val in updated_item.__dict__.items()
        if key not in skip_keys and val not in skip_vals
    }
    for item in items:
        if item != updated_item:
            item.__dict__.update(updates)
        if context_menu:
            item.add_context_menu(context_menu)

    if channel_id and channel_items_dict is not None:
        channel_items = channel_items_dict.setdefault(channel_id, [])
        channel_items.extend(items)
