# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import time
from datetime import date, datetime
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

from ...kodion.compatibility import string_type, unquote, urlsplit
from ...kodion.constants import CONTENT, PATHS
from ...kodion.items import AudioItem, CommandItem, DirectoryItem, menu_items
from ...kodion.logger import Logger
from ...kodion.utils import (
    datetime_parser,
    friendly_number,
    strip_html_from_text,
)


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

    datetime = datetime_parser.parse(published_at)
    local_datetime = datetime_parser.utc_to_local(datetime)

    if uri:
        comment_item = DirectoryItem(
            label,
            uri,
            image=author_image,
            plot=plot,
            category_label=' - '.join(
                (author, context.format_date_short(local_datetime))
            ),
        )
    else:
        comment_item = CommandItem(
            label,
            'Action(Info)',
            context,
            image=author_image,
            plot=plot,
        )

    comment_item.set_count(reply_count)

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
        datetime = datetime_parser.parse(updated_at)
        local_datetime = datetime_parser.utc_to_local(datetime)
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

    logged_in = provider.is_logged_in()

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

    filter_list = None
    if in_bookmarks_list or in_subscription_list:
        if settings.get_bool('youtube.folder.my_subscriptions_filtered.show',
                             False):
            filter_string = settings.get_string(
                'youtube.filter.my_subscriptions_filtered.list', ''
            ).replace(', ', ',')
            custom_filters = []
            filter_list = {
                item.lower()
                for item in filter_string.split(',')
                if item and filter_split(item, custom_filters)
            }

    thumb_size = settings.get_thumbnail_size()

    for channel_id, yt_item in data.items():
        if not yt_item or 'snippet' not in yt_item:
            continue
        snippet = yt_item['snippet']

        channel_item = channel_id_dict.get(channel_id)
        if not channel_item:
            continue

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
        # Refer XbmcContext.set_content for usage
        channel_item.set_production_code(label_stats)

        # channel name and title
        localised_info = snippet.get('localized') or {}
        channel_name = (localised_info.get('title')
                        or snippet.get('title')
                        or untitled)
        channel_item.set_name(channel_name)
        channel_item.add_artist(channel_name)

        # plot
        description = strip_html_from_text(localised_info.get('description')
                                           or snippet.get('description')
                                           or '')
        if show_details:
            description = ''.join((
                ui.bold(channel_name, cr_after=1),
                ui.new_line(stats, cr_after=1) if stats else '',
                ui.new_line(description, cr_after=1) if description else '',
                ui.new_line('--------', cr_before=1, cr_after=1),
                'https://www.youtube.com/' + channel_id
                if channel_id.startswith('@') else
                'https://www.youtube.com/channel/' + channel_id,
            ))
        channel_item.set_plot(description)

        # date time
        published_at = snippet.get('publishedAt')
        if published_at:
            datetime = datetime_parser.parse(published_at)
            channel_item.set_added_utc(datetime)
            local_datetime = datetime_parser.utc_to_local(datetime)
            channel_item.set_date_from_datetime(local_datetime)

        # image
        image = get_thumbnail(thumb_size, snippet.get('thumbnails'))
        channel_item.set_image(image)

        # - update context menu
        context_menu = []

        # -- unsubscribe from channel
        subscription_id = subscription_id_dict.get(channel_id, '')
        if subscription_id:
            channel_item.subscription_id = subscription_id
            context_menu.append(
                menu_items.unsubscribe_from_channel(
                    context, subscription_id=subscription_id
                )
            )

        # -- subscribe to the channel
        if logged_in and not in_subscription_list:
            context_menu.append(
                menu_items.subscribe_to_channel(
                    context, channel_id
                )
            )

        # add/remove from filter list
        if filter_list is not None:
            channel = channel_name.lower().replace(',', '')
            context_menu.append(
                menu_items.remove_my_subscriptions_filter(
                    context, channel_name
                ) if channel in filter_list else
                menu_items.add_my_subscriptions_filter(
                    context, channel_name
                )
            )

        if not in_bookmarks_list:
            context_menu.append(
                menu_items.bookmark_add_channel(
                    context, channel_id
                )
            )

        if context_menu:
            channel_item.add_context_menu(context_menu)

        # update channel mapping
        if channel_items_dict is not None:
            if channel_id not in channel_items_dict:
                channel_items_dict[channel_id] = []
            channel_items_dict[channel_id].append(channel_item)

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
    custom_watch_later_id = access_manager.get_watch_later_id()
    custom_history_id = access_manager.get_watch_history_id()
    logged_in = provider.is_logged_in()

    settings = context.get_settings()
    thumb_size = settings.get_thumbnail_size()
    show_details = settings.show_detailed_description()
    item_count_color = settings.get_label_color('itemCount')

    localize = context.localize
    episode_count_label = localize('stats.itemCount')
    video_count_label = localize('stats.videoCount')
    podcast_label = context.localize('playlist.podcast')
    untitled = localize('untitled')
    separator = menu_items.separator()

    path = context.get_path()
    ui = context.get_ui()

    # if the path directs to a playlist of our own, set channel id to 'mine'
    if path.startswith(PATHS.MY_PLAYLISTS):
        in_bookmarks_list = False
        in_my_playlists = True
    elif path.startswith(PATHS.BOOKMARKS):
        in_bookmarks_list = True
        in_my_playlists = False
    else:
        in_bookmarks_list = False
        in_my_playlists = False

    for playlist_id, yt_item in data.items():
        playlist_item = playlist_id_dict.get(playlist_id)
        if not playlist_item:
            continue

        if not yt_item or 'snippet' not in yt_item:
            continue
        snippet = yt_item['snippet']

        item_count_str, item_count = friendly_number(
            yt_item.get('contentDetails', {}).get('itemCount', 0),
            as_str=False,
        )
        if not item_count and playlist_id.startswith('UU'):
            continue

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
        # Refer XbmcContext.set_content for usage
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
                ui.new_line('--------', cr_before=1, cr_after=1),
                'https://youtube.com/playlist?list=' + playlist_id,
            ))
        playlist_item.set_plot(description)

        # date time
        published_at = snippet.get('publishedAt')
        if published_at:
            datetime = datetime_parser.parse(published_at)
            playlist_item.set_added_utc(datetime)
            local_datetime = datetime_parser.utc_to_local(datetime)
            playlist_item.set_date_from_datetime(local_datetime)

        image = get_thumbnail(thumb_size, snippet.get('thumbnails'))
        playlist_item.set_image(image)

        # update channel mapping
        channel_id = snippet.get('channelId', '')
        playlist_item.channel_id = channel_id
        if channel_id and channel_items_dict is not None:
            if channel_id not in channel_items_dict:
                channel_items_dict[channel_id] = []
            channel_items_dict[channel_id].append(playlist_item)

        # play all videos of the playlist
        context_menu = [
            menu_items.play_playlist(
                context, playlist_id
            ),
            menu_items.play_playlist_recently_added(
                context, playlist_id
            ),
            menu_items.view_playlist(
                context, playlist_id
            ),
            menu_items.shuffle_playlist(
                context, playlist_id
            ),
            separator,
            menu_items.bookmark_add(
                context, playlist_item
            ) if not in_bookmarks_list and not in_my_playlists else None,
        ]

        if logged_in:
            if in_my_playlists:
                context_menu.extend((
                    # remove my playlist
                    menu_items.delete_playlist(
                        context, playlist_id, title
                    ),
                    # rename playlist
                    menu_items.rename_playlist(
                        context, playlist_id, title
                    ),
                    # remove as my custom watch later playlist
                    menu_items.remove_as_watch_later(
                        context, playlist_id, title
                    ) if playlist_id == custom_watch_later_id else
                    # set as my custom watch later playlist
                    menu_items.set_as_watch_later(
                        context, playlist_id, title
                    ),
                    # remove as custom history playlist
                    menu_items.remove_as_history(
                        context, playlist_id, title
                    ) if playlist_id == custom_history_id else
                    # set as custom history playlist
                    menu_items.set_as_history(
                        context, playlist_id, title
                    ),
                ))
            else:
                # subscribe to the channel via the playlist item
                context_menu.append(
                    menu_items.subscribe_to_channel(
                        context, channel_id, channel_name
                    )
                )

        if not in_bookmarks_list and not in_my_playlists:
            context_menu.append(
                # bookmark channel of the playlist
                menu_items.bookmark_add_channel(
                    context, channel_id, channel_name
                )
            )

        if context_menu:
            playlist_item.add_context_menu(context_menu)


def update_video_items(provider, context, video_id_dict,
                       channel_items_dict=None,
                       live_details=True,
                       item_filter=None,
                       data=None,
                       yt_items=None):
    if not video_id_dict and not data:
        return

    video_ids = list(video_id_dict)
    if video_ids and not data:
        resource_manager = provider.get_resource_manager(context)
        data = resource_manager.get_videos(video_ids,
                                           live_details=live_details,
                                           suppress_errors=True,
                                           yt_items=yt_items)

    if not data:
        return

    logged_in = provider.is_logged_in()
    if logged_in:
        watch_later_id = context.get_access_manager().get_watch_later_id()
    else:
        watch_later_id = None

    settings = context.get_settings()
    alternate_player = settings.support_alternative_player()
    default_web_urls = settings.default_player_web_urls()
    ask_quality = not default_web_urls and settings.ask_for_video_quality()
    audio_only = settings.audio_only()
    show_details = settings.show_detailed_description()
    shorts_duration = settings.shorts_duration()
    subtitles_prompt = settings.get_subtitle_selection() == 1
    thumb_size = settings.get_thumbnail_size()
    thumb_stamp = get_thumb_timestamp()
    use_play_data = settings.use_local_history()

    localize = context.localize
    untitled = localize('untitled')

    path = context.get_path()
    ui = context.get_ui()

    if path.startswith(PATHS.MY_SUBSCRIPTIONS):
        in_bookmarks_list = False
        in_my_subscriptions_list = True
        in_watched_later_list = False
        playlist_match = False
    elif path.startswith(PATHS.WATCH_LATER):
        in_bookmarks_list = False
        in_my_subscriptions_list = False
        in_watched_later_list = True
        playlist_match = False
    elif path.startswith(PATHS.BOOKMARKS):
        in_bookmarks_list = True
        in_my_subscriptions_list = False
        in_watched_later_list = False
        playlist_match = False
    else:
        in_bookmarks_list = False
        in_my_subscriptions_list = False
        in_watched_later_list = False
        playlist_match = __RE_PLAYLIST.match(path)

    media_items = None
    media_item = None

    for video_id, yt_item in data.items():
        if media_items and media_item:
            update_duplicate_items(media_item, media_items)

        if not yt_item:
            continue

        media_items = video_id_dict.get(video_id)
        if media_items:
            media_item = media_items.pop()
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
                duration = datetime_parser.parse(duration)
                if duration.seconds:
                    # subtract 1s because YouTube duration is +1s too long
                    duration = duration.seconds - 1
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
                    (not item_filter['shorts']
                     and media_item.short)
                    or (not item_filter['completed']
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
            ):
                continue

        if media_item.live:
            media_item.set_play_count(0)
            use_play_data = False
            play_data = None
        elif play_data:
            if 'play_count' in play_data:
                media_item.set_play_count(play_data['play_count'])

            if 'played_percent' in play_data:
                media_item.set_start_percent(play_data['played_percent'])

            if 'played_time' in play_data:
                media_item.set_start_time(play_data['played_time'])

            if 'last_played' in play_data:
                media_item.set_last_played(play_data['last_played'])

        if start_at:
            datetime = datetime_parser.parse(start_at)
            media_item.set_scheduled_start_utc(datetime)
            local_datetime = datetime_parser.utc_to_local(datetime)
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
                datetime_parser.get_scheduled_start(context, local_datetime),
            ))

        label_stats = []
        stats = []
        rating = [0, 0]
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
                    rating[0] = value
                elif stat == 'viewCount':
                    rating[1] = value
                    media_item.set_count(value)

            label_stats = ' | '.join(label_stats)
            stats = ' | '.join(stats)

            if 0 < rating[0] <= rating[1]:
                if rating[0] == rating[1]:
                    rating = 10
                else:
                    # This is a completely made up, arbitrary ranking score
                    rating = (10 * (log10(rating[1]) * log10(rating[0]))
                              / (log10(rating[0] + rating[1]) ** 2))
                media_item.set_rating(rating)

        # Used for label2, but is poorly supported in skins
        media_item.set_short_details(label_stats)
        # Hack to force a custom label mask containing production code,
        # activated on sort order selection, to display details
        # Refer XbmcContext.set_content for usage
        media_item.set_production_code(label_stats)

        # update and set the title
        localised_info = snippet.get('localized') or {}
        title = media_item.get_name()
        if not title or title == untitled:
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
                ui.new_line('--------', cr_before=1, cr_after=1),
                'https://youtu.be/' + video_id,
            ))
        media_item.set_plot(description)

        # date time
        published_at = snippet.get('publishedAt')
        if not published_at:
            datetime = None
        elif isinstance(published_at, string_type):
            datetime = datetime_parser.parse(published_at)
        else:
            datetime = published_at
        if datetime:
            media_item.set_added_utc(datetime)
            local_datetime = datetime_parser.utc_to_local(datetime)
            # If item is in a playlist, then use data added to playlist rather
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
        if not image or image.startswith('Default'):
            image = get_thumbnail(thumb_size, snippet.get('thumbnails'))
        if image.endswith('_live.jpg'):
            image = ''.join((image, '?ct=', thumb_stamp))
        media_item.set_image(image)

        # update channel mapping
        channel_id = snippet.get('channelId', '')
        media_item.channel_id = channel_id
        if channel_id and channel_items_dict is not None:
            if channel_id not in channel_items_dict:
                channel_items_dict[channel_id] = []
            channel_items_dict[channel_id].append(media_item)

        """
        Play all videos of the playlist.

        /channel/[CHANNEL_ID]/playlist/[PLAYLIST_ID]/
        /playlist/[PLAYLIST_ID]/
        """
        playlist_channel_id = ''
        if playlist_match:
            playlist_id = playlist_match.group('playlist_id')
            playlist_channel_id = playlist_match.group('channel_id')
        else:
            playlist_id = media_item.playlist_id

        # provide 'remove' in my playlists that have a real playlist_id
        if (playlist_id
                and logged_in
                and playlist_channel_id == 'mine'
                and playlist_id.strip().lower() not in {'wl', 'hl'}):
            context_menu = [
                menu_items.remove_video_from_playlist(
                    context,
                    playlist_id=playlist_id,
                    video_id=media_item.playlist_item_id,
                    video_name=title,
                ),
                menu_items.separator(),
            ]
        else:
            context_menu = []

        if available:
            context_menu.extend((
                menu_items.play_video(context),
                menu_items.play_with_subtitles(
                    context, video_id
                ) if not subtitles_prompt else None,
                menu_items.play_audio_only(
                    context, video_id
                ) if not audio_only else None,
                menu_items.play_ask_for_quality(
                    context, video_id
                ) if not ask_quality else None,
                menu_items.play_timeshift(
                    context, video_id
                ) if media_item.live else None,
                # 'play with...' (external player)
                menu_items.play_with(
                    context, video_id
                ) if alternate_player else None,
                menu_items.play_playlist_from(
                    context, playlist_id, video_id
                ) if playlist_id else None,
                menu_items.queue_video(context),
            ))

        # add 'Watch Later' only if we are not in my 'Watch Later' list
        if not available:
            pass
        elif watch_later_id:
            if not playlist_id or watch_later_id != playlist_id:
                context_menu.append(
                    menu_items.watch_later_add(
                        context, watch_later_id, video_id
                    )
                )
        elif not in_watched_later_list:
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
                context_menu.append(
                    menu_items.go_to_channel(
                        context, channel_id, channel_name
                    )
                )

            if logged_in:
                context_menu.append(
                    # unsubscribe from the channel of the video
                    menu_items.unsubscribe_from_channel(
                        context, channel_id=channel_id
                    ) if in_my_subscriptions_list else
                    # subscribe to the channel of the video
                    menu_items.subscribe_to_channel(
                        context, channel_id, channel_name
                    )
                )

            if not in_bookmarks_list:
                context_menu.append(
                    # remove bookmarked channel of the video
                    menu_items.bookmark_remove(
                        context, channel_id, channel_name
                    ) if in_my_subscriptions_list else
                    # bookmark channel of the video
                    menu_items.bookmark_add_channel(
                        context, channel_id, channel_name
                    )
                )

        if use_play_data:
            context_menu.append(
                menu_items.history_mark_unwatched(
                    context, video_id
                ) if play_data and play_data.get('play_count') else
                menu_items.history_mark_watched(
                    context, video_id
                )
            )
            if play_data and (play_data.get('played_percent', 0) > 0
                              or play_data.get('played_time', 0) > 0):
                context_menu.append(
                    menu_items.history_reset_resume(
                        context, video_id
                    )
                )

        # more...
        refresh = path.startswith((PATHS.LIKED_VIDEOS, PATHS.DISLIKED_VIDEOS))
        context_menu.extend((
            menu_items.refresh(context),
            menu_items.more_for_video(
                context,
                video_id,
                video_name=title,
                logged_in=logged_in,
                refresh=refresh,
            ),
        ))

        if context_menu:
            media_item.add_context_menu(context_menu)


def update_play_info(provider,
                     context,
                     video_id,
                     media_item,
                     video_stream,
                     yt_item=None):
    update_video_items(
        provider, context, {video_id: [media_item]}, yt_items=[yt_item]
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
    fanart_type = context.get_param('fanart_type')
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


THUMB_TYPES = {
    'default': {
        'url': 'https://i.ytimg.com/vi/{0}/default{1}.jpg',
        'width': 120,
        'height': 90,
        'size': 120 * 90,
        'ratio': 120 / 90,  # 4:3
    },
    'medium': {
        'url': 'https://i.ytimg.com/vi/{0}/mqdefault{1}.jpg',
        'width': 320,
        'height': 180,
        'size': 320 * 180,
        'ratio': 320 / 180,  # 16:9
    },
    'high': {
        'url': 'https://i.ytimg.com/vi/{0}/hqdefault{1}.jpg',
        'width': 480,
        'height': 360,
        'size': 480 * 360,
        'ratio': 480 / 360,  # 4:3
    },
    'standard': {
        'url': 'https://i.ytimg.com/vi/{0}/sddefault{1}.jpg',
        'width': 640,
        'height': 480,
        'size': 640 * 480,
        'ratio': 640 / 480,  # 4:3
    },
    '720': {
        'url': 'https://i.ytimg.com/vi/{0}/hq720{1}.jpg',
        'width': 1280,
        'height': 720,
        'size': 1280 * 720,
        'ratio': 1280 / 720,  # 16:9
    },
    'oar': {
        'url': 'https://i.ytimg.com/vi/{0}/oardefault{1}.jpg',
        'size': 0,
        'ratio': 0,
    },
    'maxres': {
        'url': 'https://i.ytimg.com/vi/{0}/maxresdefault{1}.jpg',
        'width': 1920,
        'height': 1080,
        'size': 1920 * 1080,
        'ratio': 1920 / 1080,  # 16:9
    },
}


def get_thumbnail(thumb_size, thumbnails):
    if not thumbnails:
        return None
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
            return False, False
        return (
            ratio_limit and ratio_limit * 0.9 <= ratio <= ratio_limit * 1.1,
            size <= size_limit and size if size_limit else size
        )

    thumbnail = sorted(thumbnails.items() if is_dict else thumbnails,
                       key=_sort_ratio_size,
                       reverse=True)[0]
    url = (thumbnail[1] if is_dict else thumbnail).get('url')
    if url and url.startswith('//'):
        url = 'https:' + url
    return url


def get_shelf_index_by_title(context, json_data, shelf_title):
    shelf_index = None

    contents = json_data.get('contents', {}).get('sectionListRenderer', {}).get('contents', [{}])
    for idx, shelf in enumerate(contents):
        title = shelf.get('shelfRenderer', {}).get('title', {}).get('runs', [{}])[0].get('text', '')
        if title.lower() == shelf_title.lower():
            shelf_index = idx
            context.log_debug('Found shelf index |{index}| for |{title}|'.format(
                index=shelf_index, title=shelf_title
            ))
            break

    if shelf_index is not None and 0 > shelf_index >= len(contents):
        context.log_debug('Shelf index |{0}| out of range |0-{1}|'
                          .format(shelf_index, len(contents)))
        shelf_index = None

    return shelf_index


def add_related_video_to_playlist(provider, context, client, v3, video_id):
    playlist_player = context.get_playlist_player()

    if playlist_player.size() <= 999:
        a = 0
        add_item = None
        page_token = ''
        playlist_items = playlist_player.get_items()

        while not add_item and a <= 2:
            a += 1
            result_items = []

            try:
                json_data = client.get_related_videos(video_id,
                                                      page_token=page_token,
                                                      max_results=5)
                result_items = v3.response_to_items(provider,
                                                    context,
                                                    json_data,
                                                    process_next_page=False)
                page_token = json_data.get('nextPageToken', '')
            except Exception:
                context.get_ui().show_notification('Failed to add a suggested video.', time_ms=5000)

            if result_items:
                add_item = next((
                    item for item in result_items
                    if not any((item.get_uri() == pitem.get('file') or
                                item.get_name() == pitem.get('title'))
                               for pitem in playlist_items)),
                    None)

            if not add_item and page_token:
                continue

            if add_item:
                playlist_player.add(add_item)
                break

            if not page_token:
                break


def filter_videos(items,
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
    return [
        item
        for item in items
        if ((not item.callback or item.callback(item))
            and (not callback or callback(item))
            and (not custom or filter_parse(item, custom))
            and (not item.playable
                 or not ((not completed and item.completed)
                         or (not live and item.live and not item.upcoming)
                         or (not upcoming and item.upcoming)
                         or (not premieres and item.upcoming and not item.live)
                         or (not upcoming_live and item.upcoming and item.live)
                         or (not vod and item.vod)
                         or (not shorts and item.short))))
    ]


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
                 }):
    replacement_criteria = []
    criteria_met = False
    for idx, criteria in enumerate(all_criteria):
        if isinstance(criteria, string_type):
            criteria = criteria_re.findall(criteria)
            replacement_criteria.append((idx, criteria))
        for input_1, op_str, input_2 in criteria:
            try:
                if input_1.startswith('.'):
                    input_1 = getattr(item, input_1[1:])
                else:
                    input_1 = getattr(item, 'get_{0}'.format(input_1))()

                if input_2.startswith('"'):
                    input_2 = unquote(input_2[1:-1])
                    if input_1 is None:
                        input_1 = ''
                    elif isinstance(input_1, (date, datetime)):
                        input_2 = datetime_parser.parse(input_2)
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
            except (AttributeError, TypeError, ValueError, re_error) as exc:
                Logger.log_error('filter_parse - Error'
                                 '\n\tException: {exc!r}'
                                 '\n\tCriteria:  |{criteria}|'
                                 '\n\tinput_1:   |{input_1}|'
                                 '\n\top:        |{op_str}|'
                                 '\n\tinput_2:   |{input_2}|'
                                 .format(exc=exc,
                                         criteria=criteria,
                                         input_1=input_1,
                                         op_str=op_str,
                                         input_2=input_2))
                break
        else:
            criteria_met = True
            break
    for idx, criteria in replacement_criteria:
        all_criteria[idx] = criteria
    return criteria_met


def filter_split(item,
                 _all_criteria,
                 criteria_re=re_compile(
                     r'{?{([^}]+)}{([^}]+)}{([^}]+)}}?'
                 )):
    criteria = criteria_re.findall(item)
    if not criteria:
        return True
    _all_criteria.append(criteria)
    return False


def update_duplicate_items(item,
                           duplicates,
                           skip_keys=frozenset((
                               '_bookmark_id',
                               '_bookmark_timestamp',
                               '_callback',
                               '_track_number',
                           )),
                           skip_vals=(None, '', -1)):
    item = item.__dict__
    keys = frozenset(item.keys()).difference(skip_keys)
    for duplicate in duplicates:
        duplicate = duplicate.__dict__
        for key in keys:
            val = item[key]
            if val not in skip_vals:
                duplicate[key] = val
