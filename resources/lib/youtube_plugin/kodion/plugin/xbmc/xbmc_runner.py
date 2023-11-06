# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import xbmcgui
import xbmcplugin

from ..abstract_provider_runner import AbstractProviderRunner
from ...exceptions import KodionException
from ...items import AudioItem, DirectoryItem, ImageItem, UriItem, VideoItem
from ... import AbstractProvider
from ...ui.xbmc import info_labels, xbmc_items


class XbmcRunner(AbstractProviderRunner):
    def __init__(self):
        super(XbmcRunner, self).__init__()
        self.handle = None
        self.settings = None

    def run(self, provider, context):

        self.handle = context.get_handle()

        try:
            results = provider.navigate(context)
        except KodionException as ex:
            if provider.handle_exception(context, ex):
                context.log_error(ex.__str__())
                xbmcgui.Dialog().ok("Exception in ContentProvider", ex.__str__())
            xbmcplugin.endOfDirectory(self.handle, succeeded=False)
            return False

        self.settings = context.get_settings()

        result = results[0]
        options = {}
        options.update(results[1])

        if isinstance(result, bool) and not result:
            xbmcplugin.endOfDirectory(self.handle, succeeded=False)
            return False

        if isinstance(result, (VideoItem, AudioItem, UriItem)):
            return self._set_resolved_url(context, result)

        show_fanart = self.settings.show_fanart()

        if isinstance(result, DirectoryItem):
            item_count = 1
            items = [self._add_directory(result, show_fanart)]
        elif isinstance(result, list):
            item_count = len(result)
            items = [
                self._add_directory(item, show_fanart) if isinstance(item, DirectoryItem)
                else self._add_video(context, item) if isinstance(item, VideoItem)
                else self._add_audio(context, item) if isinstance(item, AudioItem)
                else self._add_image(item, show_fanart) if isinstance(item, ImageItem)
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
            updateListing=options.get(AbstractProvider.RESULT_UPDATE_LISTING, False),
            cacheToDisc=options.get(AbstractProvider.RESULT_CACHE_TO_DISC, True)
        )
        return succeeded

    def _set_resolved_url(self, context, base_item, succeeded=True):
        item = xbmc_items.to_playback_item(context, base_item)
        item.setPath(base_item.get_uri())
        xbmcplugin.setResolvedUrl(self.handle, succeeded=succeeded, listitem=item)
        """
        # just to be sure :)
        if not isLiveStream:
            tries = 100
            while tries>0:
                xbmc.sleep(50)
                if xbmc.Player().isPlaying() and xbmc.getCondVisibility("Player.Paused"):
                    xbmc.Player().pause()
                    break
                tries-=1
        """
        return succeeded

    @staticmethod
    def _add_directory(directory_item, show_fanart=False):
        art = {'icon': 'DefaultFolder.png',
               'thumb': directory_item.get_image()}

        item = xbmcgui.ListItem(label=directory_item.get_name(), offscreen=True)

        info_tag = xbmc_items.ListItemInfoTag(item, tag_type='video')

        # only set fanart is enabled
        if show_fanart:
            fanart = directory_item.get_fanart()
            if fanart:
                art['fanart'] = fanart

        item.setArt(art)

        if directory_item.get_context_menu() is not None:
            item.addContextMenuItems(directory_item.get_context_menu(),
                                     replaceItems=directory_item.replace_context_menu())

        info_tag.set_info(info_labels.create_from_item(directory_item))
        item.setPath(directory_item.get_uri())

        is_folder = True
        if directory_item.is_action():
            is_folder = False
            item.setProperty('isPlayable', 'false')

        if directory_item.next_page:
            item.setProperty('specialSort', 'bottom')

        if directory_item.get_channel_subscription_id():  # make channel_subscription_id property available for keymapping
            item.setProperty('channel_subscription_id', directory_item.get_channel_subscription_id())

        return directory_item.get_uri(), item, is_folder

    @staticmethod
    def _add_video(context, video_item):
        item = xbmc_items.to_video_item(context, video_item)
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

        if image_item.get_context_menu() is not None:
            item.addContextMenuItems(image_item.get_context_menu(), replaceItems=image_item.replace_context_menu())

        item.setInfo(type='picture', infoLabels=info_labels.create_from_item(image_item))

        item.setPath(image_item.get_uri())
        return image_item.get_uri(), item, False

    @staticmethod
    def _add_audio(context, audio_item):
        item = xbmc_items.to_audio_item(context, audio_item)
        item.setPath(audio_item.get_uri())
        return audio_item.get_uri(), item, False
