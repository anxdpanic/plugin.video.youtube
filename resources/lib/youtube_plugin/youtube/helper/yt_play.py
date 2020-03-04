# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import json
import random
import re
import traceback

import xbmcplugin

from ... import kodion
from ...kodion import constants
from ...kodion.items import VideoItem
from ...kodion.impl.xbmc.xbmc_items import to_playback_item
from ...youtube.youtube_exceptions import YouTubeException
from ...youtube.helper import utils, v3


def play_video(provider, context):
    try:
        video_id = context.get_param('video_id')

        client = provider.get_client(context)
        settings = context.get_settings()

        ask_for_quality = None
        if video_id and context.get_ui().get_home_window_property('ask_for_quality') == video_id:
            ask_for_quality = True
        context.get_ui().clear_home_window_property('ask_for_quality')

        screensaver = False
        if context.get_param('screensaver', None) and str(context.get_param('screensaver')).lower() == 'true':
            ask_for_quality = False
            screensaver = True

        audio_only = None
        if video_id and context.get_ui().get_home_window_property('audio_only') == video_id:
            ask_for_quality = False
            audio_only = True
        context.get_ui().clear_home_window_property('audio_only')

        try:
            video_streams = client.get_video_streams(context, video_id)
        except YouTubeException as e:
            context.get_ui().show_notification(message=e.get_message())
            context.log_error(traceback.print_exc())
            return False

        if len(video_streams) == 0:
            message = context.localize(provider.LOCAL_MAP['youtube.error.no_video_streams_found'])
            context.get_ui().show_notification(message, time_milliseconds=5000)
            return False

        video_stream = kodion.utils.select_stream(context, video_streams, ask_for_quality=ask_for_quality, audio_only=audio_only)

        if video_stream is None:
            return False

        is_video = True if video_stream.get('video') else False
        is_live = video_stream.get('Live') is True

        if is_video and video_stream['video'].get('rtmpe', False):
            message = context.localize(provider.LOCAL_MAP['youtube.error.rtmpe_not_supported'])
            context.get_ui().show_notification(message, time_milliseconds=5000)
            return False

        play_suggested = settings.get_bool('youtube.suggested_videos', False)
        if play_suggested and not screensaver:
            utils.add_related_video_to_playlist(provider, context, client, v3, video_id)

        metadata = video_stream.get('meta', {})

        title = metadata.get('video', {}).get('title', '')
        video_item = VideoItem(title, video_stream['url'])

        incognito = str(context.get_param('incognito', False)).lower() == 'true'
        use_history = not is_live and not screensaver and not incognito
        playback_history = use_history and settings.use_playback_history()

        video_item = utils.update_play_info(provider, context, video_id, video_item, video_stream,
                                            use_play_data=playback_history)

        seek_time = None
        play_count = 0
        playback_stats = video_stream.get('playback_stats')

        if use_history:
            major_version = context.get_system_version().get_version()[0]
            if video_item.get_start_time() and video_item.use_dash() and major_version > 17:
                seek_time = video_item.get_start_time()
            play_count = video_item.get_play_count() if video_item.get_play_count() is not None else '0'

        item = to_playback_item(context, video_item)
        item.setPath(video_item.get_uri())

        try:
            seek = float(context.get_param('seek', None))
            if seek:
                seek_time = seek
        except (ValueError, TypeError):
            pass

        playback_json = {
            "video_id": video_id,
            "channel_id": metadata.get('channel', {}).get('id', ''),
            "video_status": metadata.get('video', {}).get('status', {}),
            "playing_file": video_item.get_uri(),
            "play_count": play_count,
            "use_history": use_history,
            "playback_history": playback_history,
            "playback_stats": playback_stats,
            "seek_time": seek_time,
            "refresh_only": screensaver
        }

        context.get_ui().set_home_window_property('playback_json', json.dumps(playback_json))
        context.send_notification('PlaybackInit', {
            'video_id': video_id,
            'channel_id': playback_json.get('channel_id', ''),
            'status': playback_json.get('video_status', {})
        })
        xbmcplugin.setResolvedUrl(handle=context.get_handle(), succeeded=True, listitem=item)

    except YouTubeException as ex:
        message = ex.get_message()
        message = kodion.utils.strip_html_from_text(message)
        context.get_ui().show_notification(message, time_milliseconds=15000)


def play_playlist(provider, context):
    videos = []

    def _load_videos(_page_token='', _progress_dialog=None):
        if _progress_dialog is None:
            _progress_dialog = context.get_ui().create_progress_dialog(
                context.localize(provider.LOCAL_MAP['youtube.playlist.progress.updating']),
                context.localize(constants.localize.COMMON_PLEASE_WAIT), background=True)
        json_data = client.get_playlist_items(playlist_id, page_token=_page_token)
        if not v3.handle_error(provider, context, json_data):
            return None
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
        if order not in order_list:
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
        return
    elif context.get_param('play', '') == '1':
        return videos[playlist_position]

    return True


def play_channel_live(provider, context):
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
