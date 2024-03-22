# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ...kodion import KodionException
from ...kodion.utils import find_video_id


def _process_add_video(provider, context, keymap_action=False):
    path = context.get_listitem_detail('FileNameAndPath', attr=True)

    client = provider.get_client(context)
    logged_in = provider.is_logged_in()
    if not logged_in:
        raise KodionException('Playlist/Add: not logged in')

    watch_later_id = context.get_access_manager().get_watch_later_id()

    playlist_id = context.get_param('playlist_id', '')
    if playlist_id.lower() == 'watch_later':
        playlist_id = watch_later_id

    if not playlist_id:
        raise KodionException('Playlist/Add: missing playlist_id')

    video_id = context.get_param('video_id', '')
    if not video_id:
        if context.is_plugin_path(path, 'play/'):
            video_id = find_video_id(path)
            keymap_action = True
        if not video_id:
            raise KodionException('Playlist/Add: missing video_id')

    json_data = client.add_video_to_playlist(playlist_id=playlist_id,
                                             video_id=video_id)
    if not json_data:
        context.log_debug('Playlist/Add: failed for playlist |{playlist_id}|'
                          .format(playlist_id=playlist_id))
        return False

    if playlist_id == watch_later_id:
        notify_message = context.localize('watch_later.added_to')
    else:
        notify_message = context.localize('playlist.added_to')

    context.get_ui().show_notification(
        message=notify_message,
        time_ms=2500,
        audible=False
    )

    if keymap_action:
        context.get_ui().set_focus_next_item()

    return True


def _process_remove_video(provider, context):
    listitem_playlist_id = context.get_listitem_detail('playlist_id')
    listitem_playlist_item_id = context.get_listitem_detail('playlist_item_id')
    listitem_title = context.get_listitem_detail('Title', attr=True)
    keymap_action = False

    params = context.get_params()
    playlist_id = params.pop('playlist_id', '')
    video_id = params.pop('video_id', '')
    video_name = params.pop('video_name', '')

    # keymap support
    if (not playlist_id and not video_id and listitem_playlist_id
            and listitem_playlist_id.startswith('PL')
            and listitem_playlist_item_id
            and listitem_playlist_item_id.startswith('UE')):
        playlist_id = listitem_playlist_id
        video_id = listitem_playlist_item_id
        keymap_action = True

    if not playlist_id:
        raise KodionException('Playlist/Remove: missing playlist_id')

    if not video_id:
        raise KodionException('Playlist/Remove: missing video_id')

    if not video_name:
        if listitem_title:
            video_name = listitem_title
        else:
            raise KodionException('Playlist/Remove: missing video_name')

    if playlist_id.strip().lower() not in ('wl', 'hl'):
        if context.get_ui().on_remove_content(video_name):
            success = provider.get_client(context).remove_video_from_playlist(
                playlist_id=playlist_id,
                playlist_item_id=video_id,
            )
            if not success:
                return False

            path = params.pop('reload_path', None)
            context.get_ui().reload_container(path)

            context.get_ui().show_notification(
                message=context.localize('playlist.removed_from'),
                time_ms=2500,
                audible=False
            )

            if keymap_action:
                context.get_ui().set_focus_next_item()

            return True
    else:
        context.log_debug('Cannot remove from playlist id |%s|' % playlist_id)

    return False


def _process_remove_playlist(provider, context):
    playlist_id = context.get_param('playlist_id', '')
    if not playlist_id:
        raise KodionException('Playlist/Remove: missing playlist_id')

    playlist_name = context.get_param('playlist_name', '')
    if not playlist_name:
        raise KodionException('Playlist/Remove: missing playlist_name')

    if context.get_ui().on_delete_content(playlist_name):
        json_data = provider.get_client(context).remove_playlist(playlist_id=playlist_id)
        if not json_data:
            return False

        context.get_ui().refresh_container()
    return True


def _process_select_playlist(provider, context):
    # Get listitem path asap, relies on listitems focus
    path = context.get_listitem_detail('FileNameAndPath', attr=True)

    params = context.get_params()
    ui = context.get_ui()
    keymap_action = False
    page_token = ''
    current_page = 0

    video_id = params.get('video_id', '')
    if not video_id:
        if context.is_plugin_path(path, 'play/'):
            video_id = find_video_id(path)
            if video_id:
                context.set_param('video_id', video_id)
                keymap_action = True
        if not video_id:
            raise KodionException('Playlist/Select: missing video_id')

    function_cache = context.get_function_cache()
    client = provider.get_client(context)
    while True:
        current_page += 1
        json_data = function_cache.run(client.get_playlists_of_channel,
                                       function_cache.ONE_MINUTE // 3,
                                       _refresh=params.get('refresh'),
                                       channel_id='mine',
                                       page_token=page_token)

        playlists = json_data.get('items', [])
        page_token = json_data.get('nextPageToken', '')

        items = []
        if current_page == 1:
            # create playlist
            items.append((
                ui.bold(context.localize('playlist.create')), '',
                'playlist.create',
                context.create_resource_path('media', 'playlist.png')
            ))

            # add the 'Watch Later' playlist
            resource_manager = provider.get_resource_manager(context)
            my_playlists = resource_manager.get_related_playlists(channel_id='mine')
            if 'watchLater' in my_playlists:
                watch_later_id = context.get_access_manager().get_watch_later_id()
                if watch_later_id:
                    items.append((
                        ui.bold(context.localize('watch_later')), '',
                        watch_later_id,
                        context.create_resource_path('media', 'watch_later.png')
                    ))

        default_thumb = context.create_resource_path('media', 'playlist.png')
        for playlist in playlists:
            snippet = playlist.get('snippet', {})
            title = snippet.get('title', '')
            description = snippet.get('description', '')
            thumbnail = snippet.get('thumbnails', {}).get('default', {})
            playlist_id = playlist.get('id', '')
            if title and playlist_id:
                items.append((
                    title, description,
                    playlist_id,
                    thumbnail.get('url') or default_thumb
                ))

        if page_token:
            items.append((ui.bold(context.localize('next_page')).replace('%d', str(current_page + 1)), '',
                          'playlist.next', 'DefaultFolder.png'))

        result = ui.on_select(context.localize('playlist.select'), items)
        if result == 'playlist.create':
            result, text = ui.on_keyboard_input(
                context.localize('playlist.create'))
            if result and text:
                json_data = client.create_playlist(title=text)
                if not json_data:
                    break

                playlist_id = json_data.get('id', '')
                if playlist_id:
                    new_params = dict(context.get_params(),
                                      playlist_id=playlist_id)
                    new_context = context.clone(new_params=new_params)
                    _process_add_video(provider, new_context, keymap_action)
            break
        if result == 'playlist.next':
            continue
        if result != -1:
            new_params = dict(context.get_params(), playlist_id=result)
            new_context = context.clone(new_params=new_params)
            _process_add_video(provider, new_context, keymap_action)
            break
        break


def _process_rename_playlist(provider, context):
    playlist_id = context.get_param('playlist_id', '')
    if not playlist_id:
        raise KodionException('playlist/rename: missing playlist_id')

    current_playlist_name = context.get_param('playlist_name', '')
    result, text = context.get_ui().on_keyboard_input(context.localize('rename'),
                                                      default=current_playlist_name)
    if result and text:
        json_data = provider.get_client(context).rename_playlist(playlist_id=playlist_id, new_title=text)
        if not json_data:
            return

        context.get_ui().refresh_container()


def _watch_later_playlist_id_change(context, method):
    playlist_id = context.get_param('playlist_id', '')
    if not playlist_id:
        raise KodionException('watchlater_list/%s: missing playlist_id' % method)
    playlist_name = context.get_param('playlist_name', '')
    if not playlist_name:
        raise KodionException('watchlater_list/%s: missing playlist_name' % method)

    if method == 'set':
        if context.get_ui().on_yes_no_input(context.get_name(), context.localize('watch_later.list.set.confirm') % playlist_name):
            context.get_access_manager().set_watch_later_id(playlist_id)
        else:
            return
    elif method == 'remove':
        if context.get_ui().on_yes_no_input(context.get_name(), context.localize('watch_later.list.remove.confirm') % playlist_name):
            context.get_access_manager().set_watch_later_id('WL')
        else:
            return
    else:
        return
    context.get_ui().refresh_container()


def _history_playlist_id_change(context, method):
    playlist_id = context.get_param('playlist_id', '')
    if not playlist_id:
        raise KodionException('history_list/%s: missing playlist_id' % method)
    playlist_name = context.get_param('playlist_name', '')
    if not playlist_name:
        raise KodionException('history_list/%s: missing playlist_name' % method)

    if method == 'set':
        if context.get_ui().on_yes_no_input(context.get_name(), context.localize('history.list.set.confirm') % playlist_name):
            context.get_access_manager().set_watch_history_id(playlist_id)
        else:
            return
    elif method == 'remove':
        if context.get_ui().on_yes_no_input(context.get_name(), context.localize('history.list.remove.confirm') % playlist_name):
            context.get_access_manager().set_watch_history_id('HL')
        else:
            return
    else:
        return
    context.get_ui().refresh_container()


def process(method, category, provider, context):
    if method == 'add' and category == 'video':
        return _process_add_video(provider, context)
    if method == 'remove' and category == 'video':
        return _process_remove_video(provider, context)
    if method == 'remove' and category == 'playlist':
        return _process_remove_playlist(provider, context)
    if method == 'select' and category == 'playlist':
        return _process_select_playlist(provider, context)
    if method == 'rename' and category == 'playlist':
        return _process_rename_playlist(provider, context)
    if method in {'set', 'remove'} and category == 'watch_later':
        return _watch_later_playlist_id_change(context, method)
    if method in {'set', 'remove'} and category == 'history':
        return _history_playlist_id_change(context, method)
    raise KodionException("Unknown category '%s' or method '%s'" % (category, method))
