__author__ = 'bromix'
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

    re_url = re.compile('(https?://[^\s]+)')
    matches = re_url.findall(text)
    result = matches or result

    return result


def get_thumb_timestamp(minutes=15):
    return str(time.mktime(time.gmtime(minutes * 60 * (round(time.time() / (minutes * 60))))))


def update_channel_infos(provider, context, channel_id_dict, subscription_id_dict={}, channel_items_dict=None):
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

        # update channel mapping
        if channel_items_dict is not None:
            if not channel_id in channel_items_dict:
                channel_items_dict[channel_id] = []
            channel_items_dict[channel_id].append(channel_item)


def update_playlist_infos(provider, context, playlist_id_dict, channel_items_dict=None):
    playlist_ids = list(playlist_id_dict.keys())
    if len(playlist_ids) == 0:
        return

    resource_manager = provider.get_resource_manager(context)
    playlist_data = resource_manager.get_playlists(playlist_ids)

    custom_watch_later_id = context.get_settings().get_string('youtube.folder.watch_later.playlist', '').strip()
    custom_history_id = context.get_settings().get_string('youtube.folder.history.playlist', '').strip()

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
            if not channel_id in channel_items_dict:
                channel_items_dict[channel_id] = []
            channel_items_dict[channel_id].append(playlist_item)


def update_video_infos(provider, context, video_id_dict, playlist_item_id_dict=None, channel_items_dict=None):
    settings = context.get_settings()

    video_ids = list(video_id_dict.keys())
    if len(video_ids) == 0:
        return

    if not playlist_item_id_dict:
        playlist_item_id_dict = {}

    resource_manager = provider.get_resource_manager(context)
    video_data = resource_manager.get_videos(video_ids)

    my_playlists = {}
    if provider.is_logged_in():
        my_playlists = resource_manager.get_related_playlists(channel_id='mine')

    thumb_size = settings.use_thumbnail_size()
    thumb_stamp = get_thumb_timestamp()
    for video_id in list(video_data.keys()):
        yt_item = video_data[video_id]
        video_item = video_id_dict[video_id]

        snippet = yt_item['snippet']  # crash if not conform

        # set uses_dash
        video_item.set_use_dash(settings.use_dash())

        # set mediatype
        video_item.set_mediatype('video')  # using video

        # set the title
        if not video_item.get_title():
            video_item.set_title(snippet['title'])

        if not video_item.use_dash() and not settings.is_support_alternative_player_enabled() and \
                video_item.get_headers() and video_item.get_uri().startswith('http'):
            video_item.set_uri(video_item.get_uri() + '|' + video_item.get_headers())

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
            description = '[UPPERCASE][B]%s[/B][/UPPERCASE][CR][CR]%s' % (channel_name, description)
        video_item.set_studio(channel_name)
        # video_item.add_cast(channel_name)
        video_item.add_artist(channel_name)
        video_item.set_plot(description)

        # date time
        if 'publishedAt' in snippet:
            datetime = utils.datetime_parser.parse(snippet['publishedAt'])
            video_item.set_year_from_datetime(datetime)
            video_item.set_aired_from_datetime(datetime)
            video_item.set_premiered_from_datetime(datetime)
            video_item.set_date_from_datetime(datetime)

        # duration
        duration = yt_item.get('contentDetails', {}).get('duration', '')
        duration = utils.datetime_parser.parse(duration)
        # we subtract 1 seconds because YouTube returns +1 second to much
        video_item.set_duration_from_seconds(duration.seconds - 1)

        # try to find a better resolution for the image
        image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))
        if image.endswith('_live.jpg'):
            image += '?ct=' + thumb_stamp
        video_item.set_image(image)

        # set fanart
        video_item.set_fanart(provider.get_fanart(context))

        # update channel mapping
        channel_id = snippet.get('channelId', '')
        if channel_items_dict is not None:
            if not channel_id in channel_items_dict:
                channel_items_dict[channel_id] = []
            channel_items_dict[channel_id].append(video_item)

        context_menu = []
        replace_context_menu = False

        # Refresh ('My Subscriptions')
        if context.get_path().startswith('/special/new_uploaded_videos_tv') or \
                context.get_path().startswith('/channel/mine/playlist/'):
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
            watch_later_playlist_id = my_playlists.get('watchLater', '')
            if not watch_later_playlist_id or re.match('^\s*WL$', watch_later_playlist_id):
                cplid = settings.get_string('youtube.folder.watch_later.playlist', ' WL').strip()
                if re.match('^\s*(?:WL)*$', cplid):
                    cplid = ' WL'
                watch_later_playlist_id = cplid
            yt_context_menu.append_watch_later(context_menu, provider, context, watch_later_playlist_id, video_id)

            # provide 'remove' for videos in my playlists
            if video_id in playlist_item_id_dict:
                playlist_match = re.match('^/channel/mine/playlist/(?P<playlist_id>[^/]+)/$', context.get_path())
                if playlist_match:
                    playlist_id = playlist_match.group('playlist_id')
                    # we support all playlist except 'Watch History'
                    if not playlist_id.startswith('HL'):
                        playlist_item_id = playlist_item_id_dict[video_id]
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
                yt_context_menu.append_go_to_channel(context_menu, provider, context, channel_id, channel_name)

        if provider.is_logged_in():
            # subscribe to the channel of the video
            yt_context_menu.append_subscribe_to_channel(context_menu, provider, context, channel_id, channel_name)

        # more...
        refresh_container = context.get_path().startswith('/channel/mine/playlist/LL') or \
                            context.get_path() == '/special/disliked_videos/'
        yt_context_menu.append_more_for_video(context_menu, provider, context, video_id,
                                              is_logged_in=provider.is_logged_in(),
                                              refresh_container=refresh_container)

        if len(context_menu) > 0:
            video_item.set_context_menu(context_menu, replace=replace_context_menu)


def update_play_info(provider, context, video_id, video_item, video_stream):
    settings = context.get_settings()
    ui = context.get_ui()
    resource_manager = provider.get_resource_manager(context)
    video_data = resource_manager.get_videos([video_id])

    meta_data = video_stream.get('meta', None)
    live = video_stream.get('Live', False)

    thumb_size = settings.use_thumbnail_size()
    image = None

    if meta_data:
        video_item.set_subtitles(meta_data.get('subtitles', None))
        video_item.set_headers(meta_data.get('headers', ''))
        image = get_thumbnail(thumb_size, meta_data.get('images', {}))

    yt_item = video_data[video_id]

    snippet = yt_item['snippet']  # crash if not conform

    # set uses_dash
    video_item.set_use_dash(settings.use_dash())

    # set mediatype
    video_item.set_mediatype('video')  # using video

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

    # set the title
    if not video_item.get_title():
        video_item.set_title(snippet['title'])

    if not video_item.use_dash() and not settings.is_support_alternative_player_enabled() and \
            video_item.get_headers() and video_item.get_uri().startswith('http'):
        video_item.set_uri(video_item.get_uri() + '|' + video_item.get_headers())

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
        description = '[UPPERCASE][B]%s[/B][/UPPERCASE][CR][CR]%s' % (channel_name, description)
    video_item.set_studio(channel_name)
    # video_item.add_cast(channel_name)
    video_item.add_artist(channel_name)
    video_item.set_plot(description)

    # date time
    if 'publishedAt' in snippet:
        date_time = utils.datetime_parser.parse(snippet['publishedAt'])
        video_item.set_year_from_datetime(date_time)
        video_item.set_aired_from_datetime(date_time)
        video_item.set_premiered_from_datetime(date_time)
        video_item.set_date_from_datetime(date_time)

    # duration
    duration = yt_item.get('contentDetails', {}).get('duration', '')
    duration = utils.datetime_parser.parse(duration)
    # we subtract 1 seconds because YouTube returns +1 second to much
    video_item.set_duration_from_seconds(duration.seconds - 1)

    if not image:
        image = get_thumbnail(thumb_size, snippet.get('thumbnails', {}))

    if live and image:
        image += '?ct=' + get_thumb_timestamp()
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
