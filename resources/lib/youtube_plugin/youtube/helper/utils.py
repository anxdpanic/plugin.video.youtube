# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import re
import time

from ...kodion import utils
from ...kodion.items import DirectoryItem
from ...youtube.helper import yt_context_menu

try:
    from inputstreamhelper import Helper as ISHelper
except ImportError:
    ISHelper = None


__RE_SEASON_EPISODE_MATCHES__ = [
    re.compile(r'Part (?P<episode>\d+)'),
    re.compile(r'#(?P<episode>\d+)'),
    re.compile(r'Ep.[^\w]?(?P<episode>\d+)'),
    re.compile(r'\[(?P<episode>\d+)\]'),
    re.compile(r'S(?P<season>\d+)E(?P<episode>\d+)'),
    re.compile(r'Season (?P<season>\d+)(.+)Episode (?P<episode>\d+)'),
    re.compile(r'Episode (?P<episode>\d+)'),
]


def extract_urls(text):
    result = []

    re_url = re.compile(r'(https?://[^\s]+)')
    matches = re_url.findall(text)
    result = matches or result

    return result


def get_thumb_timestamp(minutes=15):
    return str(time.mktime(time.gmtime(minutes * 60 * (round(time.time() / (minutes * 60))))))


def make_comment_item(context, provider, snippet, uri, total_replies=0):
    author = '[B]{}[/B]'.format(utils.to_str(snippet['authorDisplayName']))
    body = utils.to_str(snippet['textOriginal'])

    label_props = None
    plot_props = None
    is_edited = (snippet['publishedAt'] != snippet['updatedAt'])

    str_likes = ('%.1fK' % (snippet['likeCount'] / 1000.0)) if snippet['likeCount'] > 1000 else str(snippet['likeCount'])
    str_replies = ('%.1fK' % (total_replies / 1000.0)) if total_replies > 1000 else str(total_replies)

    if snippet['likeCount'] and total_replies:
        label_props = '[COLOR lime][B]+%s[/B][/COLOR]|[COLOR cyan][B]%s[/B][/COLOR]' % (str_likes, str_replies)
        plot_props = '[COLOR lime][B]%s %s[/B][/COLOR]|[COLOR cyan][B]%s %s[/B][/COLOR]' % (str_likes,
                     context.localize(provider.LOCAL_MAP['youtube.video.comments.likes']), str_replies,
                     context.localize(provider.LOCAL_MAP['youtube.video.comments.replies']))
    elif snippet['likeCount']:
        label_props = '[COLOR lime][B]+%s[/B][/COLOR]' % str_likes
        plot_props = '[COLOR lime][B]%s %s[/B][/COLOR]' % (str_likes,
                     context.localize(provider.LOCAL_MAP['youtube.video.comments.likes']))
    elif total_replies:
        label_props = '[COLOR cyan][B]%s[/B][/COLOR]' % str_replies
        plot_props = '[COLOR cyan][B]%s %s[/B][/COLOR]' % (str_replies,
                     context.localize(provider.LOCAL_MAP['youtube.video.comments.replies']))
    else:
        pass # The comment has no likes or replies.

    # Format the label of the comment item.
    edited = '[B]*[/B]' if is_edited else ''
    if label_props:
        label = '{author} ({props}){edited} {body}'.format(author=author, props=label_props, edited=edited,
                                                             body=body.replace('\n', ' '))
    else:
        label = '{author}{edited} {body}'.format(author=author, edited=edited, body=body.replace('\n', ' '))

    # Format the plot of the comment item.
    edited = ' (%s)' % context.localize(provider.LOCAL_MAP['youtube.video.comments.edited']) if is_edited else ''
    if plot_props:
        plot = '{author} ({props}){edited}[CR][CR]{body}'.format(author=author, props=plot_props,
                                                               edited=edited, body=body)
    else:
        plot = '{author}{edited}[CR][CR]{body}'.format(author=author, edited=edited, body=body)

    comment_item = DirectoryItem(label, uri)
    comment_item.set_plot(plot)
    comment_item.set_date_from_datetime(utils.datetime_parser.parse(snippet['publishedAt']))
    if not uri:
        comment_item.set_action(True) # Cosmetic, makes the item not a folder.
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

    filter_list = []
    logged_in = provider.is_logged_in()
    path = context.get_path()
    if path == '/subscriptions/list/':
        filter_string = context.get_settings().get_string('youtube.filter.my_subscriptions_filtered.list', '')
        filter_string = filter_string.replace(', ', ',')
        filter_list = filter_string.split(',')
        filter_list = [x.lower() for x in filter_list]

    thumb_size = context.get_settings().use_thumbnail_size
    banners = ['bannerTvMediumImageUrl', 'bannerTvLowImageUrl', 'bannerTvImageUrl']

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
            yt_context_menu.append_unsubscribe_from_channel(context_menu, provider, context, subscription_id)
        # -- subscribe to the channel
        if logged_in and path != '/subscriptions/list/':
            yt_context_menu.append_subscribe_to_channel(context_menu, provider, context, channel_id)

        if path == '/subscriptions/list/':
            channel = title.lower().replace(',', '')
            if channel in filter_list:
                yt_context_menu.append_remove_my_subscriptions_filter(context_menu, provider, context, title)
            else:
                yt_context_menu.append_add_my_subscriptions_filter(context_menu, provider, context, title)
        channel_item.set_context_menu(context_menu)

        fanart_images = yt_item.get('brandingSettings', {}).get('image', {})
        for banner in banners:
            fanart = fanart_images.get(banner)
            if fanart:
                break
        else:
            fanart = ''
        channel_item.set_fanart(fanart)

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
        # if the path directs to a playlist of our own, we correct the channel id to 'mine'
        if path == '/channel/mine/playlists/':
            channel_id = 'mine'
        channel_name = snippet.get('channelTitle', '')
        context_menu = []
        # play all videos of the playlist
        yt_context_menu.append_play_all_from_playlist(context_menu, provider, context, playlist_id)

        if logged_in:
            if channel_id != 'mine':
                # subscribe to the channel via the playlist item
                yt_context_menu.append_subscribe_to_channel(context_menu, provider, context, channel_id,
                                                            channel_name)
            else:
                # remove my playlist
                yt_context_menu.append_delete_playlist(context_menu, provider, context, playlist_id, title)

                # rename playlist
                yt_context_menu.append_rename_playlist(context_menu, provider, context, playlist_id, title)

                # remove as my custom watch later playlist
                if playlist_id == custom_watch_later_id:
                    yt_context_menu.append_remove_as_watchlater(context_menu, provider, context, playlist_id, title)
                # set as my custom watch later playlist
                else:
                    yt_context_menu.append_set_as_watchlater(context_menu, provider, context, playlist_id, title)
                # remove as custom history playlist
                if playlist_id == custom_history_id:
                    yt_context_menu.append_remove_as_history(context_menu, provider, context, playlist_id, title)
                # set as custom history playlist
                else:
                    yt_context_menu.append_set_as_history(context_menu, provider, context, playlist_id, title)

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

    settings = context.get_settings()
    alternate_player = settings.is_support_alternative_player_enabled()
    logged_in = provider.is_logged_in()
    path = context.get_path()
    show_details = settings.show_detailed_description()
    thumb_size = settings.use_thumbnail_size()
    thumb_stamp = get_thumb_timestamp()
    ui = context.get_ui()

    for video_id, yt_item in data.items():
        video_item = video_id_dict[video_id]

        # set mediatype
        video_item.set_mediatype('video')  # using video

        if not yt_item:
            continue

        snippet = yt_item['snippet']  # crash if not conform
        play_data = use_play_data and yt_item.get('play_data')
        broadcast_type = snippet.get('liveBroadcastContent')
        video_item.live = broadcast_type == 'live'
        video_item.upcoming = broadcast_type == 'upcoming'

        # duration
        if not video_item.live and play_data and 'total_time' in play_data:
            duration = play_data['total_time']
        else:
            duration = yt_item.get('contentDetails', {}).get('duration')
            if duration:
                # subtract 1s because YouTube duration is +1s too long
                duration = utils.datetime_parser.parse(duration).seconds - 1
        if duration:
            video_item.set_duration_from_seconds(duration)

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
            datetime = utils.datetime_parser.parse(start_at, as_utc=True)
            video_item.set_scheduled_start_utc(datetime)
            local_datetime = utils.datetime_parser.utc_to_local(datetime)
            video_item.set_year_from_datetime(local_datetime)
            video_item.set_aired_from_datetime(local_datetime)
            video_item.set_premiered_from_datetime(local_datetime)
            video_item.set_date_from_datetime(local_datetime)
            type_label = context.localize(provider.LOCAL_MAP[
                'youtube.live' if video_item.live else 'youtube.upcoming'
            ])
            start_at = '{type_label} {start_at}'.format(
                type_label=type_label,
                start_at=utils.datetime_parser.get_scheduled_start(
                    context, local_datetime
                )
            )

        # update and set the title
        title = video_item.get_title() or snippet['title'] or ''
        if video_item.upcoming:
            title = ui.italic(title)
        video_item.set_title(title)

        stats = []
        if 'statistics' in yt_item:
            for stat, value in yt_item['statistics'].items():
                label = provider.LOCAL_MAP.get('youtube.stats.' + stat)
                if label:
                    stats.append('{value} {name}'.format(
                        name=context.localize(label).lower(),
                        value=utils.friendly_number(value)
                    ))
            stats = ', '.join(stats)

        # Used for label2, but is poorly supported in skins
        video_details = ' | '.join((detail for detail in (
            ui.light(stats) if stats else '',
            ui.italic(start_at) if start_at else '',
        ) if detail))
        video_item.set_short_details(video_details)

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
        description = utils.strip_html_from_text(snippet['description'])
        if show_details:
            description = ''.join((
                ui.bold(channel_name, cr_after=2) if channel_name else '',
                ui.light(stats, cr_after=1) if stats else '',
                ui.italic(start_at, cr_after=1) if start_at else '',
                ui.new_line() if stats or start_at else '',
                description,
            ))
        video_item.set_studio(channel_name)
        # video_item.add_cast(channel_name)
        video_item.add_artist(channel_name)
        video_item.set_plot(description)

        # date time
        published_at = snippet.get('publishedAt')
        if published_at:
            datetime = utils.datetime_parser.parse(published_at, as_utc=True)
            video_item.set_added_utc(datetime)
            local_datetime = utils.datetime_parser.utc_to_local(datetime)
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
            image = ''.join([image, '?ct=', thumb_stamp])
        video_item.set_image(image)

        # set fanart
        video_item.set_fanart(provider.get_fanart(context))

        # update channel mapping
        channel_id = snippet.get('channelId', '')
        if channel_items_dict is not None:
            if channel_id not in channel_items_dict:
                channel_items_dict[channel_id] = []
            channel_items_dict[channel_id].append(video_item)

        context_menu = []
        replace_context_menu = False

        # Refresh
        yt_context_menu.append_refresh(context_menu, provider, context)

        # Queue Video
        yt_context_menu.append_queue_video(context_menu, provider, context)

        """
        Play all videos of the playlist.

        /channel/[CHANNEL_ID]/playlist/[PLAYLIST_ID]/
        /playlist/[PLAYLIST_ID]/
        """
        some_playlist_match = re.match(r'^(/channel/([^/]+))/playlist/(?P<playlist_id>[^/]+)/$', path)
        if some_playlist_match:
            replace_context_menu = True
            playlist_id = some_playlist_match.group('playlist_id')

            yt_context_menu.append_play_all_from_playlist(context_menu, provider, context, playlist_id, video_id)
            yt_context_menu.append_play_all_from_playlist(context_menu, provider, context, playlist_id)

        # 'play with...' (external player)
        if alternate_player:
            yt_context_menu.append_play_with(context_menu, provider, context)

        if logged_in:
            # add 'Watch Later' only if we are not in my 'Watch Later' list
            watch_later_playlist_id = context.get_access_manager().get_watch_later_id()
            if watch_later_playlist_id:
                yt_context_menu.append_watch_later(context_menu, provider, context, watch_later_playlist_id, video_id)

            # provide 'remove' for videos in my playlists
            if video_id in playlist_item_id_dict:
                playlist_match = re.match('^/channel/mine/playlist/(?P<playlist_id>[^/]+)/$', path)
                if playlist_match:
                    playlist_id = playlist_match.group('playlist_id')
                    # we support all playlist except 'Watch History'
                    if playlist_id and playlist_id != 'HL' and playlist_id.strip().lower() != 'wl':
                        playlist_item_id = playlist_item_id_dict[video_id]
                        video_item.set_playlist_id(playlist_id)
                        video_item.set_playlist_item_id(playlist_item_id)
                        context_menu.append((context.localize(provider.LOCAL_MAP['youtube.remove']),
                                             'RunPlugin(%s)' % context.create_uri(
                                                 ['playlist', 'remove', 'video'],
                                                 {'playlist_id': playlist_id,
                                                  'video_id': playlist_item_id,
                                                  'video_name': video_item.get_name()}
                                             )))

            is_history = re.match('^/special/watch_history_tv/$', context.get_path())
            if is_history:
                yt_context_menu.append_clear_watch_history(context_menu, provider, context)

        # got to [CHANNEL], only if we are not directly in the channel provide a jump to the channel
        if (channel_id and channel_name and
                utils.create_path('channel', channel_id) != path):
            video_item.set_channel_id(channel_id)
            yt_context_menu.append_go_to_channel(context_menu, provider, context, channel_id, channel_name)

        if logged_in:
            # subscribe to the channel of the video
            video_item.set_subscription_id(channel_id)
            yt_context_menu.append_subscribe_to_channel(context_menu, provider, context, channel_id, channel_name)

        if not video_item.live and play_data:
            if not play_data.get('play_count'):
                yt_context_menu.append_mark_watched(context_menu, provider, context, video_id)
            else:
                yt_context_menu.append_mark_unwatched(context_menu, provider, context, video_id)

            if play_data.get('played_percent', 0) > 0 or play_data.get('played_time', 0) > 0:
                yt_context_menu.append_reset_resume_point(context_menu, provider, context, video_id)

        # more...
        refresh_container = (path.startswith('/channel/mine/playlist/LL')
                             or path == '/special/disliked_videos/')
        yt_context_menu.append_more_for_video(context_menu, context, video_id,
                                              is_logged_in=logged_in,
                                              refresh_container=refresh_container)

        if not video_item.live:
            yt_context_menu.append_play_with_subtitles(context_menu, context, video_id)
            yt_context_menu.append_play_audio_only(context_menu, context, video_id)

        yt_context_menu.append_play_ask_for_quality(context_menu, provider, context, video_id)

        if context_menu:
            video_item.set_context_menu(context_menu, replace=replace_context_menu)


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
        video_item.set_subtitles(meta_data.get('subtitles', None))
        image = get_thumbnail(settings.use_thumbnail_size(),
                              meta_data.get('images', {}))
        if image:
            if video_item.live:
                image = ''.join([image, '?ct=', get_thumb_timestamp()])
            video_item.set_image(image)

    if 'headers' in video_stream:
        video_item.set_headers(video_stream['headers'])

    # set _uses_isa
    if video_item.live:
        video_item.set_isa_video(settings.use_isa_live_streams())
    elif video_item.use_hls_video() or video_item.use_mpd_video():
        video_item.set_isa_video(settings.use_isa())

    license_info = video_stream.get('license_info', {})
    license_proxy = license_info.get('proxy', '')
    license_url = license_info.get('url', '')
    license_token = license_info.get('token', '')

    if ISHelper and license_proxy and license_url and license_token:
        ISHelper('mpd', drm='com.widevine.alpha').check_inputstream()

    video_item.set_license_key(license_proxy)
    ui.set_home_window_property('license_url', license_url)
    ui.set_home_window_property('license_token', license_token)


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
                json_data = client.get_related_videos(video_id, page_token=page_token, max_results=17)
                result_items = v3.response_to_items(provider, context, json_data, process_next_page=False)
                page_token = json_data.get('nextPageToken', '')
            except:
                context.get_ui().show_notification('Failed to add a suggested video.', time_milliseconds=5000)

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


def filter_short_videos(context, items):
    if context.get_settings().hide_short_videos():
        shorts_filtered = []

        for item in items:
            if hasattr(item, '_duration'):
                item_duration = 0 if item.get_duration() is None else item.get_duration()
                if 0 < item_duration <= 60:
                    continue
            shorts_filtered += [item]

        return shorts_filtered

    return items
