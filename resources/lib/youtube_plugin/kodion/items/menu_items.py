# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..constants import paths


def more_for_video(context, video_id, logged_in=False, refresh=False):
    return (
        context.localize('video.more'),
        'RunPlugin({0})'.format(context.create_uri(
            ('video', 'more',),
            {
                'video_id': video_id,
                'logged_in': logged_in,
                'refresh': refresh,
            },
        ))
    )


def related_videos(context, video_id):
    return (
        context.localize('related_videos'),
        'ActivateWindow(Videos, {0}, return)'.format(context.create_uri(
            ('special', 'related_videos',),
            {
                'video_id': video_id,
            },
        ))
    )


def video_comments(context, video_id):
    return (
        context.localize('video.comments'),
        'ActivateWindow(Videos, {0}, return)'.format(context.create_uri(
            ('special', 'parent_comments',),
            {
                'video_id': video_id,
            },
        ))
    )


def content_from_description(context, video_id):
    return (
        context.localize('video.description.links'),
        'ActivateWindow(Videos, {0}, return)'.format(context.create_uri(
            ('special', 'description_links',),
            {
                'video_id': video_id,
            },
        ))
    )


def play_with(context):
    return (
        context.localize('video.play.with'),
        'Action(SwitchPlayer)'
    )


def refresh(context):
    return (
        context.localize('refresh'),
        'ReplaceWindow(Videos, {0})'.format(context.create_uri(
            context.get_path(),
            dict(context.get_params(), refresh=True),
        ))
    )


def queue_video(context):
    return (
        context.localize('video.queue'),
        'Action(Queue)'
    )


def play_all_from_playlist(context, playlist_id, video_id=''):
    if video_id:
        return (
            context.localize('playlist.play.from_here'),
            'RunPlugin({0})'.format(context.create_uri(
                ('play',),
                {
                    'playlist_id': playlist_id,
                    'video_id': video_id,
                    'play': True,
                },
            ))
        )
    return (
        context.localize('playlist.play.all'),
        'RunPlugin({0})'.format(context.create_uri(
            ('play',),
            {
                'playlist_id': playlist_id,
                'play': True,
            },
        ))
    )


def add_video_to_playlist(context, video_id):
    return (
        context.localize('video.add_to_playlist'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'select', 'playlist',),
            {
                'video_id': video_id,
            },
        ))
    )


def remove_video_from_playlist(context, playlist_id, video_id, video_name):
    return (
        context.localize('remove'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'remove', 'video',),
            dict(
                context.get_params(),
                playlist_id=playlist_id,
                video_id=video_id,
                video_name=video_name,
                reload_path=context.get_path(),
            ),
        ))
    )


def rename_playlist(context, playlist_id, playlist_name):
    return (
        context.localize('rename'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'rename', 'playlist',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
        ))
    )


def delete_playlist(context, playlist_id, playlist_name):
    return (
        context.localize('delete'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'remove', 'playlist',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
        ))
    )


def remove_as_watch_later(context, playlist_id, playlist_name):
    return (
        context.localize('watch_later.list.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'remove', 'watch_later',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
        ))
    )


def set_as_watch_later(context, playlist_id, playlist_name):
    return (
        context.localize('watch_later.list.set'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'set', 'watch_later',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
        ))
    )


def remove_as_history(context, playlist_id, playlist_name):
    return (
        context.localize('history.list.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'remove', 'history',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
        ))
    )


def set_as_history(context, playlist_id, playlist_name):
    return (
        context.localize('history.list.set'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'set', 'history',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
        ))
    )


def remove_my_subscriptions_filter(context, channel_name):
    return (
        context.localize('my_subscriptions.filter.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            ('my_subscriptions', 'filter',),
            {
                'channel_name': channel_name,
                'action': 'remove'
            },
        ))
    )


def add_my_subscriptions_filter(context, channel_name):
    return (
        context.localize('my_subscriptions.filter.add'),
        'RunPlugin({0})'.format(context.create_uri(
            ('my_subscriptions', 'filter',),
            {
                'channel_name': channel_name,
                'action': 'add',
            },
        ))
    )


def rate_video(context, video_id, refresh=False):
    return (
        context.localize('video.rate'),
        'RunPlugin({0})'.format(context.create_uri(
            ('video', 'rate',),
            {
                'video_id': video_id,
                'refresh': refresh,
            },
        ))
    )


def watch_later_add(context, playlist_id, video_id):
    return (
        context.localize('watch_later.add'),
        'RunPlugin({0})'.format(context.create_uri(
            ('playlist', 'add', 'video',),
            {
                'playlist_id': playlist_id,
                'video_id': video_id,
            },
        ))
    )


def watch_later_local_add(context, item):
    return (
        context.localize('watch_later.add'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.WATCH_LATER, 'add',),
            {
                'video_id': item.video_id,
                'item': item.dumps(),
            },
        ))
    )


def watch_later_local_remove(context, video_id):
    return (
        context.localize('watch_later.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.WATCH_LATER, 'remove',),
            {
                'video_id': video_id,
            },
        ))
    )


def watch_later_local_clear(context):
    return (
        context.localize('watch_later.clear'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.WATCH_LATER, 'clear',),
        ))
    )


def go_to_channel(context, channel_id, channel_name):
    return (
        context.localize('go_to_channel') % context.get_ui().bold(channel_name),
        'ActivateWindow(Videos, {0}, return)'.format(context.create_uri(
            ('channel', channel_id,),
        ))
    )


def subscribe_to_channel(context, channel_id, channel_name=''):
    return (
        context.localize('subscribe_to') % context.get_ui().bold(channel_name)
        if channel_name else
        context.localize('subscribe'),
        'RunPlugin({0})'.format(context.create_uri(
            ('subscriptions', 'add',),
            {
                'subscription_id': channel_id,
            },
        ))
    )


def unsubscribe_from_channel(context, channel_id=None, subscription_id=None):
    return (
        context.localize('unsubscribe'),
        'RunPlugin({0})'.format(context.create_uri(
            ('subscriptions', 'remove',),
            {
                'subscription_id': subscription_id,
            },
        )) if subscription_id else
        'RunPlugin({0})'.format(context.create_uri(
            ('subscriptions', 'remove',),
            {
                'channel_id': channel_id,
            },
        ))
    )


def play_with_subtitles(context, video_id):
    return (
        context.localize('video.play.with_subtitles'),
        'RunPlugin({0})'.format(context.create_uri(
            ('play',),
            {
                'video_id': video_id,
                'prompt_for_subtitles': True,
            },
        ))
    )


def play_audio_only(context, video_id):
    return (
        context.localize('video.play.audio_only'),
        'RunPlugin({0})'.format(context.create_uri(
            ('play',),
            {
                'video_id': video_id,
                'audio_only': True,
            },
        ))
    )


def play_ask_for_quality(context, video_id):
    return (
        context.localize('video.play.ask_for_quality'),
        'RunPlugin({0})'.format(context.create_uri(
            ('play',),
            {
                'video_id': video_id,
                'ask_for_quality': True,
            },
        ))
    )


def history_remove(context, video_id):
    return (
        context.localize('history.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.HISTORY,),
            {
                'action': 'remove',
                'video_id': video_id
            },
        ))
    )


def history_clear(context):
    return (
        context.localize('history.clear'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.HISTORY,),
            {
                'action': 'clear'
            },
        ))
    )


def history_mark_watched(context, video_id):
    return (
        context.localize('history.mark.watched'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.HISTORY,),
            {
                'video_id': video_id,
                'action': 'mark_watched',
            },
        ))
    )


def history_mark_unwatched(context, video_id):
    return (
        context.localize('history.mark.unwatched'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.HISTORY,),
            {
                'video_id': video_id,
                'action': 'mark_unwatched',
            },
        ))
    )


def history_reset_resume(context, video_id):
    return (
        context.localize('history.reset.resume_point'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.HISTORY,),
            {
                'video_id': video_id,
                'action': 'reset_resume',
            },
        ))
    )


def favorites_add(context, item):
    return (
        context.localize('favorites.add'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.FAVORITES, 'add',),
            {
                'video_id': item.video_id,
                'item': item.dumps(),
            },
        ))
    )


def favorites_remove(context, video_id):
    return (
        context.localize('favorites.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.FAVORITES, 'remove',),
            {
                'vide_id': video_id,
            },
        ))
    )


def search_remove(context, query):
    return (
        context.localize('search.remove'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.SEARCH, 'remove',),
            {
                'q': query,
            },
        ))
    )


def search_rename(context, query):
    return (
        context.localize('search.rename'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.SEARCH, 'rename',),
            {
                'q': query,
            },
        ))
    )


def search_clear(context):
    return (
        context.localize('search.clear'),
        'RunPlugin({0})'.format(context.create_uri(
            (paths.SEARCH, 'clear',),
        ))
    )
