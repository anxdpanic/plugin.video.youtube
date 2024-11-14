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
from ...compatibility import urlsplit, xbmcplugin
from ...constants import (
    BUSY_FLAG,
    CONTAINER_FOCUS,
    CONTAINER_ID,
    CONTAINER_POSITION,
    CONTENT_TYPE,
    PATHS,
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
    CommandItem,
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

    def run(self, provider, context, focused=None):
        handle = context.get_handle()
        ui = context.get_ui()

        route = ui.pop_property(REROUTE_PATH)
        post_run_action = None
        succeeded = False
        for was_busy in (ui.pop_property(BUSY_FLAG),):
            if was_busy:
                if ui.busy_dialog_active():
                    ui.set_property(BUSY_FLAG)
                if route:
                    break
            else:
                break

            uri = context.get_uri()
            playlist_player = context.get_playlist_player()
            position, remaining = playlist_player.get_position()
            playing = (playlist_player.is_playing()
                       and context.is_plugin_path(uri, PATHS.PLAY))

            if playing:
                items = playlist_player.get_items()
                playlist_player.clear()
                context.log_warning('Multiple busy dialogs active'
                                    ' - Playlist cleared to avoid Kodi crash')

            xbmcplugin.endOfDirectory(
                handle,
                succeeded=False,
                updateListing=True,
                cacheToDisc=False,
            )

            if not playing:
                context.log_warning('Multiple busy dialogs active'
                                    ' - Plugin call ended to avoid Kodi crash')
                result, post_run_action = self.uri_action(context, uri)
                succeeded = result
                continue

            if position:
                path = items[position - 1]['file']
                old_path = ui.pop_property(PLAYLIST_PATH)
                old_position = ui.pop_property(PLAYLIST_POSITION)
                if (old_position and position == int(old_position)
                        and old_path and path == old_path):
                    if remaining:
                        position += 1
                    else:
                        continue

            max_wait_time = 30
            while ui.busy_dialog_active():
                max_wait_time -= 1
                if max_wait_time < 0:
                    context.log_error('Multiple busy dialogs active'
                                      ' - Extended busy period')
                    continue
                context.sleep(1)

            context.log_warning('Multiple busy dialogs active'
                                ' - Reloading playlist')

            num_items = playlist_player.add_items(items)
            if position:
                max_wait_time = min(position, num_items)
            else:
                position = 1
                max_wait_time = num_items

            while ui.busy_dialog_active() or playlist_player.size() < position:
                max_wait_time -= 1
                if max_wait_time < 0:
                    context.log_error('Multiple busy dialogs active'
                                      ' - Unable to restart playback')
                    result, post_run_action = self.uri_action(
                        context,
                        'command://Playlist.PlayOffset({type},{position})'
                        .format(type='video',
                                position=(position - 1)),
                    )
                    succeeded = False
                    continue
                context.sleep(1)
            else:
                playlist_player.play_playlist_item(position)
        else:
            if post_run_action:
                self.post_run(context, ui, post_run_action)
            return succeeded

        if ui.get_property(PLUGIN_SLEEPING):
            context.wakeup(PLUGIN_WAKEUP)

        if ui.pop_property(REFRESH_CONTAINER):
            focused = False
        elif focused:
            focused = ui.get_property(VIDEO_ID)

        if ui.pop_property(RELOAD_ACCESS_MANAGER):
            context.reload_access_manager()

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
                msg = ('XbmcRunner.run - Error'
                       '\n\tException: {exc!r}'
                       '\n\tStack trace (most recent call last):\n{stack}'
                       .format(exc=exc,
                               stack=''.join(format_stack())))
                context.log_error(msg)
                ui.on_ok('Error in ContentProvider', exc.__str__())

        items = isinstance(result, (list, tuple))
        item_count = 0
        if items:
            if not result:
                result = [
                    CommandItem(
                        name=context.localize('page.back'),
                        command='Action(ParentDir)',
                        context=context,
                        image='DefaultFolderBack.png',
                        plot=context.localize('page.empty'),
                    )
                ]

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
            else:
                result = None

        if result and result.__class__.__name__ in self._PLAY_ITEM_MAP:
            uri = result.get_uri()

            if result.playable:
                item = self._PLAY_ITEM_MAP[result.__class__.__name__](
                    context,
                    result,
                    show_fanart=context.get_settings().fanart_selection(),
                )
                uri = result.get_uri()
                result = xbmcplugin.addDirectoryItem(handle,
                                                     url=uri,
                                                     listitem=item)
                if route:
                    playlist_player = context.get_playlist_player()
                    playlist_player.play_item(item=uri, listitem=item)
                else:
                    xbmcplugin.setResolvedUrl(handle,
                                              succeeded=result,
                                              listitem=item)

            else:
                result, post_run_action = self.uri_action(context, uri)

        if item_count:
            context.apply_content()
            succeeded = xbmcplugin.addDirectoryItems(
                handle, items, item_count
            )
            cache_to_disc = options.get(provider.RESULT_CACHE_TO_DISC, True)
            update_listing = options.get(provider.RESULT_UPDATE_LISTING, False)
        else:
            succeeded = bool(result)
            if not succeeded:
                ui.clear_property(CONTENT_TYPE)

                if not options or options.get(provider.RESULT_FALLBACK, True):
                    result, post_run_action = self.uri_action(
                        context,
                        context.get_parent_uri(params={
                            'window_fallback': True,
                            'window_replace': True,
                            'window_return': False,
                        }),
                    )
            cache_to_disc = False
            update_listing = True

        xbmcplugin.endOfDirectory(
            handle,
            succeeded=succeeded,
            updateListing=update_listing,
            cacheToDisc=cache_to_disc,
        )
        container = ui.pop_property(CONTAINER_ID)
        position = ui.pop_property(CONTAINER_POSITION)
        if container and position:
            context.send_notification(CONTAINER_FOCUS, [container, position])

        if post_run_action:
            self.post_run(context, ui, post_run_action)
        return succeeded

    @staticmethod
    def post_run(context, ui, action, timeout=30):
        while ui.busy_dialog_active():
            timeout -= 1
            if timeout < 0:
                context.log_error('Multiple busy dialogs active'
                                  ' - Post run action unable to execute')
                break
            context.sleep(1)
        else:
            context.execute(action)

    @staticmethod
    def uri_action(context, uri):
        if uri.startswith('script://'):
            uri = uri[len('script://'):]
            context.log_debug('Running script: |{0}|'.format(uri))
            action = 'RunScript({0})'.format(uri)
            result = True

        elif uri.startswith('command://'):
            uri = uri[len('command://'):]
            context.log_debug('Running command: |{0}|'.format(uri))
            action = uri
            result = True

        elif context.is_plugin_path(uri, PATHS.PLAY):
            context.log_debug('Redirecting for playback: |{0}|'.format(uri))
            action = 'PlayMedia({0}, playlist_time_hint=1)'.format(uri)
            result = False

        elif context.is_plugin_path(uri):
            context.log_debug('Redirecting to: |{0}|'.format(uri))
            uri = urlsplit(uri)
            action = context.create_uri(
                (PATHS.ROUTE, uri.path.rstrip('/') or PATHS.HOME),
                uri.query,
                run=True,
            )
            result = False

        else:
            action = None
            result = False

        return result, action
