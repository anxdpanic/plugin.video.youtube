__author__ = 'bromix'

import random
import re

from ... import kodion
from ...kodion import constants
from ...kodion.items import VideoItem, AudioVideoItem
from ...youtube.youtube_exceptions import YouTubeException
from ...youtube.helper import utils, v3


def play_video(provider, context, re_match):
    try:
        video_id = context.get_param('video_id')
        client = provider.get_client(context)
        settings = context.get_settings()

        ask_for_quality = None
        screensaver = False
        if context.get_param('screensaver', None) and str(context.get_param('screensaver')).lower() == 'true':
            ask_for_quality = False
            screensaver = True

        video_streams = client.get_video_streams(context, video_id)
        if len(video_streams) == 0:
            message = context.localize(provider.LOCAL_MAP['youtube.error.no_video_streams_found'])
            context.get_ui().show_notification(message, time_milliseconds=5000)
            return False

        video_stream = kodion.utils.select_stream(context, video_streams, ask_for_quality=ask_for_quality)

        if video_stream is None:
            return False

        is_video = True if video_stream.get('video') else False

        if is_video and video_stream['video'].get('rtmpe', False):
            message = context.localize(provider.LOCAL_MAP['youtube.error.rtmpe_not_supported'])
            context.get_ui().show_notification(message, time_milliseconds=5000)
            return False

        suggested_param = str(context.get_param('suggested', True)).lower() == 'true'
        play_suggested = settings.get_bool('youtube.suggested_videos', False) and suggested_param
        items = None
        if play_suggested and not screensaver:
            try:
                json_data = client.get_related_videos(video_id)
                items = v3.response_to_items(provider, context, json_data, process_next_page=False)
            except:
                context.get_ui().show_notification('Failed to add suggested videos.', time_milliseconds=5000)
        if items:
            playlist = context.get_video_playlist()
            for i in items:
                playlist.add(i)

        title = video_stream.get('meta', {}).get('video', {}).get('title', '')
        if is_video:
            video_item = VideoItem(title, video_stream['url'])
        else:
            video_item = AudioVideoItem(title, video_stream['url'])

        video_item = utils.update_play_info(provider, context, video_id, video_item, video_stream)

        # Trigger post play events
        if provider.is_logged_in():
            try:
                if str(context.get_param('incognito', False)).lower() != 'true' and not screensaver:
                    command = 'RunPlugin(%s)' % context.create_uri(['events', 'post_play'], {'video_id': video_id})
                    context.get_ui().set_home_window_property('post_play', command)
            except:
                context.log_debug('Failed to set post play events.')

        context.get_ui().set_home_window_property('playing', video_id)

        return video_item
    except YouTubeException as ex:
        message = ex.get_message()
        message = kodion.utils.strip_html_from_text(message)
        context.get_ui().show_notification(message, time_milliseconds=15000)


def play_playlist(provider, context, re_match):
    videos = []

    def _load_videos(_page_token='', _progress_dialog=None):
        if not _progress_dialog:
            _progress_dialog = context.get_ui().create_progress_dialog(
                context.localize(provider.LOCAL_MAP['youtube.playlist.progress.updating']),
                context.localize(constants.localize.COMMON_PLEASE_WAIT), background=True)
        json_data = client.get_playlist_items(playlist_id, page_token=_page_token)
        if not v3.handle_error(provider, context, json_data):
            return False
        _progress_dialog.set_total(int(json_data.get('pageInfo', {}).get('totalResults', 0)))

        result = v3.response_to_items(provider, context, json_data, process_next_page=False)
        videos.extend(result)
        progress_text = '%s %d/%d' % (
            context.localize(constants.localize.COMMON_PLEASE_WAIT), len(videos), _progress_dialog.get_total())
        _progress_dialog.update(steps=len(result), text=progress_text)

        next_page_token = json_data.get('nextPageToken', '')
        if next_page_token:
            _load_videos(_page_token=next_page_token, _progress_dialog=_progress_dialog)

        return _progress_dialog

    # select order
    video_id = context.get_param('video_id', '')
    order = context.get_param('order', '')
    if not order:
        order_list = ['default', 'reverse']
        # we support shuffle only without a starting video position
        if not video_id:
            order_list.append('shuffle')
        items = []
        for order in order_list:
            items.append((context.localize(provider.LOCAL_MAP['youtube.playlist.play.%s' % order]), order))

        order = context.get_ui().on_select(context.localize(provider.LOCAL_MAP['youtube.playlist.play.select']), items)
        if not order in order_list:
            return False

    player = context.get_video_player()
    player.stop()

    playlist_id = context.get_param('playlist_id')
    client = provider.get_client(context)

    # start the loop and fill the list with video items
    progress_dialog = _load_videos()

    # reverse the list
    if order == 'reverse':
        videos = videos[::-1]
    elif order == 'shuffle':
        # we have to shuffle the playlist by our self. The implementation of XBMC/KODI is quite weak :(
        random.shuffle(videos)

    playlist_position = 0
    # check if we have a video as starting point for the playlist
    if video_id:
        find_video_id = re.compile(r'video_id=(?P<video_id>[^&]+)')
        for video in videos:
            video_id_match = find_video_id.search(video.get_uri())
            if video_id_match and video_id_match.group('video_id') == video_id:
                break
            playlist_position += 1

    # clear the playlist
    playlist = context.get_video_playlist()
    playlist.clear()

    # select unshuffle
    if order == 'shuffle':
        playlist.unshuffle()

    # add videos to playlist
    for video in videos:
        playlist.add(video)

    # we use the shuffle implementation of the playlist
    """
    if order == 'shuffle':
        playlist.shuffle()
    """

    if progress_dialog:
        progress_dialog.close()

    if (context.get_param('play', '') == '1') and (context.get_handle() == -1):
        player.play(playlist_index=playlist_position)
    elif context.get_param('play', '') == '1':
        return videos[playlist_position]

    return True


def play_channel_live(provider, context, re_match):
    channel_id = context.get_param('channel_id')
    index = int(context.get_param('live')) - 1
    if index < 0:
        index = 0
    json_data = provider.get_client(context).search(q='', search_type='video', event_type='live', channel_id=channel_id, safe_search=False)
    if not v3.handle_error(provider, context, json_data):
        return False

    video_items = v3.response_to_items(provider, context, json_data, process_next_page=False)

    try:
        video_item = video_items[index]
    except IndexError:
        return False

    player = context.get_video_player()
    player.stop()

    playlist = context.get_video_playlist()
    playlist.clear()
    playlist.add(video_item)

    if context.get_handle() == -1:
        player.play(playlist_index=0)
    else:
        return video_item
