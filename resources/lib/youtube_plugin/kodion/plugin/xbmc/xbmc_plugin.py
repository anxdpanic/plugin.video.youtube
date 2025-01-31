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
from ...compatibility import string_type, xbmc, xbmcgui, xbmcplugin
from ...constants import (
    BUSY_FLAG,
    CONTAINER_FOCUS,
    CONTAINER_ID,
    CONTAINER_POSITION,
    CONTENT_TYPE,
    FORCE_PLAY_PARAMS,
    PATHS,
    PLAYBACK_FAILED,
    PLAYLIST_PATH,
    PLAYLIST_POSITION,
    PLAY_FORCED,
    PLAY_FORCE_AUDIO,
    PLUGIN_SLEEPING,
    PLUGIN_WAKEUP,
    REFRESH_CONTAINER,
    RELOAD_ACCESS_MANAGER,
    REROUTE_PATH,
    VIDEO_ID,
    WINDOW_FALLBACK,
    WINDOW_REPLACE,
    WINDOW_RETURN,
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
from ...utils import parse_and_redact_uri


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

    def run(self, provider, context, forced=None):
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

        if not ui.pop_property(REFRESH_CONTAINER) and forced:
            focused = ui.get_property(VIDEO_ID)
        else:
            focused = False

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
            result = None
            options = {}
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
        else:
            succeeded = bool(result)
            if not succeeded:
                ui.clear_property(CONTENT_TYPE)
                ui.clear_property(BUSY_FLAG)
                for param in FORCE_PLAY_PARAMS:
                    ui.clear_property(param)

                uri = context.get_uri()
                fallback = options.get(provider.RESULT_FALLBACK, True)
                if isinstance(fallback, string_type) and fallback != uri:
                    context.parse_uri(fallback, update=True)
                    return self.run(provider, context, forced=forced)
                if fallback:
                    _post_run_action = None

                    if context.is_plugin_folder():
                        if context.is_plugin_path(
                                uri, PATHS.PLAY
                        ):
                            context.send_notification(
                                PLAYBACK_FAILED,
                                {'video_id': context.get_param('video_id')},
                            )
                            # None of the following will actually prevent the
                            # playback attempt from occurring
                            item = xbmcgui.ListItem(path=uri, offscreen=True)
                            item.setContentLookup(False)
                            props = {
                                'isPlayable': 'false',
                                'ForceResolvePlugin': 'true',
                            }
                            item.setProperties(props)
                            xbmcplugin.setResolvedUrl(
                                handle,
                                succeeded=False,
                                listitem=item,
                            )
                        elif context.is_plugin_path(
                                context.get_infolabel('Container.FolderPath')
                        ):
                            _, _post_run_action = self.uri_action(
                                context,
                                context.get_parent_uri(params={
                                    WINDOW_FALLBACK: True,
                                    WINDOW_REPLACE: True,
                                    WINDOW_RETURN: False,
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

            cache_to_disc = options.get(provider.RESULT_CACHE_TO_DISC, False)
            update_listing = options.get(provider.RESULT_UPDATE_LISTING, True)

        if ui.pop_property(PLAY_FORCED):
            context.set_path(PATHS.PLAY)
            return self.run(provider, context, forced=forced)

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
            _uri = uri[len('script://'):]
            log_action = 'Running script'
            log_uri = _uri
            action = 'RunScript({0})'.format(_uri)
            result = True

        elif uri.startswith('command://'):
            _uri = uri[len('command://'):]
            log_action = 'Running command'
            log_uri = _uri
            action = _uri
            result = True

        elif uri.startswith('PlayMedia('):
            log_action = 'Redirecting for playback'
            log_uri = uri[len('PlayMedia('):-1].split(',')
            log_uri[0] = parse_and_redact_uri(
                log_uri[0],
                redact_only=True,
            )
            log_uri = ','.join(log_uri)
            action = uri
            result = True

        elif uri.startswith('RunPlugin('):
            log_action = 'Running plugin'
            log_uri = parse_and_redact_uri(
                uri[len('RunPlugin('):-1],
                redact_only=True,
            )
            action = uri
            result = True

        elif uri.startswith('ActivateWindow('):
            log_action = 'Activating window'
            log_uri = uri[len('ActivateWindow('):-1].split(',')
            if len(log_uri) >= 2:
                log_uri[1] = parse_and_redact_uri(
                    log_uri[1],
                    redact_only=True,
                )
            log_uri = ','.join(log_uri)
            action = uri
            result = False

        elif uri.startswith('ReplaceWindow('):
            log_action = 'Replacing window'
            log_uri = uri[len('ReplaceWindow('):-1].split(',')
            if len(log_uri) >= 2:
                log_uri[1] = parse_and_redact_uri(
                    log_uri[1],
                    redact_only=True,
                )
            log_uri = ','.join(log_uri)
            action = uri
            result = False

        elif context.is_plugin_path(uri, PATHS.PLAY):
            parts, params, log_uri, _ = parse_and_redact_uri(uri)
            if params.get('action') == 'list':
                log_action = 'Redirecting to'
                action = context.create_uri(
                    (PATHS.ROUTE, parts.path.rstrip('/')),
                    params,
                    run=True,
                )
                result = False
            else:
                log_action = 'Redirecting for playback'
                action = context.create_uri(
                    (parts.path.rstrip('/'),),
                    params,
                    play=(xbmc.PLAYLIST_MUSIC
                          if (context.get_ui().get_property(PLAY_FORCE_AUDIO)
                              or context.get_settings().audio_only()) else
                          xbmc.PLAYLIST_VIDEO),
                )
                result = True

        elif context.is_plugin_path(uri):
            log_action = 'Redirecting to'
            parts, params, log_uri, _ = parse_and_redact_uri(uri)
            action = context.create_uri(
                (PATHS.ROUTE, parts.path.rstrip('/') or PATHS.HOME),
                params,
                run=True,
            )
            result = False

        else:
            action = None
            result = False
            return result, action

        context.log_debug(''.join((
            log_action,
            ': |',
            log_uri,
            '|',
        )))
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
