# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..youtube_exceptions import YouTubeException
from ...kodion.utils import strip_html_from_text


class ResourceManager(object):
    def __init__(self, context, client):
        self._context = context
        self._client = client
        self._channel_data = {}
        self._video_data = {}
        self._playlist_data = {}
        self._enable_channel_fanart = context.get_settings().get_bool('youtube.channel.fanart.show', True)

    def clear(self):
        self._context.get_function_cache().clear()
        self._context.get_data_cache().clear()

    def _get_channel_data(self, channel_id):
        return self._channel_data.get(channel_id, {})

    def _get_video_data(self, video_id):
        return self._video_data.get(video_id, {})

    def _get_playlist_data(self, playlist_id):
        return self._playlist_data.get(playlist_id, {})

    def _update_channels(self, channel_ids):
        json_data = None
        updated_channel_ids = []
        function_cache = self._context.get_function_cache()

        for channel_id in channel_ids:
            if channel_id == 'mine':
                json_data = function_cache.get(self._client.get_channel_by_username,
                                               function_cache.ONE_DAY,
                                               channel_id)
                items = json_data.get('items', [{'id': 'mine'}])

                try:
                    channel_id = items[0]['id']
                except IndexError:
                    self._context.log_debug('Channel "mine" not found: %s' % json_data)
                    channel_id = None

                json_data = None

            if channel_id:
                updated_channel_ids.append(channel_id)

        channel_ids = updated_channel_ids

        data_cache = self._context.get_data_cache()
        channel_data = data_cache.get_items(channel_ids, data_cache.ONE_MONTH)

        channel_ids = set(channel_ids)
        channel_ids_cached = set(channel_data)
        channel_ids_to_update = channel_ids - channel_ids_cached
        channel_ids_cached = channel_ids & channel_ids_cached

        result = channel_data
        if channel_ids_cached:
            self._context.log_debug('Found cached data for channels |%s|' % ', '.join(channel_ids_cached))

        if channel_ids_to_update:
            self._context.log_debug('No data for channels |%s| cached' % ', '.join(channel_ids_to_update))
            json_data = [
                self._client.get_channels(list_of_50)
                for list_of_50 in self._list_batch(channel_ids_to_update, n=50)
            ]
            channel_data = {
                yt_item['id']: yt_item
                for batch in json_data
                for yt_item in batch.get('items', [])
                if yt_item
            }
            result.update(channel_data)
            data_cache.set_items(channel_data)
            self._context.log_debug('Cached data for channels |%s|' % ', '.join(channel_data))

        if self.handle_error(json_data):
            return result
        return {}

    def _update_videos(self, video_ids, live_details=False, suppress_errors=False):
        json_data = None
        data_cache = self._context.get_data_cache()
        video_data = data_cache.get_items(video_ids, data_cache.ONE_MONTH)

        video_ids = set(video_ids)
        video_ids_cached = set(video_data)
        video_ids_to_update = video_ids - video_ids_cached
        video_ids_cached = video_ids & video_ids_cached

        result = video_data
        if video_ids_cached:
            self._context.log_debug('Found cached data for videos |%s|' % ', '.join(video_ids_cached))

        if video_ids_to_update:
            self._context.log_debug('No data for videos |%s| cached' % ', '.join(video_ids_to_update))
            json_data = self._client.get_videos(video_ids_to_update, live_details)
            video_data = dict.fromkeys(video_ids_to_update, {})
            video_data.update({
                yt_item['id']: yt_item or {}
                for yt_item in json_data.get('items', [])
            })
            result.update(video_data)
            data_cache.set_items(video_data)
            self._context.log_debug('Cached data for videos |%s|' % ', '.join(video_data))

        if self._context.get_settings().use_local_history():
            playback_history = self._context.get_playback_history()
            played_items = playback_history.get_items(video_ids)
            for video_id, play_data in played_items.items():
                result[video_id]['play_data'] = play_data

        if self.handle_error(json_data, suppress_errors) or suppress_errors:
            return result
        return {}

    @staticmethod
    def _list_batch(input_list, n=50):
        if not isinstance(input_list, (list, tuple)):
            input_list = list(input_list)
        for i in range(0, len(input_list), n):
            yield input_list[i:i + n]

    def get_videos(self, video_ids, live_details=False, suppress_errors=False):
        list_of_50s = self._list_batch(video_ids, n=50)

        result = {}
        for list_of_50 in list_of_50s:
            result.update(self._update_videos(list_of_50, live_details, suppress_errors))
        return result

    def _update_playlists(self, playlists_ids):
        json_data = None
        data_cache = self._context.get_data_cache()
        playlist_data = data_cache.get_items(playlists_ids, data_cache.ONE_MONTH)

        playlists_ids = set(playlists_ids)
        playlists_ids_cached = set(playlist_data)
        playlist_ids_to_update = playlists_ids - playlists_ids_cached
        playlists_ids_cached = playlists_ids & playlists_ids_cached

        result = playlist_data
        if playlists_ids_cached:
            self._context.log_debug('Found cached data for playlists |%s|' % ', '.join(playlists_ids_cached))

        if playlist_ids_to_update:
            self._context.log_debug('No data for playlists |%s| cached' % ', '.join(playlist_ids_to_update))
            json_data = self._client.get_playlists(playlist_ids_to_update)
            playlist_data = {
                yt_item['id']: yt_item
                for yt_item in json_data.get('items', [])
                if yt_item
            }
            result.update(playlist_data)
            data_cache.set_items(playlist_data)
            self._context.log_debug('Cached data for playlists |%s|' % ', '.join(playlist_data))

        if self.handle_error(json_data):
            return result
        return {}

    def get_playlists(self, playlists_ids):
        list_of_50s = self._list_batch(playlists_ids, n=50)

        result = {}
        for list_of_50 in list_of_50s:
            result.update(self._update_playlists(list_of_50))
        return result

    def get_related_playlists(self, channel_id):
        result = self._update_channels([channel_id])

        # transform
        item = None
        if channel_id != 'mine':
            item = result.get(channel_id, {})
        else:
            for item in result.values():
                if item:
                    break

        if item is None:
            return {}

        return item.get('contentDetails', {}).get('relatedPlaylists', {})

    def get_channels(self, channel_ids):
        list_of_50s = self._list_batch(channel_ids, n=50)

        result = {}
        for list_of_50 in list_of_50s:
            result.update(self._update_channels(list_of_50))
        return result

    def get_fanarts(self, channel_ids):
        if not self._enable_channel_fanart:
            return {}

        result = self._update_channels(channel_ids)
        banners = ['bannerTvMediumImageUrl', 'bannerTvLowImageUrl',
                   'bannerTvImageUrl', 'bannerExternalUrl']
        # transform
        for key, item in result.items():
            images = item.get('brandingSettings', {}).get('image', {})
            for banner in banners:
                image = images.get(banner)
                if not image:
                    continue
                result[key] = image
                break
            else:
                # set an empty url
                result[key] = ''

        return result

    def handle_error(self, json_data, suppress_errors=False):
        context = self._context
        if json_data and 'error' in json_data:
            ok_dialog = False
            message_timeout = 5000
            message = json_data['error'].get('message', '')
            message = strip_html_from_text(message)
            reason = json_data['error']['errors'][0].get('reason', '')
            title = '%s: %s' % (context.get_name(), reason)
            error_message = 'Error reason: |%s| with message: |%s|' % (reason, message)

            context.log_error(error_message)

            if reason == 'accessNotConfigured':
                message = context.localize('key.requirement.notification')
                ok_dialog = True

            elif reason in {'quotaExceeded', 'dailyLimitExceeded'}:
                message_timeout = 7000

            if not suppress_errors:
                if ok_dialog:
                    context.get_ui().on_ok(title, message)
                else:
                    context.get_ui().show_notification(message, title,
                                                       time_milliseconds=message_timeout)

                raise YouTubeException(error_message)

            return False

        return True
