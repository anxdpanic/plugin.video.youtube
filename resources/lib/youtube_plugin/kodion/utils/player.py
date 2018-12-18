# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import re

import xbmc


def playback_monitor(provider, context, video_id, play_count=0, use_history=False,
                     playback_stats=None, seek_time=None, refresh_only=False):

    client = provider.get_client(context)
    access_manager = context.get_access_manager()

    monitor = xbmc.Monitor()
    player = xbmc.Player()
    settings = context.get_settings()
    ui = context.get_ui()

    if playback_stats is None:
        playback_stats = {}

    play_count = str(play_count)

    total_time = 0.0
    current_time = 0.0
    percent_complete = 0

    np_wait_time = 0.2
    np_waited = 0.0
    p_wait_time = 0.5

    while not player.isPlaying() and not monitor.abortRequested():
        context.log_debug('Waiting for playback to start')

        if np_waited >= 5 or monitor.waitForAbort(np_wait_time):
            return

        np_waited += np_wait_time

    while player.isPlaying() and not monitor.abortRequested():
        try:
            current_time = int(player.getTime())
            total_time = int(player.getTotalTime())
        except RuntimeError:
            pass

        try:
            percent_complete = int(float(current_time) / float(total_time) * 100)
        except ZeroDivisionError:
            percent_complete = 0

        if seek_time and seek_time != '0.0':
            try:
                player.seekTime(float(seek_time))
            except ValueError:
                pass
            seek_time = None

        if monitor.waitForAbort(p_wait_time):
            break

    context.log_debug('Playback stopped [%s]: %s secs of %s @ %s%%' % (video_id, current_time, total_time, percent_complete))

    if percent_complete >= settings.get_play_count_min_percent():
        play_count = '1'
        current_time = 0.0
    else:
        refresh_only = True

    if use_history:
        context.get_playback_history().update(video_id, play_count, total_time, current_time, percent_complete)

    if not refresh_only:
        if provider.is_logged_in():

            if playback_stats.get('playback_url', ''):
                client.update_watch_history(video_id, playback_stats.get('playback_url'))

            if settings.get_bool('youtube.playlist.watchlater.autoremove', True):
                watch_later_id = access_manager.get_watch_later_id()

                if watch_later_id and watch_later_id.strip().lower() != 'wl':
                    playlist_item_id = client.get_playlist_item_id_of_video_id(playlist_id=watch_later_id, video_id=video_id)
                    if playlist_item_id:
                        json_data = client.remove_video_from_playlist(watch_later_id, playlist_item_id)
                        if not provider._v3_handle_error(provider, context, json_data):
                            return False

            history_playlist_id = access_manager.get_watch_history_id()
            if history_playlist_id and history_playlist_id != 'HL':
                json_data = client.add_video_to_playlist(history_playlist_id, video_id)
                if not provider._v3_handle_error(provider, context, json_data):
                    return False

            # rate video
            if settings.get_bool('youtube.post.play.rate', False):
                json_data = client.get_video_rating(video_id)
                if not provider._v3_handle_error(provider, context, json_data):
                    return False
                items = json_data.get('items', [{'rating': 'none'}])
                rating = items[0].get('rating', 'none')
                if rating == 'none':
                    rating_match = re.search('/(?P<video_id>[^/]+)/(?P<rating>[^/]+)', '/%s/%s/' % (video_id, rating))
                    provider._yt_video.process('rate', provider, context, rating_match)

    if settings.get_bool('youtube.post.play.refresh', False) and \
            not xbmc.getInfoLabel('Container.FolderPath').startswith(context.create_uri(['kodion', 'search', 'input'])):
        # don't refresh search input it causes request for new input, (Container.Update in abstract_provider /kodion/search/input/
        # would resolve this but doesn't work with Remotes(Yatse))
        ui.refresh_container()
