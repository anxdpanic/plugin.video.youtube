# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .utils import get_thumbnail
from ...kodion import KodionException
from ...kodion.constants import CHANNEL_ID, PATHS, PLAYLISTITEM_ID, PLAYLIST_ID
from ...kodion.utils import find_video_id


def _process_add_video(provider, context, keymap_action=False):
    listitem_path = context.get_listitem_info('FileNameAndPath')

    client = provider.get_client(context)
    logged_in = provider.is_logged_in()
    if not logged_in:
        raise KodionException('Playlist/Add: not logged in')

    playlist_id = context.get_param('playlist_id', '')
    if not playlist_id:
        raise KodionException('Playlist/Add: missing playlist_id')

    if playlist_id.lower() == 'watch_later':
        playlist_id = context.get_access_manager().get_watch_later_id()
        notify_message = context.localize('watch_later.added_to')
    else:
        notify_message = context.localize('playlist.added_to')

    video_id = context.get_param('video_id', '')
    if not video_id:
        if context.is_plugin_path(listitem_path, PATHS.PLAY):
            video_id = find_video_id(listitem_path)
            keymap_action = True
        if not video_id:
            raise KodionException('Playlist/Add: missing video_id')

    json_data = client.add_video_to_playlist(playlist_id=playlist_id,
                                             video_id=video_id)
    if not json_data:
        context.log_debug('Playlist/Add: failed for playlist |{playlist_id}|'
                          .format(playlist_id=playlist_id))
        return False

    context.get_ui().show_notification(
        message=notify_message,
        time_ms=2500,
        audible=False,
    )

    if keymap_action:
        context.get_ui().set_focus_next_item()

    data_cache = context.get_data_cache()
    playlist_cache = data_cache.get_item_like(','.join((playlist_id, '%')))
    if playlist_cache:
        cache_key, _, cached_last_page = playlist_cache[0]
        if cached_last_page:
            data_cache.update_item(cache_key, None)

    return True


def _process_remove_video(provider,
                          context,
                          playlist_id=None,
                          video_id=None,
                          video_name=None,
                          confirmed=None):
    container_uri = context.get_infolabel('Container.FolderPath')
    listitem_playlist_id = context.get_listitem_property(PLAYLIST_ID)
    listitem_video_id = context.get_listitem_property(PLAYLISTITEM_ID)
    listitem_video_name = context.get_listitem_info('Title')
    keymap_action = False

    params = context.get_params()
    if playlist_id is None:
        playlist_id = params.pop('playlist_id', None)
    if video_id is None:
        video_id = params.pop('video_id', None)
    if video_name is None:
        video_name = params.pop('item_name', None)
    if confirmed is None:
        confirmed = params.pop('confirmed', False)

    video_params = (
        {playlist_id, video_id} if confirmed else
        {playlist_id, video_id, video_name}
    )
    params_required = 2 if confirmed else 3
    if None in video_params or len(video_params) != params_required:
        if len(video_params) != 1:
            if confirmed:
                return False
            raise KodionException('Playlist/Remove: missing parameters |{0}|'
                                  .format(video_params))

        video_params = (
            {listitem_playlist_id, listitem_video_id} if confirmed else
            {listitem_playlist_id, listitem_video_id, listitem_video_name}
        )
        if '' in video_params or len(video_params) != params_required:
            if confirmed:
                return False
            raise KodionException('Playlist/Remove: missing listitem info |{0}|'
                                  .format(video_params))

        playlist_id = listitem_playlist_id
        video_id = listitem_video_id
        video_name = listitem_video_name
        keymap_action = True

    if playlist_id.strip().lower() in {'wl', 'hl'}:
        context.log_debug('Playlist/Remove: failed for playlist |{playlist_id}|'
                          .format(playlist_id=playlist_id))
        return False

    if confirmed or context.get_ui().on_remove_content(video_name):
        success = provider.get_client(context).remove_video_from_playlist(
            playlist_id=playlist_id,
            playlist_item_id=video_id,
        )
        if not success:
            return False

        context.get_ui().show_notification(
            message=context.localize('playlist.removed_from'),
            time_ms=2500,
            audible=False,
        )

        if not context.is_plugin_path(container_uri):
            return True

        if (keymap_action or video_id == listitem_video_id) and not confirmed:
            context.get_ui().set_focus_next_item()

        if playlist_id in container_uri:
            uri = container_uri
            path = None
            params = {'refresh': params.get('refresh', 0) + 1}
        else:
            path = params.pop('reload_path', False if confirmed else None)
            uri = None

        if uri or path is not False:
            provider.reroute(
                context,
                path=path,
                params=params,
                uri=uri,
            )
        return True
    return False


def _process_remove_playlist(provider, context):
    channel_id = context.get_listitem_property(CHANNEL_ID)

    params = context.get_params()
    ui = context.get_ui()

    playlist_id = params.get('playlist_id', '')
    if not playlist_id:
        raise KodionException('Playlist/Remove: missing playlist_id')

    playlist_name = params.get('item_name', '')
    if not playlist_name:
        raise KodionException('Playlist/Remove: missing playlist_name')

    if ui.on_delete_content(playlist_name):
        json_data = provider.get_client(context).remove_playlist(playlist_id)
        if not json_data:
            return False

        if channel_id:
            data_cache = context.get_data_cache()
            data_cache.del_item(channel_id)
            ui.refresh_container()
    return False


def _process_select_playlist(provider, context):
    # Get listitem path asap, relies on listitems focus
    listitem_path = context.get_listitem_info('FileNameAndPath')

    params = context.get_params()
    ui = context.get_ui()
    keymap_action = False
    page_token = ''
    current_page = 0

    video_id = params.get('video_id', '')
    if not video_id:
        if context.is_plugin_path(listitem_path, PATHS.PLAY):
            video_id = find_video_id(listitem_path)
            if video_id:
                context.set_param('video_id', video_id)
                keymap_action = True
        if not video_id:
            raise KodionException('Playlist/Select: missing video_id')

    function_cache = context.get_function_cache()
    client = provider.get_client(context)
    resource_manager = provider.get_resource_manager(context)

    # add the 'Watch Later' playlist
    if 'watchLater' in resource_manager.get_related_playlists('mine'):
        watch_later_id = context.get_access_manager().get_watch_later_id()
    else:
        watch_later_id = None

    thumb_size = context.get_settings().get_thumbnail_size()
    default_thumb = context.create_resource_path('media', 'playlist.png')

    while 1:
        current_page += 1
        json_data = function_cache.run(client.get_playlists_of_channel,
                                       function_cache.ONE_MINUTE // 3,
                                       _refresh=params.get('refresh'),
                                       channel_id='mine',
                                       page_token=page_token)
        if not json_data:
            break
        playlists = json_data.get('items', [])
        page_token = json_data.get('nextPageToken', '')

        items = []
        if current_page == 1:
            # create playlist
            items.append((
                ui.bold(context.localize('playlist.create')), '',
                'playlist.create',
                default_thumb,
            ))

            # add the 'Watch Later' playlist
            if watch_later_id:
                items.append((
                    ui.bold(context.localize('watch_later')), '',
                    watch_later_id,
                    context.create_resource_path('media', 'watch_later.png')
                ))

        for playlist in playlists:
            snippet = playlist.get('snippet', {})
            title = snippet.get('title', '')
            description = snippet.get('description', '')
            thumbnail = get_thumbnail(thumb_size, snippet.get('thumbnails'))
            playlist_id = playlist.get('id', '')
            if title and playlist_id:
                items.append((
                    title, description,
                    playlist_id,
                    thumbnail or default_thumb
                ))

        if page_token:
            next_page = current_page + 1
            items.append((
                ui.bold(context.localize('page.next') % next_page), '',
                'playlist.next',
                'DefaultFolder.png',
            ))

        playlist_id = None
        result = ui.on_select(context.localize('playlist.select'), items)
        if result == 'playlist.next':
            continue
        elif result == 'playlist.create':
            result, text = ui.on_keyboard_input(
                context.localize('playlist.create'))
            if result and text:
                json_data = client.create_playlist(title=text)
                if not json_data:
                    break
                playlist_id = json_data.get('id', '')
        elif result != -1:
            playlist_id = result

        if playlist_id:
            new_params = dict(context.get_params(), playlist_id=playlist_id)
            new_context = context.clone(new_params=new_params)
            _process_add_video(provider, new_context, keymap_action)
        break


def _process_rename_playlist(provider, context):
    params = context.get_params()
    ui = context.get_ui()

    playlist_id = params.get('playlist_id', '')
    if not playlist_id:
        raise KodionException('playlist/rename: missing playlist_id')

    result, text = ui.on_keyboard_input(
        context.localize('rename'), default=params.get('item_name', ''),
    )
    if not result or not text:
        return False

    json_data = provider.get_client(context).rename_playlist(
        playlist_id=playlist_id, new_title=text,
    )
    if not json_data:
        return False

    data_cache = context.get_data_cache()
    data_cache.del_item(playlist_id)
    ui.refresh_container()
    return False


def _playlist_id_change(context, playlist, command):
    playlist_id = context.get_param('playlist_id', '')
    if not playlist_id:
        raise KodionException('{type}/{command}: missing playlist_id'
                              .format(type=playlist, command=command))
    playlist_name = context.get_param('item_name', '')
    if not playlist_name:
        raise KodionException('{type}/{command}: missing playlist_name'
                              .format(type=playlist, command=command))

    if context.get_ui().on_yes_no_input(
            context.get_name(),
            context.localize('{type}.list.{command}.check'.format(
                type=playlist, command=command
            )) % playlist_name
    ):
        if command == 'remove':
            playlist_id = None
        if playlist == 'watch_later':
            context.get_access_manager().set_watch_later_id(playlist_id)
        else:
            context.get_access_manager().set_watch_history_id(playlist_id)
        return True
    return False


def process(provider,
            context,
            re_match=None,
            command=None,
            category=None,
            **kwargs):
    if re_match:
        if command is None:
            command = re_match.group('command')
        if category is None:
            category = re_match.group('category')

    if command == 'add' and category == 'video':
        return _process_add_video(provider, context)

    if command == 'remove' and category == 'video':
        return _process_remove_video(provider, context, **kwargs)

    if command == 'remove' and category == 'playlist':
        return _process_remove_playlist(provider, context)

    if command == 'select' and category == 'playlist':
        return _process_select_playlist(provider, context)

    if command == 'rename' and category == 'playlist':
        return _process_rename_playlist(provider, context)

    if command in {'set', 'remove'} and category == 'watch_later':
        return _playlist_id_change(context, category, command)

    if command in {'set', 'remove'} and category == 'history':
        return _playlist_id_change(context, category, command)

    raise KodionException('Unknown playlist category |{0}| or command |{1}|'
                          .format(category, command))
