# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from ... import kodion
from ...youtube.helper import v3


def _process_rate_video(provider, context, re_match):
    listitem_path = context.get_ui().get_info_label('Container.ListItem(0).FileNameAndPath')
    ratings = ['like', 'dislike', 'none']

    rating_param = context.get_param('rating', '')
    if rating_param:
        rating_param = rating_param.lower() if rating_param.lower() in ratings else ''

    video_id = context.get_param('video_id', '')
    if not video_id:
        try:
            video_id = re_match.group('video_id')
        except IndexError:
            if context.is_plugin_path(listitem_path, 'play'):
                video_id = kodion.utils.find_video_id(listitem_path)

            if not video_id:
                raise kodion.KodionException('video/rate/: missing video_id')

    try:
        current_rating = re_match.group('rating')
    except IndexError:
        current_rating = None

    if not current_rating:
        client = provider.get_client(context)
        json_data = client.get_video_rating(video_id)
        if not v3.handle_error(provider, context, json_data):
            return False

        items = json_data.get('items', [])
        if items:
            current_rating = items[0].get('rating', '')

    rating_items = []
    if not rating_param:
        for rating in ratings:
            if rating != current_rating:
                rating_items.append((context.localize(provider.LOCAL_MAP['youtube.video.rate.%s' % rating]), rating))
        result = context.get_ui().on_select(context.localize(provider.LOCAL_MAP['youtube.video.rate']), rating_items)
    else:
        if rating_param != current_rating:
            result = rating_param
        else:
            result = -1

    if result != -1:
        _ = provider.get_client(context).rate_video(video_id, result)

        # this will be set if we are in the 'Liked Video' playlist
        if context.get_param('refresh_container', '0') == '1':
            context.get_ui().refresh_container()

        notify_message = ''
        if result == 'none':
            notify_message = context.localize(provider.LOCAL_MAP['youtube.unrated.video'])
        elif result == 'like':
            notify_message = context.localize(provider.LOCAL_MAP['youtube.liked.video'])
        elif result == 'dislike':
            notify_message = context.localize(provider.LOCAL_MAP['youtube.disliked.video'])

        if notify_message:
            context.get_ui().show_notification(
                message=notify_message,
                time_milliseconds=2500,
                audible=False
            )


def _process_more_for_video(provider, context):
    video_id = context.get_param('video_id', '')
    if not video_id:
        raise kodion.KodionException('video/more/: missing video_id')

    items = []

    is_logged_in = context.get_param('logged_in', '0')
    if is_logged_in == '1':
        # add video to a playlist
        items.append((context.localize(provider.LOCAL_MAP['youtube.video.add_to_playlist']),
                      'RunPlugin(%s)' % context.create_uri(['playlist', 'select', 'playlist'], {'video_id': video_id})))

    # default items
    items.extend([(context.localize(provider.LOCAL_MAP['youtube.related_videos']),
                   'Container.Update(%s)' % context.create_uri(['special', 'related_videos'], {'video_id': video_id})),
                  (context.localize(provider.LOCAL_MAP['youtube.video.description.links']),
                   'Container.Update(%s)' % context.create_uri(['special', 'description_links'],
                                                               {'video_id': video_id}))])

    if is_logged_in == '1':
        # rate a video
        refresh_container = context.get_param('refresh_container', '0')
        items.append((context.localize(provider.LOCAL_MAP['youtube.video.rate']),
                      'RunPlugin(%s)' % context.create_uri(['video', 'rate'], {'video_id': video_id,
                                                                               'refresh_container': refresh_container})))

    result = context.get_ui().on_select(context.localize(provider.LOCAL_MAP['youtube.video.more']), items)
    if result != -1:
        context.execute(result)


def process(method, provider, context, re_match):
    if method == 'rate':
        return _process_rate_video(provider, context, re_match)
    elif method == 'more':
        return _process_more_for_video(provider, context)
    else:
        raise kodion.KodionException("Unknown method '%s'" % method)
