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
from ...kodion.compatibility import string_type, urlencode, urlunsplit
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
    PLAY_STRM,
    PLAY_TIMESHIFT,
    PLAY_WITH,
    SERVER_WAKEUP,
)
from ...kodion.items import AudioItem, UriItem, VideoItem
from ...kodion.network import get_connect_address
from ...kodion.utils import datetime_parser, find_video_id, select_stream


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
        yt_item = None
    else:
        ask_for_quality = settings.ask_for_video_quality()
        if ui.pop_property(PLAY_PROMPT_QUALITY) and not screensaver:
            ask_for_quality = True
        elif ui.pop_property(PLAY_FORCE_AUDIO):
            audio_only = True
        else:
            audio_only = settings.audio_only()
        use_mpd = ((not is_external or settings.alternative_player_mpd())
                   and settings.use_mpd_videos()
                   and context.wakeup(SERVER_WAKEUP, timeout=5))

        try:
            streams, yt_item = client.get_streams(
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
            use_mpd=use_mpd,
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

    utils.update_play_info(
        provider, context, video_id, media_item, stream, yt_item
    )

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

    playlist_id = params.get('playlist_id')
    playlist_ids = params.get('playlist_ids')
    video_ids = params.get('video_ids')
    if not playlist_ids and playlist_id:
        playlist_ids = [params.get('playlist_id')]

    resource_manager = provider.get_resource_manager(context)
    ui = context.get_ui()

    with ui.create_progress_dialog(
            heading=context.localize('playlist.progress.updating'),
            message=context.localize('please_wait'),
            background=True,
    ) as progress_dialog:
        if playlist_ids:
            json_data = resource_manager.get_playlist_items(playlist_ids)
            if not json_data:
                return False
            chunks = json_data.values()
            total = sum(len(chunk.get('items', [])) for chunk in chunks)
        elif video_ids:
            json_data = resource_manager.get_videos(video_ids,
                                                    live_details=True)
            if not json_data:
                return False
            chunks = [{
                'kind': 'plugin#playlistItemListResponse',
                'items': json_data.values(),
            }]
            total = len(json_data)

        progress_dialog.reset_total(total)

        # start the loop and fill the list with video items
        for chunk in chunks:
            result = v3.response_to_items(provider,
                                          context,
                                          chunk,
                                          process_next_page=False)
            video_items.extend(result)

            progress_dialog.update(steps=len(result))

        if not video_items:
            return False

        return (
            process_items_for_playlist(context, video_items, action=action),
            {
                provider.RESULT_CACHE_TO_DISC: action == 'list',
                provider.RESULT_FORCE_RESOLVE: action != 'list',
                provider.RESULT_UPDATE_LISTING: action != 'list',
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

    if ({'channel_id', 'playlist_id', 'playlist_ids', 'video_id', 'video_ids'}
            .isdisjoint(param_keys)):
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
    video_ids = params.get('video_ids')
    playlist_id = params.get('playlist_id')

    force_play_params = {
        PLAY_FORCE_AUDIO,
        PLAY_TIMESHIFT,
        PLAY_PROMPT_QUALITY,
        PLAY_PROMPT_SUBTITLES,
        PLAY_WITH,
    }.intersection(param_keys)

    if video_id and not playlist_id and not video_ids:
        for param in force_play_params:
            del params[param]
            ui.set_property(param)

        if context.get_handle() == -1:
            # This is required to trigger Kodi resume prompt, along with using
            # RunPlugin. Prompt will not be used if using PlayMedia
            if force_play_params and not params.get(PLAY_STRM):
                return UriItem('command://Action(Play)')

            return UriItem('command://{0}'.format(
                context.create_uri(
                    (PATHS.PLAY,),
                    params,
                    play=True,
                )
            ))

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
            for param in force_play_params:
                ui.clear_property(param)

        return media_item

    if playlist_id or video_ids or 'playlist_ids' in params:
        return _play_playlist(provider, context)

    if 'channel_id' in params:
        return _play_channel_live(provider, context)
    return False


def process_items_for_playlist(context,
                               items,
                               action=None,
                               play_from=None,
                               order=None,
                               recent_days=None):
    params = context.get_params()

    if play_from is None:
        play_from = params.get('video_id')

    if recent_days is None:
        recent_days = params.get('recent_days')

    num_items = len(items) if items else 0
    if num_items > 1:
        # select order
        if order is None:
            order = params.get('order')
        if not order and play_from is None and recent_days is None:
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
    elif not num_items:
        return False

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
        position = play_from
    elif isinstance(play_from, string_type):
        position = None
    else:
        position = False

    # add videos to playlist
    num_items = 0
    # convert from days to seconds
    recent_limit = recent_days * 24 * 60 * 60 if recent_days else None
    for idx, item in enumerate(items):
        if not item.playable:
            continue
        if (recent_limit and datetime_parser.datetime_to_since(
                context,
                item.get_dateadded(),
                as_seconds=True,
        ) > recent_limit):
            continue
        playlist_player.add(item)
        num_items += 1
        if position is None and item.video_id == play_from:
            position = num_items

    if not num_items:
        return False

    if isinstance(play_from, int):
        if num_items >= play_from > 0:
            position = play_from
        elif play_from < 0:
            position = num_items + play_from
        else:
            position = 1
    elif not position:
        position = 1

    if action == 'queue':
        return items
    if action == 'play':
        ui = context.get_ui()
        max_wait_time = position
        while ui.busy_dialog_active() or playlist_player.size() < position:
            max_wait_time -= 1
            if max_wait_time < 0:
                command = playlist_player.play_playlist_item(position,
                                                             defer=True)
                return UriItem(command)
            context.sleep(1)
        else:
            playlist_player.play_playlist_item(position)
    return items[position - 1]
