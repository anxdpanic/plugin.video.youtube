# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from traceback import format_stack

from ..abstract_plugin import AbstractPlugin
from ...compatibility import xbmcplugin
from ...constants import (
    BUSY_FLAG,
    CHECK_SETTINGS,
    CONTAINER_FOCUS,
    CONTAINER_ID,
    CONTAINER_POSITION,
    PLAYLIST_PATH,
    PLAYLIST_POSITION,
    PLUGIN_SLEEPING,
    PLUGIN_WAKEUP,
    REFRESH_CONTAINER,
    RELOAD_ACCESS_MANAGER,
    REROUTE_PATH,
    VIDEO_ID,
)
from ...exceptions import KodionException
from ...items import (
    directory_listitem,
    image_listitem,
    media_listitem,
    playback_item,
    uri_listitem,
)


class XbmcPlugin(AbstractPlugin):
    _LIST_ITEM_MAP = {
        'AudioItem': media_listitem,
        'CommandItem': directory_listitem,
        'DirectoryItem': directory_listitem,
        'ImageItem': image_listitem,
        'SearchItem': directory_listitem,
        'SearchHistoryItem': directory_listitem,
        'NewSearchItem': directory_listitem,
        'NextPageItem': directory_listitem,
        'VideoItem': media_listitem,
        'WatchLaterItem': directory_listitem,
    }

    _PLAY_ITEM_MAP = {
        'AudioItem': playback_item,
        'UriItem': uri_listitem,
        'VideoItem': playback_item,
    }

    def __init__(self):
        super(XbmcPlugin, self).__init__()
        self.handle = None

    def run(self, provider, context, focused=None):
        self.handle = context.get_handle()
        ui = context.get_ui()

        route = ui.pop_property(REROUTE_PATH)
        for was_busy in (ui.pop_property(BUSY_FLAG),):
            if was_busy:
                if ui.busy_dialog_active():
                    ui.set_property(BUSY_FLAG)
                if route:
                    break
            else:
                break

            xbmcplugin.endOfDirectory(
                self.handle,
                succeeded=False,
            )

            playlist_player = context.get_playlist_player()

            items = playlist_player.get_items()
            if not items and not playlist_player.is_playing():
                context.log_warning('Multiple busy dialogs active - '
                                    'plugin call stopped to avoid Kodi crash')
                break

            playlist_player.clear()
            context.log_warning('Multiple busy dialogs active - '
                                'playlist cleared to avoid Kodi crash')

            position, remaining = playlist_player.get_position()
            if position:
                path = items[position - 1]['file']
                old_path = ui.pop_property(PLAYLIST_PATH)
                old_position = ui.pop_property(PLAYLIST_POSITION)
                if (old_position and position == int(old_position)
                        and old_path and path == old_path):
                    if remaining:
                        position += 1
                    else:
                        return False

            max_wait_time = 30
            while ui.busy_dialog_active():
                max_wait_time -= 1
                if max_wait_time < 0:
                    context.log_error('Multiple busy dialogs active - '
                                      'extended busy period')
                    break
                context.sleep(1)

            context.log_warning('Multiple busy dialogs active - '
                                'reloading playlist')

            num_items = playlist_player.add_items(items)
            if playlist_player.is_playing():
                return False

            if position:
                max_wait_time = min(position, num_items)
            else:
                position = 1
                max_wait_time = num_items

            while ui.busy_dialog_active() or playlist_player.size() < position:
                max_wait_time -= 1
                if max_wait_time < 0:
                    context.log_error('Multiple busy dialogs active - '
                                      'unable to restart playback')
                    break
                context.sleep(1)
            else:
                playlist_player.play_playlist_item(position)
        else:
            return False

        if ui.get_property(PLUGIN_SLEEPING):
            context.wakeup(PLUGIN_WAKEUP)

        if ui.pop_property(REFRESH_CONTAINER):
            focused = False
        elif focused:
            focused = ui.get_property(VIDEO_ID)

        if ui.pop_property(RELOAD_ACCESS_MANAGER):
            context.reload_access_manager()

        if ui.pop_property(CHECK_SETTINGS):
            provider.reset_client()
            settings = context.get_settings(refresh=True)
        else:
            settings = context.get_settings()

        if settings.setup_wizard_enabled():
            provider.run_wizard(context)

        try:
            if route:
                function_cache = context.get_function_cache()
                result, options = function_cache.run(
                    provider.navigate,
                    _oneshot=True,
                    _scope=function_cache.SCOPE_NONE,
                    context=context.clone(route),
                )
            else:
                result, options = provider.navigate(context)
        except KodionException as exc:
            result = options = None
            if provider.handle_exception(context, exc):
                context.log_error('XbmcRunner.run - {exc}:\n{details}'.format(
                    exc=exc, details=''.join(format_stack())
                ))
                ui.on_ok('Error in ContentProvider', exc.__str__())

        items = None
        item_count = 0

        if result and isinstance(result, (list, tuple)):
            show_fanart = settings.fanart_selection()
            items = [
                self._LIST_ITEM_MAP[item.__class__.__name__](
                    context,
                    item,
                    show_fanart=show_fanart,
                    focused=focused,
                )
                for item in result
                if item.__class__.__name__ in self._LIST_ITEM_MAP
            ]
            item_count = len(items)

            if options.get(provider.RESULT_FORCE_RESOLVE):
                result = result[0]

        if result and result.__class__.__name__ in self._PLAY_ITEM_MAP:
            uri = result.get_uri()

            if result.playable:
                item = self._PLAY_ITEM_MAP[result.__class__.__name__](
                    context,
                    result,
                    show_fanart=context.get_settings().fanart_selection(),
                )
                result = xbmcplugin.addDirectoryItem(self.handle,
                                                     url=uri,
                                                     listitem=item)
                if route:
                    playlist_player = context.get_playlist_player()
                    playlist_player.play_item(item=uri, listitem=item)
                else:
                    xbmcplugin.setResolvedUrl(self.handle,
                                              succeeded=result,
                                              listitem=item)

            elif uri.startswith('script://'):
                uri = uri[len('script://'):]
                context.log_debug('Running script: |{0}|'.format(uri))
                context.execute('RunScript({0})'.format(uri))
                result = False

            elif uri.startswith('command://'):
                uri = uri[len('command://'):]
                context.log_debug('Running command: |{0}|'.format(uri))
                context.execute(uri)
                result = True

            elif context.is_plugin_path(uri):
                context.log_debug('Redirecting to: |{0}|'.format(uri))
                context.execute('RunPlugin({0})'.format(uri))
                result = False

            else:
                result = False

        if item_count:
            context.apply_content()
            succeeded = xbmcplugin.addDirectoryItems(
                self.handle, items, item_count
            )
            cache_to_disc = options.get(provider.RESULT_CACHE_TO_DISC, True)
            update_listing = options.get(provider.RESULT_UPDATE_LISTING, False)
        else:
            succeeded = bool(result)
            cache_to_disc = False
            update_listing = True

        xbmcplugin.endOfDirectory(
            self.handle,
            succeeded=succeeded,
            updateListing=update_listing,
            cacheToDisc=cache_to_disc,
        )
        container = ui.pop_property(CONTAINER_ID)
        position = ui.pop_property(CONTAINER_POSITION)
        if container and position:
            context.send_notification(CONTAINER_FOCUS, [container, position])
        return succeeded
