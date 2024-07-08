# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals


class ResourceManager(object):
    def __init__(self, provider, context):
        self._context = context
        fanart_type = context.get_param('fanart_type')
        if fanart_type is None:
            fanart_type = context.get_settings().fanart_selection()
        self._fanart_type = fanart_type
        self._provider = provider
        self.new_data = {}

    def context_changed(self, context):
        return self._context != context

    @staticmethod
    def _list_batch(input_list, n=50):
        if not isinstance(input_list, (list, tuple)):
            input_list = list(input_list)
        for i in range(0, len(input_list), n):
            yield input_list[i:i + n]

    def get_channels(self, ids, defer_cache=False):
        client = self._provider.get_client(self._context)
        data_cache = self._context.get_data_cache()
        function_cache = self._context.get_function_cache()
        refresh = self._context.get_param('refresh')
        updated = []
        for channel_id in ids:
            if not channel_id:
                continue

            if channel_id != 'mine':
                updated.append(channel_id)
                continue

            data = function_cache.run(
                client.get_channel_by_identifier,
                function_cache.ONE_DAY,
                _refresh=refresh,
                identifier=channel_id,
            ) or {}
            items = data.get('items', [{'id': 'mine'}])

            try:
                channel_id = items[0]['id']
                updated.append(channel_id)
            except IndexError:
                self._context.log_error('Channel not found:\n{data}'
                                        .format(data=data))

        ids = updated
        if refresh:
            result = {}
        else:
            result = data_cache.get_items(ids, data_cache.ONE_MONTH)
        to_update = [id_ for id_ in ids
                     if id_ not in result
                     or not result[id_]
                     or result[id_].get('_partial')]

        if result:
            self._context.log_debug('Found cached data for channels:\n|{ids}|'
                                    .format(ids=list(result)))

        if to_update:
            new_data = [client.get_channels(list_of_50)
                        for list_of_50 in self._list_batch(to_update, n=50)]
            if not any(new_data):
                new_data = None
        else:
            new_data = None

        if new_data:
            self._context.log_debug('Got data for channels:\n|{ids}|'
                                    .format(ids=to_update))
            new_data = {
                yt_item['id']: yt_item
                for batch in new_data
                for yt_item in batch.get('items', [])
                if yt_item
            }
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

    def get_fanarts(self, channel_ids, force=False, defer_cache=False):
        if force:
            pass
        elif self._fanart_type != self._context.get_settings().FANART_CHANNEL:
            return {}

        result = self.get_channels(channel_ids, defer_cache=defer_cache)
        banners = (
            'bannerTvMediumImageUrl',
            'bannerTvLowImageUrl',
            'bannerTvImageUrl',
            'bannerExternalUrl',
        )
        # transform
        for key, item in result.items():
            images = item.get('brandingSettings', {}).get('image', {})
            for banner in banners:
                image = images.get(banner)
                if image:
                    result[key] = image
                    break
            else:
                # set an empty url
                result[key] = ''

        return result

    def get_playlists(self, ids, defer_cache=False):
        ids = tuple(ids)
        refresh = self._context.get_param('refresh')
        if refresh:
            result = {}
        else:
            data_cache = self._context.get_data_cache()
            result = data_cache.get_items(ids, data_cache.ONE_MONTH)
        to_update = [id_ for id_ in ids
                     if id_ not in result
                     or not result[id_]
                     or result[id_].get('_partial')]

        if result:
            self._context.log_debug('Found cached data for playlists:\n|{ids}|'
                                    .format(ids=list(result)))

        if to_update:
            client = self._provider.get_client(self._context)
            new_data = [client.get_playlists(list_of_50)
                        for list_of_50 in self._list_batch(to_update, n=50)]
            if not any(new_data):
                new_data = None
        else:
            new_data = None

        if new_data:
            self._context.log_debug('Got data for playlists:\n|{ids}|'
                                    .format(ids=to_update))
            new_data = {
                yt_item['id']: yt_item
                for batch in new_data
                for yt_item in batch.get('items', [])
                if yt_item
            }
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

    def get_playlist_items(self, ids=None, batch_id=None, defer_cache=False):
        if not ids and not batch_id:
            return None

        refresh = self._context.get_param('refresh')

        if batch_id:
            ids = [batch_id[0]]
            page_token = batch_id[1]
            fetch_next = False
        else:
            page_token = None
            fetch_next = True

        data_cache = self._context.get_data_cache()
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
                        data_cache.ONE_HOUR if page_token
                        else data_cache.ONE_MINUTE * 5
                    )
                if not batch:
                    to_update.append(batch_id)
                    break
                result[batch_id] = batch
                page_token = batch.get('nextPageToken') if fetch_next else None
                if page_token is None:
                    break

        if result:
            self._context.log_debug('Found cached items for playlists:\n|{ids}|'
                                    .format(ids=list(result)))

        client = self._provider.get_client(self._context)
        new_data = {}
        insert_point = 0
        for playlist_id, page_token in to_update:
            new_batch_ids = []
            batch_id = (playlist_id, page_token)
            insert_point = batch_ids.index(batch_id, insert_point)
            while 1:
                batch_id = (playlist_id, page_token)
                new_batch_ids.append(batch_id)
                batch = client.get_playlist_items(*batch_id)
                new_data[batch_id] = batch
                page_token = batch.get('nextPageToken') if fetch_next else None
                if page_token is None:
                    batch_ids[insert_point:insert_point] = new_batch_ids
                    insert_point += len(new_batch_ids)
                    break

        if new_data:
            to_update = list(new_data)
            self._context.log_debug('Got items for playlists:\n|{ids}|'
                                    .format(ids=to_update))
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

    def get_videos(self,
                   ids,
                   live_details=False,
                   suppress_errors=False,
                   defer_cache=False):
        ids = tuple(ids)
        refresh = self._context.get_param('refresh')
        if refresh:
            result = {}
        else:
            data_cache = self._context.get_data_cache()
            result = data_cache.get_items(ids, data_cache.ONE_MONTH)
        to_update = [id_ for id_ in ids
                     if id_ not in result
                     or not result[id_]
                     or result[id_].get('_partial')]

        if result:
            self._context.log_debug('Found cached data for videos:\n|{ids}|'
                                    .format(ids=list(result)))

        if to_update:
            notify_and_raise = not suppress_errors
            client = self._provider.get_client(self._context)
            new_data = [client.get_videos(list_of_50,
                                          live_details,
                                          notify=notify_and_raise,
                                          raise_exc=notify_and_raise)
                        for list_of_50 in self._list_batch(to_update, n=50)]
            if not any(new_data):
                new_data = None
        else:
            new_data = None

        if new_data:
            self._context.log_debug('Got data for videos:\n|{ids}|'
                                    .format(ids=to_update))
            new_data = {
                yt_item['id']: yt_item
                for batch in new_data
                for yt_item in batch.get('items', [])
                if yt_item
            }
            new_data = dict(dict.fromkeys(to_update, {}), **new_data)
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

        if self._context.get_settings().use_local_history():
            playback_history = self._context.get_playback_history()
            played_items = playback_history.get_items(ids)
            for video_id, play_data in played_items.items():
                if video_id in result:
                    result[video_id]['play_data'] = play_data

        return result

    def cache_data(self, data=None, defer=False):
        if defer:
            if data:
                self.new_data.update(data)
            return

        flush = False
        if not data:
            data = self.new_data
            flush = True
        if data:
            self._context.get_data_cache().set_items(data)
            self._context.log_debug('Cached data for items:\n|{ids}|'
                                    .format(ids=list(data)))
        if flush:
            self.new_data = {}
