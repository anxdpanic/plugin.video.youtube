# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..abstract_plugin import AbstractPlugin
from ... import logging
from ...compatibility import string_type, xbmc, xbmcgui, xbmcplugin
from ...constants import (
    ACTION,
    BUSY_FLAG,
    CONTAINER_FOCUS,
    CONTAINER_ID,
    CONTAINER_POSITION,
    FOLDER_URI,
    FORCE_PLAY_PARAMS,
    PATHS,
    PLAYBACK_FAILED,
    PLAYER_VIDEO_ID,
    PLAYLIST_PATH,
    PLAYLIST_POSITION,
    PLAY_CANCELLED,
    PLAY_FORCED,
    PLAY_FORCE_AUDIO,
    PLUGIN_SLEEPING,
    PLUGIN_WAKEUP,
    REFRESH_CONTAINER,
    RELOAD_ACCESS_MANAGER,
    REROUTE_PATH,
    SYNC_LISTITEM,
    TRAKT_PAUSE_FLAG,
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
from ...utils.redact import parse_and_redact_uri


class XbmcPlugin(AbstractPlugin):
    _LIST_ITEM_MAP = {
        'AudioItem': media_listitem,
        'BookmarkItem': directory_listitem,
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
        'BookmarkItem': playback_item,
        'UriItem': uri_listitem,
        'VideoItem': playback_item,
    }

    def __init__(self):
        super(XbmcPlugin, self).__init__()

    def run(self,
            provider,
            context,
            forced=False,
            is_same_path=False,
            **kwargs):
        handle = context.get_handle()
        ui = context.get_ui()

        uri = context.get_uri()
        path = context.get_path().rstrip('/')

        route = ui.pop_property(REROUTE_PATH)
        _post_run_action = None
        post_run_actions = []
        succeeded = False
        for was_busy in (ui.pop_property(BUSY_FLAG),):
            if was_busy:
                if ui.busy_dialog_active():
                    ui.set_property(BUSY_FLAG)
                if route:
                    break
            else:
                break

            playlist_player = context.get_playlist_player()
            position, remaining = playlist_player.get_position()
            playing = path == PATHS.PLAY and playlist_player.is_playing()

            if playing:
                items = playlist_player.get_items()
                playlist_player.clear()
                logging.warning('Multiple busy dialogs active'
                                ' - Playlist cleared to avoid Kodi crash')

            xbmcplugin.endOfDirectory(
                handle,
                succeeded=False,
                updateListing=True,
                cacheToDisc=False,
            )

            if not playing:
                logging.warning('Multiple busy dialogs active'
                                ' - Plugin call ended to avoid Kodi crash')
                result, _post_run_action = self.uri_action(context, uri)
                succeeded = result
                if _post_run_action:
                    post_run_actions.append(_post_run_action)
                    _post_run_action = None
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

            timeout = 30
            while ui.busy_dialog_active():
                timeout -= 1
                if timeout < 0:
                    logging.error('Multiple busy dialogs active'
                                  ' - Extended busy period')
                    break
                context.sleep(1)

            logging.warning('Multiple busy dialogs active'
                            ' - Reloading playlist...')

            num_items = playlist_player.add_items(items)
            if position:
                timeout = min(position, num_items)
            else:
                position = 1
                timeout = num_items

            while ui.busy_dialog_active() or playlist_player.size() < position:
                timeout -= 1
                if timeout < 0:
                    logging.error('Multiple busy dialogs active'
                                  ' - Playback restart failed, retrying...')
                    command = playlist_player.play_playlist_item(position,
                                                                 defer=True)
                    result, _post_run_action = self.uri_action(
                        context,
                        command,
                    )
                    succeeded = False
                    if _post_run_action:
                        post_run_actions.append(_post_run_action)
                        _post_run_action = None
                    break
                context.sleep(1)
            else:
                playlist_player.play_playlist_item(position)
        else:
            if post_run_actions:
                self.post_run(context, ui, *post_run_actions)
            return succeeded

        if ui.get_property(PLUGIN_SLEEPING):
            context.ipc_exec(PLUGIN_WAKEUP)

        if ui.pop_property(RELOAD_ACCESS_MANAGER):
            context.reload_access_manager()

        settings = context.get_settings()
        setup_wizard_required = settings.setup_wizard_enabled()
        if setup_wizard_required:
            provider.run_wizard(context, last_run=setup_wizard_required)
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
                if ui.get_property(REROUTE_PATH):
                    xbmcplugin.endOfDirectory(
                        handle,
                        succeeded=False,
                        updateListing=True,
                        cacheToDisc=False,
                    )
                    return False
        except KodionException as exc:
            result = None
            options = {}
            if not provider.handle_exception(context, exc):
                logging.exception('Error')
                ui.on_ok('Error in ContentProvider', exc.__str__())

        if not ui.pop_property(REFRESH_CONTAINER, as_bool=True) and forced:
            played_video_id = ui.pop_property(PLAYER_VIDEO_ID)
            if played_video_id:
                focused_video_id = None
            else:
                focused_video_id = None if route else ui.get_property(VIDEO_ID)
                played_video_id = None
        else:
            focused_video_id = None
            played_video_id = None
        sync_items = (focused_video_id, played_video_id)

        play_cancelled = ui.pop_property(PLAY_CANCELLED)
        if play_cancelled:
            result = None

        force_resolve = options.get(provider.FORCE_RESOLVE)
        force_return = options.get(provider.FORCE_RETURN)
        result_item = None
        result_item_type = None
        items = None
        if isinstance(result, (list, tuple)):
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
                if force_return:
                    _, _post_run_action = self.uri_action(
                        context,
                        'command://Action(Back)'
                    )
                    if _post_run_action:
                        post_run_actions.append(_post_run_action)
                        _post_run_action = None

            items = []
            for item in result:
                item_type = item.__class__.__name__

                if (force_resolve
                        and not result_item
                        and item_type in self._PLAY_ITEM_MAP
                        and item.playable):
                    result_item = item
                    result_item_type = item_type

                listitem_type = self._LIST_ITEM_MAP.get(item_type)
                if (not listitem_type
                        or (listitem_type == directory_listitem
                            and not item.available)):
                    continue

                items.append(listitem_type(
                    context,
                    item,
                    show_fanart=show_fanart,
                    to_sync=sync_items,
                ))
        else:
            result_item = result
            result_item_type = result.__class__.__name__

        if items:
            content_type = options.get(provider.CONTENT_TYPE)
            if content_type:
                context.apply_content(**content_type)
            else:
                context.apply_content()
            succeeded = xbmcplugin.addDirectoryItems(
                handle, items, len(items)
            )
            cache_to_disc = options.get(provider.CACHE_TO_DISC, True)
            update_listing = options.get(provider.UPDATE_LISTING, False)

            fallback = options.get(provider.FALLBACK)
            if not fallback or fallback != ui.get_property(provider.FALLBACK):
                ui.clear_property(provider.FALLBACK)
        else:
            succeeded = bool(result)
            cache_to_disc = options.get(provider.CACHE_TO_DISC, False)
            update_listing = options.get(provider.UPDATE_LISTING, True)

        if result_item and result_item_type in self._PLAY_ITEM_MAP:
            if not forced and not force_resolve and path != PATHS.PLAY:
                force_play = True
            else:
                force_play = options.get(provider.FORCE_PLAY)

            if force_play or not result_item.playable:
                _, _post_run_action = self.uri_action(
                    context,
                    result_item.get_uri()
                )
                if _post_run_action:
                    post_run_actions.append(_post_run_action)
                    _post_run_action = None
            else:
                item = self._PLAY_ITEM_MAP[result_item_type](
                    context,
                    result_item,
                    show_fanart=show_fanart,
                )
                xbmcplugin.setResolvedUrl(
                    handle, succeeded=True, listitem=item
                )
        elif not items or force_return:
            ui.clear_property(BUSY_FLAG)
            ui.clear_property(TRAKT_PAUSE_FLAG, raw=True)
            for param in FORCE_PLAY_PARAMS:
                ui.clear_property(param)

            fallback = options.get(provider.FALLBACK, not force_return)
            if isinstance(fallback, string_type) and fallback != uri:
                if options.get(provider.POST_RUN):
                    _, _post_run_action = self.uri_action(
                        context,
                        fallback,
                    )
                else:
                    context.parse_uri(fallback, update=True)
                    return self.run(provider, context, forced=forced)
            elif fallback:
                if play_cancelled:
                    _, _post_run_action = self.uri_action(context, uri)
                elif path == PATHS.PLAY:
                    context.send_notification(
                        PLAYBACK_FAILED,
                        {VIDEO_ID: context.get_param(VIDEO_ID)},
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
                elif options.get(provider.FORCE_REFRESH):
                    _post_run_action = (
                        context.send_notification,
                        {
                            'method': REFRESH_CONTAINER,
                        },
                    )
                else:
                    if context.is_plugin_path(
                            ui.get_container_info(FOLDER_URI, container_id=None)
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
            if _post_run_action:
                post_run_actions.append(_post_run_action)
                _post_run_action = None

        if ui.pop_property(PLAY_FORCED):
            context.set_path(PATHS.PLAY)
            return self.run(provider, context, forced=forced)

        xbmcplugin.endOfDirectory(
            handle,
            succeeded=succeeded,
            updateListing=update_listing,
            cacheToDisc=cache_to_disc,
        )

        if not force_return:
            if any(sync_items):
                context.send_notification(SYNC_LISTITEM, sync_items)

            container = ui.get_property(CONTAINER_ID)
            position = ui.get_property(CONTAINER_POSITION)

            if is_same_path:
                if (container and position
                        and (forced or position == 'current')
                        and (not played_video_id or route)):
                    post_run_actions.append((
                        context.send_notification,
                        {
                            'method': CONTAINER_FOCUS,
                            'data': {
                                CONTAINER_ID: container,
                                CONTAINER_POSITION: position,
                            },
                        },
                    ))

        if post_run_actions:
            self.post_run(context, ui, *post_run_actions)
        return succeeded

    @staticmethod
    def post_run(context, ui, *actions, **kwargs):
        timeout = kwargs.get('timeout', 30)
        interval = kwargs.get('interval', 0.1)
        for action in actions:
            while not ui.get_container(container_type=False, check_ready=True):
                timeout -= interval
                if timeout < 0:
                    logging.error('Container not ready'
                                  ' - Post run action unable to execute')
                    break
                context.sleep(interval)
            else:
                if isinstance(action, tuple):
                    action, action_kwargs = action
                else:
                    action_kwargs = None
                logging.debug('Executing queued post-run action: {action}',
                              action=action,
                              stacklevel=2)
                if callable(action):
                    if action_kwargs:
                        action(**action_kwargs)
                    else:
                        action()
                else:
                    context.execute(action)
                context.sleep(interval)

    @staticmethod
    def uri_action(context, uri):
        if uri.startswith('script://'):
            _uri = uri[len('script://'):]
            log_action = 'RunScript queued'
            log_uri = _uri
            action = 'RunScript({0})'.format(_uri)
            result = True

        elif uri.startswith('command://'):
            _uri = uri[len('command://'):]
            log_action = 'Builtin command queued'
            log_uri = _uri
            action = _uri
            result = True

        elif uri.startswith('PlayMedia('):
            log_action = 'Redirect for playback queued'
            log_uri = uri[len('PlayMedia('):-1].split(',')
            log_uri[0] = parse_and_redact_uri(
                log_uri[0],
                redact_only=True,
            )
            log_uri = ','.join(log_uri)
            action = uri
            result = True

        elif uri.startswith('RunPlugin('):
            log_action = 'RunPlugin queued'
            log_uri = parse_and_redact_uri(
                uri[len('RunPlugin('):-1],
                redact_only=True,
            )
            action = uri
            result = True

        elif uri.startswith('ActivateWindow('):
            log_action = 'ActivateWindow queued'
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
            log_action = 'ReplaceWindow queued'
            log_uri = uri[len('ReplaceWindow('):-1].split(',')
            if len(log_uri) >= 2:
                log_uri[1] = parse_and_redact_uri(
                    log_uri[1],
                    redact_only=True,
                )
            log_uri = ','.join(log_uri)
            action = uri
            result = False

        elif uri.startswith('Container.Update('):
            log_action = 'Container.Update queued'
            log_uri = uri[len('Container.Update('):-1].split(',')
            if log_uri[0]:
                log_uri[0] = parse_and_redact_uri(
                    log_uri[0],
                    redact_only=True,
                )
            log_uri = ','.join(log_uri)
            action = uri
            result = False

        elif uri.startswith('Container.Refresh('):
            log_action = 'Container.Refresh queued'
            log_uri = uri[len('Container.Refresh('):-1].split(',')
            if log_uri[0]:
                log_uri[0] = parse_and_redact_uri(
                    log_uri[0],
                    redact_only=True,
                )
            log_uri = ','.join(log_uri)
            action = uri
            result = False

        elif context.is_plugin_path(uri, PATHS.PLAY):
            parts, params, log_uri, _ = parse_and_redact_uri(uri)
            if params.get(ACTION, [None])[0] == 'list':
                log_action = 'Redirect queued'
                action = context.create_uri(
                    (PATHS.ROUTE, parts.path.rstrip('/')),
                    params,
                    run=True,
                )
                result = False
            else:
                log_action = 'Redirect for playback queued'
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
            log_action = 'Redirect queued'
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

        logging.debug('{action}: {uri!r}',
                      action=log_action,
                      uri=log_uri,
                      stacklevel=2)
        return result, action
