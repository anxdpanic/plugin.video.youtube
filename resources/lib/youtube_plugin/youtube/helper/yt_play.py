import random
import re

__author__ = 'bromix'

from ... import kodion
from ...kodion import constants
from ...kodion.items import VideoItem
from ...youtube.youtube_exceptions import YouTubeException
from ...youtube.helper import utils, v3


def play_video(provider, context, re_match):
    try:
        video_id = context.get_param('video_id')
        client = provider.get_client(context)
        settings = context.get_settings()

        video_streams = client.get_video_streams(context, video_id)
        if len(video_streams) == 0:
            message = context.localize(provider.LOCAL_MAP['youtube.error.no_video_streams_found'])
            context.get_ui().show_notification(message, time_milliseconds=5000)
            return False

        video_stream = kodion.utils.select_stream(context, video_streams)

        if video_stream is None:
            return False

        if video_stream['video'].get('rtmpe', False):
            message = context.localize(provider.LOCAL_MAP['youtube.error.rtmpe_not_supported'])
            context.get_ui().show_notification(message, time_milliseconds=5000)
            return False

        play_suggested = settings.get_bool('youtube.suggested_videos', False)
        items = None
        if play_suggested:
            try:
                json_data = client.get_related_videos(video_id)
                items = v3.response_to_items(provider, context, json_data, process_next_page=False)
            except:
                context.get_ui().show_notification('Failed to add suggested videos.', time_milliseconds=5000)
        if items:
            playlist = context.get_video_playlist()
            for i in items:
                playlist.add(i)

        video_item = VideoItem(video_id, video_stream['url'])

        if video_stream.get('meta', None):
            video_item.set_subtitles(video_stream['meta'].get('subtitles', None))

        video_id_dict = {video_id: video_item}
        utils.update_video_infos(provider, context, video_id_dict)

        # Trigger post play events
        if provider.is_logged_in():
            try:
                command = 'RunPlugin(%s)' % context.create_uri(['events', 'post_play'], {'video_id': video_id})
                context.execute(command)
            except:
                context.get_ui().show_notification('Failed to execute post play events.', time_milliseconds=5000)

        return video_item
    except YouTubeException, ex:
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
            pass
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
            pass

        return _progress_dialog

    # select order
    video_id = context.get_param('video_id', '')
    order = context.get_param('order', '')
    if not order:
        order_list = ['default', 'reverse']
        # we support shuffle only without a starting video position
        if not video_id:
            order_list.append('shuffle')
            pass
        items = []
        for order in order_list:
            items.append((context.localize(provider.LOCAL_MAP['youtube.playlist.play.%s' % order]), order))
            pass

        order = context.get_ui().on_select(context.localize(provider.LOCAL_MAP['youtube.playlist.play.select']), items)
        if not order in order_list:
            return False
        pass

    player = context.get_video_player()
    player.stop()

    playlist_id = context.get_param('playlist_id')
    client = provider.get_client(context)

    # start the loop and fill the list with video items
    progress_dialog = _load_videos()

    # reverse the list
    if order == 'reverse':
        videos = videos[::-1]
        pass
    elif order == 'shuffle':
        # we have to shuffle the playlist by our self. The implementation of XBMC/KODI is quite weak :(
        random.shuffle(videos)
        pass

    playlist_position = 0
    # check if we have a video as starting point for the playlist
    if video_id:
        find_video_id = re.compile(r'video_id=(?P<video_id>[^&]+)')
        for video in videos:
            video_id_match = find_video_id.search(video.get_uri())
            if video_id_match and video_id_match.group('video_id') == video_id:
                break
            playlist_position += 1
            pass
        pass

    # clear the playlist
    playlist = context.get_video_playlist()
    playlist.clear()

    # select unshuffle
    if order == 'shuffle':
        playlist.unshuffle()
        pass

    # add videos to playlist
    for video in videos:
        playlist.add(video)
        pass

    # we use the shuffle implementation of the playlist
    """
    if order == 'shuffle':
        playlist.shuffle()
        pass
    """

    if progress_dialog:
        progress_dialog.close()
        pass

    if (context.get_param('play', '') == '1') and (context.get_handle() == -1):
        player.play(playlist_index=playlist_position)
    elif context.get_param('play', '') == '1':
        return videos[playlist_position]

    return True
