# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from ...kodion.utils.function_cache import FunctionCache

from ... import kodion
from ...youtube.helper import v3


def _process_add_video(provider, context, keymap_action=False):
    listitem_path = context.get_ui().get_info_label('Container.ListItem(0).FileNameAndPath')

    client = provider.get_client(context)
    watch_later_id = context.get_access_manager().get_watch_later_id()

    playlist_id = context.get_param('playlist_id', '')
    if not playlist_id:
        raise kodion.KodionException('Playlist/Add: missing playlist_id')

    if playlist_id.lower() == 'watch_later':
        playlist_id = watch_later_id

    video_id = context.get_param('video_id', '')
    if not video_id:
        if context.is_plugin_path(listitem_path, 'play'):
            video_id = kodion.utils.find_video_id(listitem_path)
            keymap_action = True
        if not video_id:
            raise kodion.KodionException('Playlist/Add: missing video_id')

    if playlist_id != 'HL':
        json_data = client.add_video_to_playlist(playlist_id=playlist_id, video_id=video_id)
        if not v3.handle_error(provider, context, json_data):
            return False

        if playlist_id == watch_later_id:
            notify_message = context.localize(provider.LOCAL_MAP['youtube.added.to.watch.later'])
        else:
            notify_message = context.localize(provider.LOCAL_MAP['youtube.added.to.playlist'])

        context.get_ui().show_notification(
            message=notify_message,
            time_milliseconds=2500,
            audible=False
        )

        if keymap_action:
            context.get_ui().set_focus_next_item()

        return True
    else:
        context.log_debug('Cannot add to playlist id |%s|' % playlist_id)

    return False


def _process_remove_video(provider, context):
    listitem_playlist_id = context.get_ui().get_info_label('Container.ListItem(0).Property(playlist_id)')
    listitem_playlist_item_id = context.get_ui().get_info_label('Container.ListItem(0).Property(playlist_item_id)')
    listitem_title = context.get_ui().get_info_label('Container.ListItem(0).Title')
    keymap_action = False

    playlist_id = context.get_param('playlist_id', '')
    video_id = context.get_param('video_id', '')
    video_name = context.get_param('video_name', '')

    if not playlist_id and not video_id:  # keymap support
        if listitem_playlist_id and listitem_playlist_id.startswith('PL') \
                and listitem_playlist_item_id and listitem_playlist_item_id.startswith('UE'):
            playlist_id = listitem_playlist_id
            video_id = listitem_playlist_item_id
            keymap_action = True

    if not playlist_id:
        raise kodion.KodionException('Playlist/Remove: missing playlist_id')

    if not video_id:
        raise kodion.KodionException('Playlist/Remove: missing video_id')

    if not video_name:
        if listitem_title:
            video_name = listitem_title
        else:
            raise kodion.KodionException('Playlist/Remove: missing video_name')

    if playlist_id != 'HL' and playlist_id.strip().lower() != 'wl':
        if context.get_ui().on_remove_content(video_name):
            json_data = provider.get_client(context).remove_video_from_playlist(playlist_id=playlist_id,
                                                                                playlist_item_id=video_id)
            if not v3.handle_error(provider, context, json_data):
                return False

            context.get_ui().refresh_container()

            context.get_ui().show_notification(
                message=context.localize(provider.LOCAL_MAP['youtube.removed.from.playlist']),
                time_milliseconds=2500,
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
        raise kodion.KodionException('Playlist/Remove: missing playlist_id')

    playlist_name = context.get_param('playlist_name', '')
    if not playlist_name:
        raise kodion.KodionException('Playlist/Remove: missing playlist_name')

    if context.get_ui().on_delete_content(playlist_name):
        json_data = provider.get_client(context).remove_playlist(playlist_id=playlist_id)
        if not v3.handle_error(provider, context, json_data):
            return False

        context.get_ui().refresh_container()
    return True


def _process_select_playlist(provider, context):
    listitem_path = context.get_ui().get_info_label('Container.ListItem(0).FileNameAndPath')  # do this asap, relies on listitems focus
    keymap_action = False
    ui = context.get_ui()
    page_token = ''
    current_page = 0

    video_id = context.get_param('video_id', '')
    if not video_id:
        if context.is_plugin_path(listitem_path, 'play'):
            video_id = kodion.utils.find_video_id(listitem_path)
            if video_id:
                context.set_param('video_id', video_id)
                keymap_action = True
        if not video_id:
            raise kodion.KodionException('Playlist/Select: missing video_id')

    while True:
        current_page += 1
        if not page_token:
            json_data = context.get_function_cache().get((FunctionCache.ONE_MINUTE // 3),
                                                         provider.get_client(context).get_playlists_of_channel,
                                                         channel_id='mine')
        else:
            json_data = context.get_function_cache().get((FunctionCache.ONE_MINUTE // 3),
                                                         provider.get_client(context).get_playlists_of_channel,
                                                         channel_id='mine', page_token=page_token)

        playlists = json_data.get('items', [])
        page_token = json_data.get('nextPageToken', False)

        items = []
        if current_page == 1:
            # create playlist
            items.append((ui.bold(context.localize(provider.LOCAL_MAP['youtube.playlist.create'])), '',
                          'playlist.create', context.create_resource_path('media', 'playlist.png')))

            # add the 'Watch Later' playlist
            resource_manager = provider.get_resource_manager(context)
            my_playlists = resource_manager.get_related_playlists(channel_id='mine')
            if 'watchLater' in my_playlists:
                watch_later_playlist_id = context.get_access_manager().get_watch_later_id()
                if watch_later_playlist_id:
                    items.append((ui.bold(context.localize(provider.LOCAL_MAP['youtube.watch_later'])), '',
                                  watch_later_playlist_id, context.create_resource_path('media', 'watch_later.png')))

        for playlist in playlists:
            snippet = playlist.get('snippet', {})
            title = snippet.get('title', '')
            description = snippet.get('description', '')
            thumbnail = snippet.get('thumbnails', {}).get('default', {}).get('url', context.create_resource_path('media', 'playlist.png'))
            playlist_id = playlist.get('id', '')
            if title and playlist_id:
                items.append((title, description, playlist_id, thumbnail))

        if page_token:
            items.append((ui.bold(context.localize(provider.LOCAL_MAP['youtube.next_page'])).replace('%d', str(current_page + 1)), '',
                          'playlist.next', 'DefaultFolder.png'))

        result = context.get_ui().on_select(context.localize(provider.LOCAL_MAP['youtube.playlist.select']), items)
        if result == 'playlist.create':
            result, text = context.get_ui().on_keyboard_input(
                context.localize(provider.LOCAL_MAP['youtube.playlist.create']))
            if result and text:
                json_data = provider.get_client(context).create_playlist(title=text)
                if not v3.handle_error(provider, context, json_data):
                    break

                playlist_id = json_data.get('id', '')
                if playlist_id:
                    new_params = {}
                    new_params.update(context.get_params())
                    new_params['playlist_id'] = playlist_id
                    new_context = context.clone(new_params=new_params)
                    _process_add_video(provider, new_context, keymap_action)
            break
        elif result == 'playlist.next':
            continue
        elif result != -1:
            new_params = {}
            new_params.update(context.get_params())
            new_params['playlist_id'] = result
            new_context = context.clone(new_params=new_params)
            _process_add_video(provider, new_context, keymap_action)
            break
        else:
            break


def _process_rename_playlist(provider, context):
    playlist_id = context.get_param('playlist_id', '')
    if not playlist_id:
        raise kodion.KodionException('playlist/rename: missing playlist_id')

    current_playlist_name = context.get_param('playlist_name', '')
    result, text = context.get_ui().on_keyboard_input(context.localize(provider.LOCAL_MAP['youtube.rename']),
                                                      default=current_playlist_name)
    if result and text:
        json_data = provider.get_client(context).rename_playlist(playlist_id=playlist_id, new_title=text)
        if not v3.handle_error(provider, context, json_data):
            return

        context.get_ui().refresh_container()


def _watchlater_playlist_id_change(context, method):
    playlist_id = context.get_param('playlist_id', '')
    if not playlist_id:
        raise kodion.KodionException('watchlater_list/%s: missing playlist_id' % method)
    playlist_name = context.get_param('playlist_name', '')
    if not playlist_name:
        raise kodion.KodionException('watchlater_list/%s: missing playlist_name' % method)

    if method == 'set':
        if context.get_ui().on_yes_no_input(context.get_name(), context.localize(30570) % playlist_name):
            context.get_access_manager().set_watch_later_id(playlist_id)
        else:
            return
    elif method == 'remove':
        if context.get_ui().on_yes_no_input(context.get_name(), context.localize(30569) % playlist_name):
            context.get_access_manager().set_watch_later_id(' WL')
        else:
            return
    else:
        return
    context.get_ui().refresh_container()


def _history_playlist_id_change(context, method):
    playlist_id = context.get_param('playlist_id', '')
    if not playlist_id:
        raise kodion.KodionException('history_list/%s: missing playlist_id' % method)
    playlist_name = context.get_param('playlist_name', '')
    if not playlist_name:
        raise kodion.KodionException('history_list/%s: missing playlist_name' % method)

    if method == 'set':
        if context.get_ui().on_yes_no_input(context.get_name(), context.localize(30574) % playlist_name):
            context.get_access_manager().set_watch_history_id(playlist_id)
        else:
            return
    elif method == 'remove':
        if context.get_ui().on_yes_no_input(context.get_name(), context.localize(30573) % playlist_name):
            context.get_access_manager().set_watch_history_id('HL')
        else:
            return
    else:
        return
    context.get_ui().refresh_container()


def process(method, category, provider, context):
    if method == 'add' and category == 'video':
        return _process_add_video(provider, context)
    elif method == 'remove' and category == 'video':
        return _process_remove_video(provider, context)
    elif method == 'remove' and category == 'playlist':
        return _process_remove_playlist(provider, context)
    elif method == 'select' and category == 'playlist':
        return _process_select_playlist(provider, context)
    elif method == 'rename' and category == 'playlist':
        return _process_rename_playlist(provider, context)
    elif (method == 'set' or method == 'remove') and category == 'watchlater':
        return _watchlater_playlist_id_change(context, method)
    elif (method == 'set' or method == 'remove') and category == 'history':
        return _history_playlist_id_change(context, method)
    else:
        raise kodion.KodionException("Unknown category '%s' or method '%s'" % (category, method))
