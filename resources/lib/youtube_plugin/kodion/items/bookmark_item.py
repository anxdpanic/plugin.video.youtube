# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .directory_item import DirectoryItem
from .media_item import VideoItem


class BookmarkItem(VideoItem, DirectoryItem):
    def __init__(self,
                 name,
                 uri,
                 image='{media}/bookmarks.png',
                 fanart=None,
                 plot=None,
                 action=False,
                 playable=None,
                 special_sort=None,
                 date_time=None,
                 category_label=None,
                 bookmark_id=None,
                 video_id=None,
                 channel_id=None,
                 playlist_id=None,
                 playlist_item_id=None,
                 subscription_id=None,
                 **_kwargs):
        super(BookmarkItem, self).__init__(
            name=name,
            uri=uri,
            image=image,
            fanart=fanart,
            plot=plot,
            action=action,
            special_sort=special_sort,
            date_time=date_time,
            category_label=category_label,
            bookmark_id=bookmark_id,
            video_id=video_id,
            channel_id=channel_id,
            playlist_id=playlist_id,
            playlist_item_id=playlist_item_id,
            subscription_id=subscription_id,
        )
        self._bookmark_id = bookmark_id
        if playable is not None:
            self._playable = playable
