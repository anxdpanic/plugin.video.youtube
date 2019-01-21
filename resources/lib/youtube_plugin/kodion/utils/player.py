# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import re

import xbmc


def playback_monitor(provider, context, video_id, playing_file, play_count=0,
                     use_history=False, playback_stats=None, seek_time=None,
                     refresh_only=False):
    access_manager = context.get_access_manager()

    player = xbmc.Player()
    settings = context.get_settings()
    ui = context.get_ui()

    if playback_stats is None:
        playback_stats = {}

    play_count = str(play_count)

    total_time = 0.0
    current_time = 0.0
    segment_start = 0.0
    played_time = -1.0
    percent_complete = 0

    state = 'playing'
    last_state = 'playing'

    np_wait_time = 0.2
    np_waited = 0.0
    p_wait_time = 0.5
    p_waited = 0.0

    report_interval = 10.0
    first_report = True

    report_url = playback_stats.get('playback_url', '')

    while not player.isPlaying() and not context.abort_requested():
        context.log_debug('Waiting for playback to start')

        xbmc.sleep(int(np_wait_time * 1000))
        if np_waited >= 5:
            return

        np_waited += np_wait_time

    client = provider.get_client(context)
    is_logged_in = provider.is_logged_in()

    if is_logged_in and report_url:
        client.update_watch_history(video_id, report_url)
        context.log_debug('Playback start reported: |%s|' % video_id)

    report_url = playback_stats.get('watchtime_url', '')

    plugin_play_path = 'plugin://plugin.video.youtube/play/?video_id=%s' % video_id

    while player.isPlaying() and not context.abort_requested():
        try:
            if player.getPlayingFile() != playing_file and \
                    player.getPlayingFile() != plugin_play_path:
                break
        except RuntimeError:
            pass

        try:
            current_time = float(player.getTime())
            total_time = float(player.getTotalTime())
        except RuntimeError:
            pass

        try:
            percent_complete = int(float(current_time) / float(total_time) * 100)
        except ZeroDivisionError:
            percent_complete = 0

        if seek_time and seek_time != '0.0':
            try:
                player.seekTime(float(seek_time))
                current_time = float(seek_time)
            except ValueError:
                pass
            seek_time = None

        if p_waited >= report_interval:
            if is_logged_in:
                provider.reset_client()  # refresh client, tokens may need refreshing
                client = provider.get_client(context)
                is_logged_in = provider.is_logged_in()

            if current_time == played_time:
                last_state = state
                state = 'paused'
            else:
                last_state = state
                state = 'playing'

            played_time = current_time

        if is_logged_in and report_url:
            if first_report or (p_waited >= report_interval):
                first_report = False
                p_waited = 0.0

                if state == 'playing':
                    segment_end = current_time
                else:
                    segment_end = segment_start

                if segment_end > float(total_time):
                    segment_end = float(total_time)

                if state == 'playing' or last_state == 'playing':  # only report state='paused' once
                    client.update_watch_history(video_id, report_url
                                                .format(st=format(segment_start, '.3f'), et=format(segment_end, '.3f'), state=state))
                    context.log_debug('Playback reported [%s]: %s segment start, %s segment end @ %s%% state=%s' %
                                      (video_id, format(segment_start, '.3f'), format(segment_end, '.3f'), percent_complete, state))

                segment_start = segment_end

        xbmc.sleep(int(p_wait_time * 1000))

        p_waited += p_wait_time

    if is_logged_in and report_url:
        client.update_watch_history(video_id, report_url
                                    .format(st=format(segment_start, '.3f'), et=format(current_time, '.3f'), state=state))
        context.log_debug('Playback reported [%s]: %s segment start, %s segment end @ %s%% state=%s' %
                          (video_id, format(segment_start, '.3f'), format(current_time, '.3f'), percent_complete, state))

    context.log_debug('Playback stopped [%s]: %s secs of %s @ %s%%' % (video_id, format(current_time, '.3f'), format(total_time, '.3f'), percent_complete))

    state = 'stopped'
    if is_logged_in:
        provider.reset_client()  # refresh client, tokens may need refreshing
        client = provider.get_client(context)
        is_logged_in = provider.is_logged_in()

    if percent_complete >= settings.get_play_count_min_percent():
        play_count = '1'
        current_time = 0.0
        if is_logged_in and report_url:
            client.update_watch_history(video_id, report_url
                                        .format(st=format(total_time, '.3f'), et=format(total_time, '.3f'), state=state))
            context.log_debug('Playback reported [%s] @ 100%% state=%s' % (video_id, state))

    else:
        if is_logged_in and report_url:
            client.update_watch_history(video_id, report_url
                                        .format(st=format(current_time, '.3f'), et=format(current_time, '.3f'), state=state))
            context.log_debug('Playback reported [%s]: %s segment start, %s segment end @ %s%% state=%s' %
                              (video_id, format(current_time, '.3f'), format(current_time, '.3f'), percent_complete, state))

        refresh_only = True

    if use_history:
        context.get_playback_history().update(video_id, play_count, total_time, current_time, percent_complete)

    if not refresh_only:
        if is_logged_in:

            if settings.get_bool('youtube.playlist.watchlater.autoremove', True):
                watch_later_id = access_manager.get_watch_later_id()

                if watch_later_id and watch_later_id.strip().lower() != 'wl':
                    playlist_item_id = client.get_playlist_item_id_of_video_id(playlist_id=watch_later_id, video_id=video_id)
                    if playlist_item_id:
                        json_data = client.remove_video_from_playlist(watch_later_id, playlist_item_id)
                        if not provider.v3_handle_error(provider, context, json_data):
                            return False

            history_playlist_id = access_manager.get_watch_history_id()
            if history_playlist_id and history_playlist_id != 'HL':
                json_data = client.add_video_to_playlist(history_playlist_id, video_id)
                if not provider.v3_handle_error(provider, context, json_data):
                    return False

            # rate video
            if settings.get_bool('youtube.post.play.rate', False):
                do_rating = True
                if not settings.get_bool('youtube.post.play.rate.playlists', False):
                    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                    do_rating = int(playlist.size()) < 2

                if do_rating:
                    json_data = client.get_video_rating(video_id)
                    if not provider.v3_handle_error(provider, context, json_data):
                        return False
                    items = json_data.get('items', [{'rating': 'none'}])
                    rating = items[0].get('rating', 'none')
                    if rating == 'none':
                        rating_match = re.search('/(?P<video_id>[^/]+)/(?P<rating>[^/]+)', '/%s/%s/' % (video_id, rating))
                        provider.yt_video.process('rate', provider, context, rating_match)

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    do_refresh = (int(playlist.size()) < 2) or (playlist.getposition() == -1)

    if do_refresh and settings.get_bool('youtube.post.play.refresh', False) and \
            not xbmc.getInfoLabel('Container.FolderPath').startswith(context.create_uri(['kodion', 'search', 'input'])):
        # don't refresh search input it causes request for new input, (Container.Update in abstract_provider /kodion/search/input/
        # would resolve this but doesn't work with Remotes(Yatse))
        ui.refresh_container()
