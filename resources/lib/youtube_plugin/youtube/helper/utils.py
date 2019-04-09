# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from six import PY2

import re
import time

from ... import kodion
from ...kodion import utils
from ...youtube.helper import yt_context_menu

try:
    import inputstreamhelper
except ImportError:
    inputstreamhelper = None

__RE_SEASON_EPISODE_MATCHES__ = [re.compile(r'Part (?P<episode>\d+)'),
                                 re.compile(r'#(?P<episode>\d+)'),
                                 re.compile(r'Ep.[^\w]?(?P<episode>\d+)'),
                                 re.compile(r'\[(?P<episode>\d+)\]'),
                                 re.compile(r'S(?P<season>\d+)E(?P<episode>\d+)'),
                                 re.compile(r'Season (?P<season>\d+)(.+)Episode (?P<episode>\d+)'),
                                 re.compile(r'Episode (?P<episode>\d+)')]


def extract_urls(text):
    result = []

    re_url = re.compile(r'(https?://[^\s]+)')
    matches = re_url.findall(text)
    result = matches or result

    return result


def get_thumb_timestamp(minutes=15):
    return str(time.mktime(time.gmtime(minutes * 60 * (round(time.time() / (minutes * 60))))))


def update_channel_infos(provider, context, channel_id_dict, subscription_id_dict=None, channel_items_dict=None):
    if subscription_id_dict is None:
        subscription_id_dict = {}

    channel_ids = list(channel_id_dict.keys())
    if len(channel_ids) == 0:
        return

    resource_manager = provider.get_resource_manager(context)
    channel_data = resource_manager.get_channels(channel_ids)

    filter_list = []
    if context.get_path() == '/subscriptions/list/':
        filter_string = context.get_settings().get_string('youtube.filter.my_subscriptions_filtered.list', '')
        filter_string = filter_string.replace(', ', ',')
        filter_list = filter_string.split(',')
        filter_list = [x.lower() for x in filter_list]

    thumb_size = context.get_settings().use_thumbnail_size()
    for channel_id in list(channel_data.keys()):
        yt_item = channel_data[channel_id]
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
        if provider.is_logged_in() and context.get_path() != '/subscriptions/list/':
            yt_context_menu.append_subscribe_to_channel(context_menu, provider, context, channel_id)

        if context.get_path() == '/subscriptions/list/':
            channel = title.lower()
            channel = channel.replace(',', '')
            if PY2:
                channel = channel.encode('utf-8', 'ignore')
            if channel in filter_list:
                yt_context_menu.append_remove_my_subscriptions_filter(context_menu, provider, context, title)
            else:
                yt_context_menu.append_add_my_subscriptions_filter(context_menu, provider, context, title)

        channel_item.set_context_menu(context_menu)

        fanart = u''
        fanart_images = yt_item.get('brandingSettings', {}).get('image', {})
        banners = ['bannerTvMediumImageUrl', 'bannerTvLowImageUrl', 'bannerTvImageUrl']
        for banner in banners:
            fanart = fanart_images.get(banner, u'')
            if fanart:
                break

        channel_item.set_fanart(fanart)

        # update channel mapping
        if channel_items_dict is not None:
            if channel_id not in channel_items_dict:
                channel_items_dict[channel_id] = []
            channel_items_dict[channel_id].append(channel_item)


def update_playlist_infos(provider, context, playlist_id_dict, channel_items_dict=None):
    playlist_ids = list(playlist_id_dict.keys())
    if len(playlist_ids) == 0:
        return

    resource_manager = provider.get_resource_manager(context)
    access_manager = context.get_access_manager()
    playlist_data = resource_manager.get_playlists(playlist_ids)

    custom_watch_later_id = access_manager.get_watch_later_id()
    custom_history_id = access_manager.get_watch_history_id()

    thumb_size = context.get_settings().use_thumbnail_size()
    for playlist_id in list(playlist_data.keys()):
        yt_item = playlist_data[playlist_id]
        playlist_item = playlist_id_dict[playlist_id]

        snippet = yt_item['snippet']
        title = snippet['title']
        playlist_item.set_name(title)
        image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))
        playlist_item.set_image(image)

        channel_id = snippet['channelId']
        # if the path directs to a playlist of our own, we correct the channel id to 'mine'
        if context.get_path() == '/channel/mine/playlists/':
            channel_id = 'mine'
        channel_name = snippet.get('channelTitle', '')
        context_menu = []
        # play all videos of the playlist
        yt_context_menu.append_play_all_from_playlist(context_menu, provider, context, playlist_id)

        if provider.is_logged_in():
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

        if len(context_menu) > 0:
            playlist_item.set_context_menu(context_menu)

        # update channel mapping
        if channel_items_dict is not None:
            if channel_id not in channel_items_dict:
                channel_items_dict[channel_id] = []
            channel_items_dict[channel_id].append(playlist_item)


def update_video_infos(provider, context, video_id_dict, playlist_item_id_dict=None, channel_items_dict=None, live_details=False, use_play_data=True):
    settings = context.get_settings()
    ui = context.get_ui()

    video_ids = list(video_id_dict.keys())
    if len(video_ids) == 0:
        return

    if not playlist_item_id_dict:
        playlist_item_id_dict = {}

    resource_manager = provider.get_resource_manager(context)
    video_data = resource_manager.get_videos(video_ids, live_details=live_details)

    thumb_size = settings.use_thumbnail_size()
    thumb_stamp = get_thumb_timestamp()
    for video_id in list(video_data.keys()):
        datetime = None
        yt_item = video_data[video_id]
        video_item = video_id_dict[video_id]

        snippet = yt_item['snippet']  # crash if not conform
        play_data = yt_item['play_data']
        video_item.live = snippet.get('liveBroadcastContent') == 'live'

        # set mediatype
        video_item.set_mediatype('video')  # using video

        # duration
        if not video_item.live and use_play_data and play_data.get('total_time'):
            video_item.set_duration_from_seconds(float(play_data.get('total_time')))
        else:
            duration = yt_item.get('contentDetails', {}).get('duration', '')
            if duration:
                duration = utils.datetime_parser.parse(duration)
                # we subtract 1 seconds because YouTube returns +1 second to much
                video_item.set_duration_from_seconds(duration.seconds - 1)

        if not video_item.live and use_play_data:
            # play count
            if play_data.get('play_count'):
                video_item.set_play_count(int(play_data.get('play_count')))

            if play_data.get('played_percent'):
                video_item.set_start_percent(play_data.get('played_percent'))

            if play_data.get('played_time'):
                video_item.set_start_time(play_data.get('played_time'))

            if play_data.get('last_played'):
                video_item.set_last_played(play_data.get('last_played'))
        elif video_item.live:
            video_item.set_play_count(0)

        scheduled_start = video_data[video_id].get('liveStreamingDetails', {}).get('scheduledStartTime')
        if scheduled_start:
            datetime = utils.datetime_parser.parse(scheduled_start)
            video_item.set_scheduled_start_utc(datetime)
            start_date, start_time = utils.datetime_parser.get_scheduled_start(datetime)
            if start_date:
                title = u'({live} {date}@{time}) {title}' \
                    .format(live=context.localize(provider.LOCAL_MAP['youtube.live']), date=start_date, time=start_time, title=snippet['title'])
            else:
                title = u'({live} @ {time}) {title}' \
                    .format(live=context.localize(provider.LOCAL_MAP['youtube.live']), date=start_date, time=start_time, title=snippet['title'])
            video_item.set_title(title)
        else:
            # set the title
            if not video_item.get_title():
                video_item.set_title(snippet['title'])

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
        description = kodion.utils.strip_html_from_text(snippet['description'])
        if channel_name and settings.get_bool('youtube.view.description.show_channel_name', True):
            description = '%s[CR][CR]%s' % (ui.uppercase(ui.bold(channel_name)), description)
        video_item.set_studio(channel_name)
        # video_item.add_cast(channel_name)
        video_item.add_artist(channel_name)
        video_item.set_plot(description)

        # date time
        if not datetime and 'publishedAt' in snippet and snippet['publishedAt']:
            datetime = utils.datetime_parser.parse(snippet['publishedAt'])
            video_item.set_aired_utc(utils.datetime_parser.strptime(snippet['publishedAt']))

        if datetime:
            video_item.set_year_from_datetime(datetime)
            video_item.set_aired_from_datetime(datetime)
            video_item.set_premiered_from_datetime(datetime)
            video_item.set_date_from_datetime(datetime)

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
        some_playlist_match = re.match(r'^(/channel/([^/]+))/playlist/(?P<playlist_id>[^/]+)/$', context.get_path())
        if some_playlist_match:
            replace_context_menu = True
            playlist_id = some_playlist_match.group('playlist_id')

            yt_context_menu.append_play_all_from_playlist(context_menu, provider, context, playlist_id, video_id)
            yt_context_menu.append_play_all_from_playlist(context_menu, provider, context, playlist_id)

        # 'play with...' (external player)
        if settings.is_support_alternative_player_enabled():
            yt_context_menu.append_play_with(context_menu, provider, context)

        if provider.is_logged_in():
            # add 'Watch Later' only if we are not in my 'Watch Later' list
            watch_later_playlist_id = context.get_access_manager().get_watch_later_id()
            yt_context_menu.append_watch_later(context_menu, provider, context, watch_later_playlist_id, video_id)

            # provide 'remove' for videos in my playlists
            if video_id in playlist_item_id_dict:
                playlist_match = re.match('^/channel/mine/playlist/(?P<playlist_id>[^/]+)/$', context.get_path())
                if playlist_match:
                    playlist_id = playlist_match.group('playlist_id')
                    # we support all playlist except 'Watch History'
                    if playlist_id:
                        if playlist_id != 'HL' and playlist_id.strip().lower() != 'wl':
                            playlist_item_id = playlist_item_id_dict[video_id]
                            video_item.set_playlist_id(playlist_id)
                            video_item.set_playlist_item_id(playlist_item_id)
                            context_menu.append((context.localize(provider.LOCAL_MAP['youtube.remove']),
                                                 'RunPlugin(%s)' % context.create_uri(
                                                     ['playlist', 'remove', 'video'],
                                                     {'playlist_id': playlist_id, 'video_id': playlist_item_id,
                                                      'video_name': video_item.get_name()})))

            is_history = re.match('^/special/watch_history_tv/$', context.get_path())
            if is_history:
                yt_context_menu.append_clear_watch_history(context_menu, provider, context)

        # got to [CHANNEL]
        if channel_id and channel_name:
            # only if we are not directly in the channel provide a jump to the channel
            if kodion.utils.create_path('channel', channel_id) != context.get_path():
                video_item.set_channel_id(channel_id)
                yt_context_menu.append_go_to_channel(context_menu, provider, context, channel_id, channel_name)

        if provider.is_logged_in():
            # subscribe to the channel of the video
            video_item.set_subscription_id(channel_id)
            yt_context_menu.append_subscribe_to_channel(context_menu, provider, context, channel_id, channel_name)

        if not video_item.live and use_play_data:
            if play_data.get('play_count') is None or int(play_data.get('play_count')) == 0:
                yt_context_menu.append_mark_watched(context_menu, provider, context, video_id)
            else:
                yt_context_menu.append_mark_unwatched(context_menu, provider, context, video_id)

            if int(play_data.get('played_percent', '0')) > 0 or float(play_data.get('played_time', '0.0')) > 0.0:
                yt_context_menu.append_reset_resume_point(context_menu, provider, context, video_id)

        # more...
        refresh_container = \
            context.get_path().startswith('/channel/mine/playlist/LL') or \
            context.get_path() == '/special/disliked_videos/'
        yt_context_menu.append_more_for_video(context_menu, provider, context, video_id,
                                              is_logged_in=provider.is_logged_in(),
                                              refresh_container=refresh_container)

        if not video_item.live:
            yt_context_menu.append_play_with_subtitles(context_menu, provider, context, video_id)
            yt_context_menu.append_play_audio_only(context_menu, provider, context, video_id)

        if len(context_menu) > 0:
            video_item.set_context_menu(context_menu, replace=replace_context_menu)


def update_play_info(provider, context, video_id, video_item, video_stream, use_play_data=True):
    settings = context.get_settings()
    ui = context.get_ui()
    resource_manager = provider.get_resource_manager(context)
    video_data = resource_manager.get_videos([video_id])

    meta_data = video_stream.get('meta', None)
    thumb_size = settings.use_thumbnail_size()
    image = None

    if meta_data:
        video_item.set_subtitles(meta_data.get('subtitles', None))
        image = get_thumbnail(thumb_size, meta_data.get('images', {}))

    if 'headers' in video_stream:
        video_item.set_headers(video_stream['headers'])

    yt_item = video_data[video_id]

    snippet = yt_item['snippet']  # crash if not conform
    play_data = yt_item['play_data']
    video_item.live = snippet.get('liveBroadcastContent') == 'live'

    video_item.video_id = video_id

    # set the title
    if not video_item.get_title():
        video_item.set_title(snippet['title'])

    # set uses_dash
    video_item.set_use_dash(settings.use_dash())

    license_info = video_stream.get('license_info', {})

    if inputstreamhelper and \
            license_info.get('proxy') and \
            license_info.get('url') and \
            license_info.get('token'):
        ishelper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        ishelper.check_inputstream()

    video_item.set_license_key(license_info.get('proxy'))
    ui.set_home_window_property('license_url', license_info.get('url'))
    ui.set_home_window_property('license_token', license_info.get('token'))

    # duration
    if not video_item.live and use_play_data and play_data.get('total_time'):
        video_item.set_duration_from_seconds(float(play_data.get('total_time')))
    else:
        duration = yt_item.get('contentDetails', {}).get('duration', '')
        if duration:
            duration = utils.datetime_parser.parse(duration)
            # we subtract 1 seconds because YouTube returns +1 second to much
            video_item.set_duration_from_seconds(duration.seconds - 1)

    if not video_item.live and use_play_data:
        # play count
        if play_data.get('play_count'):
            video_item.set_play_count(int(play_data.get('play_count')))

        if play_data.get('played_percent'):
            video_item.set_start_percent(play_data.get('played_percent'))

        if play_data.get('played_time'):
            video_item.set_start_time(play_data.get('played_time'))

        if play_data.get('last_played'):
            video_item.set_last_played(play_data.get('last_played'))
    elif video_item.live:
        video_item.set_play_count(0)

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
    description = kodion.utils.strip_html_from_text(snippet['description'])
    if channel_name and settings.get_bool('youtube.view.description.show_channel_name', True):
        description = '%s[CR][CR]%s' % (ui.uppercase(ui.bold(channel_name)), description)
    video_item.set_studio(channel_name)
    # video_item.add_cast(channel_name)
    video_item.add_artist(channel_name)
    video_item.set_plot(description)

    # date time
    if 'publishedAt' in snippet and snippet['publishedAt']:
        date_time = utils.datetime_parser.parse(snippet['publishedAt'])
        video_item.set_year_from_datetime(date_time)
        video_item.set_aired_from_datetime(date_time)
        video_item.set_premiered_from_datetime(date_time)
        video_item.set_date_from_datetime(date_time)

    if not image:
        image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))

    if video_item.live and image:
        image = ''.join([image, '?ct=', get_thumb_timestamp()])
    video_item.set_image(image)

    # set fanart
    video_item.set_fanart(provider.get_fanart(context))

    return video_item


def update_fanarts(provider, context, channel_items_dict):
    # at least we need one channel id
    channel_ids = list(channel_items_dict.keys())
    if len(channel_ids) == 0:
        return

    fanarts = provider.get_resource_manager(context).get_fanarts(channel_ids)

    for channel_id in channel_ids:
        channel_items = channel_items_dict[channel_id]
        for channel_item in channel_items:
            # only set not empty fanarts
            fanart = fanarts.get(channel_id, '')
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
            context.log_debug('Found shelf index |{index}| for |{title}|'.format(index=str(shelf_index), title=shelf_title))
            break

    if shelf_index is not None:
        if 0 > shelf_index >= len(contents):
            context.log_debug('Shelf index |{index}| out of range |0-{content_length}|'.format(index=str(shelf_index), content_length=str(len(contents))))
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
