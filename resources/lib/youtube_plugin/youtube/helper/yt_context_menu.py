# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from ... import kodion


def append_more_for_video(context_menu, provider, context, video_id, is_logged_in=False, refresh_container=False):
    _is_logged_in = '0'
    if is_logged_in:
        _is_logged_in = '1'

    _refresh_container = '0'
    if refresh_container:
        _refresh_container = '1'

    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.more']),
                         'RunPlugin(%s)' % context.create_uri(['video', 'more'],
                                                              {'video_id': video_id,
                                                               'logged_in': _is_logged_in,
                                                               'refresh_container': _refresh_container})))


def append_content_from_description(context_menu, provider, context, video_id):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.description.links']),
                         'Container.Update(%s)' % context.create_uri(['special', 'description_links'],
                                                                     {'video_id': video_id})))


def append_play_with(context_menu, provider, context):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.play_with']), 'Action(SwitchPlayer)'))


def append_queue_video(context_menu, provider, context):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.queue']), 'Action(Queue)'))


def append_play_all_from_playlist(context_menu, provider, context, playlist_id, video_id=''):
    if video_id:
        context_menu.append((context.localize(provider.LOCAL_MAP['youtube.playlist.play.from_here']),
                             'RunPlugin(%s)' % context.create_uri(['play'],
                                                                  {'playlist_id': playlist_id,
                                                                   'video_id': video_id,
                                                                   'play': '1'})))
    else:
        context_menu.append((context.localize(provider.LOCAL_MAP['youtube.playlist.play.all']),
                             'RunPlugin(%s)' % context.create_uri(['play'],
                                                                  {'playlist_id': playlist_id,
                                                                   'play': '1'})))


def append_add_video_to_playlist(context_menu, provider, context, video_id):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.add_to_playlist']),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'select', 'playlist'],
                                                              {'video_id': video_id})))


def append_rename_playlist(context_menu, provider, context, playlist_id, playlist_name):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.rename']),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'rename', 'playlist'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))


def append_delete_playlist(context_menu, provider, context, playlist_id, playlist_name):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.delete']),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'remove', 'playlist'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))


def append_remove_as_watchlater(context_menu, provider, context, playlist_id, playlist_name):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.remove.as.watchlater']),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'remove', 'watchlater'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))


def append_set_as_watchlater(context_menu, provider, context, playlist_id, playlist_name):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.set.as.watchlater']),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'set', 'watchlater'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))


def append_remove_as_history(context_menu, provider, context, playlist_id, playlist_name):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.remove.as.history']),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'remove', 'history'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))


def append_set_as_history(context_menu, provider, context, playlist_id, playlist_name):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.set.as.history']),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'set', 'history'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))


def append_remove_my_subscriptions_filter(context_menu, provider, context, channel_name):
    if context.get_settings().get_bool('youtube.folder.my_subscriptions_filtered.show', False):
        context_menu.append((context.localize(provider.LOCAL_MAP['youtube.remove.my_subscriptions.filter']),
                             'RunPlugin(%s)' % context.create_uri(['my_subscriptions', 'filter'],
                                                                  {'channel_name': channel_name,
                                                                   'action': 'remove'})))


def append_add_my_subscriptions_filter(context_menu, provider, context, channel_name):
    if context.get_settings().get_bool('youtube.folder.my_subscriptions_filtered.show', False):
        context_menu.append((context.localize(provider.LOCAL_MAP['youtube.add.my_subscriptions.filter']),
                             'RunPlugin(%s)' % context.create_uri(['my_subscriptions', 'filter'],
                                                                  {'channel_name': channel_name,
                                                                   'action': 'add'})))


def append_rate_video(context_menu, provider, context, video_id, refresh_container=False):
    if refresh_container:
        refresh_container = '1'
    else:
        refresh_container = '0'
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.rate']),
                         'RunPlugin(%s)' % context.create_uri(['video', 'rate'],
                                                              {'video_id': video_id,
                                                               'refresh_container': refresh_container})))


def append_watch_later(context_menu, provider, context, playlist_id, video_id):
    playlist_path = kodion.utils.create_path('channel', 'mine', 'playlist', playlist_id)
    if playlist_id and playlist_path != context.get_path():
        context_menu.append((context.localize(provider.LOCAL_MAP['youtube.watch_later']),
                             'RunPlugin(%s)' % context.create_uri(['playlist', 'add', 'video'],
                                                                  {'playlist_id': playlist_id, 'video_id': video_id})))


def append_go_to_channel(context_menu, provider, context, channel_id, channel_name):
    text = context.localize(provider.LOCAL_MAP['youtube.go_to_channel']) % context.get_ui().bold(channel_name)
    context_menu.append((text, 'Container.Update(%s)' % context.create_uri(['channel', channel_id])))


def append_related_videos(context_menu, provider, context, video_id):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.related_videos']),
                         'Container.Update(%s)' % context.create_uri(['special', 'related_videos'],
                                                                     {'video_id': video_id})))


def append_clear_watch_history(context_menu, provider, context):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.clear_history']),
                         'Container.Update(%s)' % context.create_uri(['history', 'clear'])))


def append_refresh(context_menu, provider, context):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.refresh']), 'Container.Refresh'))


def append_subscribe_to_channel(context_menu, provider, context, channel_id, channel_name=u''):
    if channel_name:
        text = context.localize(provider.LOCAL_MAP['youtube.subscribe_to']) % context.get_ui().bold(channel_name)
        context_menu.append(
            (text, 'RunPlugin(%s)' % context.create_uri(['subscriptions', 'add'], {'subscription_id': channel_id})))
    else:
        context_menu.append((context.localize(provider.LOCAL_MAP['youtube.subscribe']),
                             'RunPlugin(%s)' % context.create_uri(['subscriptions', 'add'],
                                                                  {'subscription_id': channel_id})))


def append_unsubscribe_from_channel(context_menu, provider, context, channel_id):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.unsubscribe']),
                         'RunPlugin(%s)' % context.create_uri(['subscriptions', 'remove'],
                                                              {'subscription_id': channel_id})))


def append_mark_watched(context_menu, provider, context, video_id):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.mark.watched']),
                         'RunPlugin(%s)' % context.create_uri(['playback_history'],
                                                              {'video_id': video_id,
                                                               'action': 'mark_watched'})))


def append_mark_unwatched(context_menu, provider, context, video_id):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.mark.unwatched']),
                         'RunPlugin(%s)' % context.create_uri(['playback_history'],
                                                              {'video_id': video_id,
                                                               'action': 'mark_unwatched'})))


def append_reset_resume_point(context_menu, provider, context, video_id):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.reset.resume.point']),
                         'RunPlugin(%s)' % context.create_uri(['playback_history'],
                                                              {'video_id': video_id,
                                                               'action': 'reset_resume'})))


def append_play_with_subtitles(context_menu, provider, context, video_id):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.play_with_subtitles']),
                         'RunPlugin(%s)' % context.create_uri(['play'],
                                                              {'video_id': video_id,
                                                               'prompt_for_subtitles': '1'})))


def append_play_audio_only(context_menu, provider, context, video_id):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.play_audio_only']),
                         'RunPlugin(%s)' % context.create_uri(['play'],
                                                              {'video_id': video_id,
                                                               'audio_only': '1'})))
