# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import random
from traceback import format_stack

from ..helper import utils, v3
from ..youtube_exceptions import YouTubeException
from ...kodion.compatibility import urlencode, urlunsplit
from ...kodion.constants import SWITCH_PLAYER_FLAG, paths
from ...kodion.items import VideoItem
from ...kodion.network import get_connect_address
from ...kodion.utils import select_stream


def play_video(provider, context):
    ui = context.get_ui()
    params = context.get_params()
    video_id = params.get('video_id')
    if not video_id:
        message = context.localize('error.no_video_streams_found')
        ui.show_notification(message, time_ms=5000)
        return False

    client = provider.get_client(context)
    settings = context.get_settings()

    incognito = params.get('incognito', False)
    screensaver = params.get('screensaver', False)

    is_external = ui.get_property(SWITCH_PLAYER_FLAG)
    if ((is_external and settings.alternative_player_web_urls())
            or settings.default_player_web_urls()):
        video_stream = {
            'url': 'https://www.youtube.com/watch?v={0}'.format(video_id),
        }
    else:
        ask_for_quality = None
        if not screensaver and ui.get_property('ask_for_quality') == video_id:
            ask_for_quality = True
        ui.clear_property('ask_for_quality')

        audio_only = None
        if ui.get_property('audio_only') == video_id:
            ask_for_quality = False
            audio_only = True
        ui.clear_property('audio_only')

        try:
            video_streams = client.get_video_streams(context, video_id)
        except YouTubeException as exc:
            context.log_error('yt_play.play_video - {exc}:\n{details}'.format(
                exc=exc, details=''.join(format_stack())
            ))
            ui.show_notification(message=exc.get_message())
            return False

        if not video_streams:
            message = context.localize('error.no_video_streams_found')
            ui.show_notification(message, time_ms=5000)
            return False

        video_stream = select_stream(
            context,
            video_streams,
            ask_for_quality=ask_for_quality,
            audio_only=audio_only,
            use_adaptive_formats=(not is_external
                                  or settings.alternative_player_adaptive()),
        )

        if video_stream is None:
            return False

    video_type = video_stream.get('video')
    if video_type and video_type.get('rtmpe'):
        message = context.localize('error.rtmpe_not_supported')
        ui.show_notification(message, time_ms=5000)
        return False

    play_suggested = settings.get_bool('youtube.suggested_videos', False)
    if play_suggested and not screensaver:
        utils.add_related_video_to_playlist(provider,
                                            context,
                                            client,
                                            v3,
                                            video_id)

    metadata = video_stream.get('meta', {})
    video_details = metadata.get('video', {})

    if is_external:
        url = urlunsplit((
            'http',
            get_connect_address(as_netloc=True),
            paths.REDIRECT,
            urlencode({'url': video_stream['url']}),
            '',
        ))
        video_stream['url'] = url
    video_item = VideoItem(video_details.get('title', ''), video_stream['url'])

    use_history = not (screensaver or incognito or video_stream.get('Live'))
    use_remote_history = use_history and settings.use_remote_history()
    use_play_data = use_history and settings.use_local_history()

    utils.update_play_info(provider, context, video_id, video_item,
                           video_stream, use_play_data=use_play_data)

    seek_time = 0.0 if params.get('resume') else params.get('seek', 0.0)
    start_time = params.get('start', 0.0)
    end_time = params.get('end', 0.0)

    if start_time:
        video_item.set_start_time(start_time)
    # Setting the duration based on end_time can cause issues with
    # listing/sorting and other addons that monitor playback
    # if end_time:
    #     video_item.set_duration_from_seconds(end_time)

    play_count = use_play_data and video_item.get_play_count() or 0
    playback_stats = video_stream.get('playback_stats')

    playback_json = {
        'video_id': video_id,
        'channel_id': metadata.get('channel', {}).get('id', ''),
        'video_status': video_details.get('status', {}),
        'playing_file': video_item.get_uri(),
        'play_count': play_count,
        'use_remote_history': use_remote_history,
        'use_local_history': use_play_data,
        'playback_stats': playback_stats,
        'seek_time': seek_time,
        'start_time': start_time,
        'end_time': end_time,
        'clip': params.get('clip'),
        'refresh_only': screensaver
    }

    ui.set_property('playback_json', json.dumps(playback_json,
                                                ensure_ascii=False))
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

    resource_manager = provider.get_resource_manager(context)
    ui = context.get_ui()

    with ui.create_progress_dialog(
            context.localize('playlist.progress.updating'),
            context.localize('please_wait'),
            background=True
    ) as progress_dialog:
        json_data = resource_manager.get_playlist_items(playlist_ids)

        total = sum(len(chunk.get('items', [])) for chunk in json_data.values())
        progress_dialog.set_total(total)
        progress_dialog.update(
            steps=0,
            text='{wait} {current}/{total}'.format(
                wait=context.localize('please_wait'),
                current=0,
                total=total
            )
        )

        # start the loop and fill the list with video items
        for chunk in json_data.values():
            result = v3.response_to_items(provider,
                                          context,
                                          chunk,
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

        if not videos:
            return False

        # select order
        order = params.get('order', '')
        if not order:
            order_list = ('default', 'reverse', 'shuffle')
            items = [(context.localize('playlist.play.%s' % order), order)
                     for order in order_list]
            order = ui.on_select(context.localize('playlist.play.select'),
                                 items)
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
            if (video_id and not playlist_position
                    and video_id in video.get_uri()):
                playlist_position = idx

        # we use the shuffle implementation of the playlist
        """
        if order == 'shuffle':
            playlist.shuffle()
        """

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
    json_data = provider.get_client(context).search(q='',
                                                    search_type='video',
                                                    event_type='live',
                                                    channel_id=channel_id,
                                                    safe_search=False)
    if not json_data:
        return False

    video_items = v3.response_to_items(provider,
                                       context,
                                       json_data,
                                       process_next_page=False)

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
