# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import re
import time
from math import log10

from ...kodion.constants import content, paths
from ...kodion.items import DirectoryItem, menu_items
from ...kodion.utils import (
    create_path,
    datetime_parser,
    friendly_number,
    strip_html_from_text,
)

try:
    from inputstreamhelper import Helper as ISHelper
except ImportError:
    ISHelper = None


__RE_PLAYLIST_MATCH = re.compile(
    r'^(/channel/(?P<channel_id>[^/]+))/playlist/(?P<playlist_id>[^/]+)/?$'
)

__RE_SEASON_EPISODE_MATCHES__ = [
    re.compile(r'Part (?P<episode>\d+)'),
    re.compile(r'#(?P<episode>\d+)'),
    re.compile(r'Ep.\W?(?P<episode>\d+)'),
    re.compile(r'\[(?P<episode>\d+)]'),
    re.compile(r'S(?P<season>\d+)E(?P<episode>\d+)'),
    re.compile(r'Season (?P<season>\d+)(.+)Episode (?P<episode>\d+)'),
    re.compile(r'Episode (?P<episode>\d+)'),
]

__RE_URL = re.compile(r'(https?://\S+)')


def extract_urls(text):
    return __RE_URL.findall(text)


def get_thumb_timestamp(minutes=15):
    seconds = minutes * 60
    return str(time.mktime(time.gmtime(
        seconds * (round(time.time() / seconds))
    )))


def make_comment_item(context, snippet, uri, total_replies=0):
    settings = context.get_settings()
    ui = context.get_ui()

    author = ui.bold(snippet['authorDisplayName'])
    body = snippet['textOriginal']

    label_props = []
    plot_props = []

    like_count = snippet['likeCount']
    if like_count:
        like_count = friendly_number(like_count)
        color = settings.get_label_color('likeCount')
        label_likes = ui.color(color, ui.bold(like_count))
        plot_likes = ui.color(color, ui.bold(' '.join((
            like_count, context.localize('video.comments.likes')
        ))))
        label_props.append(label_likes)
        plot_props.append(plot_likes)

    if total_replies:
        total_replies = friendly_number(total_replies)
        color = settings.get_label_color('commentCount')
        label_replies = ui.color(color, ui.bold(total_replies))
        plot_replies = ui.color(color, ui.bold(' '.join((
            total_replies, context.localize('video.comments.replies')
        ))))
        label_props.append(label_replies)
        plot_props.append(plot_replies)

    published_at = snippet['publishedAt']
    updated_at = snippet['updatedAt']
    edited = published_at != updated_at
    if edited:
        label_props.append('*')
        plot_props.append(context.localize('video.comments.edited'))

    # Format the label of the comment item.
    if label_props:
        label = '{author} ({props}) {body}'.format(
            author=author,
            props='|'.join(label_props),
            body=body.replace('\n', ' ')
        )
    else:
        label = '{author} {body}'.format(
            author=author, body=body.replace('\n', ' ')
        )

    # Format the plot of the comment item.
    if plot_props:
        plot = '{author} ({props}){body}'.format(
            author=author,
            props='|'.join(plot_props),
            body=ui.new_line(body, cr_before=2)
        )
    else:
        plot = '{author}{body}'.format(
            author=author, body=ui.new_line(body, cr_before=2)
        )

    comment_item = DirectoryItem(label, uri)
    comment_item.set_plot(plot)

    datetime = datetime_parser.parse(published_at)
    comment_item.set_added_utc(datetime)
    local_datetime = datetime_parser.utc_to_local(datetime)
    comment_item.set_dateadded_from_datetime(local_datetime)
    if edited:
        datetime = datetime_parser.parse(updated_at)
        local_datetime = datetime_parser.utc_to_local(datetime)
    comment_item.set_date_from_datetime(local_datetime)

    if not uri:
        # Cosmetic, makes the item not a folder.
        comment_item.set_action(True)

    return comment_item


def update_channel_infos(provider, context, channel_id_dict,
                         subscription_id_dict=None,
                         channel_items_dict=None,
                         data=None):
    channel_ids = list(channel_id_dict)
    if not channel_ids and not data:
        return

    if not data:
        resource_manager = provider.get_resource_manager(context)
        data = resource_manager.get_channels(channel_ids)

    if not data:
        return

    if subscription_id_dict is None:
        subscription_id_dict = {}

    settings = context.get_settings()
    logged_in = provider.is_logged_in()
    path = context.get_path()

    filter_list = None
    if path.startswith(paths.SUBSCRIPTIONS):
        in_subscription_list = True
        if settings.get_bool('youtube.folder.my_subscriptions_filtered.show',
                             False):
            filter_string = settings.get_string(
                'youtube.filter.my_subscriptions_filtered.list', ''
            )
            filter_string = filter_string.replace(', ', ',')
            filter_list = filter_string.split(',')
            filter_list = [x.lower() for x in filter_list]
    else:
        in_subscription_list = False

    thumb_size = settings.use_thumbnail_size
    banners = [
        'bannerTvMediumImageUrl',
        'bannerTvLowImageUrl',
        'bannerTvImageUrl'
    ]

    for channel_id, yt_item in data.items():
        channel_item = channel_id_dict[channel_id]

        snippet = yt_item['snippet']

        # title
        title = snippet['title']
        channel_item.set_name(title)

        # image
        image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))
        channel_item.set_image(image)

        # - update context menu
        context_menu = []

        # -- unsubscribe from channel
        subscription_id = subscription_id_dict.get(channel_id, '')
        if subscription_id:
            channel_item.set_channel_subscription_id(subscription_id)
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
        if in_subscription_list and filter_list is not None:
            channel = title.lower().replace(',', '')
            context_menu.append(
                menu_items.remove_my_subscriptions_filter(
                    context, title
                ) if channel in filter_list else
                menu_items.add_my_subscriptions_filter(
                    context, title
                )
            )

        if context_menu:
            channel_item.set_context_menu(context_menu)

        fanart_images = yt_item.get('brandingSettings', {}).get('image', {})
        for banner in banners:
            fanart = fanart_images.get(banner)
            if fanart:
                channel_item.set_fanart(fanart)
                break

        # update channel mapping
        if channel_items_dict is not None:
            if channel_id not in channel_items_dict:
                channel_items_dict[channel_id] = []
            channel_items_dict[channel_id].append(channel_item)


def update_playlist_infos(provider, context, playlist_id_dict,
                          channel_items_dict=None,
                          data=None):
    playlist_ids = list(playlist_id_dict)
    if not playlist_ids and not data:
        return

    if not data:
        resource_manager = provider.get_resource_manager(context)
        data = resource_manager.get_playlists(playlist_ids)

    if not data:
        return

    access_manager = context.get_access_manager()
    custom_watch_later_id = access_manager.get_watch_later_id()
    custom_history_id = access_manager.get_watch_history_id()
    logged_in = provider.is_logged_in()
    path = context.get_path()
    thumb_size = context.get_settings().use_thumbnail_size()

    for playlist_id, yt_item in data.items():
        playlist_item = playlist_id_dict[playlist_id]

        snippet = yt_item['snippet']
        title = snippet['title']
        playlist_item.set_name(title)
        image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))
        playlist_item.set_image(image)

        channel_id = snippet['channelId']
        # if the path directs to a playlist of our own, set channel id to 'mine'
        if path.startswith(paths.MY_PLAYLISTS):
            channel_id = 'mine'
        channel_name = snippet.get('channelTitle', '')

        # play all videos of the playlist
        context_menu = [
            menu_items.play_all_from_playlist(
                context, playlist_id
            )
        ]

        if logged_in:
            if channel_id != 'mine':
                # subscribe to the channel via the playlist item
                context_menu.append(
                    menu_items.subscribe_to_channel(
                        context, channel_id, channel_name
                    )
                )
            else:
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

        if context_menu:
            playlist_item.set_context_menu(context_menu)

        # update channel mapping
        if channel_items_dict is not None:
            if channel_id not in channel_items_dict:
                channel_items_dict[channel_id] = []
            channel_items_dict[channel_id].append(playlist_item)


def update_video_infos(provider, context, video_id_dict,
                       playlist_item_id_dict=None,
                       channel_items_dict=None,
                       live_details=True,
                       use_play_data=True,
                       data=None):
    video_ids = list(video_id_dict)
    if not video_ids and not data:
        return

    if not data:
        resource_manager = provider.get_resource_manager(context)
        data = resource_manager.get_videos(video_ids,
                                           live_details=live_details,
                                           suppress_errors=True)

    if not data:
        return

    if not playlist_item_id_dict:
        playlist_item_id_dict = {}

    logged_in = provider.is_logged_in()
    if logged_in:
        watch_later_id = context.get_access_manager().get_watch_later_id()
    else:
        watch_later_id = None

    settings = context.get_settings()
    hide_shorts = settings.hide_short_videos()
    alternate_player = settings.support_alternative_player()
    show_details = settings.show_detailed_description()
    thumb_size = settings.use_thumbnail_size()
    thumb_stamp = get_thumb_timestamp()
    untitled = context.localize('untitled')

    path = context.get_path()
    ui = context.get_ui()

    if path.startswith(paths.MY_SUBSCRIPTIONS):
        in_my_subscriptions_list = True
        in_watched_later_list = False
        playlist_match = False
    elif path.startswith(paths.WATCH_LATER):
        in_my_subscriptions_list = False
        in_watched_later_list = True
        playlist_match = False
    else:
        in_my_subscriptions_list = False
        in_watched_later_list = False
        playlist_match = __RE_PLAYLIST_MATCH.match(path)

    for video_id, yt_item in data.items():
        video_item = video_id_dict[video_id]

        # set mediatype
        video_item.set_mediatype(content.VIDEO_TYPE)

        if not yt_item or 'snippet' not in yt_item:
            continue

        snippet = yt_item['snippet']
        play_data = use_play_data and yt_item.get('play_data')
        broadcast_type = snippet.get('liveBroadcastContent')
        video_item.live = broadcast_type == 'live'
        video_item.upcoming = broadcast_type == 'upcoming'

        # duration
        if (not (video_item.live or video_item.upcoming)
                and play_data and 'total_time' in play_data):
            duration = play_data['total_time']
        else:
            duration = yt_item.get('contentDetails', {}).get('duration')
            if duration:
                duration = datetime_parser.parse(duration)
                # subtract 1s because YouTube duration is +1s too long
                duration = (duration.seconds - 1) if duration.seconds else None
        if duration:
            video_item.set_duration_from_seconds(duration)
            if hide_shorts and duration <= 60:
                continue

        if not video_item.live and play_data:
            if 'play_count' in play_data:
                video_item.set_play_count(play_data['play_count'])

            if 'played_percent' in play_data:
                video_item.set_start_percent(play_data['played_percent'])

            if 'played_time' in play_data:
                video_item.set_start_time(play_data['played_time'])

            if 'last_played' in play_data:
                video_item.set_last_played(play_data['last_played'])
        elif video_item.live:
            video_item.set_play_count(0)

        if ((video_item.live or video_item.upcoming)
                and 'liveStreamingDetails' in yt_item):
            start_at = yt_item['liveStreamingDetails'].get('scheduledStartTime')
        else:
            start_at = None
        if start_at:
            datetime = datetime_parser.parse(start_at)
            video_item.set_scheduled_start_utc(datetime)
            local_datetime = datetime_parser.utc_to_local(datetime)
            video_item.set_year_from_datetime(local_datetime)
            video_item.set_aired_from_datetime(local_datetime)
            video_item.set_premiered_from_datetime(local_datetime)
            video_item.set_date_from_datetime(local_datetime)
            type_label = context.localize('live' if video_item.live
                                          else 'upcoming')
            start_at = '{type_label} {start_at}'.format(
                type_label=type_label,
                start_at=datetime_parser.get_scheduled_start(
                    context, local_datetime
                )
            )

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
                label = context.localize(label)
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
                    video_item.set_count(value)

            label_stats = ' | '.join(label_stats)
            stats = ' | '.join(stats)

            if 0 < rating[0] <= rating[1]:
                if rating[0] == rating[1]:
                    rating = 10
                else:
                    # This is a completely made up, arbitrary ranking score
                    rating = (10 * (log10(rating[1]) * log10(rating[0]))
                              / (log10(rating[0] + rating[1]) ** 2))
                video_item.set_rating(rating)

        # Used for label2, but is poorly supported in skins
        video_item.set_short_details(label_stats)
        # Hack to force a custom label mask containing production code,
        # activated on sort order selection, to display details
        # Refer XbmcContext.set_content for usage
        video_item.set_code(label_stats)

        # update and set the title
        title = video_item.get_title()
        if not title or title == untitled:
            title = snippet.get('title') or untitled
        video_item.set_title(ui.italic(title) if video_item.upcoming else title)

        """
        This is experimental. We try to get the most information out of the title of a video.
        This is not based on any language. In some cases this won't work at all.
        TODO: via language and settings provide the regex for matching episode and season.
        """
        # video_item.set_season(1)
        # video_item.set_episode(1)
        for regex in __RE_SEASON_EPISODE_MATCHES__:
            re_match = regex.search(video_item.get_name())
            if re_match:
                if 'season' in re_match.groupdict():
                    video_item.set_season(int(re_match.group('season')))

                if 'episode' in re_match.groupdict():
                    video_item.set_episode(int(re_match.group('episode')))
                break

        # plot
        channel_name = snippet.get('channelTitle', '')
        description = strip_html_from_text(snippet['description'])
        if show_details:
            description = ''.join((
                ui.bold(channel_name, cr_after=1) if channel_name else '',
                ui.new_line(stats, cr_after=1) if stats else '',
                (ui.italic(start_at, cr_after=1) if video_item.upcoming
                 else ui.new_line(start_at, cr_after=1)) if start_at else '',
                description,
            ))
        # video_item.add_studio(channel_name)
        # video_item.add_cast(channel_name)
        video_item.add_artist(channel_name)
        video_item.set_plot(description)

        # date time
        published_at = snippet.get('publishedAt')
        if published_at:
            datetime = datetime_parser.parse(published_at)
            video_item.set_added_utc(datetime)
            local_datetime = datetime_parser.utc_to_local(datetime)
            video_item.set_dateadded_from_datetime(local_datetime)
            if not start_at:
                video_item.set_year_from_datetime(local_datetime)
                video_item.set_aired_from_datetime(local_datetime)
                video_item.set_premiered_from_datetime(local_datetime)
                video_item.set_date_from_datetime(local_datetime)

        # try to find a better resolution for the image
        image = video_item.get_image()
        if not image:
            image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))
        if image.endswith('_live.jpg'):
            image = ''.join((image, '?ct=', thumb_stamp))
        video_item.set_image(image)

        # update channel mapping
        channel_id = snippet.get('channelId', '')
        video_item.set_subscription_id(channel_id)
        if channel_id and channel_items_dict is not None:
            if channel_id not in channel_items_dict:
                channel_items_dict[channel_id] = []
            channel_items_dict[channel_id].append(video_item)

        context_menu = [
            # Refresh
            menu_items.refresh(context),
            # Queue Video
            menu_items.queue_video(context),
        ]
        replace_context_menu = False

        """
        Play all videos of the playlist.

        /channel/[CHANNEL_ID]/playlist/[PLAYLIST_ID]/
        /playlist/[PLAYLIST_ID]/
        """
        playlist_id = playlist_channel_id = ''
        if playlist_match:
            replace_context_menu = True
            playlist_id = playlist_match.group('playlist_id')
            playlist_channel_id = playlist_match.group('channel_id')

            context_menu.extend((
                menu_items.play_all_from_playlist(
                    context, playlist_id, video_id
                ),
                menu_items.play_all_from_playlist(
                    context, playlist_id
                )
            ))

        # 'play with...' (external player)
        if alternate_player:
            context_menu.append(menu_items.play_with(context))

        # add 'Watch Later' only if we are not in my 'Watch Later' list
        if watch_later_id:
            if not playlist_id or watch_later_id != playlist_id:
                context_menu.append(
                    menu_items.watch_later_add(
                        context, watch_later_id, video_id
                    )
                )
        elif not in_watched_later_list:
            context_menu.append(
                menu_items.watch_later_local_add(
                    context, video_item
                )
            )

        # provide 'remove' for videos in my playlists
        # we support all playlist except 'Watch History'
        if (logged_in and video_id in playlist_item_id_dict and playlist_id
                and playlist_channel_id == 'mine'
                and playlist_id.strip().lower() not in ('hl', 'wl')):
            playlist_item_id = playlist_item_id_dict[video_id]
            video_item.set_playlist_id(playlist_id)
            video_item.set_playlist_item_id(playlist_item_id)
            context_menu.append(
                menu_items.remove_video_from_playlist(
                    context,
                    playlist_id=playlist_id,
                    video_id=playlist_item_id,
                    video_name=video_item.get_name(),
                )
            )

        # got to [CHANNEL] only if we are not directly in the channel
        if (channel_id and channel_name and
                create_path('channel', channel_id) != path):
            video_item.set_channel_id(channel_id)
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

        if not video_item.live and play_data:
            context_menu.append(
                menu_items.history_mark_unwatched(
                    context, video_id
                ) if play_data.get('play_count') else
                menu_items.history_mark_watched(
                    context, video_id
                )
            )

            if (play_data.get('played_percent', 0) > 0
                    or play_data.get('played_time', 0) > 0):
                context_menu.append(
                    menu_items.history_reset_resume(
                        context, video_id
                    )
                )

        # more...
        refresh = path.startswith((paths.LIKED_VIDEOS, paths.DISLIKED_VIDEOS))
        context_menu.extend((
            menu_items.more_for_video(
                context,
                video_id,
                logged_in=logged_in,
                refresh=refresh,
            ),
            menu_items.play_with_subtitles(
                context, video_id
            ),
            menu_items.play_audio_only(
                context, video_id
            ),
            menu_items.play_ask_for_quality(
                context, video_id
            ),
            ('--------', 'noop'),
        ))

        if context_menu:
            video_item.set_context_menu(
                context_menu, replace=replace_context_menu
            )


def update_play_info(provider, context, video_id, video_item, video_stream,
                     use_play_data=True):
    video_item.video_id = video_id
    update_video_infos(provider,
                       context,
                       {video_id: video_item},
                       use_play_data=use_play_data)

    settings = context.get_settings()
    ui = context.get_ui()

    meta_data = video_stream.get('meta', None)
    if meta_data:
        video_item.live = meta_data.get('status', {}).get('live', False)
        video_item.set_subtitles(meta_data.get('subtitles', None))
        image = get_thumbnail(settings.use_thumbnail_size(),
                              meta_data.get('images', {}))
        if image:
            if video_item.live:
                image = ''.join((image, '?ct=', get_thumb_timestamp()))
            video_item.set_image(image)

    if 'headers' in video_stream:
        video_item.set_headers(video_stream['headers'])

    # set _uses_isa
    if video_item.live:
        video_item.set_isa_video(settings.use_isa_live_streams())
    elif video_item.use_hls_video() or video_item.use_mpd_video():
        video_item.set_isa_video(settings.use_isa())

    if video_item.use_isa_video():
        license_info = video_stream.get('license_info', {})
        license_proxy = license_info.get('proxy', '')
        license_url = license_info.get('url', '')
        license_token = license_info.get('token', '')

        if ISHelper and license_proxy and license_url and license_token:
            ISHelper('mpd' if video_item.use_mpd_video() else 'hls',
                     drm='com.widevine.alpha').check_inputstream()

        video_item.set_license_key(license_proxy)
        ui.set_property('license_url', license_url)
        ui.set_property('license_token', license_token)


def update_fanarts(provider, context, channel_items_dict, data=None):
    # at least we need one channel id
    channel_ids = list(channel_items_dict)
    if not channel_ids and not data:
        return

    if not data:
        resource_manager = provider.get_resource_manager(context)
        data = resource_manager.get_fanarts(channel_ids)

    if not data:
        return

    for channel_id, channel_items in channel_items_dict.items():
        for channel_item in channel_items:
            # only set not empty fanarts
            fanart = data.get(channel_id, '')
            if fanart:
                channel_item.set_fanart(fanart)


def get_thumbnail(thumb_size, thumbnails):
    if thumb_size == 'high':
        thumbnail_sizes = ['high', 'medium', 'default']
    else:
        thumbnail_sizes = ['medium', 'high', 'default']

    image = ''
    for thumbnail_size in thumbnail_sizes:
        try:
            image = thumbnails.get(thumbnail_size, {}).get('url', '')
        except AttributeError:
            image = thumbnails.get(thumbnail_size, '')
        if image:
            break
    return image


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
        context.log_debug('Shelf index |{index}| out of range |0-{content_length}|'.format(
            index=shelf_index, content_length=len(contents)
        ))
        shelf_index = None

    return shelf_index


def add_related_video_to_playlist(provider, context, client, v3, video_id):
    playlist = context.get_video_playlist()

    if playlist.size() <= 999:
        a = 0
        add_item = None
        page_token = ''
        playlist_items = playlist.get_items()

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
            except:
                context.get_ui().show_notification('Failed to add a suggested video.', time_ms=5000)

            if result_items:
                add_item = next((
                    item for item in result_items
                    if not any((item.get_uri() == pitem.get('file') or
                                item.get_title() == pitem.get('title'))
                               for pitem in playlist_items)),
                    None)

            if not add_item and page_token:
                continue

            if add_item:
                playlist.add(add_item)
                break

            if not page_token:
                break


def filter_short_videos(items):
    return [
        item
        for item in items
        if not item.playable or not 0 <= item.get_duration() <= 60
    ]
