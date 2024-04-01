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
from ...exceptions import KodionException
from ...items import (
    AudioItem,
    DirectoryItem,
    ImageItem,
    UriItem,
    VideoItem,
    audio_listitem,
    directory_listitem,
    image_listitem,
    playback_item,
    video_listitem,
)
from ...player import XbmcPlaylist


class XbmcPlugin(AbstractPlugin):
    def __init__(self):
        super(XbmcPlugin, self).__init__()
        self.handle = None

    def run(self, provider, context):
        self.handle = context.get_handle()
        settings = context.get_settings()
        ui = context.get_ui()

        if ui.get_property('busy').lower() == 'true':
            ui.clear_property('busy')
            if ui.busy_dialog_active():
                playlist = XbmcPlaylist('auto', context)
                playlist.clear()
                xbmcplugin.endOfDirectory(self.handle, succeeded=False)

                context.log_warning('Multiple busy dialogs active - '
                                    'playlist cleared to avoid Kodi crash')

                num_items = 0
                items = ui.get_property('playlist')
                position = ui.get_property('position')

                if position and items:
                    position = int(position)
                    ui.clear_property('playlist')

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
                    num_items = playlist.add_items(items, loads=True)

                if position and num_items:
                    position += 1
                    max_wait_time = min(position, num_items)
                    while ui.busy_dialog_active() or playlist.size() < position:
                        max_wait_time -= 1
                        if max_wait_time < 0:
                            context.log_error('Multiple busy dialogs active - '
                                              'unable to restart playback')
                            break
                        context.sleep(1)
                    else:
                        playlist.play_playlist_item(position)

                return False

        if settings.is_setup_wizard_enabled():
            provider.run_wizard(context)

        try:
            results = provider.navigate(context)
        except KodionException as exc:
            if provider.handle_exception(context, exc):
                context.log_error('XbmcRunner.run - {exc}:\n{details}'.format(
                    exc=exc, details=''.join(format_stack())
                ))
                ui.on_ok("Error in ContentProvider", exc.__str__())
            xbmcplugin.endOfDirectory(self.handle, succeeded=False)
            return False

        result, options = results
        if isinstance(result, bool):
            xbmcplugin.endOfDirectory(self.handle, succeeded=result)
            return result

        show_fanart = settings.show_fanart()

        if isinstance(result, (VideoItem, AudioItem, UriItem)):
            return self._set_resolved_url(context, result, show_fanart)

        if isinstance(result, DirectoryItem):
            item_count = 1
            items = [directory_listitem(context, result, show_fanart)]
        elif isinstance(result, (list, tuple)):
            item_count = len(result)
            items = [
                directory_listitem(context, item, show_fanart)
                if isinstance(item, DirectoryItem)
                else video_listitem(context, item, show_fanart)
                if isinstance(item, VideoItem)
                else audio_listitem(context, item, show_fanart)
                if isinstance(item, AudioItem)
                else image_listitem(context, item, show_fanart)
                if isinstance(item, ImageItem)
                else None
                for item in result
            ]
        else:
            # handle exception
            return False

        succeeded = xbmcplugin.addDirectoryItems(
            self.handle, items, item_count
        )
        xbmcplugin.endOfDirectory(
            self.handle,
            succeeded=succeeded,
            updateListing=options.get(provider.RESULT_UPDATE_LISTING, False),
            cacheToDisc=options.get(provider.RESULT_CACHE_TO_DISC, True)
        )

        # set alternative view mode
        view_manager = ui.get_view_manager()
        if view_manager.is_override_view_enabled():
            view_mode = view_manager.get_view_mode()
            if view_mode is not None:
                context.log_debug('Override view mode to "%d"' % view_mode)
                context.execute('Container.SetViewMode(%d)' % view_mode)

        return succeeded

    def _set_resolved_url(self, context, base_item, show_fanart):
        uri = base_item.get_uri()

        if base_item.playable:
            ui = context.get_ui()
            if not context.is_plugin_path(uri) and ui.busy_dialog_active():
                ui.set_property('busy', 'true')
                playlist = XbmcPlaylist('auto', context)
                position, remaining = playlist.get_position()
                if remaining:
                    ui.set_property('playlist', playlist.get_items(dumps=True))
                    ui.set_property('position', str(position))

            item = playback_item(context, base_item, show_fanart)
            xbmcplugin.setResolvedUrl(self.handle,
                                      succeeded=True,
                                      listitem=item)
            return True

        if context.is_plugin_path(uri):
            context.log_debug('Redirecting to: |{0}|'.format(uri))
            context.execute('RunPlugin({0})'.format(uri))
        else:
            context.log_debug('Running script: |{0}|'.format(uri))
            context.execute('RunScript({0})'.format(uri))

        xbmcplugin.endOfDirectory(self.handle,
                                  succeeded=False,
                                  updateListing=False,
                                  cacheToDisc=False)
        return False
