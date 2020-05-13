# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from ..youtube_exceptions import YouTubeException
from ...kodion.utils import FunctionCache, DataCache, strip_html_from_text


class ResourceManager(object):
    def __init__(self, context, youtube_client):
        self._context = context
        self._youtube_client = youtube_client
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
        result = dict()
        json_data = dict()
        channel_ids_to_update = list()
        channel_ids_cached = list()
        updated_channel_ids = list()

        data_cache = self._context.get_data_cache()
        function_cache = self._context.get_function_cache()

        for channel_id in channel_ids:
            if channel_id == 'mine':
                json_data = function_cache.get(FunctionCache.ONE_DAY, self._youtube_client.get_channel_by_username, channel_id)
                items = json_data.get('items', [{'id': 'mine'}])

                try:
                    channel_id = items[0]['id']
                except IndexError:
                    self._context.log_debug('Channel "mine" not found: %s' % json_data)
                    channel_id = None

                json_data = dict()

            if channel_id:
                updated_channel_ids.append(channel_id)

        channel_ids = updated_channel_ids

        channel_data = data_cache.get_items(DataCache.ONE_MONTH, channel_ids)
        for channel_id in channel_ids:
            if not channel_data.get(channel_id):
                channel_ids_to_update.append(channel_id)
            else:
                channel_ids_cached.append(channel_id)
        result.update(channel_data)
        if len(channel_ids_cached) > 0:
            self._context.log_debug('Found cached data for channels |%s|' % ', '.join(channel_ids_cached))

        if len(channel_ids_to_update) > 0:
            self._context.log_debug('No data for channels |%s| cached' % ', '.join(channel_ids_to_update))

            data = []
            list_of_50s = self._make_list_of_50(channel_ids_to_update)
            for list_of_50 in list_of_50s:
                data.append(self._youtube_client.get_channels(list_of_50))

            channel_data = dict()
            yt_items = []
            for response in data:
                yt_items += response.get('items', [])

            for yt_item in yt_items:
                channel_id = str(yt_item['id'])
                channel_data[channel_id] = yt_item
                result[channel_id] = yt_item

            data_cache.set_all(channel_data)
            self._context.log_debug('Cached data for channels |%s|' % ', '.join(list(channel_data.keys())))

        if self.handle_error(json_data):
            return result

        return result

    def _update_videos(self, video_ids, live_details=False, suppress_errors=False):
        result = dict()
        json_data = dict()
        video_ids_to_update = list()
        video_ids_cached = list()

        data_cache = self._context.get_data_cache()

        video_data = data_cache.get_items(DataCache.ONE_MONTH, video_ids)
        for video_id in video_ids:
            if not video_data.get(video_id):
                video_ids_to_update.append(video_id)
            else:
                video_ids_cached.append(video_id)
        result.update(video_data)
        if len(video_ids_cached) > 0:
            self._context.log_debug('Found cached data for videos |%s|' % ', '.join(video_ids_cached))

        if len(video_ids_to_update) > 0:
            self._context.log_debug('No data for videos |%s| cached' % ', '.join(video_ids_to_update))
            json_data = self._youtube_client.get_videos(video_ids_to_update, live_details)
            video_data = dict()
            yt_items = json_data.get('items', [])
            for yt_item in yt_items:
                video_id = str(yt_item['id'])
                video_data[video_id] = yt_item
                result[video_id] = yt_item
            data_cache.set_all(video_data)
            self._context.log_debug('Cached data for videos |%s|' % ', '.join(list(video_data.keys())))

        played_items = dict()
        if self._context.get_settings().use_playback_history():
            playback_history = self._context.get_playback_history()
            played_items = playback_history.get_items(video_ids)

        for k in list(result.keys()):
            result[k]['play_data'] = played_items.get(k, dict())

        if self.handle_error(json_data, suppress_errors) or suppress_errors:
            return result

    @staticmethod
    def _make_list_of_50(list_of_ids):
        list_of_50 = []
        pos = 0
        while pos < len(list_of_ids):
            list_of_50.append(list_of_ids[pos:pos + 50])
            pos += 50
        return list_of_50

    def get_videos(self, video_ids, live_details=False, suppress_errors=False):
        list_of_50s = self._make_list_of_50(video_ids)

        result = {}
        for list_of_50 in list_of_50s:
            result.update(self._update_videos(list_of_50, live_details, suppress_errors))
        return result

    def _update_playlists(self, playlists_ids):
        result = dict()
        json_data = dict()
        playlist_ids_to_update = list()
        playlists_ids_cached = list()

        data_cache = self._context.get_data_cache()

        playlist_data = data_cache.get_items(DataCache.ONE_MONTH, playlists_ids)
        for playlist_id in playlists_ids:
            if not playlist_data.get(playlist_id):
                playlist_ids_to_update.append(playlist_id)
            else:
                playlists_ids_cached.append(playlist_id)
        result.update(playlist_data)
        if len(playlists_ids_cached) > 0:
            self._context.log_debug('Found cached data for playlists |%s|' % ', '.join(playlists_ids_cached))

        if len(playlist_ids_to_update) > 0:
            self._context.log_debug('No data for playlists |%s| cached' % ', '.join(playlist_ids_to_update))
            json_data = self._youtube_client.get_playlists(playlist_ids_to_update)
            playlist_data = dict()
            yt_items = json_data.get('items', [])
            for yt_item in yt_items:
                playlist_id = str(yt_item['id'])
                playlist_data[playlist_id] = yt_item
                result[playlist_id] = yt_item
            data_cache.set_all(playlist_data)
            self._context.log_debug('Cached data for playlists |%s|' % ', '.join(list(playlist_data.keys())))

        if self.handle_error(json_data):
            return result

    def get_playlists(self, playlists_ids):
        list_of_50s = self._make_list_of_50(playlists_ids)

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
            for key in list(result.keys()):
                item = result[key]

        if item is None:
            return {}

        return item.get('contentDetails', {}).get('relatedPlaylists', {})

    def get_channels(self, channel_ids):
        list_of_50s = self._make_list_of_50(channel_ids)

        result = {}
        for list_of_50 in list_of_50s:
            result.update(self._update_channels(list_of_50))
        return result

    def get_fanarts(self, channel_ids):
        if not self._enable_channel_fanart:
            return {}

        result = self._update_channels(channel_ids)

        # transform
        for key in list(result.keys()):
            item = result[key]

            # set an empty url
            result[key] = u''
            images = item.get('brandingSettings', {}).get('image', {})
            banners = ['bannerTvMediumImageUrl', 'bannerTvLowImageUrl', 'bannerTvImageUrl']
            for banner in banners:
                image = images.get(banner, '')
                if image:
                    result[key] = image
                    break

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
                message = context.localize(30731)
                ok_dialog = True

            if reason == 'quotaExceeded' or reason == 'dailyLimitExceeded':
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
