# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ...kodion import KodionException
from ...kodion.constants import PATHS
from ...kodion.items import menu_items
from ...kodion.utils import find_video_id


def _process_rate_video(provider,
                        context,
                        re_match=None,
                        video_id=None,
                        current_rating=None):
    listitem_path = context.get_listitem_info('FileNameAndPath')
    ratings = ['like', 'dislike', 'none']

    rating_param = context.get_param('rating', '')
    if rating_param:
        rating_param = rating_param.lower() if rating_param.lower() in ratings else ''

    if video_id is None:
        video_id = context.get_param('video_id')
    if not video_id:
        try:
            video_id = re_match.group('video_id')
        except IndexError:
            if context.is_plugin_path(listitem_path, PATHS.PLAY):
                video_id = find_video_id(listitem_path)

            if not video_id:
                raise KodionException('video/rate/: missing video_id')

    if current_rating is None:
        try:
            current_rating = re_match.group('rating')
        except IndexError:
            current_rating = None
    if not current_rating:
        client = provider.get_client(context)
        json_data = client.get_video_rating(video_id)
        if not json_data:
            return False, {provider.RESULT_FALLBACK: False}

        items = json_data.get('items', [])
        if items:
            current_rating = items[0].get('rating', '')

    rating_items = []
    if not rating_param:
        for rating in ratings:
            if rating != current_rating:
                rating_items.append((context.localize('video.rate.%s' % rating), rating))
        result = context.get_ui().on_select(context.localize('video.rate'), rating_items)
    elif rating_param != current_rating:
        result = rating_param
    else:
        result = -1

    if result != -1:
        notify_message = ''

        response = provider.get_client(context).rate_video(video_id, result)

        if response:
            # this will be set if we are in the 'Liked Video' playlist
            if context.get_param('refresh'):
                context.get_ui().refresh_container()

            if result == 'none':
                notify_message = context.localize('unrated.video')
            elif result == 'like':
                notify_message = context.localize('liked.video')
            elif result == 'dislike':
                notify_message = context.localize('disliked.video')
        else:
            notify_message = context.localize('failed')

        if notify_message:
            context.get_ui().show_notification(
                message=notify_message,
                time_ms=2500,
                audible=False,
            )

    return True


def _process_more_for_video(context):
    params = context.get_params()

    video_id = params.get('video_id')
    if not video_id:
        raise KodionException('video/more/: missing video_id')

    items = [
        menu_items.add_video_to_playlist(context, video_id),
        menu_items.related_videos(context, video_id),
        menu_items.video_comments(context, video_id, params.get('item_name')),
        menu_items.content_from_description(context, video_id),
        menu_items.rate_video(context, video_id, params.get('refresh')),
    ] if params.get('logged_in') else [
        menu_items.related_videos(context, video_id),
        menu_items.video_comments(context, video_id, params.get('item_name')),
        menu_items.content_from_description(context, video_id),
    ]

    result = context.get_ui().on_select(context.localize('video.more'), items)
    if result != -1:
        context.execute(result)


def process(provider, context, re_match=None, command=None, **kwargs):
    if re_match and command is None:
        command = re_match.group('command')

    if command == 'rate':
        return _process_rate_video(provider, context, re_match, **kwargs)

    if command == 'more':
        return _process_more_for_video(context)

    raise KodionException('Unknown video command: %s' % command)
