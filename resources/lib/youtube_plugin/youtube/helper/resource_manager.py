# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from itertools import chain

from .utils import get_thumbnail
from ...kodion import logging
from ...kodion.constants import CHANNEL_ID, FANART_TYPE, INCOGNITO


class ResourceManager(object):
    log = logging.getLogger(__name__)

    def __init__(self, provider, context, client, progress_dialog=None):
        self._provider = provider
        self._context = context
        self._client = client
        self._progress_dialog = progress_dialog

        self.new_data = {}

        params = context.get_params()
        self._incognito = params.get(INCOGNITO)

        fanart_type = params.get(FANART_TYPE)
        settings = context.get_settings()
        if fanart_type is None:
            fanart_type = settings.fanart_selection()
        self._channel_fanart = fanart_type == settings.FANART_CHANNEL
        self._thumb_size = settings.get_thumbnail_size()

    def context_changed(self, context, client):
        return self._context != context or self._client != client

    def update_progress_dialog(self, progress_dialog):
        old_progress_dialog = self._progress_dialog
        if not progress_dialog or old_progress_dialog == progress_dialog:
            return
        if old_progress_dialog:
            old_progress_dialog.close()
        self._progress_dialog = progress_dialog

    def _list_batch(self, input_list, n=50):
        if not isinstance(input_list, (list, tuple)):
            input_list = list(input_list)
        num_items = len(input_list)
        for i in range(0, num_items, n):
            yield input_list[i:i + n]
            if self._progress_dialog:
                self._progress_dialog.update(steps=min(n, num_items))

    def get_channels(self, ids, suppress_errors=False, defer_cache=False):
        context = self._context
        client = self._client
        data_cache = context.get_data_cache()
        function_cache = context.get_function_cache()

        refresh = context.refresh_requested()
        forced_cache = not function_cache.run(
            client.internet_available,
            function_cache.ONE_MINUTE * 5,
            _refresh=refresh,
        )
        refresh = not forced_cache and refresh

        updated = []
        handles = {}
        for identifier in ids:
            if not identifier:
                continue

            if identifier != 'mine' and not identifier.startswith('@'):
                updated.append(identifier)
                continue

            channel_id = function_cache.run(
                client.get_channel_by_identifier,
                function_cache.ONE_MONTH,
                _refresh=refresh,
                identifier=identifier,
            )
            if channel_id:
                updated.append(channel_id)
                if channel_id != identifier:
                    handles[channel_id] = identifier

        ids = updated
        if refresh or not ids:
            result = {}
        else:
            result = data_cache.get_items(
                ids,
                None if forced_cache else data_cache.ONE_DAY,
            )
        to_update = (
            []
            if forced_cache else
            [id_ for id_ in ids
             if id_
             and (id_ not in result
                  or not result[id_]
                  or result[id_].get('_partial'))]
        )

        if result:
            self.log.debugging and self.log.debug(
                ('Using cached data for {num} channel(s)',
                 'Channel IDs: {ids}'),
                num=len(result),
                ids=list(result),
            )
            if self._progress_dialog:
                self._progress_dialog.update(steps=len(result) - len(to_update))

        if to_update:
            notify_and_raise = not suppress_errors
            new_data = [client.get_channels(list_of_50,
                                            max_results=50,
                                            notify=notify_and_raise,
                                            raise_exc=notify_and_raise)
                        for list_of_50 in self._list_batch(to_update, n=50)]
            if any(new_data):
                new_data = {
                    yt_item['id']: yt_item
                    for batch in new_data
                    for yt_item in batch.get('items', [])
                    if yt_item
                }
            else:
                new_data = None
        else:
            new_data = None

        if new_data:
            self.log.debugging and self.log.debug(
                ('Retrieved new data for {num} channel(s)',
                 'Channel IDs: {ids}'),
                num=len(to_update),
                ids=to_update,
            )
            result.update(new_data)
            self.cache_data(new_data, defer=defer_cache)

        # Re-sort result to match order of requested IDs
        # Will only work in Python v3.7+
        if handles or list(result) != ids[:len(result)]:
            result = {
                handles.get(id_, id_): result[id_]
                for id_ in ids
                if id_ in result
            }

        return result

    def get_channel_info(self,
                         ids,
                         channel_data=None,
                         suppress_errors=False,
                         defer_cache=False):
        context = self._context
        client = self._client
        function_cache = context.get_function_cache()

        refresh = context.refresh_requested()
        forced_cache = not function_cache.run(
            client.internet_available,
            function_cache.ONE_MINUTE * 5,
            _refresh=refresh,
        )
        refresh = not forced_cache and refresh

        if not refresh and channel_data:
            result = channel_data
        else:
            result = {}

        to_check = [id_ for id_ in ids
                    if id_
                    and (id_ not in result
                         or not result[id_]
                         or result[id_].get('_partial'))]
        if to_check:
            data_cache = context.get_data_cache()
            result.update(data_cache.get_items(
                to_check,
                None if forced_cache else data_cache.ONE_MONTH,
            ))
        to_update = (
            []
            if forced_cache else
            [id_ for id_ in ids
             if id_
             and (id_ not in result
                  or not result[id_]
                  or result[id_].get('_partial'))]
        )

        if result:
            self.log.debugging and self.log.debug(
                ('Using cached data for {num} channel(s)',
                 'Channel IDs: {ids}'),
                num=len(result),
                ids=list(result),
            )
            if self._progress_dialog:
                self._progress_dialog.update(steps=len(result) - len(to_update))

        if to_update:
            notify_and_raise = not suppress_errors
            new_data = [client.get_channels(list_of_50,
                                            max_results=50,
                                            notify=notify_and_raise,
                                            raise_exc=notify_and_raise)
                        for list_of_50 in self._list_batch(to_update, n=50)]
            if any(new_data):
                new_data = {
                    yt_item['id']: yt_item
                    for batch in new_data
                    for yt_item in batch.get('items', [])
                    if yt_item
                }
            else:
                new_data = None
        else:
            new_data = None

        if new_data:
            self.log.debugging and self.log.debug(
                ('Retrieved new data for {num} channel(s)',
                 'Channel IDs: {ids}'),
                num=len(to_update),
                ids=to_update,
            )
            result.update(new_data)
            self.cache_data(new_data, defer=defer_cache)

        banners = (
            'bannerTvMediumImageUrl',
            'bannerTvLowImageUrl',
            'bannerTvImageUrl',
            'bannerExternalUrl',
        )
        untitled = context.localize('untitled')
        thumb_size = self._thumb_size
        channel_fanart = self._channel_fanart

        # transform
        for key, item in result.items():
            channel_info = {
                'name': None,
                'image': None,
                'fanart': None,
            }

            if channel_fanart:
                images = item.get('brandingSettings', {}).get('image', {})
                for banner in banners:
                    image = images.get(banner)
                    if image:
                        channel_info['fanart'] = image
                        break

            snippet = item.get('snippet')
            if snippet:
                localised_info = snippet.get('localized') or {}
                channel_info['name'] = (localised_info.get('title')
                                        or snippet.get('title')
                                        or untitled)
                channel_info['image'] = get_thumbnail(thumb_size,
                                                      snippet.get('thumbnails'))
            result[key] = channel_info

        return result

    def get_playlists(self, ids, suppress_errors=False, defer_cache=False):
        ids = tuple(ids)

        context = self._context
        client = self._client
        function_cache = context.get_function_cache()

        refresh = context.refresh_requested()
        forced_cache = not function_cache.run(
            client.internet_available,
            function_cache.ONE_MINUTE * 5,
            _refresh=refresh,
        )
        refresh = not forced_cache and refresh

        if refresh or not ids:
            result = {}
        else:
            data_cache = context.get_data_cache()
            result = data_cache.get_items(
                ids,
                None if forced_cache else data_cache.ONE_DAY,
            )
        to_update = (
            []
            if forced_cache else
            [id_ for id_ in ids
             if id_
             and (id_ not in result
                  or not result[id_]
                  or result[id_].get('_partial'))]
        )

        if result:
            self.log.debugging and self.log.debug(
                ('Using cached data for {num} playlist(s)',
                 'Playlist IDs: {ids}'),
                num=len(result),
                ids=list(result),
            )
            if self._progress_dialog:
                self._progress_dialog.update(steps=len(result) - len(to_update))

        if to_update:
            notify_and_raise = not suppress_errors
            new_data = [client.get_playlists(list_of_50,
                                             max_results=50,
                                             notify=notify_and_raise,
                                             raise_exc=notify_and_raise)
                        for list_of_50 in self._list_batch(to_update, n=50)]
            if any(new_data):
                new_data = {
                    yt_item['id']: yt_item
                    for batch in new_data
                    for yt_item in batch.get('items', [])
                    if yt_item
                }
            else:
                new_data = None
        else:
            new_data = None

        if new_data:
            self.log.debugging and self.log.debug(
                ('Retrieved new data for {num} playlist(s)',
                 'Playlist IDs: {ids}'),
                num=len(to_update),
                ids=to_update,
            )
            result.update(new_data)
            self.cache_data(new_data, defer=defer_cache)

        # Re-sort result to match order of requested IDs
        # Will only work in Python v3.7+
        if list(result) != ids[:len(result)]:
            result = {
                id_: result[id_]
                for id_ in ids
                if id_ in result
            }

        return result

    def get_playlist_items(self,
                           ids=None,
                           batch_id=None,
                           page_token=None,
                           defer_cache=False,
                           flatten=False,
                           **kwargs):
        if not ids and not batch_id:
            return None

        context = self._context
        client = self._client
        function_cache = context.get_function_cache()

        refresh = context.refresh_requested()
        forced_cache = (
                not function_cache.run(
                    client.internet_available,
                    function_cache.ONE_MINUTE * 5,
                    _refresh=refresh,
                )
                or (context.get_param(CHANNEL_ID) == 'mine'
                    and not client.logged_in)
        )
        refresh = not forced_cache and refresh

        if batch_id:
            ids = [batch_id[0]]
            page_token = batch_id[1] or page_token
            fetch_next = False
        elif page_token is None:
            fetch_next = True
        elif len(ids) == 1:
            fetch_next = False
        else:
            page_token = None
            fetch_next = True

        data_cache = context.get_data_cache()
        batch_ids = []
        to_update = []
        result = {}
        for playlist_id in ids:
            page_token = page_token or 0
            while 1:
                batch_id = (playlist_id, page_token)
                batch_ids.append(batch_id)
                if refresh:
                    batch = None
                else:
                    batch = data_cache.get_item(
                        '{0},{1}'.format(*batch_id),
                        as_dict=True,
                    )
                if not batch:
                    if not forced_cache:
                        to_update.append(batch_id)
                    break
                age = batch.get('age')
                batch = batch.get('value')
                if not batch:
                    to_update.append(batch_id)
                    break
                elif forced_cache:
                    result[batch_id] = batch
                elif page_token:
                    if age <= data_cache.ONE_DAY:
                        result[batch_id] = batch
                    else:
                        to_update.append(batch_id)
                        break
                else:
                    if age <= data_cache.ONE_MINUTE * 5:
                        result[batch_id] = batch
                    else:
                        to_update.append(batch_id)
                page_token = batch.get('nextPageToken') if fetch_next else None
                if not page_token:
                    break

        if result:
            self.log.debugging and self.log.debug(
                ('Using cached data for {num} playlist part(s)',
                 'Batch IDs: {ids}'),
                num=len(result),
                ids=list(result),
            )
            if self._progress_dialog:
                self._progress_dialog.update(steps=len(result) - len(to_update))

        new_data = {}
        insert_point = 0
        for playlist_id, page_token in to_update:
            new_batch_ids = []
            batch_id = (playlist_id, page_token)
            insert_point = batch_ids.index(batch_id, insert_point)
            while 1:
                batch_id = (playlist_id, page_token)
                if batch_id in result:
                    break
                batch = client.get_playlist_items(*batch_id, **kwargs)
                if not batch:
                    break
                new_batch_ids.append(batch_id)
                new_data[batch_id] = batch
                page_token = batch.get('nextPageToken') if fetch_next else None
                if not page_token:
                    break

            if new_batch_ids:
                batch_ids[insert_point:insert_point] = new_batch_ids
                insert_point += len(new_batch_ids)

        if new_data:
            self.log.debugging and self.log.debug(
                ('Retrieved new data for {num} playlist part(s)',
                 'Batch IDs: {ids}'),
                num=len(new_data),
                ids=list(new_data),
            )
            result.update(new_data)
            self.cache_data({
                '{0},{1}'.format(*batch_id): batch
                for batch_id, batch in new_data.items()
            }, defer=defer_cache)

        # Re-sort result to match order of requested IDs
        # Will only work in Python v3.7+
        if list(result) != batch_ids[:len(result)]:
            result = {
                batch_id: result[batch_id]
                for batch_id in batch_ids
                if batch_id in result
            }

        if not fetch_next:
            return result[batch_ids[0]]
        if flatten:
            items = chain.from_iterable(
                batch.get('items', [])
                for batch in result.values()
            )
            result = result[batch_ids[-1]]
            result['items'] = list(items)
            return result
        return result

    def get_related_playlists(self, channel_id, defer_cache=False):
        result = self.get_channels((channel_id,), defer_cache=defer_cache)

        # transform
        item = None
        if channel_id != 'mine':
            item = result.get(channel_id, {})
        else:
            for item in result.values():
                if item:
                    break

        if item is None:
            return None
        return item.get('contentDetails', {}).get('relatedPlaylists')

    def get_my_playlists(self, channel_id, page_token, defer_cache=False):
        result = self._client.get_playlists_of_channel(channel_id, page_token)
        if not result:
            return None

        new_data = {
            yt_item['id']: yt_item
            for yt_item in result.get('items', [])
            if yt_item
        }
        if new_data:
            self.log.debugging and self.log.debug(
                ('Retrieved new data for {num} playlist(s)',
                 'Playlist IDs: {ids}'),
                num=len(new_data),
                ids=list(new_data),
            )
            self.cache_data(new_data, defer=defer_cache)

        return result

    def get_videos(self,
                   ids,
                   live_details=False,
                   suppress_errors=False,
                   defer_cache=False,
                   yt_items_dict=None):
        ids = tuple(ids)

        context = self._context
        client = self._client
        function_cache = context.get_function_cache()

        refresh = context.refresh_requested()
        forced_cache = not function_cache.run(
            client.internet_available,
            function_cache.ONE_MINUTE * 5,
            _refresh=refresh,
        )
        refresh = not forced_cache and refresh

        if refresh or not ids:
            result = {}
        else:
            data_cache = context.get_data_cache()
            result = data_cache.get_items(
                ids,
                None if forced_cache else data_cache.ONE_MONTH,
            )
        to_update = (
            []
            if forced_cache else
            [id_ for id_ in ids
             if id_
             and (id_ not in result
                  or not result[id_]
                  or result[id_].get('_partial')
                  or (yt_items_dict
                      and yt_items_dict.get(id_)
                      and result[id_].get('_unavailable')))]
        )

        if result:
            self.log.debugging and self.log.debug(
                ('Using cached data for {num} video(s)',
                 'Video IDs: {ids}'),
                num=len(result),
                ids=list(result),
            )
            if self._progress_dialog:
                self._progress_dialog.update(steps=len(result) - len(to_update))

        if to_update:
            notify_and_raise = not suppress_errors
            new_data = [client.get_videos(list_of_50,
                                          live_details,
                                          max_results=50,
                                          notify=notify_and_raise,
                                          raise_exc=notify_and_raise)
                        for list_of_50 in self._list_batch(to_update, n=50)]
            if any(new_data):
                new_data = {
                    yt_item['id']: yt_item
                    for batch in new_data
                    for yt_item in batch.get('items', [])
                    if yt_item
                }
            else:
                new_data = None
        else:
            new_data = None

        if new_data:
            self.log.debugging and self.log.debug(
                ('Retrieved new data for {num} video(s)',
                 'Video IDs: {ids}'),
                num=len(to_update),
                ids=to_update,
            )
            new_data = dict(dict.fromkeys(to_update, {'_unavailable': True}),
                            **new_data)
            result.update(new_data)
            self.cache_data(new_data, defer=defer_cache)

        if not result and not new_data and yt_items_dict:
            result = yt_items_dict
            self.cache_data(result, defer=defer_cache)

        # Re-sort result to match order of requested IDs
        # Will only work in Python v3.7+
        if list(result) != ids[:len(result)]:
            result = {
                id_: result[id_]
                for id_ in ids
                if id_ in result
            }

        if context.get_settings().use_local_history():
            playback_history = context.get_playback_history()
            played_items = playback_history.get_items(ids)
            for video_id, play_data in played_items.items():
                if video_id in result:
                    result[video_id]['play_data'] = play_data

        return result

    def cache_data(self, data=None, defer=False):
        if not data:
            return None

        incognito = self._incognito
        if not defer and self.log.debugging:
            self.log.debug(
                (
                    'Incognito mode active - discarded data for {num} item(s)',
                    'IDs: {ids}'
                ) if incognito else (
                    'Storing new data to cache for {num} item(s)',
                    'IDs: {ids}'
                ),
                num=len(data),
                ids=list(data)
            )

        return self._context.get_data_cache().set_items(
            data,
            defer=defer,
            flush=incognito,
        )
