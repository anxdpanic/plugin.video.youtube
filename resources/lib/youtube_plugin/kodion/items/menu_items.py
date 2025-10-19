# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..constants import (
    ARTIST,
    BOOKMARK_ID,
    CHANNEL_ID,
    CONTEXT_MENU,
    INCOGNITO,
    MARK_AS_LABEL,
    ORDER,
    PATHS,
    PLAYLIST_ITEM_ID,
    PLAYLIST_ID,
    PLAY_FORCE_AUDIO,
    PLAY_PROMPT_QUALITY,
    PLAY_PROMPT_SUBTITLES,
    PLAY_TIMESHIFT,
    PLAY_USING,
    PROPERTY_AS_LABEL,
    SUBSCRIPTION_ID,
    TITLE,
    URI,
    VIDEO_ID,
    WINDOW_RETURN,
)


ARTIST_INFOLABEL = PROPERTY_AS_LABEL % ARTIST
BOOKMARK_ID_INFOLABEL = PROPERTY_AS_LABEL % BOOKMARK_ID
CHANNEL_ID_INFOLABEL = PROPERTY_AS_LABEL % CHANNEL_ID
PLAYLIST_ID_INFOLABEL = PROPERTY_AS_LABEL % PLAYLIST_ID
PLAYLIST_ITEM_ID_INFOLABEL = PROPERTY_AS_LABEL % PLAYLIST_ITEM_ID
SUBSCRIPTION_ID_INFOLABEL = PROPERTY_AS_LABEL % SUBSCRIPTION_ID
TITLE_INFOLABEL = PROPERTY_AS_LABEL % TITLE
URI_INFOLABEL = PROPERTY_AS_LABEL % URI
VIDEO_ID_INFOLABEL = PROPERTY_AS_LABEL % VIDEO_ID


def context_menu_uri(context, path, params=None):
    if params is None:
        params = {CONTEXT_MENU: True}
    else:
        params[CONTEXT_MENU] = True
    return context.create_uri(path, params, run=True)


def video_more_for(context,
                   video_id=VIDEO_ID_INFOLABEL,
                   video_name=TITLE_INFOLABEL,
                   logged_in=False,
                   refresh=False):
    params = {
        VIDEO_ID: video_id,
        'item_name': video_name,
        'logged_in': logged_in,
    }
    _refresh = context.refresh_requested(force=True, on=refresh)
    if _refresh:
        params['refresh'] = _refresh
    return (
        context.localize('video.more'),
        context_menu_uri(
            context,
            ('video', 'more',),
            params,
        ),
    )


def video_related(context,
                  video_id=VIDEO_ID_INFOLABEL,
                  video_name=TITLE_INFOLABEL):
    return (
        context.localize('video.related'),
        context_menu_uri(
            context,
            (PATHS.ROUTE, PATHS.RELATED_VIDEOS,),
            {
                VIDEO_ID: video_id,
                'item_name': video_name,
            },
        ),
    )


def video_comments(context,
                   video_id=VIDEO_ID_INFOLABEL,
                   video_name=TITLE_INFOLABEL):
    return (
        context.localize('video.comments'),
        context_menu_uri(
            context,
            (PATHS.ROUTE, PATHS.VIDEO_COMMENTS),
            {
                VIDEO_ID: video_id,
                'item_name': video_name,
            },
        )
    )


def video_description_links(context,
                            video_id=VIDEO_ID_INFOLABEL,
                            video_name=TITLE_INFOLABEL):
    return (
        context.localize('video.description_links'),
        context_menu_uri(
            context,
            (PATHS.ROUTE, PATHS.DESCRIPTION_LINKS),
            {
                VIDEO_ID: video_id,
                'item_name': video_name,
            },
        )
    )


def media_play_using(context, video_id=VIDEO_ID_INFOLABEL):
    return (
        context.localize('video.play.using'),
        context_menu_uri(
            context,
            (PATHS.PLAY,),
            {
                VIDEO_ID: video_id,
                PLAY_USING: True,
            },
        ),
    )


def refresh_listing(context, path=None, params=None):
    if path is None:
        path = (PATHS.ROUTE, context.get_path(),)
    elif isinstance(path, tuple):
        path = (PATHS.ROUTE,) + path
    else:
        path = (PATHS.ROUTE, path,)
    if params is None:
        params = context.get_params()
    return (
        context.localize('refresh'),
        context_menu_uri(
            context,
            path,
            dict(params,
                 refresh=context.refresh_requested(
                     force=True,
                     on=True,
                     params=params,
                 )),
        ),
    )


def folder_play(context, path, order='normal'):
    return (
        context.localize('playlist.play.shuffle')
        if order == 'shuffle' else
        context.localize('playlist.play.all'),
        context_menu_uri(
            context,
            (path, 'play',),
            {
                'order': order,
            },
        ),
    )


def media_play(context):
    return (
        context.localize('video.play'),
        'Action(Play)'
    )


def media_queue(context):
    return (
        context.localize('video.queue'),
        'Action(Queue)'
    )


def playlist_play(context, playlist_id=PLAYLIST_ID_INFOLABEL):
    return (
        context.localize('playlist.play.all'),
        context_menu_uri(
            context,
            (PATHS.PLAY,),
            {
                PLAYLIST_ID: playlist_id,
                'order': 'ask',
            },
        ),
    )


def playlist_play_from(context,
                       playlist_id=PLAYLIST_ID_INFOLABEL,
                       video_id=VIDEO_ID_INFOLABEL):
    return (
        context.localize('playlist.play.from_here'),
        context_menu_uri(
            context,
            (PATHS.PLAY,),
            {
                PLAYLIST_ID: playlist_id,
                VIDEO_ID: video_id,
            },
        ),
    )


def playlist_play_recently_added(context, playlist_id=PLAYLIST_ID_INFOLABEL):
    return (
        context.localize('playlist.play.recently_added'),
        context_menu_uri(
            context,
            (PATHS.PLAY,),
            {
                PLAYLIST_ID: playlist_id,
                'recent_days': 1,
            },
        ),
    )


def playlist_view(context, playlist_id=PLAYLIST_ID_INFOLABEL):
    return (
        context.localize('playlist.view.all'),
        context_menu_uri(
            context,
            (PATHS.ROUTE, PATHS.PLAY,),
            {
                PLAYLIST_ID: playlist_id,
                'order': 'normal',
                'action': 'list',
            },
        ),
    )


def playlist_shuffle(context, playlist_id=PLAYLIST_ID_INFOLABEL):
    return (
        context.localize('playlist.play.shuffle'),
        context_menu_uri(
            context,
            (PATHS.PLAY,),
            {
                PLAYLIST_ID: playlist_id,
                'order': 'shuffle',
                'action': 'play',
            },
        ),
    )


def playlist_add_to(context,
                    playlist_id,
                    name_id='playlist',
                    video_id=VIDEO_ID_INFOLABEL):
    return (
        context.localize(('add.to.x', name_id)),
        context_menu_uri(
            context,
            (PATHS.PLAYLIST, 'add', 'video',),
            {
                PLAYLIST_ID: playlist_id,
                VIDEO_ID: video_id,
            },
        ),
    )


def playlist_add_to_selected(context, video_id=VIDEO_ID_INFOLABEL):
    return (
        context.localize('video.add_to_playlist'),
        context_menu_uri(
            context,
            (PATHS.PLAYLIST, 'select', 'playlist',),
            {
                VIDEO_ID: video_id,
            },
        ),
    )


def playlist_remove_from(context,
                         playlist_id=PLAYLIST_ID_INFOLABEL,
                         playlist_item_id=PLAYLIST_ITEM_ID_INFOLABEL,
                         video_id=VIDEO_ID_INFOLABEL,
                         video_name=TITLE_INFOLABEL):
    return (
        context.localize('remove'),
        context_menu_uri(
            context,
            (PATHS.PLAYLIST, 'remove', 'video',),
            dict(
                context.get_params(),
                **{
                    PLAYLIST_ID: playlist_id,
                    PLAYLIST_ITEM_ID: playlist_item_id,
                    VIDEO_ID: video_id,
                    'item_name': video_name,
                    'reload_path': context.get_path(),
                }
            ),
        ),
    )


def playlist_rename(context,
                    playlist_id=PLAYLIST_ID_INFOLABEL,
                    playlist_name=TITLE_INFOLABEL):
    return (
        context.localize('rename'),
        context_menu_uri(
            context,
            (PATHS.PLAYLIST, 'rename', 'playlist',),
            {
                PLAYLIST_ID: playlist_id,
                'item_name': playlist_name
            },
        ),
    )


def playlist_delete(context,
                    playlist_id=PLAYLIST_ID_INFOLABEL,
                    playlist_name=TITLE_INFOLABEL):
    return (
        context.localize('delete'),
        context_menu_uri(
            context,
            (PATHS.PLAYLIST, 'remove', 'playlist',),
            {
                PLAYLIST_ID: playlist_id,
                'item_name': playlist_name
            },
        ),
    )


def playlist_save_to_library(context, playlist_id=PLAYLIST_ID_INFOLABEL):
    return (
        context.localize('save'),
        context_menu_uri(
            context,
            (PATHS.PLAYLIST, 'like', 'playlist',),
            {
                PLAYLIST_ID: playlist_id,
            },
        ),
    )


def playlist_remove_from_library(context,
                                 playlist_id=PLAYLIST_ID_INFOLABEL,
                                 playlist_name=TITLE_INFOLABEL):
    return (
        context.localize('remove'),
        context_menu_uri(
            context,
            (PATHS.PLAYLIST, 'unlike', 'playlist',),
            {
                PLAYLIST_ID: playlist_id,
                'item_name': playlist_name,
                'reload_path': context.get_path(),
            },
        ),
    )


def watch_later_list_unassign(context,
                              playlist_id=PLAYLIST_ID_INFOLABEL,
                              playlist_name=TITLE_INFOLABEL):
    return (
        context.localize('watch_later.list.unassign'),
        context_menu_uri(
            context,
            (PATHS.PLAYLIST, 'unassign', 'watch_later',),
            {
                PLAYLIST_ID: playlist_id,
                'item_name': playlist_name
            },
        ),
    )


def watch_later_list_assign(context,
                            playlist_id=PLAYLIST_ID_INFOLABEL,
                            playlist_name=TITLE_INFOLABEL):
    return (
        context.localize('watch_later.list.assign'),
        context_menu_uri(
            context,
            (PATHS.PLAYLIST, 'assign', 'watch_later',),
            {
                PLAYLIST_ID: playlist_id,
                'item_name': playlist_name
            },
        ),
    )


def history_list_unassign(context,
                          playlist_id=PLAYLIST_ID_INFOLABEL,
                          playlist_name=TITLE_INFOLABEL):
    return (
        context.localize('history.list.unassign'),
        context_menu_uri(
            context,
            (PATHS.PLAYLIST, 'unassign', 'history',),
            {
                PLAYLIST_ID: playlist_id,
                'item_name': playlist_name
            },
        ),
    )


def history_list_assign(context,
                        playlist_id=PLAYLIST_ID_INFOLABEL,
                        playlist_name=TITLE_INFOLABEL):
    return (
        context.localize('history.list.assign'),
        context_menu_uri(
            context,
            (PATHS.PLAYLIST, 'assign', 'history',),
            {
                PLAYLIST_ID: playlist_id,
                'item_name': playlist_name
            },
        ),
    )


def my_subscriptions_filter_remove(context, channel_name=ARTIST_INFOLABEL):
    return (
        context.localize(('remove.from.x', 'my_subscriptions.filtered')),
        context_menu_uri(
            context,
            ('my_subscriptions', 'filter', 'remove'),
            {
                'item_name': channel_name,
            },
        ),
    )


def my_subscriptions_filter_add(context, channel_name=ARTIST_INFOLABEL):
    return (
        context.localize(('add.to.x', 'my_subscriptions.filtered')),
        context_menu_uri(
            context,
            ('my_subscriptions', 'filter', 'add',),
            {
                'item_name': channel_name,
            },
        ),
    )


def video_rate(context, video_id=VIDEO_ID_INFOLABEL, refresh=False):
    params = {
        VIDEO_ID: video_id,
    }
    _refresh = context.refresh_requested(force=True, on=refresh)
    if _refresh:
        params['refresh'] = _refresh
    return (
        context.localize('video.rate'),
        context_menu_uri(
            context,
            ('video', 'rate',),
            params,
        ),
    )


def watch_later_local_add(context, item):
    return (
        context.localize('watch_later.add'),
        context_menu_uri(
            context,
            (PATHS.WATCH_LATER, 'add',),
            {
                VIDEO_ID: item.video_id,
                'item': repr(item),
            },
        ),
    )


def watch_later_local_remove(context,
                             video_id=VIDEO_ID_INFOLABEL,
                             video_name=TITLE_INFOLABEL):
    return (
        context.localize('watch_later.remove'),
        context_menu_uri(
            context,
            (PATHS.WATCH_LATER, 'remove',),
            {
                VIDEO_ID: video_id,
                'item_name': video_name,
            },
        ),
    )


def watch_later_local_clear(context):
    return (
        context.localize('watch_later.clear'),
        context_menu_uri(
            context,
            (PATHS.WATCH_LATER, 'clear',),
        ),
    )


def channel_go_to(context,
                  channel_id=CHANNEL_ID_INFOLABEL,
                  channel_name=ARTIST_INFOLABEL):
    return (
        context.localize('go_to.x', context.get_ui().bold(channel_name)),
        context_menu_uri(
            context,
            (PATHS.ROUTE, PATHS.CHANNEL, channel_id,),
            {
                'category_label': channel_name,
            }
        ),
    )


def channel_subscribe_to(context,
                         channel_id=CHANNEL_ID_INFOLABEL,
                         channel_name=ARTIST_INFOLABEL):
    return (
        context.localize('subscribe_to.x', context.get_ui().bold(channel_name))
        if channel_name else
        context.localize('subscribe'),
        context_menu_uri(
            context,
            ('subscriptions', 'add',),
            {
                SUBSCRIPTION_ID: channel_id,
            },
        ),
    )


def channel_unsubscribe_from(context, channel_id=None, subscription_id=None):
    return (
        context.localize('unsubscribe'),
        context_menu_uri(
            context,
            ('subscriptions', 'remove',),
            {
                SUBSCRIPTION_ID: subscription_id,
            },
        ) if subscription_id else
        context_menu_uri(
            context,
            ('subscriptions', 'remove',),
            {
                CHANNEL_ID: channel_id,
            },
        ),
    )


def media_play_with_subtitles(context,
                              video_id=VIDEO_ID_INFOLABEL):
    return (
        context.localize('video.play.with_subtitles'),
        context_menu_uri(
            context,
            (PATHS.PLAY,),
            {
                VIDEO_ID: video_id,
                PLAY_PROMPT_SUBTITLES: True,
            },
        ),
    )


def media_play_audio_only(context,
                          video_id=VIDEO_ID_INFOLABEL):
    return (
        context.localize('video.play.audio_only'),
        context_menu_uri(
            context,
            (PATHS.PLAY,),
            {
                VIDEO_ID: video_id,
                PLAY_FORCE_AUDIO: True,
            },
        ),
    )


def media_play_ask_for_quality(context,
                               video_id=VIDEO_ID_INFOLABEL):
    return (
        context.localize('video.play.ask_for_quality'),
        context_menu_uri(
            context,
            (PATHS.PLAY,),
            {
                VIDEO_ID: video_id,
                PLAY_PROMPT_QUALITY: True,
            },
        ),
    )


def media_play_timeshift(context,
                         video_id=VIDEO_ID_INFOLABEL):
    return (
        context.localize('video.play.timeshift'),
        context_menu_uri(
            context,
            (PATHS.PLAY,),
            {
                VIDEO_ID: video_id,
                PLAY_TIMESHIFT: True,
            },
        ),
    )


def history_local_remove(context,
                         video_id=VIDEO_ID_INFOLABEL,
                         video_name=TITLE_INFOLABEL):
    return (
        context.localize('history.remove'),
        context_menu_uri(
            context,
            (PATHS.HISTORY, 'remove',),
            {
                VIDEO_ID: video_id,
                'item_name': video_name,
            },
        ),
    )


def history_local_clear(context):
    return (
        context.localize('history.clear'),
        context_menu_uri(
            context,
            (PATHS.HISTORY, 'clear',),
        ),
    )


def history_local_mark_as(context, video_id=VIDEO_ID_INFOLABEL):
    return (
        PROPERTY_AS_LABEL % MARK_AS_LABEL,
        context_menu_uri(
            context,
            (PATHS.HISTORY, 'mark_as',),
            {
                VIDEO_ID: video_id,
            },
        ),
    )


def history_local_mark_watched(context, video_id=VIDEO_ID_INFOLABEL):
    return (
        context.localize('history.mark.watched'),
        context_menu_uri(
            context,
            (PATHS.HISTORY, 'mark_watched',),
            {
                VIDEO_ID: video_id,
            },
        ),
    )


def history_local_mark_unwatched(context, video_id=VIDEO_ID_INFOLABEL):
    return (
        context.localize('history.mark.unwatched'),
        context_menu_uri(
            context,
            (PATHS.HISTORY, 'mark_unwatched',),
            {
                VIDEO_ID: video_id,
            },
        ),
    )


def history_local_reset_resume(context, video_id=VIDEO_ID_INFOLABEL):
    return (
        context.localize('history.reset.resume_point'),
        context_menu_uri(
            context,
            (PATHS.HISTORY, 'reset_resume',),
            {
                VIDEO_ID: video_id,
            },
        ),
    )


def bookmark_add(context, item):
    return (
        context.localize('bookmark'),
        context_menu_uri(
            context,
            (PATHS.BOOKMARKS, 'add',),
            {
                'item_id': item.get_id(),
                'item': repr(item),
            },
        ),
    )


def bookmark_add_channel(context,
                         channel_id=CHANNEL_ID_INFOLABEL,
                         channel_name=ARTIST_INFOLABEL):
    return (
        context.localize('bookmark.x',
                         context.get_ui().bold(channel_name)
                         if channel_name else
                         context.localize('channel')),
        context_menu_uri(
            context,
            (PATHS.BOOKMARKS, 'add',),
            {
                'item_id': channel_id,
                'item': None,
            },
        ),
    )


def bookmark_edit(context,
                  item_id=BOOKMARK_ID_INFOLABEL,
                  item_name=TITLE_INFOLABEL,
                  item_uri=URI_INFOLABEL):
    return (
        context.localize(('edit.x', 'bookmark')),
        context_menu_uri(
            context,
            (PATHS.BOOKMARKS, 'edit',),
            {
                'item_id': item_id,
                'item_name': item_name,
                'uri': item_uri,
            },
        ),
    )


def bookmark_remove(context,
                    item_id=BOOKMARK_ID_INFOLABEL,
                    item_name=TITLE_INFOLABEL):
    return (
        context.localize('bookmark.remove'),
        context_menu_uri(
            context,
            (PATHS.BOOKMARKS, 'remove',),
            {
                'item_id': item_id,
                'item_name': item_name,
            },
        ),
    )


def bookmarks_clear(context):
    return (
        context.localize('bookmarks.clear'),
        context_menu_uri(
            context,
            (PATHS.BOOKMARKS, 'clear',),
        ),
    )


def search_remove(context, query):
    return (
        context.localize('search.remove'),
        context_menu_uri(
            context,
            (PATHS.SEARCH, 'remove',),
            {
                'q': query,
            },
        ),
    )


def search_rename(context, query):
    return (
        context.localize('search.rename'),
        context_menu_uri(
            context,
            (PATHS.SEARCH, 'rename',),
            {
                'q': query,
            },
        ),
    )


def search_clear(context):
    return (
        context.localize('search.clear'),
        context_menu_uri(
            context,
            (PATHS.SEARCH, 'clear',),
        ),
    )


def search_sort_by(context, params, order):
    selected = params.get(ORDER, 'relevance') == order
    order_label = context.localize('search.sort.' + order)
    return (
        context.localize('search.sort').format(
            context.get_ui().bold(order_label) if selected else order_label
        ),
        context_menu_uri(
            context,
            (PATHS.ROUTE, context.get_path(),),
            params=dict(params,
                        order=order,
                        page=1,
                        page_token='',
                        pageToken='',
                        window_replace=True,
                        window_return=False),
        ),
    )


def separator():
    return (
        '--------',
        'noop'
    )


def goto_home(context):
    return (
        context.localize('home'),
        context_menu_uri(
            context,
            (PATHS.ROUTE, PATHS.HOME,),
            {
                WINDOW_RETURN: False,
            },
        ),
    )


def goto_quick_search(context, params=None, incognito=None):
    if params is None:
        params = {}
    if incognito is None:
        incognito = params.get(INCOGNITO)
    else:
        params[INCOGNITO] = incognito
    return (
        context.localize('search.quick.incognito'
                         if incognito else
                         'search.quick'),
        context_menu_uri(
            context,
            (PATHS.ROUTE, PATHS.SEARCH, 'input',),
            params,
        ),
    )


def goto_page(context, params=None):
    return (
        context.localize('page.choose'),
        context_menu_uri(
            context,
            (PATHS.GOTO_PAGE, context.get_path(),),
            params or context.get_params(),
        ),
    )
