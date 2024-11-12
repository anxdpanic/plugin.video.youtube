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
    CONTENT,
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
    SERVER_WAKEUP,
)
from ...kodion.items import AudioItem, UriItem, VideoItem
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
        use_adaptive_formats = (not is_external
                                or settings.alternative_player_adaptive())
        use_mpd = (use_adaptive_formats
                   and settings.use_mpd_videos()
                   and context.wakeup(SERVER_WAKEUP, timeout=5))

        try:
            streams = client.get_streams(
                context,
                video_id=video_id,
                ask_for_quality=ask_for_quality,
                audio_only=audio_only,
                use_mpd=use_mpd,
            )
        except YouTubeException as exc:
            msg = ('yt_play.play_video - Error'
                   '\n\tException: {exc!r}'
                   '\n\tStack trace (most recent call last):\n{stack}'
                   .format(exc=exc,
                           stack=''.join(format_stack())))
            context.log_error(msg)
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
            use_adaptive_formats=use_adaptive_formats,
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

    media_item = (AudioItem if audio_only or not video_type else VideoItem)(
        name=metadata.get('title', ''),
        uri=stream['url'],
        video_id=video_id,
    )

    use_history = not (screensaver or incognito or stream.get('live'))
    use_remote_history = use_history and settings.use_remote_history()
    use_local_history = use_history and settings.use_local_history()

    utils.update_play_info(provider, context, video_id, media_item, stream)

    seek_time = 0.0 if params.get('resume') else params.get('seek', 0.0)
    start_time = params.get('start', 0.0)
    end_time = params.get('end', 0.0)

    if start_time:
        media_item.set_start_time(start_time)
    # Setting the duration based on end_time can cause issues with
    # listing/sorting and other addons that monitor playback
    # if end_time:
    #     video_item.set_duration_from_seconds(end_time)

    play_count = use_local_history and media_item.get_play_count() or 0
    playback_stats = stream.get('playback_stats')

    playback_data = {
        'video_id': video_id,
        'channel_id': metadata.get('channel', {}).get('id', ''),
        'video_status': metadata.get('status', {}),
        'playing_file': media_item.get_uri(),
        'play_count': play_count,
        'use_remote_history': use_remote_history,
        'use_local_history': use_local_history,
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
    video_items = []
    params = context.get_params()

    action = params.get('action')
    if not action and context.get_handle() == -1:
        action = 'play'

    playlist_ids = params.get('playlist_ids')
    if not playlist_ids:
        playlist_ids = [params.get('playlist_id')]
    video_id = params.get('video_id')

    resource_manager = provider.get_resource_manager(context)
    ui = context.get_ui()

    with ui.create_progress_dialog(
            heading=context.localize('playlist.progress.updating'),
            message=context.localize('please_wait'),
            background=True,
            message_template=(
                    '{wait} {{current}}/{{total}}'.format(
                        wait=context.localize('please_wait'),
                    )
            ),
    ) as progress_dialog:
        json_data = resource_manager.get_playlist_items(playlist_ids)

        total = sum(len(chunk.get('items', [])) for chunk in json_data.values())
        progress_dialog.set_total(total)
        progress_dialog.update(
            steps=0,
            current=0,
            total=total,
        )

        # start the loop and fill the list with video items
        for chunk in json_data.values():
            result = v3.response_to_items(provider,
                                          context,
                                          chunk,
                                          process_next_page=False)
            video_items.extend(result)

            progress_dialog.update(
                steps=len(result),
                current=len(video_items),
                total=total,
            )

        if not video_items:
            return False

        return (
            process_items_for_playlist(context, video_items, action, video_id),
            {
                provider.RESULT_CACHE_TO_DISC: False,
                provider.RESULT_FORCE_RESOLVE: True,
                provider.RESULT_UPDATE_LISTING: True,
            },
        )


def _play_channel_live(provider, context):
    channel_id = context.get_param('channel_id')
    _, json_data = provider.get_client(context).search_with_params(params={
        'type': 'video',
        'eventType': 'live',
        'channelId': channel_id,
        'safeSearch': 'none',
    })
    if not json_data:
        return False

    channel_streams = v3.response_to_items(provider,
                                           context,
                                           json_data,
                                           process_next_page=False)
    if not channel_streams:
        return False

    return (
        process_items_for_playlist(
            context,
            channel_streams,
            action='play' if context.get_handle() == -1 else None,
            play_from=context.get_param('live', 1),
        ),
        {
            provider.RESULT_CACHE_TO_DISC: False,
            provider.RESULT_FORCE_RESOLVE: True,
            provider.RESULT_UPDATE_LISTING: True,
        },
    )


def process(provider, context, **_kwargs):
    """
    Plays a video, playlist, or channel live stream.

    Video:
    plugin://plugin.video.youtube/play/?video_id=<VIDEO_ID>

    * VIDEO_ID: YouTube Video ID

    Playlist:
    plugin://plugin.video.youtube/play/?playlist_id=<PLAYLIST_ID>[&order=<ORDER>][&action=<ACTION>]

    * PLAYLIST_ID: YouTube Playlist ID
    * ORDER: [ask(default)|normal|reverse|shuffle] optional playlist order
    * ACTION: [list|play|queue|None(default)] optional action to perform

    Channel live streams:
    plugin://plugin.video.youtube/play/?channel_id=<CHANNEL_ID>[&live=X]

    * CHANNEL_ID: YouTube Channel ID
    * X: optional index of live stream to play if channel has multiple live streams. 1 (default) for first live stream
    """
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
            return UriItem('command://Action(Play)')

        if context.get_handle() == -1:
            return UriItem('command://PlayMedia({0}, playlist_type_hint=1)'
                           .format(context.create_uri((PATHS.PLAY,), params)))

        ui.set_property(BUSY_FLAG)
        playlist_player = context.get_playlist_player()
        position, _ = playlist_player.get_position()
        items = playlist_player.get_items()

        media_item = _play_stream(provider, context)
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


def process_items_for_playlist(context, items, action=None, play_from=None):
    # select order
    order = context.get_param('order')
    if not order and play_from is None:
        order = 'ask'
    if order == 'ask':
        order_list = ('default', 'reverse', 'shuffle')
        selection_list = [
            (context.localize('playlist.play.%s' % order), order)
            for order in order_list
        ]
        order = context.get_ui().on_select(
            context.localize('playlist.play.select'),
            selection_list,
        )
        if order not in order_list:
            order = 'default'

    # reverse the list
    if order == 'reverse':
        items = items[::-1]
    elif order == 'shuffle':
        # we have to shuffle the playlist by our self.
        # The implementation of XBMC/KODI is quite weak :(
        random.shuffle(items)

    if action == 'list':
        context.set_content(CONTENT.VIDEO_CONTENT)
        return items

    # stop and clear the playlist
    playlist_player = context.get_playlist_player()
    playlist_player.clear()
    playlist_player.unshuffle()

    # check if we have a video as starting point for the playlist
    if play_from == 'start':
        play_from = 0
    elif play_from == 'end':
        play_from = -1
    if isinstance(play_from, int):
        playlist_position = play_from
    else:
        playlist_position = None

    # add videos to playlist
    for idx, item in enumerate(items):
        if not item.playable:
            continue
        playlist_player.add(item)
        if playlist_position is None and item.video_id == play_from:
            playlist_position = idx

    num_items = playlist_player.size()
    if not num_items:
        return False

    if isinstance(play_from, int):
        if num_items >= play_from > 0:
            playlist_position = play_from - 1
        elif play_from < 0:
            playlist_position = num_items + play_from
        else:
            playlist_position = 0
    elif playlist_position is None:
        playlist_position = 0

    if action == 'queue':
        return items
    if action == 'play':
        playlist_player.play_playlist_item(playlist_position + 1)
        return False
    return items[playlist_position]
