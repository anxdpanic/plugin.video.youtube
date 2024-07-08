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
from ...compatibility import parse_qsl, urlsplit, xbmcplugin
from ...constants import (
    BUSY_FLAG,
    CONTAINER_FOCUS,
    CONTAINER_ID,
    CONTAINER_POSITION,
    CONTENT_TYPE,
    PATHS,
    PLAY_FORCED,
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
                    command = playlist_player.play_playlist_item(position,
                                                                 defer=True)
                    result, post_run_action = self.uri_action(
                        context,
                        command,
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
        show_fanart = settings.fanart_selection()

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
            if not provider.handle_exception(context, exc):
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
                        command='Action(Back)',
                        context=context,
                        image='DefaultFolderBack.png',
                        plot=context.localize('page.empty'),
                    )
                ]

            force_resolve = provider.RESULT_FORCE_RESOLVE
            if not options.pop(force_resolve, False):
                force_resolve = False

            items = [
                self._LIST_ITEM_MAP[item.__class__.__name__](
                    context,
                    item,
                    show_fanart=show_fanart,
                    focused=focused,
                )
                for item in result
                if self.classify_list_item(item, options, force_resolve)
            ]
            item_count = len(items)

            if force_resolve:
                result = options.get(force_resolve)

        if result and result.__class__.__name__ in self._PLAY_ITEM_MAP:
            if options.get(provider.RESULT_FORCE_PLAY) or not result.playable:
                result, post_run_action = self.uri_action(
                    context,
                    result.get_uri()
                )
            else:
                item = self._PLAY_ITEM_MAP[result.__class__.__name__](
                    context,
                    result,
                    show_fanart=show_fanart,
                )
                xbmcplugin.setResolvedUrl(
                    handle, succeeded=True, listitem=item
                )

        if item_count:
            context.apply_content()
            succeeded = xbmcplugin.addDirectoryItems(
                handle, items, item_count
            )
            cache_to_disc = options.get(provider.RESULT_CACHE_TO_DISC, True)
            update_listing = options.get(provider.RESULT_UPDATE_LISTING, False)

            # set alternative view mode
            view_manager = ui.get_view_manager()
            if view_manager.is_override_view_enabled():
                view_mode = view_manager.get_view_mode()
                if view_mode is not None:
                    context.log_debug('Override view mode to "%d"' % view_mode)
                    context.execute('Container.SetViewMode(%d)' % view_mode)
        else:
            succeeded = bool(result)
            if not succeeded:
                ui.clear_property(CONTENT_TYPE)

                if not options or options.get(provider.RESULT_FALLBACK, True):
                    if (context.is_plugin_folder()
                            and context.is_plugin_path(
                                context.get_infolabel('Container.FolderPath')
                            )):
                        _, _post_run_action = self.uri_action(
                            context,
                            context.get_parent_uri(params={
                                'window_fallback': True,
                                'window_replace': True,
                                'window_return': False,
                            }),
                        )
                    else:
                        _, _post_run_action = self.uri_action(
                            context,
                            'command://Action(Back)',
                        )
                    if post_run_action and _post_run_action:
                        post_run_action = (post_run_action, _post_run_action)
                    else:
                        post_run_action = _post_run_action

            cache_to_disc = False
            update_listing = True

        if ui.pop_property(PLAY_FORCED):
            context.set_path(PATHS.PLAY)
            return self.run(provider, context, focused=focused)

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

        if isinstance(post_run_action, tuple):
            self.post_run(context, ui, *post_run_action)
        elif post_run_action:
            self.post_run(context, ui, post_run_action)
        return succeeded

    @staticmethod
    def post_run(context, ui, *actions, **kwargs):
        timeout = kwargs.get('timeout', 30)
        for action in actions:
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

        elif uri.startswith('PlayMedia('):
            context.log_debug('Redirecting for playback: |{0}|'.format(uri))
            action = uri
            result = True

        elif uri.startswith('RunPlugin('):
            context.log_debug('Running plugin: |{0}|'.format(uri))
            action = uri
            result = True

        elif context.is_plugin_path(uri, PATHS.PLAY):
            _uri = urlsplit(uri)
            params = dict(parse_qsl(_uri.query, keep_blank_values=True))
            if params.get('action') == 'list':
                context.log_debug('Redirecting to: |{0}|'.format(uri))
                action = context.create_uri(
                    (PATHS.ROUTE, _uri.path.rstrip('/')),
                    params,
                    run=True,
                )
                result = False
            else:
                context.log_debug('Redirecting for playback: |{0}|'.format(uri))
                action = context.create_uri(
                    (_uri.path.rstrip('/'),),
                    params,
                    play=True,
                )
                result = True

        elif context.is_plugin_path(uri):
            context.log_debug('Redirecting to: |{0}|'.format(uri))
            _uri = urlsplit(uri)
            action = context.create_uri(
                (PATHS.ROUTE, _uri.path.rstrip('/') or PATHS.HOME),
                _uri.query,
                parse_params=True,
                run=True,
            )
            result = False

        else:
            action = None
            result = False

        return result, action

    def classify_list_item(self, item, options, force_resolve):
        item_type = item.__class__.__name__
        listitem_type = self._LIST_ITEM_MAP.get(item_type)
        if force_resolve and item_type in self._PLAY_ITEM_MAP:
            options.setdefault(force_resolve, item)
        if listitem_type:
            if listitem_type == directory_listitem:
                return item.available
            return True
        return False
