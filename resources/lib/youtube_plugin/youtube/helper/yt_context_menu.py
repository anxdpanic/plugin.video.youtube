# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ... import kodion


def append_more_for_video(context_menu, context, video_id, is_logged_in=False, refresh_container=False):
    _is_logged_in = '0'
    if is_logged_in:
        _is_logged_in = '1'

    _refresh_container = '0'
    if refresh_container:
        _refresh_container = '1'

    context_menu.append((context.localize('video.more'),
                         'RunPlugin(%s)' % context.create_uri(['video', 'more'],
                                                              {'video_id': video_id,
                                                               'logged_in': _is_logged_in,
                                                               'refresh_container': _refresh_container})))


def append_content_from_description(context_menu, context, video_id):
    context_menu.append((context.localize('video.description.links'),
                         'Container.Update(%s)' % context.create_uri(['special', 'description_links'],
                                                                     {'video_id': video_id})))


def append_play_with(context_menu, context):
    context_menu.append((context.localize('video.play.with'), 'Action(SwitchPlayer)'))


def append_queue_video(context_menu, context):
    context_menu.append((context.localize('video.queue'), 'Action(Queue)'))


def append_play_all_from_playlist(context_menu, context, playlist_id, video_id=''):
    if video_id:
        context_menu.append((context.localize('playlist.play.from_here'),
                             'RunPlugin(%s)' % context.create_uri(['play'],
                                                                  {'playlist_id': playlist_id,
                                                                   'video_id': video_id,
                                                                   'play': '1'})))
    else:
        context_menu.append((context.localize('playlist.play.all'),
                             'RunPlugin(%s)' % context.create_uri(['play'],
                                                                  {'playlist_id': playlist_id,
                                                                   'play': '1'})))


def append_add_video_to_playlist(context_menu, context, video_id):
    context_menu.append((context.localize('video.add_to_playlist'),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'select', 'playlist'],
                                                              {'video_id': video_id})))


def append_rename_playlist(context_menu, context, playlist_id, playlist_name):
    context_menu.append((context.localize('rename'),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'rename', 'playlist'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))


def append_delete_playlist(context_menu, context, playlist_id, playlist_name):
    context_menu.append((context.localize('delete'),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'remove', 'playlist'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))


def append_remove_as_watchlater(context_menu, context, playlist_id, playlist_name):
    context_menu.append((context.localize('watch_later.list.remove'),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'remove', 'watchlater'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))


def append_set_as_watchlater(context_menu, context, playlist_id, playlist_name):
    context_menu.append((context.localize('watch_later.list.set'),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'set', 'watchlater'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))


def append_remove_as_history(context_menu, context, playlist_id, playlist_name):
    context_menu.append((context.localize('history.list.remove'),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'remove', 'history'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))


def append_set_as_history(context_menu, context, playlist_id, playlist_name):
    context_menu.append((context.localize('history.list.set'),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'set', 'history'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))


def append_remove_my_subscriptions_filter(context_menu, context, channel_name):
    if context.get_settings().get_bool('youtube.folder.my_subscriptions_filtered.show', False):
        context_menu.append((context.localize('my_subscriptions.filter.remove'),
                             'RunPlugin(%s)' % context.create_uri(['my_subscriptions', 'filter'],
                                                                  {'channel_name': channel_name,
                                                                   'action': 'remove'})))


def append_add_my_subscriptions_filter(context_menu, context, channel_name):
    if context.get_settings().get_bool('youtube.folder.my_subscriptions_filtered.show', False):
        context_menu.append((context.localize('my_subscriptions.filter.add'),
                             'RunPlugin(%s)' % context.create_uri(['my_subscriptions', 'filter'],
                                                                  {'channel_name': channel_name,
                                                                   'action': 'add'})))


def append_rate_video(context_menu, context, video_id, refresh_container=False):
    refresh_container = '1' if refresh_container else '0'
    context_menu.append((context.localize('video.rate'),
                         'RunPlugin(%s)' % context.create_uri(['video', 'rate'],
                                                              {'video_id': video_id,
                                                               'refresh_container': refresh_container})))


def append_watch_later(context_menu, context, playlist_id, video_id):
    playlist_path = kodion.utils.create_path('channel', 'mine', 'playlist', playlist_id)
    if playlist_id and playlist_path != context.get_path():
        context_menu.append((context.localize('watch_later'),
                             'RunPlugin(%s)' % context.create_uri(['playlist', 'add', 'video'],
                                                                  {'playlist_id': playlist_id, 'video_id': video_id})))


def append_go_to_channel(context_menu, context, channel_id, channel_name):
    text = context.localize('go_to_channel') % context.get_ui().bold(channel_name)
    context_menu.append((text, 'Container.Update(%s)' % context.create_uri(['channel', channel_id])))


def append_related_videos(context_menu, context, video_id):
    context_menu.append((context.localize('related_videos'),
                         'Container.Update(%s)' % context.create_uri(['special', 'related_videos'],
                                                                     {'video_id': video_id})))


def append_clear_watch_history(context_menu, context):
    context_menu.append((context.localize('clear_history'),
                         'Container.Update(%s)' % context.create_uri(['history', 'clear'])))


def append_refresh(context_menu, context):
    context_menu.append((context.localize('refresh'), 'Container.Refresh'))


def append_subscribe_to_channel(context_menu, context, channel_id, channel_name=''):
    if channel_name:
        text = context.localize('subscribe_to') % context.get_ui().bold(channel_name)
        context_menu.append(
            (text, 'RunPlugin(%s)' % context.create_uri(['subscriptions', 'add'], {'subscription_id': channel_id})))
    else:
        context_menu.append((context.localize('subscribe'),
                             'RunPlugin(%s)' % context.create_uri(['subscriptions', 'add'],
                                                                  {'subscription_id': channel_id})))


def append_unsubscribe_from_channel(context_menu, context, channel_id):
    context_menu.append((context.localize('unsubscribe'),
                         'RunPlugin(%s)' % context.create_uri(['subscriptions', 'remove'],
                                                              {'subscription_id': channel_id})))


def append_mark_watched(context_menu, context, video_id):
    context_menu.append((context.localize('mark.watched'),
                         'RunPlugin(%s)' % context.create_uri(['playback_history'],
                                                              {'video_id': video_id,
                                                               'action': 'mark_watched'})))


def append_mark_unwatched(context_menu, context, video_id):
    context_menu.append((context.localize('mark.unwatched'),
                         'RunPlugin(%s)' % context.create_uri(['playback_history'],
                                                              {'video_id': video_id,
                                                               'action': 'mark_unwatched'})))


def append_reset_resume_point(context_menu, context, video_id):
    context_menu.append((context.localize('reset.resume_point'),
                         'RunPlugin(%s)' % context.create_uri(['playback_history'],
                                                              {'video_id': video_id,
                                                               'action': 'reset_resume'})))


def append_play_with_subtitles(context_menu, context, video_id):
    context_menu.append((context.localize('video.play.with_subtitles'),
                         'RunPlugin(%s)' % context.create_uri(['play'],
                                                              {'video_id': video_id,
                                                               'prompt_for_subtitles': '1'})))


def append_play_audio_only(context_menu, context, video_id):
    context_menu.append((context.localize('video.play.audio_only'),
                         'RunPlugin(%s)' % context.create_uri(['play'],
                                                              {'video_id': video_id,
                                                               'audio_only': '1'})))


def append_play_ask_for_quality(context_menu, context, video_id):
    context_menu.append((context.localize('video.play.ask_for_quality'),
                         'RunPlugin(%s)' % context.create_uri(['play'],
                                                              {'video_id': video_id,
                                                               'ask_for_quality': '1'})))
