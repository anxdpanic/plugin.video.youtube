# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ...kodion import KodionException
from ...kodion.constants import URI, VIDEO_ID
from ...kodion.items import menu_items


def _process_rate_video(provider,
                        context,
                        re_match=None,
                        video_id=None,
                        current_rating=None,
                        new_rating=None,
                        _ratings=('like', 'dislike', 'none')):
    ui = context.get_ui()
    li_path = ui.get_listitem_info(URI)

    localize = context.localize

    if new_rating is None:
        rating_param = context.get_param('rating', '')
    else:
        rating_param = new_rating
    if rating_param:
        rating_param = rating_param.lower()
        if rating_param not in _ratings:
            rating_param = ''

    if video_id is None:
        video_id = context.get_param(VIDEO_ID)
    if not video_id:
        try:
            video_id = re_match.group(VIDEO_ID)
        except IndexError:
            pass
    if not video_id and li_path:
        video_id = context.parse_item_ids(li_path).get(VIDEO_ID)
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
            return False, {provider.FALLBACK: False}

        items = json_data.get('items', [])
        if items:
            current_rating = items[0].get('rating', '')

    if not rating_param:
        result = ui.on_select(localize('video.rate'), [
            (localize('video.rate.%s' % rating), rating)
            for rating in _ratings
            if rating != current_rating
        ])
    elif rating_param != current_rating:
        result = rating_param
    else:
        result = -1

    notify_message = None
    response = None
    if result != -1:
        response = provider.get_client(context).rate_video(video_id, result)
        if response:
            if result == 'none':
                notify_message = localize(('removed.x', 'rating'))
            elif result == 'like':
                notify_message = localize('liked.video')
            elif result == 'dislike':
                notify_message = localize('disliked.video')
        else:
            notify_message = localize('failed')

    if notify_message:
        ui.show_notification(
            message=notify_message,
            time_ms=2500,
            audible=False,
        )

    return (
        True,
        {
            # this will be set if we are in the 'Liked Video' playlist
            provider.FORCE_REFRESH: response and context.refresh_requested(),
        },
    )


def _process_more_for_video(provider, context):
    params = context.get_params()

    video_id = params.get(VIDEO_ID)
    if not video_id:
        raise KodionException('video/more/: missing video_id')

    item_name = params.get('item_name')

    items = [
        menu_items.playlist_add_to_selected(context, video_id),
        menu_items.video_related(context, video_id, item_name),
        menu_items.video_comments(context, video_id, item_name),
        menu_items.video_description_links(context, video_id, item_name),
        menu_items.video_rate(context, video_id),
    ] if params.get('logged_in') else [
        menu_items.video_related(context, video_id, item_name),
        menu_items.video_comments(context, video_id, item_name),
        menu_items.video_description_links(context, video_id, item_name),
    ]

    result = context.get_ui().on_select(context.localize('video.more'), items)
    if result == -1:
        return (
            False,
            {
                provider.FALLBACK: False,
                provider.FORCE_RETURN: True,
            },
        )
    return (
        True,
        {
            provider.FALLBACK: result,
            provider.FORCE_RETURN: True,
            provider.POST_RUN: True,
        },
    )


def process(provider, context, re_match=None, command=None, **kwargs):
    if re_match and command is None:
        command = re_match.group('command')

    if command == 'rate':
        return _process_rate_video(provider, context, re_match, **kwargs)

    if command == 'more':
        return _process_more_for_video(provider, context)

    raise KodionException('Unknown video command: %s' % command)
