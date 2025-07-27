# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ...kodion import KodionException
from ...kodion.constants import PATHS
from ...kodion.items import menu_items
from ...kodion.utils.methods import parse_item_ids


def _process_rate_video(provider,
                        context,
                        re_match=None,
                        video_id=None,
                        current_rating=None,
                        _ratings=('like', 'dislike', 'none')):
    listitem_path = context.get_listitem_info('FileNameAndPath')

    ui = context.get_ui()
    localize = context.localize

    rating_param = context.get_param('rating', '')
    if rating_param:
        rating_param = rating_param.lower()
        if rating_param not in _ratings:
            rating_param = ''

    if video_id is None:
        video_id = context.get_param('video_id')
    if not video_id:
        try:
            video_id = re_match.group('video_id')
        except IndexError:
            if context.is_plugin_path(listitem_path, PATHS.PLAY):
                video_id = parse_item_ids(listitem_path).get('video_id')
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

    if result != -1:
        notify_message = ''

        response = provider.get_client(context).rate_video(video_id, result)

        if response:
            # this will be set if we are in the 'Liked Video' playlist
            if context.refresh_requested():
                ui.refresh_container()

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

    return True


def _process_more_for_video(context):
    params = context.get_params()

    video_id = params.get('video_id')
    if not video_id:
        raise KodionException('video/more/: missing video_id')

    items = [
        menu_items.playlist_add_to_selected(context, video_id),
        menu_items.video_related(context, video_id),
        menu_items.video_comments(context, video_id, params.get('item_name')),
        menu_items.video_description_links(context, video_id),
        menu_items.video_rate(context, video_id),
    ] if params.get('logged_in') else [
        menu_items.video_related(context, video_id),
        menu_items.video_comments(context, video_id, params.get('item_name')),
        menu_items.video_description_links(context, video_id),
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
