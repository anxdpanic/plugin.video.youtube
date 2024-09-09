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
from ...kodion.constants import (
    BUSY_FLAG,
    PATHS,
    PLAYBACK_INIT,
    PLAYER_DATA,
    PLAYLIST_PATH,
    PLAYLIST_POSITION,
    PLAY_FORCE_AUDIO,
    PLAY_PROMPT_QUALITY,
    PLAY_PROMPT_SUBTITLES,
    PLAY_TIMESHIFT,
    PLAY_WITH,
    SERVER_POST_START,
    SERVER_WAKEUP,
)
from ...kodion.items import AudioItem, VideoItem
from ...kodion.network import get_connect_address
from ...kodion.utils import find_video_id, select_stream


def _play_stream(provider, context):
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

    audio_only = False
    is_external = ui.get_property(PLAY_WITH)
    if ((is_external and settings.alternative_player_web_urls())
            or settings.default_player_web_urls()):
        stream = {
            'url': 'https://youtu.be/{0}'.format(video_id),
        }
    else:
        ask_for_quality = settings.ask_for_video_quality()
        if ui.pop_property(PLAY_PROMPT_QUALITY) and not screensaver:
            ask_for_quality = True
        elif ui.pop_property(PLAY_FORCE_AUDIO):
            audio_only = True
        else:
            audio_only = settings.audio_only()

        try:
            streams = client.get_streams(context,
                                         video_id,
                                         ask_for_quality,
                                         audio_only,
                                         settings.use_mpd_videos())
        except YouTubeException as exc:
            context.log_error('yt_play.play_video - {exc}:\n{details}'.format(
                exc=exc, details=''.join(format_stack())
            ))
            ui.show_notification(message=exc.get_message())
            return False

        if not streams:
            message = context.localize('error.no_video_streams_found')
            ui.show_notification(message, time_ms=5000)
            return False

        stream = select_stream(
            context,
            streams,
            ask_for_quality=ask_for_quality,
            audio_only=audio_only,
            use_adaptive_formats=(not is_external
                                  or settings.alternative_player_adaptive()),
        )

        if stream is None:
            return False

    video_type = stream.get('video')
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

    metadata = stream.get('meta', {})
    if is_external:
        url = urlunsplit((
            'http',
            get_connect_address(context=context, as_netloc=True),
            PATHS.REDIRECT,
            urlencode({'url': stream['url']}),
            '',
        ))
        stream['url'] = url

    if audio_only or not video_type:
        media_item = AudioItem(metadata.get('title', ''), stream['url'])
    else:
        media_item = VideoItem(metadata.get('title', ''), stream['url'])

    use_history = not (screensaver or incognito or stream.get('live'))
    use_remote_history = use_history and settings.use_remote_history()
    use_play_data = use_history and settings.use_local_history()

    utils.update_play_info(provider, context, video_id, media_item,
                           stream, use_play_data=use_play_data)

    seek_time = 0.0 if params.get('resume') else params.get('seek', 0.0)
    start_time = params.get('start', 0.0)
    end_time = params.get('end', 0.0)

    if start_time:
        media_item.set_start_time(start_time)
    # Setting the duration based on end_time can cause issues with
    # listing/sorting and other addons that monitor playback
    # if end_time:
    #     video_item.set_duration_from_seconds(end_time)

    play_count = use_play_data and media_item.get_play_count() or 0
    playback_stats = stream.get('playback_stats')

    playback_data = {
        'video_id': video_id,
        'channel_id': metadata.get('channel', {}).get('id', ''),
        'video_status': metadata.get('status', {}),
        'playing_file': media_item.get_uri(),
        'play_count': play_count,
        'use_remote_history': use_remote_history,
        'use_local_history': use_play_data,
        'playback_stats': playback_stats,
        'seek_time': seek_time,
        'start_time': start_time,
        'end_time': end_time,
        'clip': params.get('clip', False),
        'refresh_only': screensaver
    }

    ui.set_property(PLAYER_DATA, json.dumps(playback_data, ensure_ascii=False))
    context.send_notification(PLAYBACK_INIT, playback_data)
    return media_item


def _play_playlist(provider, context):
    videos = []
    params = context.get_params()

    playlist_player = context.get_playlist_player()
    playlist_player.stop()

    action = params.get('action')
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

        if action == 'list':
            return videos

        # clear the playlist
        playlist_player.clear()
        playlist_player.unshuffle()

        # check if we have a video as starting point for the playlist
        video_id = params.get('video_id')
        playlist_position = None if video_id else 0
        # add videos to playlist
        for idx, video in enumerate(videos):
            playlist_player.add(video)
            if playlist_position is None and video.video_id == video_id:
                playlist_position = idx

    options = {
        provider.RESULT_CACHE_TO_DISC: False,
        provider.RESULT_FORCE_RESOLVE: True,
        provider.RESULT_UPDATE_LISTING: False,
    }

    if action == 'queue':
        return videos, options
    if context.get_handle() == -1 or action == 'play':
        playlist_player.play(playlist_index=playlist_position)
        return False
    return videos[playlist_position], options


def _play_channel_live(provider, context):
    channel_id = context.get_param('channel_id')
    index = context.get_param('live', 1) - 1
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

    playlist_player = context.get_playlist_player()
    playlist_player.stop()
    playlist_player.clear()
    playlist_player.add(video_item)

    if context.get_handle() == -1:
        playlist_player.play(playlist_index=0)
        return False
    return video_item


def process(provider, context, **_kwargs):
    ui = context.get_ui()

    params = context.get_params()
    param_keys = params.keys()

    if {'channel_id', 'playlist_id', 'playlist_ids', 'video_id'}.isdisjoint(
            param_keys
    ):
        listitem_path = context.get_listitem_info('FileNameAndPath')
        if context.is_plugin_path(listitem_path, PATHS.PLAY):
            video_id = find_video_id(listitem_path)
            if video_id:
                context.set_param('video_id', video_id)
                params['video_id'] = video_id
            else:
                return False
        else:
            return False

    video_id = params.get('video_id')
    playlist_id = params.get('playlist_id')

    force_play = False
    for param in {PLAY_FORCE_AUDIO,
                  PLAY_TIMESHIFT,
                  PLAY_PROMPT_QUALITY,
                  PLAY_PROMPT_SUBTITLES,
                  PLAY_WITH}.intersection(param_keys):
        del params[param]
        ui.set_property(param)
        force_play = True

    if video_id and not playlist_id:
        # This is required to trigger Kodi resume prompt, along with using
        # RunPlugin. Prompt will not be used if using PlayMedia
        if force_play:
            context.execute('Action(Play)')
            return False

        if context.get_handle() == -1:
            context.execute('PlayMedia({0})'.format(
                context.create_uri(('play',), params)
            ))
            return False

        ui.set_property(BUSY_FLAG)
        playlist_player = context.get_playlist_player()
        position, _ = playlist_player.get_position()
        items = playlist_player.get_items()

        ui.clear_property(SERVER_POST_START)
        context.wakeup(SERVER_WAKEUP, timeout=5)
        media_item = _play_stream(provider, context)
        ui.set_property(SERVER_POST_START)

        if media_item:
            if position and items:
                ui.set_property(PLAYLIST_PATH,
                                items[position - 1]['file'])
                ui.set_property(PLAYLIST_POSITION, str(position))
        else:
            ui.clear_property(BUSY_FLAG)

        return media_item

    if playlist_id or 'playlist_ids' in params:
        return _play_playlist(provider, context)

    if 'channel_id' in params:
        return _play_channel_live(provider, context)
    return False
