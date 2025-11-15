# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import random
from collections import defaultdict

from ..helper import utils, v3
from ..youtube_exceptions import YouTubeException
from ...kodion import logging
from ...kodion.compatibility import string_type, urlencode, urlunsplit, xbmc
from ...kodion.constants import (
    BUSY_FLAG,
    CHANNEL_ID,
    CONTENT,
    FORCE_PLAY_PARAMS,
    INCOGNITO,
    ORDER,
    PATHS,
    PLAYBACK_INIT,
    PLAYER_DATA,
    PLAYLIST_ID,
    PLAYLIST_IDS,
    PLAYLIST_PATH,
    PLAYLIST_POSITION,
    PLAY_FORCE_AUDIO,
    PLAY_PROMPT_QUALITY,
    PLAY_STRM,
    PLAY_USING,
    SCREENSAVER,
    SERVER_WAKEUP,
    TRAKT_PAUSE_FLAG,
    VIDEO_ID,
    VIDEO_IDS,
)
from ...kodion.items import AudioItem, UriItem, VideoItem
from ...kodion.network import get_connect_address
from ...kodion.utils.datetime import datetime_to_since
from ...kodion.utils.redact import redact_params


def _play_stream(provider, context):
    ui = context.get_ui()
    params = context.get_params()
    video_id = params.get(VIDEO_ID)
    if not video_id:
        ui.show_notification(context.localize('error.no_streams_found'))
        return False

    client = provider.get_client(context)
    settings = context.get_settings()

    incognito = params.get(INCOGNITO, False)
    screensaver = params.get(SCREENSAVER, False)

    audio_only = False
    is_external = ui.get_property(PLAY_USING)
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
        audio_only = not ask_for_quality and settings.audio_only()
        if ui.pop_property(PLAY_FORCE_AUDIO):
            audio_only = True
        use_mpd = ((not is_external or settings.alternative_player_mpd())
                   and settings.use_mpd_videos()
                   and context.ipc_exec(SERVER_WAKEUP, timeout=5))

        try:
            streams, yt_item = client.load_stream_info(
                video_id=video_id,
                ask_for_quality=ask_for_quality,
                audio_only=audio_only,
                incognito=incognito,
                use_mpd=use_mpd,
            )
        except YouTubeException as exc:
            logging.exception('Error')
            ui.show_notification(message=exc.get_message())
            return False

        if not streams:
            ui.show_notification(context.localize('error.no_streams_found'))
            logging.debug('No streams found')
            return False

        stream = _select_stream(
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
        ui.show_notification(context.localize('error.rtmpe_not_supported'))
        return False

    if not screensaver and settings.get_bool(settings.PLAY_SUGGESTED):
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
        VIDEO_ID: video_id,
        CHANNEL_ID: metadata.get('channel', {}).get('id', ''),
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

    ui.set_property(PLAYER_DATA,
                    value=playback_data,
                    process=json.dumps,
                    log_process=redact_params)
    ui.set_property(TRAKT_PAUSE_FLAG, raw=True)
    context.send_notification(PLAYBACK_INIT, playback_data)
    return media_item


def _play_playlist(provider, context):
    video_items = []
    params = context.get_params()

    action = params.get('action')
    if not action and context.get_handle() == -1:
        action = 'play'

    playlist_ids = params.get(PLAYLIST_IDS)
    if not playlist_ids:
        playlist_id = params.get(PLAYLIST_ID)
        if playlist_id:
            playlist_ids = [playlist_id]

    video_ids = params.get(VIDEO_IDS)
    if not playlist_ids and not video_ids:
        video_id = params.get(VIDEO_ID)
        if video_id:
            video_ids = [video_id]
        else:
            logging.warning_trace('No playlist found to play')
            return False, None

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
                return False, None
            chunks = json_data.values()
            total = sum(len(chunk.get('items', [])) for chunk in chunks)
        elif video_ids:
            json_data = resource_manager.get_videos(video_ids,
                                                    live_details=True)
            if not json_data:
                return False, None
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
                                          process_next_page=False,
                                          hide_progress=True)
            video_items.extend(result)

            progress_dialog.update(steps=len(result))

        if not video_items:
            return False, None

        result = process_items_for_playlist(context, video_items, action=action)
        if action == 'list':
            options = {
                provider.CACHE_TO_DISC: True,
                provider.FORCE_RESOLVE: False,
                provider.UPDATE_LISTING: False,
                provider.CONTENT_TYPE: {
                    'content_type': CONTENT.VIDEO_CONTENT,
                    'sub_type': None,
                    'category_label': None,
                },
            }
        else:
            options = {
                provider.CACHE_TO_DISC: False,
                provider.FORCE_RESOLVE: True,
                provider.UPDATE_LISTING: True,
            }
        return result, options


def _play_channel_live(provider, context):
    channel_id = context.get_param(CHANNEL_ID)
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
            provider.CACHE_TO_DISC: False,
            provider.FORCE_RESOLVE: True,
            provider.UPDATE_LISTING: True,
        },
    )


def _select_stream(context,
                   stream_data_list,
                   ask_for_quality,
                   audio_only,
                   use_mpd=True):
    settings = context.get_settings()
    if settings.use_isa():
        isa_capabilities = context.inputstream_adaptive_capabilities()
        use_adaptive = bool(isa_capabilities)
        use_live_adaptive = use_adaptive and 'live' in isa_capabilities
        use_live_mpd = use_live_adaptive and settings.use_mpd_live_streams()
    else:
        use_adaptive = False
        use_live_adaptive = False
        use_live_mpd = False

    if audio_only:
        logging.debug('Audio only')
        stream_list = [item for item in stream_data_list
                       if 'video' not in item]
    else:
        stream_list = [
            item for item in stream_data_list
            if (not item.get('adaptive')
                or (not item.get('live')
                    and ((use_mpd and item.get('dash/video'))
                         or (use_adaptive and item.get('hls/video'))))
                or (item.get('live')
                    and ((use_live_mpd and item.get('dash/video'))
                         or (use_live_adaptive and item.get('hls/video')))))
        ]

    if not stream_list:
        logging.debug('No streams found')
        return None

    def _stream_sort(_stream):
        return _stream.get('sort', [0, 0, 0])

    stream_list.sort(key=_stream_sort, reverse=True)
    num_streams = len(stream_list)

    if logging.debugging:
        def _default_NA():
            return 'N/A'

        logging.debug('%d available stream(s)', num_streams)
        for idx, stream in enumerate(stream_list):
            logging.debug(('Stream {idx}',
                           'Container: {stream[container]}',
                           'Adaptive:  {stream[adaptive]}',
                           'Audio:     {stream[audio]}',
                           'Video:     {stream[video]}',
                           'Sort:      {stream[sort]}'),
                          idx=idx,
                          stream=defaultdict(_default_NA, stream))

    if ask_for_quality and num_streams > 1:
        selected_stream = context.get_ui().on_select(
            context.localize('select_video_quality'),
            [stream['title'] for stream in stream_list],
        )
        if selected_stream == -1:
            logging.debug('No stream selected')
            return None
    else:
        selected_stream = 0

    logging.debug('Stream %d selected', selected_stream)
    return stream_list[selected_stream]


def process_items_for_playlist(context,
                               items,
                               action=None,
                               play_from=None,
                               order=None,
                               recent_days=None):
    params = context.get_params()

    if play_from is None:
        play_from = params.get(VIDEO_ID)

    if recent_days is None:
        recent_days = params.get('recent_days')

    num_items = len(items) if items else 0
    if num_items > 1:
        # select order
        if order is None:
            order = params.get(ORDER)
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
        if (recent_limit and datetime_to_since(
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
        timeout = position
        while ui.busy_dialog_active() or playlist_player.size() < position:
            timeout -= 1
            if timeout < 0:
                command = playlist_player.play_playlist_item(position,
                                                             defer=True)
                return UriItem(command)
            context.sleep(0.1)
        else:
            playlist_player.play_playlist_item(position)
    return items[position - 1]


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

    if ({CHANNEL_ID, PLAYLIST_ID, PLAYLIST_IDS, VIDEO_ID, VIDEO_IDS}
            .isdisjoint(param_keys)):
        item_ids = context.parse_item_ids()
        if item_ids and VIDEO_ID in item_ids:
            context.set_params(**item_ids)
        else:
            return False

    video_id = params.get(VIDEO_ID)
    video_ids = params.get(VIDEO_IDS)
    playlist_id = params.get(PLAYLIST_ID)

    force_play_params = FORCE_PLAY_PARAMS.intersection(param_keys)

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
                    play=(xbmc.PLAYLIST_MUSIC
                          if (ui.get_property(PLAY_FORCE_AUDIO)
                              or context.get_settings().audio_only()) else
                          xbmc.PLAYLIST_VIDEO),
                )
            ))

        if not context.get_system_version().compatible(22):
            ui.set_property(BUSY_FLAG)

        media_item = _play_stream(provider, context)
        if media_item:
            playlist_player = context.get_playlist_player()
            position, _ = playlist_player.get_position()
            if position:
                item_uri = playlist_player.get_item_path(position - 1)
                if item_uri:
                    ui.set_property(PLAYLIST_PATH, item_uri)
                    ui.set_property(PLAYLIST_POSITION, str(position))
        else:
            ui.clear_property(BUSY_FLAG)
            for param in force_play_params:
                ui.clear_property(param)

        return media_item

    if playlist_id or video_ids or PLAYLIST_IDS in params:
        return _play_playlist(provider, context)

    if CHANNEL_ID in params:
        return _play_channel_live(provider, context)
    return False
