# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..constants import (
    PATHS,
    PLAY_FORCE_AUDIO,
    PLAY_PROMPT_QUALITY,
    PLAY_PROMPT_SUBTITLES,
    PLAY_TIMESHIFT,
    PLAY_WITH,
)


def more_for_video(context, video_id, logged_in=False, refresh=False):
    params = {
        'video_id': video_id,
        'logged_in': logged_in,
    }
    if refresh:
        params['refresh'] = context.get_param('refresh', 0) + 1
    return (
        context.localize('video.more'),
        context.create_uri(
            ('video', 'more',),
            params,
            run=True,
        ),
    )


def related_videos(context, video_id):
    return (
        context.localize('related_videos'),
        context.create_uri(
            (PATHS.ROUTE, 'special', 'related_videos',),
            {
                'video_id': video_id,
            },
            run=True,
        ),
    )


def video_comments(context, video_id):
    return (
        context.localize('video.comments'),
        context.create_uri(
            (PATHS.ROUTE, 'special', 'parent_comments',),
            {
                'video_id': video_id,
            },
            run=True,
        )
    )


def content_from_description(context, video_id):
    return (
        context.localize('video.description.links'),
        context.create_uri(
            (PATHS.ROUTE, 'special', 'description_links',),
            {
                'video_id': video_id,
            },
            run=True,
        )
    )


def play_with(context, video_id):
    return (
        context.localize('video.play.with'),
        context.create_uri(
            (PATHS.PLAY,),
            {
                'video_id': video_id,
                PLAY_WITH: True,
            },
            run=True,
        ),
    )


def refresh(context):
    params = context.get_params()
    return (
        context.localize('refresh'),
        context.create_uri(
            (PATHS.ROUTE, context.get_path(),),
            dict(params, refresh=params.get('refresh', 0) + 1),
            run=True,
        ),
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
            context.create_uri(
                (PATHS.PLAY,),
                {
                    'playlist_id': playlist_id,
                    'video_id': video_id,
                    'play': True,
                },
                run=True,
            ),
        )
    return (
        context.localize('playlist.play.all'),
        context.create_uri(
            (PATHS.PLAY,),
            {
                'playlist_id': playlist_id,
                'play': True,
            },
            run=True,
        ),
    )


def add_video_to_playlist(context, video_id):
    return (
        context.localize('video.add_to_playlist'),
        context.create_uri(
            ('playlist', 'select', 'playlist',),
            {
                'video_id': video_id,
            },
            run=True,
        ),
    )


def remove_video_from_playlist(context, playlist_id, video_id, video_name):
    return (
        context.localize('remove'),
        context.create_uri(
            ('playlist', 'remove', 'video',),
            dict(
                context.get_params(),
                playlist_id=playlist_id,
                video_id=video_id,
                video_name=video_name,
                reload_path=context.get_path(),
            ),
            run=True,
        ),
    )


def rename_playlist(context, playlist_id, playlist_name):
    return (
        context.localize('rename'),
        context.create_uri(
            ('playlist', 'rename', 'playlist',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
            run=True,
        ),
    )


def delete_playlist(context, playlist_id, playlist_name):
    return (
        context.localize('delete'),
        context.create_uri(
            ('playlist', 'remove', 'playlist',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
            run=True,
        ),
    )


def remove_as_watch_later(context, playlist_id, playlist_name):
    return (
        context.localize('watch_later.list.remove'),
        context.create_uri(
            ('playlist', 'remove', 'watch_later',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
            run=True,
        ),
    )


def set_as_watch_later(context, playlist_id, playlist_name):
    return (
        context.localize('watch_later.list.set'),
        context.create_uri(
            ('playlist', 'set', 'watch_later',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
            run=True,
        ),
    )


def remove_as_history(context, playlist_id, playlist_name):
    return (
        context.localize('history.list.remove'),
        context.create_uri(
            ('playlist', 'remove', 'history',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
            run=True,
        ),
    )


def set_as_history(context, playlist_id, playlist_name):
    return (
        context.localize('history.list.set'),
        context.create_uri(
            ('playlist', 'set', 'history',),
            {
                'playlist_id': playlist_id,
                'playlist_name': playlist_name
            },
            run=True,
        ),
    )


def remove_my_subscriptions_filter(context, channel_name):
    return (
        context.localize('my_subscriptions.filter.remove'),
        context.create_uri(
            ('my_subscriptions', 'filter',),
            {
                'channel_name': channel_name,
                'action': 'remove'
            },
            run=True,
        ),
    )


def add_my_subscriptions_filter(context, channel_name):
    return (
        context.localize('my_subscriptions.filter.add'),
        context.create_uri(
            ('my_subscriptions', 'filter',),
            {
                'channel_name': channel_name,
                'action': 'add',
            },
            run=True,
        ),
    )


def rate_video(context, video_id, refresh=False):
    params = {
        'video_id': video_id,
    }
    if refresh:
        params['refresh'] = context.get_param('refresh', 0) + 1
    return (
        context.localize('video.rate'),
        context.create_uri(
            ('video', 'rate',),
            params,
            run=True,
        ),
    )


def watch_later_add(context, playlist_id, video_id):
    return (
        context.localize('watch_later.add'),
        context.create_uri(
            ('playlist', 'add', 'video',),
            {
                'playlist_id': playlist_id,
                'video_id': video_id,
            },
            run=True,
        ),
    )


def watch_later_local_add(context, item):
    return (
        context.localize('watch_later.add'),
        context.create_uri(
            (PATHS.WATCH_LATER, 'add',),
            {
                'video_id': item.video_id,
                'item': repr(item),
            },
            run=True,
        ),
    )


def watch_later_local_remove(context, video_id):
    return (
        context.localize('watch_later.remove'),
        context.create_uri(
            (PATHS.WATCH_LATER, 'remove',),
            {
                'video_id': video_id,
            },
            run=True,
        ),
    )


def watch_later_local_clear(context):
    return (
        context.localize('watch_later.clear'),
        context.create_uri(
            (PATHS.WATCH_LATER, 'clear',),
            run=True,
        ),
    )


def go_to_channel(context, channel_id, channel_name):
    return (
        context.localize('go_to_channel') % context.get_ui().bold(channel_name),
        context.create_uri(
            (PATHS.ROUTE, 'channel', channel_id,),
            run=True,
        ),
    )


def subscribe_to_channel(context, channel_id, channel_name=''):
    return (
        context.localize('subscribe_to') % context.get_ui().bold(channel_name)
        if channel_name else
        context.localize('subscribe'),
        context.create_uri(
            ('subscriptions', 'add',),
            {
                'subscription_id': channel_id,
            },
            run=True,
        ),
    )


def unsubscribe_from_channel(context, channel_id=None, subscription_id=None):
    return (
        context.localize('unsubscribe'),
        context.create_uri(
            ('subscriptions', 'remove',),
            {
                'subscription_id': subscription_id,
            },
            run=True,
        ) if subscription_id else
        context.create_uri(
            ('subscriptions', 'remove',),
            {
                'channel_id': channel_id,
            },
            run=True,
        ),
    )


def play_with_subtitles(context, video_id):
    return (
        context.localize('video.play.with_subtitles'),
        context.create_uri(
            (PATHS.PLAY,),
            {
                'video_id': video_id,
                PLAY_PROMPT_SUBTITLES: True,
            },
            run=True,
        ),
    )


def play_audio_only(context, video_id):
    return (
        context.localize('video.play.audio_only'),
        context.create_uri(
            (PATHS.PLAY,),
            {
                'video_id': video_id,
                PLAY_FORCE_AUDIO: True,
            },
            run=True,
        ),
    )


def play_ask_for_quality(context, video_id):
    return (
        context.localize('video.play.ask_for_quality'),
        context.create_uri(
            (PATHS.PLAY,),
            {
                'video_id': video_id,
                PLAY_PROMPT_QUALITY: True,
            },
            run=True,
        ),
    )


def play_timeshift(context, video_id):
    return (
        context.localize('video.play.timeshift'),
        context.create_uri(
            (PATHS.PLAY,),
            {
                'video_id': video_id,
                PLAY_TIMESHIFT: True,
            },
            run=True,
        ),
    )


def history_remove(context, video_id):
    return (
        context.localize('history.remove'),
        context.create_uri(
            (PATHS.HISTORY,),
            {
                'action': 'remove',
                'video_id': video_id
            },
            run=True,
        ),
    )


def history_clear(context):
    return (
        context.localize('history.clear'),
        context.create_uri(
            (PATHS.HISTORY,),
            {
                'action': 'clear'
            },
            run=True,
        ),
    )


def history_mark_watched(context, video_id):
    return (
        context.localize('history.mark.watched'),
        context.create_uri(
            (PATHS.HISTORY,),
            {
                'video_id': video_id,
                'action': 'mark_watched',
            },
            run=True,
        ),
    )


def history_mark_unwatched(context, video_id):
    return (
        context.localize('history.mark.unwatched'),
        context.create_uri(
            (PATHS.HISTORY,),
            {
                'video_id': video_id,
                'action': 'mark_unwatched',
            },
            run=True,
        ),
    )


def history_reset_resume(context, video_id):
    return (
        context.localize('history.reset.resume_point'),
        context.create_uri(
            (PATHS.HISTORY,),
            {
                'video_id': video_id,
                'action': 'reset_resume',
            },
            run=True,
        ),
    )


def bookmark_add(context, item):
    return (
        context.localize('bookmark'),
        context.create_uri(
            (PATHS.BOOKMARKS, 'add',),
            {
                'item_id': item.get_id(),
                'item': repr(item),
            },
            run=True,
        ),
    )


def bookmark_add_channel(context, channel_id, channel_name=''):
    return (
        (context.localize('bookmark.channel') % (
            context.get_ui().bold(channel_name) if channel_name else
            context.localize(19029)
        )),
        context.create_uri(
            (PATHS.BOOKMARKS, 'add',),
            {
                'item_id': channel_id,
                'item': None,
            },
            run=True,
        ),
    )


def bookmark_remove(context, item_id):
    return (
        context.localize('bookmark.remove'),
        context.create_uri(
            (PATHS.BOOKMARKS, 'remove',),
            {
                'item_id': item_id,
            },
            run=True,
        ),
    )


def bookmarks_clear(context):
    return (
        context.localize('bookmarks.clear'),
        context.create_uri(
            (PATHS.BOOKMARKS, 'clear',),
            run=True,
        ),
    )


def search_remove(context, query):
    return (
        context.localize('search.remove'),
        context.create_uri(
            (PATHS.SEARCH, 'remove',),
            {
                'q': query,
            },
            run=True,
        ),
    )


def search_rename(context, query):
    return (
        context.localize('search.rename'),
        context.create_uri(
            (PATHS.SEARCH, 'rename',),
            {
                'q': query,
            },
            run=True,
        ),
    )


def search_clear(context):
    return (
        context.localize('search.clear'),
        context.create_uri(
            (PATHS.SEARCH, 'clear',),
            run=True,
        ),
    )


def separator():
    return (
        '--------',
        'noop'
    )


def goto_home(context):
    return (
        context.localize(10000),
        context.create_uri(
            (PATHS.ROUTE, PATHS.HOME,),
            {
                'window_return': False,
            },
            run=True,
        ),
    )


def goto_quick_search(context):
    return (
        context.localize('search.quick'),
        context.create_uri(
            (PATHS.ROUTE, PATHS.SEARCH, 'input',),
            run=True,
        ),
    )


def goto_page(context, params=None):
    return (
        context.localize('page.choose'),
        context.create_uri(
            (PATHS.GOTO_PAGE, context.get_path(),),
            params or context.get_params(),
            run=True,
        ),
    )
