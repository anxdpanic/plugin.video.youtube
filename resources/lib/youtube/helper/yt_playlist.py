from resources.lib.kodion.utils.function_cache import FunctionCache

__author__ = 'bromix'

from resources.lib import kodion
from resources.lib.youtube.helper import v3


def _process_add_video(provider, context, re_match):
    playlist_id = context.get_param('playlist_id', '')
    if not playlist_id:
        raise kodion.KodionException('Playlist/Remove: missing playlist_id')
    video_id = context.get_param('video_id', '')
    if not video_id:
        raise kodion.KodionException('Playlist/Remove: missing video_id')

    json_data = provider.get_client(context).add_video_to_playlist(playlist_id=playlist_id, video_id=video_id)
    if not v3.handle_error(provider, context, json_data):
        return False

    return True


def _process_remove_video(provider, context, re_match):
    playlist_id = context.get_param('playlist_id', '')
    if not playlist_id:
        raise kodion.KodionException('Playlist/Remove: missing playlist_id')

    video_id = context.get_param('video_id', '')
    if not video_id:
        raise kodion.KodionException('Playlist/Remove: missing video_id')

    video_name = context.get_param('video_name', '')
    if not video_name:
        raise kodion.KodionException('Playlist/Remove: missing video_name')

    if context.get_ui().on_remove_content(video_name):
        json_data = provider.get_client(context).remove_video_from_playlist(playlist_id=playlist_id,
                                                                            playlist_item_id=video_id)
        if not v3.handle_error(provider, context, json_data):
            return False

        context.get_ui().refresh_container()
        pass
    return True


def _process_remove_playlist(provider, context, re_match):
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
        pass
    return True


def _process_select_playlist(provider, context, re_match):
    json_data = context.get_function_cache().get(FunctionCache.ONE_MINUTE / 3,
                                                 provider.get_client(context).get_playlists_of_channel,
                                                 channel_id='mine')
    playlists = json_data.get('items', [])

    items = []
    # create playlist
    items.append(('[B]' + context.localize(provider.LOCAL_MAP['youtube.playlist.create']) + '[/B]', 'playlist.create'))

    # add the 'Watch Later' playlist
    resource_manager = provider.get_resource_manager(context)
    my_playlists = resource_manager.get_related_playlists(channel_id='mine')
    if 'watchLater' in my_playlists:
        watch_later_playlist_id = my_playlists.get('watchLater', '')
        items.append(
            ('[B]' + context.localize(provider.LOCAL_MAP['youtube.watch_later']) + '[/B]', watch_later_playlist_id))
        pass

    for playlist in playlists:
        snippet = playlist.get('snippet', {})
        title = snippet.get('title', '')
        playlist_id = playlist.get('id', '')
        if title and playlist_id:
            items.append((title, playlist_id))
            pass
        pass

    result = context.get_ui().on_select(context.localize(provider.LOCAL_MAP['youtube.playlist.select']), items)
    if result == 'playlist.create':
        result, text = context.get_ui().on_keyboard_input(
            context.localize(provider.LOCAL_MAP['youtube.playlist.create']))
        if result and text:
            json_data = provider.get_client(context).create_playlist(title=text)
            if not v3.handle_error(provider, context, json_data):
                return

            playlist_id = json_data.get('id', '')
            if playlist:
                new_params = {}
                new_params.update(context.get_params())
                new_params['playlist_id'] = playlist_id
                new_context = context.clone(new_params=new_params)
                _process_add_video(provider, new_context, re_match)
                pass
            pass
        pass
    elif result != -1:
        new_params = {}
        new_params.update(context.get_params())
        new_params['playlist_id'] = result
        new_context = context.clone(new_params=new_params)
        _process_add_video(provider, new_context, re_match)
        pass
    pass


def _process_rename_playlist(provider, context, re_match):
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
        pass
    pass


def process(method, category, provider, context, re_match):
    if method == 'add' and category == 'video':
        return _process_add_video(provider, context, re_match)
    elif method == 'remove' and category == 'video':
        return _process_remove_video(provider, context, re_match)
    elif method == 'remove' and category == 'playlist':
        return _process_remove_playlist(provider, context, re_match)
    elif method == 'select' and category == 'playlist':
        return _process_select_playlist(provider, context, re_match)
    elif method == 'rename' and category == 'playlist':
        return _process_rename_playlist(provider, context, re_match)
    else:
        raise kodion.KodionException("Unknown category '%s' or method '%s'" % (category, method))

    return True
