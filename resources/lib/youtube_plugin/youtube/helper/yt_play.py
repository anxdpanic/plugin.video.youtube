# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import json
import random
import traceback

from ... import kodion
from ...kodion.items import VideoItem
from ...youtube.helper import utils, v3
from ...youtube.youtube_exceptions import YouTubeException


def play_video(provider, context):
    params = context.get_params()
    video_id = params.get('video_id')

    client = provider.get_client(context)
    settings = context.get_settings()
    ui = context.get_ui()

    ask_for_quality = None
    if video_id and ui.get_property('ask_for_quality') == video_id:
        ask_for_quality = True
    ui.clear_property('ask_for_quality')

    screensaver = False
    if params.get('screensaver'):
        ask_for_quality = False
        screensaver = True

    audio_only = None
    if video_id and ui.get_property('audio_only') == video_id:
        ask_for_quality = False
        audio_only = True
    ui.clear_property('audio_only')

    try:
        video_streams = client.get_video_streams(context, video_id)
    except YouTubeException as e:
        ui.show_notification(message=e.get_message())
        context.log_error(traceback.print_exc())
        return False

    if not video_streams:
        message = context.localize('error.no_video_streams_found')
        ui.show_notification(message, time_milliseconds=5000)
        return False

    video_stream = kodion.utils.select_stream(
        context,
        video_streams,
        ask_for_quality=ask_for_quality,
        audio_only=audio_only
    )

    if video_stream is None:
        return False

    is_video = video_stream.get('video')
    is_live = video_stream.get('Live')

    if is_video and video_stream['video'].get('rtmpe', False):
        message = context.localize('error.rtmpe_not_supported')
        ui.show_notification(message, time_milliseconds=5000)
        return False

    play_suggested = settings.get_bool('youtube.suggested_videos', False)
    if play_suggested and not screensaver:
        utils.add_related_video_to_playlist(provider,
                                            context,
                                            client,
                                            v3,
                                            video_id)

    metadata = video_stream.get('meta', {})

    title = metadata.get('video', {}).get('title', '')
    video_item = VideoItem(title, video_stream['url'])

    incognito = params.get('incognito', False)
    use_history = not is_live and not screensaver and not incognito
    use_remote_history = use_history and settings.use_remote_history()
    use_play_data = use_history and settings.use_local_history()

    utils.update_play_info(provider, context, video_id, video_item,
                           video_stream, use_play_data=use_play_data)

    seek_time = 0.0 if params.get('resume') else params.get('seek', 0.0)
    start_time = params.get('start', 0.0)
    end_time = params.get('end', 0.0)

    if start_time:
        video_item.set_start_time(start_time)
    if end_time:
        video_item.set_duration_from_seconds(end_time)

    play_count = use_play_data and video_item.get_play_count() or 0
    playback_stats = video_stream.get('playback_stats')

    playback_json = {
        'video_id': video_id,
        'channel_id': metadata.get('channel', {}).get('id', ''),
        'video_status': metadata.get('video', {}).get('status', {}),
        'playing_file': video_item.get_uri(),
        'play_count': play_count,
        'use_remote_history': use_remote_history,
        'use_local_history': use_play_data,
        'playback_stats': playback_stats,
        'seek_time': seek_time,
        'start_time': start_time,
        'end_time': end_time,
        'refresh_only': screensaver
    }

    ui.set_property('playback_json', json.dumps(playback_json))
    context.send_notification('PlaybackInit', {
        'video_id': video_id,
        'channel_id': playback_json.get('channel_id', ''),
        'status': playback_json.get('video_status', {})
    })
    return video_item


def play_playlist(provider, context):
    videos = []
    params = context.get_params()

    player = context.get_video_player()
    player.stop()

    playlist_ids = params.get('playlist_ids')
    if not playlist_ids:
        playlist_ids = [params.get('playlist_id')]

    client = provider.get_client(context)
    ui = context.get_ui()

    progress_dialog = ui.create_progress_dialog(
        context.localize('playlist.progress.updating'),
        context.localize('please_wait'),
        background=True
    )

    # start the loop and fill the list with video items
    total = 0
    for playlist_id in playlist_ids:
        page_token = 0
        while page_token is not None:
            json_data = client.get_playlist_items(playlist_id, page_token)
            if not v3.handle_error(context, json_data):
                return None

            if page_token == 0:
                total += int(json_data.get('pageInfo', {})
                             .get('totalResults', 0))
                progress_dialog.set_total(total)

            result = v3.response_to_items(provider,
                                          context,
                                          json_data,
                                          process_next_page=False)
            videos.extend(result)

            progress_dialog.update(
                steps=len(result),
                text='{wait} {current}/{total}'.format(
                    wait=context.localize('please_wait'),
                    current=len(videos),
                    total=total
                )
            )

            page_token = json_data.get('nextPageToken') or None

    # select order
    order = params.get('order', '')
    if not order:
        order_list = ['default', 'reverse', 'shuffle']
        items = [(context.localize('playlist.play.%s' % order), order)
                 for order in order_list]
        order = ui.on_select(context.localize('playlist.play.select'), items)
        if order not in order_list:
            order = 'default'

    # reverse the list
    if order == 'reverse':
        videos = videos[::-1]
    elif order == 'shuffle':
        # we have to shuffle the playlist by our self.
        # The implementation of XBMC/KODI is quite weak :(
        random.shuffle(videos)

    # clear the playlist
    playlist = context.get_video_playlist()
    playlist.clear()

    # select unshuffle
    if order == 'shuffle':
        playlist.unshuffle()

    # check if we have a video as starting point for the playlist
    video_id = params.get('video_id', '')
    # add videos to playlist
    playlist_position = 0
    for idx, video in enumerate(videos):
        playlist.add(video)
        if video_id and not playlist_position and video_id in video.get_uri():
            playlist_position = idx

    # we use the shuffle implementation of the playlist
    """
    if order == 'shuffle':
        playlist.shuffle()
    """

    if progress_dialog:
        progress_dialog.close()

    if not params.get('play'):
        return videos
    if context.get_handle() == -1:
        player.play(playlist_index=playlist_position)
        return False
    return videos[playlist_position]


def play_channel_live(provider, context):
    channel_id = context.get_param('channel_id')
    index = context.get_param('live') - 1
    if index < 0:
        index = 0
    json_data = provider.get_client(context).search(q='', search_type='video', event_type='live', channel_id=channel_id, safe_search=False)
    if not v3.handle_error(context, json_data):
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
        return False
    return video_item
