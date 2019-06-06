# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import copy
import traceback

import requests

from .login_client import LoginClient
from ..helper.video_info import VideoInfo
from ..helper.utils import get_shelf_index_by_title
from ...kodion import constants
from ...kodion import Context

_context = Context(plugin_id='plugin.video.youtube')


class YouTube(LoginClient):
    def __init__(self, config=None, language='en-US', region='US', items_per_page=50, access_token='', access_token_tv=''):
        if config is None:
            config = {}
        LoginClient.__init__(self, config=config, language=language, region=region, access_token=access_token,
                             access_token_tv=access_token_tv)

        self._max_results = items_per_page

    def get_max_results(self):
        return self._max_results

    def get_language(self):
        return self._language

    def get_region(self):
        return self._region

    @staticmethod
    def calculate_next_page_token(page, max_result):
        page -= 1
        low = 'AEIMQUYcgkosw048'
        high = 'ABCDEFGHIJKLMNOP'
        len_low = len(low)
        len_high = len(high)

        position = page * max_result

        overflow_token = 'Q'
        if position >= 128:
            overflow_token_iteration = position // 128
            overflow_token = '%sE' % high[overflow_token_iteration]
        low_iteration = position % len_low

        # at this position the iteration starts with 'I' again (after 'P')
        if position >= 256:
            multiplier = (position // 128) - 1
            position -= 128 * multiplier
        high_iteration = (position // len_low) % len_high

        return 'C%s%s%sAA' % (high[high_iteration], low[low_iteration], overflow_token)

    def update_watch_history(self, video_id, url):
        headers = {'Host': 'www.youtube.com',
                   'Connection': 'keep-alive',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
                   'Accept': 'image/webp,*/*;q=0.8',
                   'DNT': '1',
                   'Referer': 'https://www.youtube.com/tv',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}
        params = {'noflv': '1',
                  'html5': '1',
                  'video_id': video_id,
                  'referrer': '',
                  'eurl': 'https://www.youtube.com/tv#/watch?v=%s' % video_id,
                  'skl': 'false',
                  'ns': 'yt',
                  'el': 'leanback',
                  'ps': 'leanback'}
        if self._access_token:
            params['access_token'] = self._access_token

        try:
            _ = requests.get(url, params=params, headers=headers, verify=self._verify, allow_redirects=True)
        except:
            _context.log_error('Failed to update watch history |%s|' % traceback.print_exc())

    def get_video_streams(self, context, video_id=None, player_config=None, cookies=None):
        video_info = VideoInfo(context, access_token=self._access_token, language=self._language)

        video_streams = video_info.load_stream_infos(video_id, player_config, cookies)

        # update title
        for video_stream in video_streams:
            title = '%s (%s)' % (context.get_ui().bold(video_stream['title']), video_stream['container'])

            if 'audio' in video_stream and 'video' in video_stream:
                if video_stream['audio']['bitrate'] > 0 and video_stream['video']['encoding'] and \
                        video_stream['audio']['encoding']:
                    title = '%s (%s; %s / %s@%d)' % (context.get_ui().bold(video_stream['title']),
                                                     video_stream['container'],
                                                     video_stream['video']['encoding'],
                                                     video_stream['audio']['encoding'],
                                                     video_stream['audio']['bitrate'])

                elif video_stream['video']['encoding'] and video_stream['audio']['encoding']:
                    title = '%s (%s; %s / %s)' % (context.get_ui().bold(video_stream['title']),
                                                  video_stream['container'],
                                                  video_stream['video']['encoding'],
                                                  video_stream['audio']['encoding'])
            elif 'audio' in video_stream and 'video' not in video_stream:
                if video_stream['audio']['encoding'] and video_stream['audio']['bitrate'] > 0:
                    title = '%s (%s; %s@%d)' % (context.get_ui().bold(video_stream['title']),
                                                video_stream['container'],
                                                video_stream['audio']['encoding'],
                                                video_stream['audio']['bitrate'])

            elif 'audio' in video_stream or 'video' in video_stream:
                encoding = video_stream.get('audio', dict()).get('encoding')
                if not encoding:
                    encoding = video_stream.get('video', dict()).get('encoding')
                if encoding:
                    title = '%s (%s; %s)' % (context.get_ui().bold(video_stream['title']),
                                             video_stream['container'],
                                             encoding)

            video_stream['title'] = title

        return video_streams

    def remove_playlist(self, playlist_id):
        params = {'id': playlist_id,
                  'mine': 'true'}
        return self.perform_v3_request(method='DELETE', path='playlists', params=params)

    def get_supported_languages(self, language=None):
        _language = language
        if not _language:
            _language = self._language
        _language = _language.replace('-', '_')
        params = {'part': 'snippet',
                  'hl': _language}
        return self.perform_v3_request(method='GET', path='i18nLanguages', params=params)

    def get_supported_regions(self, language=None):
        _language = language
        if not _language:
            _language = self._language
        _language = _language.replace('-', '_')
        params = {'part': 'snippet',
                  'hl': _language}
        return self.perform_v3_request(method='GET', path='i18nRegions', params=params)

    def rename_playlist(self, playlist_id, new_title, privacy_status='private'):
        params = {'part': 'snippet,id,status'}
        post_data = {'kind': 'youtube#playlist',
                     'id': playlist_id,
                     'snippet': {'title': new_title},
                     'status': {'privacyStatus': privacy_status}}
        return self.perform_v3_request(method='PUT', path='playlists', params=params, post_data=post_data)

    def create_playlist(self, title, privacy_status='private'):
        params = {'part': 'snippet,status'}
        post_data = {'kind': 'youtube#playlist',
                     'snippet': {'title': title},
                     'status': {'privacyStatus': privacy_status}}
        return self.perform_v3_request(method='POST', path='playlists', params=params, post_data=post_data)

    def get_video_rating(self, video_id):
        if isinstance(video_id, list):
            video_id = ','.join(video_id)

        params = {'id': video_id}
        return self.perform_v3_request(method='GET', path='videos/getRating', params=params)

    def rate_video(self, video_id, rating='like'):
        """
        Rate a video
        :param video_id: if of the video
        :param rating: [like|dislike|none]
        :return:
        """
        params = {'id': video_id,
                  'rating': rating}
        return self.perform_v3_request(method='POST', path='videos/rate', params=params)

    def add_video_to_playlist(self, playlist_id, video_id):
        params = {'part': 'snippet',
                  'mine': 'true'}
        post_data = {'kind': 'youtube#playlistItem',
                     'snippet': {'playlistId': playlist_id,
                                 'resourceId': {'kind': 'youtube#video',
                                                'videoId': video_id}}}
        return self.perform_v3_request(method='POST', path='playlistItems', params=params, post_data=post_data)

    # noinspection PyUnusedLocal
    def remove_video_from_playlist(self, playlist_id, playlist_item_id):
        params = {'id': playlist_item_id}
        return self.perform_v3_request(method='DELETE', path='playlistItems', params=params)

    def unsubscribe(self, subscription_id):
        params = {'id': subscription_id}
        return self.perform_v3_request(method='DELETE', path='subscriptions', params=params)

    def subscribe(self, channel_id):
        params = {'part': 'snippet'}
        post_data = {'kind': 'youtube#subscription',
                     'snippet': {'resourceId': {'kind': 'youtube#channel',
                                                'channelId': channel_id}}}
        return self.perform_v3_request(method='POST', path='subscriptions', params=params, post_data=post_data)

    def get_subscription(self, channel_id, order='alphabetical', page_token=''):
        """

        :param channel_id: [channel-id|'mine']
        :param order: ['alphabetical'|'relevance'|'unread']
        :param page_token:
        :return:
        """
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results),
                  'order': order}
        if channel_id == 'mine':
            params['mine'] = 'true'
        else:
            params['channelId'] = channel_id
        if page_token:
            params['pageToken'] = page_token

        return self.perform_v3_request(method='GET', path='subscriptions', params=params)

    def get_guide_category(self, guide_category_id, page_token=''):
        params = {'part': 'snippet,contentDetails,brandingSettings',
                  'maxResults': str(self._max_results),
                  'categoryId': guide_category_id,
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token
        return self.perform_v3_request(method='GET', path='channels', params=params)

    def get_guide_categories(self, page_token=''):
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token

        return self.perform_v3_request(method='GET', path='guideCategories', params=params)

    def get_popular_videos(self, page_token=''):
        params = {'part': 'snippet,status',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language,
                  'chart': 'mostPopular'}
        if page_token:
            params['pageToken'] = page_token
        return self.perform_v3_request(method='GET', path='videos', params=params)

    def get_video_category(self, video_category_id, page_token=''):
        params = {'part': 'snippet,contentDetails,status',
                  'maxResults': str(self._max_results),
                  'videoCategoryId': video_category_id,
                  'chart': 'mostPopular',
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token
        return self.perform_v3_request(method='GET', path='videos', params=params)

    def get_video_categories(self, page_token=''):
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token

        return self.perform_v3_request(method='GET', path='videoCategories', params=params)

    def get_activities(self, channel_id, page_token=''):
        params = {'part': 'snippet,contentDetails',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language}
        if channel_id == 'home':
            params['home'] = 'true'
        elif channel_id == 'mine':
            params['mine'] = 'true'
        else:
            params['channelId'] = channel_id
        if page_token:
            params['pageToken'] = page_token

        return self.perform_v3_request(method='GET', path='activities', params=params)

    def get_channel_sections(self, channel_id):
        params = {'part': 'snippet,contentDetails',
                  'regionCode': self._region,
                  'hl': self._language}
        if channel_id == 'mine':
            params['mine'] = 'true'
        else:
            params['channelId'] = channel_id
        return self.perform_v3_request(method='GET', path='channelSections', params=params)

    def get_playlists_of_channel(self, channel_id, page_token=''):
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results)}
        if channel_id != 'mine':
            params['channelId'] = channel_id
        else:
            params['mine'] = 'true'
        if page_token:
            params['pageToken'] = page_token

        return self.perform_v3_request(method='GET', path='playlists', params=params)

    def get_playlist_item_id_of_video_id(self, playlist_id, video_id, page_token=''):
        old_max_results = self._max_results
        self._max_results = 50
        json_data = self.get_playlist_items(playlist_id=playlist_id, page_token=page_token)
        self._max_results = old_max_results

        items = json_data.get('items', [])
        for item in items:
            playlist_item_id = item['id']
            playlist_video_id = item.get('snippet', {}).get('resourceId', {}).get('videoId', '')
            if playlist_video_id and playlist_video_id == video_id:
                return playlist_item_id

        next_page_token = json_data.get('nextPageToken', '')
        if next_page_token:
            return self.get_playlist_item_id_of_video_id(playlist_id=playlist_id, video_id=video_id,
                                                         page_token=next_page_token)

        return None

    def get_playlist_items(self, playlist_id, page_token='', max_results=None):
        # prepare params
        max_results = str(self._max_results) if max_results is None else str(max_results)
        params = {'part': 'snippet',
                  'maxResults': max_results,
                  'playlistId': playlist_id}
        if page_token:
            params['pageToken'] = page_token

        return self.perform_v3_request(method='GET', path='playlistItems', params=params)

    def get_channel_by_username(self, username):
        """
        Returns a collection of zero or more channel resources that match the request criteria.
        :param username: retrieve channel_id for username
        :return:
        """
        params = {'part': 'id'}
        if username == 'mine':
            params.update({'mine': 'true'})
        else:
            params.update({'forUsername': username})

        return self.perform_v3_request(method='GET', path='channels', params=params)

    def get_channels(self, channel_id):
        """
        Returns a collection of zero or more channel resources that match the request criteria.
        :param channel_id: list or comma-separated list of the YouTube channel ID(s)
        :return:
        """
        if isinstance(channel_id, list):
            channel_id = ','.join(channel_id)

        params = {'part': 'snippet,contentDetails,brandingSettings'}
        if channel_id != 'mine':
            params['id'] = channel_id
        else:
            params['mine'] = 'true'
        return self.perform_v3_request(method='GET', path='channels', params=params)

    def get_disliked_videos(self, page_token=''):
        # prepare page token
        if not page_token:
            page_token = ''

        # prepare params
        params = {'part': 'snippet,status',
                  'myRating': 'dislike',
                  'maxResults': str(self._max_results)}
        if page_token:
            params['pageToken'] = page_token

        return self.perform_v3_request(method='GET', path='videos', params=params)

    def get_videos(self, video_id, live_details=False):
        """
        Returns a list of videos that match the API request parameters
        :param video_id: list of video ids
        :param live_details: also retrieve liveStreamingDetails
        :return:
        """
        if isinstance(video_id, list):
            video_id = ','.join(video_id)

        parts = ['snippet,contentDetails,status']
        if live_details:
            parts.append(',liveStreamingDetails')

        params = {'part': ''.join(parts),
                  'id': video_id}
        return self.perform_v3_request(method='GET', path='videos', params=params)

    def get_playlists(self, playlist_id):
        if isinstance(playlist_id, list):
            playlist_id = ','.join(playlist_id)

        params = {'part': 'snippet,contentDetails',
                  'id': playlist_id}
        return self.perform_v3_request(method='GET', path='playlists', params=params)

    def get_live_events(self, event_type='live', order='relevance', page_token='', location=False):
        """

        :param event_type: one of: 'live', 'completed', 'upcoming'
        :param order: one of: 'date', 'rating', 'relevance', 'title', 'videoCount', 'viewCount'
        :param page_token:
        :param location: bool, use geolocation
        :return:
        """
        # prepare page token
        if not page_token:
            page_token = ''

        # prepare params
        params = {'part': 'snippet',
                  'type': 'video',
                  'order': order,
                  'eventType': event_type,
                  'regionCode': self._region,
                  'hl': self._language,
                  'relevanceLanguage': self._language,
                  'maxResults': str(self._max_results)}

        if location:
            location = _context.get_settings().get_location()
            if location:
                params['location'] = location
                params['locationRadius'] = _context.get_settings().get_location_radius()

        if page_token:
            params['pageToken'] = page_token

        return self.perform_v3_request(method='GET', path='search', params=params)

    def get_related_videos(self, video_id, page_token='', max_results=0):
        # prepare page token
        if not page_token:
            page_token = ''

        max_results = self._max_results if max_results <= 0 else max_results

        # prepare params
        params = {'relatedToVideoId': video_id,
                  'part': 'snippet',
                  'type': 'video',
                  'regionCode': self._region,
                  'hl': self._language,
                  'maxResults': str(max_results)}
        if page_token:
            params['pageToken'] = page_token

        return self.perform_v3_request(method='GET', path='search', params=params)

    def get_channel_videos(self, channel_id, page_token=''):
        """
        Returns a collection of video search results for the specified channel_id
        """

        params = {'part': 'snippet',
                  'hl': self._language,
                  'maxResults': str(self._max_results),
                  'type': 'video',
                  'safeSearch': 'none',
                  'order': 'date'}

        if channel_id == 'mine':
            params['forMine'] = 'true'
        else:
            params['channelId'] = channel_id

        if page_token:
            params['pageToken'] = page_token

        return self.perform_v3_request(method='GET', path='search', params=params)

    def search(self, q, search_type=None, event_type='', channel_id='',
               order='relevance', safe_search='moderate', page_token='', location=False):
        """
        Returns a collection of search results that match the query parameters specified in the API request. By default,
        a search result set identifies matching video, channel, and playlist resources, but you can also configure
        queries to only retrieve a specific type of resource.
        :param q:
        :param search_type: acceptable values are: 'video' | 'channel' | 'playlist'
        :param event_type: 'live', 'completed', 'upcoming'
        :param channel_id: limit search to channel id
        :param order: one of: 'date', 'rating', 'relevance', 'title', 'videoCount', 'viewCount'
        :param safe_search: one of: 'moderate', 'none', 'strict'
        :param page_token: can be ''
        :param location: bool, use geolocation
        :return:
        """

        if search_type is None:
            search_type = ['video', 'channel', 'playlist']

        # prepare search type
        if not search_type:
            search_type = ''
        if isinstance(search_type, list):
            search_type = ','.join(search_type)

        # prepare page token
        if not page_token:
            page_token = ''

        # prepare params
        params = {'q': q,
                  'part': 'snippet',
                  'regionCode': self._region,
                  'hl': self._language,
                  'relevanceLanguage': self._language,
                  'maxResults': str(self._max_results)}

        if event_type and event_type in ['live', 'upcoming', 'completed']:
            params['eventType'] = event_type
        if search_type:
            params['type'] = search_type
        if channel_id:
            params['channelId'] = channel_id
        if order:
            params['order'] = order
        if safe_search:
            params['safeSearch'] = safe_search
        if page_token:
            params['pageToken'] = page_token

        video_only_params = ['eventType', 'videoCaption', 'videoCategoryId', 'videoDefinition',
                             'videoDimension', 'videoDuration', 'videoEmbeddable', 'videoLicense',
                             'videoSyndicated', 'videoType', 'relatedToVideoId', 'forMine']
        for key in video_only_params:
            if params.get(key) is not None:
                params['type'] = 'video'
                break

        if params['type'] == 'video' and location:
            location = _context.get_settings().get_location()
            if location:
                params['location'] = location
                params['locationRadius'] = _context.get_settings().get_location_radius()

        return self.perform_v3_request(method='GET', path='search', params=params)

    def get_my_subscriptions(self, page_token=None, offset=0):
        if not page_token:
            page_token = ''

        result = {'items': [],
                  'next_page_token': page_token,
                  'offset': offset}

        def _perform(_page_token, _offset, _result):
            _post_data = {
                'context': {
                    'client': {
                        'clientName': 'TVHTML5',
                        'clientVersion': '5.20150304',
                        'theme': 'CLASSIC',
                        'acceptRegion': '%s' % self._region,
                        'acceptLanguage': '%s' % self._language.replace('_', '-')
                    },
                    'user': {
                        'enableSafetyMode': False
                    }
                },
                'browseId': 'FEsubscriptions'
            }
            if _page_token:
                _post_data['continuation'] = _page_token

            _json_data = self.perform_v1_tv_request(method='POST', path='browse', post_data=_post_data)
            _data = _json_data.get('contents', {}).get('sectionListRenderer', {}).get('contents', [{}])[0].get(
                'shelfRenderer', {}).get('content', {}).get('horizontalListRenderer', {})
            if not _data:
                _data = _json_data.get('continuationContents', {}).get('horizontalListContinuation', {})
            _items = _data.get('items', [])
            if not _result:
                _result = {'items': []}

            _new_offset = self._max_results - len(_result['items']) + _offset
            if _offset > 0:
                _items = _items[_offset:]
            _result['offset'] = _new_offset

            for _item in _items:
                _item = _item.get('gridVideoRenderer', {})
                if _item:
                    _video_item = {'id': _item['videoId'],
                                   'title': _item.get('title', {}).get('runs', [{}])[0].get('text', ''),
                                   'channel': _item.get('shortBylineText', {}).get('runs', [{}])[0].get('text', '')}
                    _result['items'].append(_video_item)

            _continuations = _data.get('continuations', [{}])[0].get('nextContinuationData', {}).get('continuation', '')
            if _continuations and len(_result['items']) <= self._max_results:
                _result['next_page_token'] = _continuations

                if len(_result['items']) < self._max_results:
                    _result = _perform(_page_token=_continuations, _offset=0, _result=_result)

            # trim result
            if len(_result['items']) > self._max_results:
                _items = _result['items']
                _items = _items[:self._max_results]
                _result['items'] = _items
                _result['continue'] = True

            if 'offset' in _result and _result['offset'] >= 100:
                _result['offset'] -= 100

            if len(_result['items']) < self._max_results:
                if 'continue' in _result:
                    del _result['continue']

                if 'next_page_token' in _result:
                    del _result['next_page_token']

                if 'offset' in _result:
                    del _result['offset']
            return _result

        return _perform(_page_token=page_token, _offset=offset, _result=result)

    def get_purchases(self, page_token, offset):
        if not page_token:
            page_token = ''

        shelf_title = 'Purchases'

        result = {'items': [],
                  'next_page_token': page_token,
                  'offset': offset}

        def _perform(_page_token, _offset, _result, _shelf_index=None):
            _post_data = {
                'context': {
                    'client': {
                        'clientName': 'TVHTML5',
                        'clientVersion': '5.20150304',
                        'theme': 'CLASSIC',
                        'acceptRegion': '%s' % self._region,
                        'acceptLanguage': '%s' % self._language.replace('_', '-')
                    },
                    'user': {
                        'enableSafetyMode': False
                    }
                }
            }
            if _page_token:
                _post_data['continuation'] = _page_token
            else:
                _post_data['browseId'] = 'FEmy_youtube'

            _json_data = self.perform_v1_tv_request(method='POST', path='browse', post_data=_post_data)

            _data = {}
            if 'continuationContents' in _json_data:
                _data = _json_data.get('continuationContents', {}).get('horizontalListContinuation', {})
            elif 'contents' in _json_data:
                _contents = _json_data.get('contents', {}).get('sectionListRenderer', {}).get('contents', [{}])

                if _shelf_index is None:
                    _shelf_index = get_shelf_index_by_title(_context, _json_data, shelf_title)

                if _shelf_index is not None:
                    _data = _contents[_shelf_index].get('shelfRenderer', {}).get('content', {}).get('horizontalListRenderer', {})

            _items = _data.get('items', [])
            if not _result:
                _result = {'items': []}

            _new_offset = self._max_results - len(_result['items']) + _offset
            if _offset > 0:
                _items = _items[_offset:]
            _result['offset'] = _new_offset

            for _listItem in _items:
                _item = _listItem.get('gridVideoRenderer', {})
                if _item:
                    _video_item = {'id': _item['videoId'],
                                   'title': _item.get('title', {}).get('runs', [{}])[0].get('text', ''),
                                   'channel': _item.get('shortBylineText', {}).get('runs', [{}])[0].get('text', '')}
                    _result['items'].append(_video_item)
                _item = _listItem.get('gridPlaylistRenderer', {})
                if _item:
                    play_next_page_token = ''
                    while True:
                        json_playlist_data = self.get_playlist_items(_item['playlistId'], page_token=play_next_page_token)
                        _playListItems = json_playlist_data.get('items', {})
                        for _playListItem in _playListItems:
                            _playListItem = _playListItem.get('snippet', {})
                            if _playListItem:
                                _video_item = {'id': _playListItem.get('resourceId', {}).get('videoId', ''),
                                               'title': _playListItem['title'],
                                               'channel': _item.get('shortBylineText', {}).get('runs', [{}])[0].get('text', '')}
                                _result['items'].append(_video_item)
                        play_next_page_token = json_playlist_data.get('nextPageToken', '')
                        if not play_next_page_token or _context.abort_requested():
                            break

            _continuations = _data.get('continuations', [{}])[0].get('nextContinuationData', {}).get('continuation', '')
            if _continuations and len(_result['items']) <= self._max_results:
                _result['next_page_token'] = _continuations

                if len(_result['items']) < self._max_results:
                    _result = _perform(_page_token=_continuations, _offset=0, _result=_result, _shelf_index=shelf_index)

            # trim result
            if len(_result['items']) > self._max_results:
                _items = _result['items']
                _items = _items[:self._max_results]
                _result['items'] = _items
                _result['continue'] = True

            if len(_result['items']) < self._max_results:
                if 'continue' in _result:
                    del _result['continue']

                if 'next_page_token' in _result:
                    del _result['next_page_token']

                if 'offset' in _result:
                    del _result['offset']

            return _result

        shelf_index = None
        if self._language != 'en' and not self._language.startswith('en-') and not page_token:
            #  shelf index is a moving target, make a request in english first to find the correct index by title
            _en_post_data = {
                'context': {
                    'client': {
                        'clientName': 'TVHTML5',
                        'clientVersion': '5.20150304',
                        'theme': 'CLASSIC',
                        'acceptRegion': 'US',
                        'acceptLanguage': 'en-US'
                    },
                    'user': {
                        'enableSafetyMode': False
                    }
                },
                'browseId': 'FEmy_youtube'
            }

            json_data = self.perform_v1_tv_request(method='POST', path='browse', post_data=_en_post_data)
            shelf_index = get_shelf_index_by_title(_context, json_data, shelf_title)

        result = _perform(_page_token=page_token, _offset=offset, _result=result, _shelf_index=shelf_index)

        return result

    def get_saved_playlists(self, page_token, offset):
        if not page_token:
            page_token = ''

        shelf_title = 'Saved Playlists'

        result = {'items': [],
                  'next_page_token': page_token,
                  'offset': offset}

        def _perform(_page_token, _offset, _result, _shelf_index=None):
            _post_data = {
                'context': {
                    'client': {
                        'clientName': 'TVHTML5',
                        'clientVersion': '5.20150304',
                        'theme': 'CLASSIC',
                        'acceptRegion': '%s' % self._region,
                        'acceptLanguage': '%s' % self._language.replace('_', '-')
                    },
                    'user': {
                        'enableSafetyMode': False
                    }
                }
            }
            if _page_token:
                _post_data['continuation'] = _page_token
            else:
                _post_data['browseId'] = 'FEmy_youtube'

            _json_data = self.perform_v1_tv_request(method='POST', path='browse', post_data=_post_data)
            _data = {}
            if 'continuationContents' in _json_data:
                _data = _json_data.get('continuationContents', {}).get('horizontalListContinuation', {})
            elif 'contents' in _json_data:
                _contents = _json_data.get('contents', {}).get('sectionListRenderer', {}).get('contents', [{}])

                if _shelf_index is None:
                    _shelf_index = get_shelf_index_by_title(_context, _json_data, shelf_title)

                if _shelf_index is not None:
                    _data = _contents[_shelf_index].get('shelfRenderer', {}).get('content', {}).get('horizontalListRenderer', {})

            _items = _data.get('items', [])
            if not _result:
                _result = {'items': []}

            _new_offset = self._max_results - len(_result['items']) + _offset
            if _offset > 0:
                _items = _items[_offset:]
            _result['offset'] = _new_offset

            for _item in _items:
                _item = _item.get('gridPlaylistRenderer', {})
                if _item:
                    _video_item = {'id': _item['playlistId'],
                                   'title': _item.get('title', {}).get('runs', [{}])[0].get('text', ''),
                                   'channel': _item.get('shortBylineText', {}).get('runs', [{}])[0].get('text', ''),
                                   'channel_id': _item.get('shortBylineText', {}).get('runs', [{}])[0].get('navigationEndpoint', {}).get('browseEndpoint', {}).get('browseId', ''),
                                   'thumbnails': {'default': {'url': ''}, 'medium': {'url': ''}, 'high': {'url': ''}}}

                    _thumbs = _item.get('thumbnail', {}).get('thumbnails', [{}])

                    for _thumb in _thumbs:
                        _thumb_url = _thumb.get('url', '')
                        if _thumb_url.startswith('//'):
                            _thumb_url = ''.join(['https:', _thumb_url])
                        if _thumb_url.endswith('/default.jpg'):
                            _video_item['thumbnails']['default']['url'] = _thumb_url
                        elif _thumb_url.endswith('/mqdefault.jpg'):
                            _video_item['thumbnails']['medium']['url'] = _thumb_url
                        elif _thumb_url.endswith('/hqdefault.jpg'):
                            _video_item['thumbnails']['high']['url'] = _thumb_url

                    _result['items'].append(_video_item)

            _continuations = _data.get('continuations', [{}])[0].get('nextContinuationData', {}).get('continuation', '')
            if _continuations and len(_result['items']) <= self._max_results:
                _result['next_page_token'] = _continuations

                if len(_result['items']) < self._max_results:
                    _result = _perform(_page_token=_continuations, _offset=0, _result=_result, _shelf_index=_shelf_index)

            # trim result
            if len(_result['items']) > self._max_results:
                _items = _result['items']
                _items = _items[:self._max_results]
                _result['items'] = _items
                _result['continue'] = True

            if len(_result['items']) < self._max_results:
                if 'continue' in _result:
                    del _result['continue']

                if 'next_page_token' in _result:
                    del _result['next_page_token']

                if 'offset' in _result:
                    del _result['offset']

            return _result

        shelf_index = None
        if self._language != 'en' and not self._language.startswith('en-') and not page_token:
            #  shelf index is a moving target, make a request in english first to find the correct index by title
            _en_post_data = {
                'context': {
                    'client': {
                        'clientName': 'TVHTML5',
                        'clientVersion': '5.20150304',
                        'theme': 'CLASSIC',
                        'acceptRegion': 'US',
                        'acceptLanguage': 'en-US'
                    },
                    'user': {
                        'enableSafetyMode': False
                    }
                },
                'browseId': 'FEmy_youtube'
            }

            json_data = self.perform_v1_tv_request(method='POST', path='browse', post_data=_en_post_data)
            shelf_index = get_shelf_index_by_title(_context, json_data, shelf_title)

        result = _perform(_page_token=page_token, _offset=offset, _result=result, _shelf_index=shelf_index)

        return result

    def clear_watch_history(self):
        _post_data = {
            'context': {
                'client': {
                    'clientName': 'TVHTML5',
                    'clientVersion': '5.20150304',
                    'theme': 'CLASSIC',
                    'acceptRegion': '%s' % self._region,
                    'acceptLanguage': '%s' % self._language.replace('_', '-')
                },
                'user': {
                    'enableSafetyMode': False
                }
            }
        }
        _json_data = self.perform_v1_tv_request(method='POST', path='history/clear_watch_history', post_data=_post_data)
        return _json_data

    def get_watch_history(self, page_token=None, offset=0):
        if not page_token:
            page_token = ''

        result = {'items': [],
                  'next_page_token': page_token,
                  'offset': offset}

        def _perform(_page_token, _offset, _result):
            _post_data = {
                'context': {
                    'client': {
                        'clientName': 'TVHTML5',
                        'clientVersion': '5.20150304',
                        'theme': 'CLASSIC',
                        'acceptRegion': '%s' % self._region,
                        'acceptLanguage': '%s' % self._language.replace('_', '-')
                    },
                    'user': {
                        'enableSafetyMode': False
                    }
                },
                'browseId': 'FEhistory'
            }
            if _page_token:
                _post_data['continuation'] = _page_token

            _json_data = self.perform_v1_tv_request(method='POST', path='browse', post_data=_post_data)
            _data = _json_data.get('contents', {}).get('sectionListRenderer', {}).get('contents', [{}])[0].get(
                'shelfRenderer', {}).get('content', {}).get('horizontalListRenderer', {})
            if not _data:
                _data = _json_data.get('continuationContents', {}).get('horizontalListContinuation', {})
            _items = _data.get('items', [])
            if not _result:
                _result = {'items': []}

            _new_offset = self._max_results - len(_result['items']) + _offset
            if _offset > 0:
                _items = _items[_offset:]
            _result['offset'] = _new_offset

            for _item in _items:
                _item = _item.get('gridVideoRenderer', {})
                if _item:
                    _video_item = {'id': _item['videoId'],
                                   'title': _item.get('title', {}).get('runs', [{}])[0].get('text', ''),
                                   'channel': _item.get('shortBylineText', {}).get('runs', [{}])[0].get('text', '')}
                    _result['items'].append(_video_item)

            _continuations = _data.get('continuations', [{}])[0].get('nextContinuationData', {}).get('continuation', '')
            if _continuations and len(_result['items']) <= self._max_results:
                _result['next_page_token'] = _continuations

                if len(_result['items']) < self._max_results:
                    _result = _perform(_page_token=_continuations, _offset=0, _result=_result)

            # trim result
            if len(_result['items']) > self._max_results:
                _items = _result['items']
                _items = _items[:self._max_results]
                _result['items'] = _items
                _result['continue'] = True

            if len(_result['items']) < self._max_results:
                if 'continue' in _result:
                    del _result['continue']

                if 'next_page_token' in _result:
                    del _result['next_page_token']

                if 'offset' in _result:
                    del _result['offset']
            return _result

        return _perform(_page_token=page_token, _offset=offset, _result=result)

    def get_watch_later_id(self):
        watch_later_id = ''

        def _get_items(_continuation=None):
            post_data = {
                'context': {
                    'client': {
                        'clientName': 'TVHTML5',
                        'clientVersion': '5.20150304',
                        'theme': 'CLASSIC',
                        'acceptRegion': 'US',
                        'acceptLanguage': 'en-US'
                    },
                    'user': {
                        'enableSafetyMode': False
                    }
                },
                'browseId': 'default'
            }

            if _continuation:
                post_data['continuation'] = _continuation

            return self.perform_v1_tv_request(method='POST', path='browse', post_data=post_data)

        current_page = 1
        pages = 30  # 28 seems to be page limit, add a couple page padding, loop will break when there is no next page data

        progress_dialog = _context.get_ui().create_progress_dialog(_context.get_name(),
                                                                   _context.localize(constants.localize.COMMON_PLEASE_WAIT),
                                                                   background=True)
        progress_dialog.set_total(pages)
        progress_dialog.update(steps=1, text=_context.localize(constants.localize.WATCH_LATER_RETRIEVAL_PAGE) % str(current_page))

        try:
            json_data = _get_items()

            while current_page < pages:
                contents = json_data.get('contents', json_data.get('continuationContents', {}))
                section = contents.get('sectionListRenderer', contents.get('sectionListContinuation', {}))
                contents = section.get('contents', [{}])

                for shelf in contents:
                    renderer = shelf.get('shelfRenderer', {})
                    endpoint = renderer.get('endpoint', {})
                    browse_endpoint = endpoint.get('browseEndpoint', {})
                    browse_id = browse_endpoint.get('browseId', '')
                    title = renderer.get('title', {})
                    title_runs = title.get('runs', [{}])[0]
                    title_text = title_runs.get('text', '')
                    if (title_text.lower() == 'watch later') and (browse_id.startswith('VLPL') or browse_id.startswith('PL')):
                        watch_later_id = browse_id.lstrip('VL')
                        break

                if watch_later_id:
                    break

                continuations = section.get('continuations', [{}])[0]
                next_continuation_data = continuations.get('nextContinuationData', {})
                continuation = next_continuation_data.get('continuation', '')

                if continuation:
                    current_page += 1
                    progress_dialog.update(steps=1, text=_context.localize(constants.localize.WATCH_LATER_RETRIEVAL_PAGE) % str(current_page))
                    json_data = _get_items(continuation)
                    continue
                else:
                    break
        finally:
            progress_dialog.close()

        return watch_later_id

    def perform_v3_request(self, method='GET', headers=None, path=None, post_data=None, params=None,
                           allow_redirects=True):

        yt_config = self._config

        # params
        if not params:
            params = {}
        _params = {'key': yt_config['key']}
        _params.update(params)

        # headers
        if not headers:
            headers = {}
        _headers = {'Host': 'www.googleapis.com',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
                    'Accept-Encoding': 'gzip, deflate'}
        # a config can decide if a token is allowed
        if self._access_token and yt_config.get('token-allowed', True):
            _headers['Authorization'] = 'Bearer %s' % self._access_token
        _headers.update(headers)

        # url
        _url = 'https://www.googleapis.com/youtube/v3/%s' % path.strip('/')

        result = None
        log_params = copy.deepcopy(params)
        if 'location' in log_params:
            log_params['location'] = 'xx.xxxx,xx.xxxx'
        _context.log_debug('[data] v3 request: |{0}| path: |{1}| params: |{2}| post_data: |{3}|'.format(method, path, log_params, post_data))
        if method == 'GET':
            result = requests.get(_url, params=_params, headers=_headers, verify=self._verify, allow_redirects=allow_redirects)
        elif method == 'POST':
            _headers['content-type'] = 'application/json'
            result = requests.post(_url, json=post_data, params=_params, headers=_headers, verify=self._verify,
                                   allow_redirects=allow_redirects)
        elif method == 'PUT':
            _headers['content-type'] = 'application/json'
            result = requests.put(_url, json=post_data, params=_params, headers=_headers, verify=self._verify,
                                  allow_redirects=allow_redirects)
        elif method == 'DELETE':
            result = requests.delete(_url, params=_params, headers=_headers, verify=self._verify,
                                     allow_redirects=allow_redirects)

        if result is None:
            return {}

        if result.headers.get('content-type', '').startswith('application/json'):
            return result.json()

    def perform_v1_tv_request(self, method='GET', headers=None, path=None, post_data=None, params=None,
                              allow_redirects=True):
        # params
        if not params:
            params = {}
        _params = {'key': self._config_tv['key']}
        _params.update(params)

        # headers
        if not headers:
            headers = {}
        _headers = {'Host': 'www.googleapis.com',
                    'Connection': 'keep-alive',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36',
                    'Origin': 'https://www.youtube.com',
                    'Accept': '*/*',
                    'DNT': '1',
                    'Referer': 'https://www.youtube.com/tv',
                    'Accept-Encoding': 'gzip',
                    'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}
        if self._access_token_tv:
            _headers['Authorization'] = 'Bearer %s' % self._access_token_tv
        _headers.update(headers)

        # url
        _url = 'https://www.googleapis.com/youtubei/v1/%s' % path.strip('/')

        result = None

        _context.log_debug('[i] v1 request: |{0}| path: |{1}| params: |{2}| post_data: |{3}|'.format(method, path, params, post_data))
        if method == 'GET':
            result = requests.get(_url, params=_params, headers=_headers, verify=self._verify, allow_redirects=allow_redirects)
        elif method == 'POST':
            _headers['content-type'] = 'application/json'
            result = requests.post(_url, json=post_data, params=_params, headers=_headers, verify=self._verify,
                                   allow_redirects=allow_redirects)
        elif method == 'PUT':
            _headers['content-type'] = 'application/json'
            result = requests.put(_url, json=post_data, params=_params, headers=_headers, verify=self._verify,
                                  allow_redirects=allow_redirects)
        elif method == 'DELETE':
            result = requests.delete(_url, params=_params, headers=_headers, verify=self._verify,
                                     allow_redirects=allow_redirects)

        if result is None:
            return {}

        if result.headers.get('content-type', '').startswith('application/json'):
            return result.json()
