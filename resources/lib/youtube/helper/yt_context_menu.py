__author__ = 'bromix'

from resources.lib import kodion


def append_more_for_video(context_menu, provider, context, video_id, is_logged_in=False, refresh_container=False):
    _is_logged_in = '0'
    if is_logged_in:
        _is_logged_in = '1'
        pass

    _refresh_container = '0'
    if refresh_container:
        _refresh_container = '1'
        pass

    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.more']),
                         'Container.Update(%s)' % context.create_uri(['video', 'more'],
                                                                     {'video_id': video_id,
                                                                      'logged_in': _is_logged_in,
                                                                      'refresh_container': _refresh_container})))
    pass


def append_content_from_description(context_menu, provider, context, video_id):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.description.links']),
                         'Container.Update(%s)' % context.create_uri(['special', 'description_links'],
                                                                     {'video_id': video_id})))
    pass


def append_play_with(context_menu, provider, context):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.play_with']), 'Action(SwitchPlayer)'))
    pass


def append_queue_video(context_menu, provider, context):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.queue']), 'Action(Queue)'))
    pass


def append_play_all_from_playlist(context_menu, provider, context, playlist_id, video_id=''):
    if video_id:
        context_menu.append((context.localize(provider.LOCAL_MAP['youtube.playlist.play.from_here']),
                             'RunPlugin(%s)' % context.create_uri(['play'],
                                                                  {'playlist_id': playlist_id,
                                                                   'video_id': video_id,
                                                                   'play': '1'})))
        pass
    else:
        context_menu.append((context.localize(provider.LOCAL_MAP['youtube.playlist.play.all']),
                             'RunPlugin(%s)' % context.create_uri(['play'],
                                                                  {'playlist_id': playlist_id,
                                                                   'play': '1'})))
        pass
    pass


def append_add_video_to_playlist(context_menu, provider, context, video_id):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.add_to_playlist']),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'select', 'playlist'],
                                                              {'video_id': video_id})))
    pass


def append_rename_playlist(context_menu, provider, context, playlist_id, playlist_name):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.rename']),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'rename', 'playlist'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))
    pass


def append_delete_playlist(context_menu, provider, context, playlist_id, playlist_name):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.delete']),
                         'RunPlugin(%s)' % context.create_uri(['playlist', 'remove', 'playlist'],
                                                              {'playlist_id': playlist_id,
                                                               'playlist_name': playlist_name})))
    pass


def append_rate_video(context_menu, provider, context, video_id, refresh_container=False):
    if refresh_container:
        refresh_container = '1'
        pass
    else:
        refresh_container = '0'
        pass
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.video.rate']),
                         'RunPlugin(%s)' % context.create_uri(['video', 'rate'],
                                                              {'video_id': video_id,
                                                               'refresh_container': refresh_container})))
    pass


def append_watch_later(context_menu, provider, context, playlist_id, video_id):
    playlist_path = kodion.utils.create_path('channel', 'mine', 'playlist', playlist_id)
    if playlist_id and playlist_path != context.get_path():
        context_menu.append((context.localize(provider.LOCAL_MAP['youtube.watch_later']),
                             'RunPlugin(%s)' % context.create_uri(['playlist', 'add', 'video'],
                                                                  {'playlist_id': playlist_id, 'video_id': video_id})))
        pass
    pass


def append_go_to_channel(context_menu, provider, context, channel_id, channel_name):
    text = context.localize(provider.LOCAL_MAP['youtube.go_to_channel']) % ('[B]%s[/B]' % channel_name)
    context_menu.append((text, 'Container.Update(%s)' % context.create_uri(['channel', channel_id])))
    pass


def append_related_videos(context_menu, provider, context, video_id):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.related_videos']),
                         'Container.Update(%s)' % context.create_uri(['special', 'related_videos'],
                                                                     {'video_id': video_id})))
    pass


def append_refresh(context_menu, provider, context):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.refresh']), 'Container.Refresh'))
    pass


def append_subscribe_to_channel(context_menu, provider, context, channel_id, channel_name=u''):
    text = u''
    if channel_name:
        text = context.localize(provider.LOCAL_MAP['youtube.subscribe_to']).replace('%s', '[B]' + channel_name + '[/B]')
        context_menu.append(
            (text, 'RunPlugin(%s)' % context.create_uri(['subscriptions', 'add'], {'subscription_id': channel_id})))
        pass
    else:
        context_menu.append((context.localize(provider.LOCAL_MAP['youtube.subscribe']),
                             'RunPlugin(%s)' % context.create_uri(['subscriptions', 'add'],
                                                                  {'subscription_id': channel_id})))
        pass
    pass


def append_unsubscribe_from_channel(context_menu, provider, context, channel_id, channel_name=u''):
    context_menu.append((context.localize(provider.LOCAL_MAP['youtube.unsubscribe']),
                         'RunPlugin(%s)' % context.create_uri(['subscriptions', 'remove'],
                                                              {'subscription_id': channel_id})))
    pass