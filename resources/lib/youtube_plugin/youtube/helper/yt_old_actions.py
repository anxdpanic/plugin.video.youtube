# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ... import kodion


def _process_play_video(provider, context, re_match):
    """
    plugin://plugin.video.youtube/?action=play_video&videoid=[ID]
    """
    video_id = context.get_param('videoid', '')
    if not video_id:
        raise kodion.KodionException('old_actions/play_video: missing video_id')

    context.log_warning('DEPRECATED "%s"' % context.get_uri())
    context.log_warning('USE INSTEAD "plugin://%s/play/?video_id=%s"' % (context.get_id(), video_id))
    new_params = {'video_id': video_id}
    new_path = '/play/'
    new_context = context.clone(new_path=new_path, new_params=new_params)
    return provider.on_play(new_context, re_match)


def _process_play_all(provider, context, re_match):
    """
    plugin://plugin.video.youtube/?path=/root/video&action=play_all&playlist=PL8_6CHho8Tq4Iie-oNxb-g0ECxIhq3CxW
    plugin://plugin.video.youtube/?action=play_all&playlist=PLZRRxQcaEjA5fgfW3a3Q0rzm6NgbmICtg&videoid=qmlYe2KS0-Y
    """
    playlist_id = context.get_param('playlist', '')
    if not playlist_id:
        raise kodion.KodionException('old_actions/play_all: missing playlist_id')

    # optional starting video id of the playlist
    video_id = context.get_param('videoid', '')
    if video_id:
        context.log_warning(
            'USE INSTEAD "plugin://%s/play/?playlist_id=%s&video_id=%s"' % (context.get_id(), playlist_id, video_id))
    else:
        context.log_warning('USE INSTEAD "plugin://%s/play/?playlist_id=%s"' % (context.get_id(), playlist_id))
    new_params = {'playlist_id': playlist_id}
    new_path = '/play/'
    new_context = context.clone(new_path=new_path, new_params=new_params)
    return provider.on_play(new_context, re_match)


def process_old_action(provider, context, re_match):
    """
    if context.get_system_version().get_version() >= (15, 0):
        message = u"You're using old YouTube-Plugin calls - please review the log for updated end points starting with Isengard"
        context.get_ui().show_notification(message, time_ms=15000)
    """

    action = context.get_param('action', '')
    if action == 'play_video':
        return _process_play_video(provider, context, re_match)
    elif action == 'play_all':
        return _process_play_all(provider, context, re_match)
    else:
        raise kodion.KodionException('old_actions: unknown action "%s"' % action)
