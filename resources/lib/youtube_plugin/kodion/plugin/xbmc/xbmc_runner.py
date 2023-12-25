# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from traceback import format_stack

from ..abstract_provider_runner import AbstractProviderRunner
from ...compatibility import xbmcgui, xbmcplugin
from ...exceptions import KodionException
from ...items import AudioItem, DirectoryItem, ImageItem, UriItem, VideoItem
from ...player import Playlist
from ...ui.xbmc import info_labels, xbmc_items


class XbmcRunner(AbstractProviderRunner):
    def __init__(self):
        super(XbmcRunner, self).__init__()
        self.handle = None
        self.settings = None

    def run(self, provider, context):
        self.handle = context.get_handle()
        ui = context.get_ui()

        if ui.get_property('busy').lower() == 'true':
            ui.clear_property('busy')
            if ui.busy_dialog_active():
                playlist = Playlist('video', context)
                playlist.clear()

                xbmcplugin.endOfDirectory(self.handle, succeeded=False)

                items = ui.get_property('playlist')
                if items:
                    ui.clear_property('playlist')
                    context.log_error('Multiple busy dialogs active - playlist'
                                      ' reloading to prevent Kodi crashing')
                    playlist.add_items(items, loads=True)
                return False

        try:
            results = provider.navigate(context)
        except KodionException as exc:
            if provider.handle_exception(context, exc):
                context.log_error('XbmcRunner.run - {exc}:\n{details}'.format(
                    exc=exc, details=''.join(format_stack())
                ))
                xbmcgui.Dialog().ok("Error in ContentProvider", exc.__str__())
            xbmcplugin.endOfDirectory(self.handle, succeeded=False)
            return False

        self.settings = context.get_settings()

        result, options = results

        if isinstance(result, bool):
            xbmcplugin.endOfDirectory(self.handle, succeeded=result)
            return result

        if isinstance(result, (VideoItem, AudioItem, UriItem)):
            return self._set_resolved_url(context, result)

        show_fanart = self.settings.show_fanart()

        if isinstance(result, DirectoryItem):
            item_count = 1
            items = [self._add_directory(result, show_fanart)]
        elif isinstance(result, (list, tuple)):
            item_count = len(result)
            items = [
                self._add_directory(item, show_fanart)
                if isinstance(item, DirectoryItem)
                else self._add_video(context, item)
                if isinstance(item, VideoItem)
                else self._add_audio(context, item)
                if isinstance(item, AudioItem)
                else self._add_image(item, show_fanart)
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
        return succeeded

    def _set_resolved_url(self, context, base_item):
        uri = base_item.get_uri()

        if base_item.playable:
            ui = context.get_ui()
            if not context.is_plugin_path(uri) and ui.busy_dialog_active():
                ui.set_property('busy', 'true')
                playlist = Playlist('video', context)
                ui.set_property('playlist', playlist.get_items(dumps=True))

            item = xbmc_items.to_playback_item(context, base_item)
            xbmcplugin.setResolvedUrl(self.handle,
                                      succeeded=True,
                                      listitem=item)
            return True

        if context.is_plugin_path(uri):
            context.log_debug('Redirecting to |{0}|'.format(uri))
            context.execute('RunPlugin({0})'.format(uri))

        xbmcplugin.endOfDirectory(self.handle,
                                  succeeded=False,
                                  updateListing=False,
                                  cacheToDisc=False)
        return False

    @staticmethod
    def _add_directory(directory_item, show_fanart=False):
        art = {'icon': 'DefaultFolder.png',
               'thumb': directory_item.get_image()}

        item = xbmcgui.ListItem(label=directory_item.get_name(), offscreen=True)
        item_info = info_labels.create_from_item(directory_item)
        xbmc_items.set_info_tag(item, item_info, 'video')

        # only set fanart if enabled
        if show_fanart:
            fanart = directory_item.get_fanart()
            if fanart:
                art['fanart'] = fanart

        item.setArt(art)

        context_menu = directory_item.get_context_menu()
        if context_menu is not None:
            item.addContextMenuItems(
                context_menu, replaceItems=directory_item.replace_context_menu()
            )

        item.setPath(directory_item.get_uri())

        is_folder = not directory_item.is_action()

        if directory_item.next_page:
            item.setProperty('specialSort', 'bottom')

        # make channel_subscription_id property available for keymapping
        subscription_id = directory_item.get_channel_subscription_id()
        if subscription_id:
            item.setProperty('channel_subscription_id', subscription_id)

        return directory_item.get_uri(), item, is_folder

    @staticmethod
    def _add_video(context, video_item):
        item = xbmc_items.video_listitem(context, video_item)
        item.setPath(video_item.get_uri())
        return video_item.get_uri(), item, False

    @staticmethod
    def _add_image(image_item, show_fanart=False):
        art = {'icon': 'DefaultPicture.png',
               'thumb': image_item.get_image()}

        item = xbmcgui.ListItem(label=image_item.get_name(), offscreen=True)

        # only set fanart is enabled
        if show_fanart:
            fanart = image_item.get_fanart()
            if fanart:
                art['fanart'] = fanart

        item.setArt(art)

        context_menu = image_item.get_context_menu()
        if context_menu is not None:
            item.addContextMenuItems(
                context_menu, replaceItems=image_item.replace_context_menu()
            )

        item.setInfo(type='picture',
                     infoLabels=info_labels.create_from_item(image_item))

        item.setPath(image_item.get_uri())
        return image_item.get_uri(), item, False

    @staticmethod
    def _add_audio(context, audio_item):
        item = xbmc_items.audio_listitem(context, audio_item)
        item.setPath(audio_item.get_uri())
        return audio_item.get_uri(), item, False
