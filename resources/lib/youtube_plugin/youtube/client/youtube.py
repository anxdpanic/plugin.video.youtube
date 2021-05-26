# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import copy
import json
import re
import threading
import time
import traceback
import xml.etree.ElementTree as ET

import requests
from six import PY3

from .login_client import LoginClient
from ..helper.video_info import VideoInfo
from ..helper.utils import get_shelf_index_by_title
from ...kodion import constants
from ...kodion import Context
from ...kodion.utils import datetime_parser
from ...kodion.utils import to_unicode

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

    def get_video_streams(self, context, video_id):
        video_info = VideoInfo(context, access_token=self._access_token, language=self._language)

        video_streams = video_info.load_stream_infos(video_id)

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

    def _get_recommendations_for_home(self):
        # YouTube has deprecated this API, so use history and related items to form
        # a recommended set. We cache aggressively because searches incur a high
        # quota cost of 100 on the YouTube API.
        # Note this is a first stab attempt and can be refined a lot more.
        payload = {
            'kind': 'youtube#activityListResponse',
            'items': []
        }

        watch_history_id = _context.get_access_manager().get_watch_history_id()
        if not watch_history_id or watch_history_id == 'HL':
            return payload

        cache = _context.get_data_cache()

        # Do we have a cached result?
        cache_home_key = 'get-activities-home'
        cached = cache.get_item(cache.ONE_HOUR * 4, cache_home_key)
        if cache_home_key in cached and cached[cache_home_key].get('items'):
            return cached[cache_home_key]

        # Fetch existing list of items, if any
        items = []
        cache_items_key = 'get-activities-home-items'
        cached = cache.get_item(cache.ONE_WEEK * 2, cache_items_key)
        if cache_items_key in cached:
            items = cached[cache_items_key]

        # Fetch history and recommended items. Use threads for faster execution.
        def helper(video_id, responses):
            _context.log_debug(
                'Method get_activities: doing expensive API fetch for related'
                'items for video %s' % video_id
            )
            di = self.get_related_videos(video_id, max_results=10)
            if 'items' in di:
                # Record for which video we fetched the items
                for item in di['items']:
                    item['plugin_fetched_for'] = video_id
                responses.extend(di['items'])

        history = self.get_playlist_items(watch_history_id, max_results=50)

        if not history.get('items'):
            return payload

        threads = []
        candidates = []
        already_fetched_for_video_ids = [item['plugin_fetched_for'] for item in items]
        history_items = [item for item in history['items']
                         if re.match(r'(?P<video_id>[\w-]{11})',
                                     item['snippet']['resourceId']['videoId'])]

        # TODO:
        # It would be nice to make this 8 user configurable
        for item in history_items[:8]:
            video_id = item['snippet']['resourceId']['videoId']
            if video_id not in already_fetched_for_video_ids:
                thread = threading.Thread(target=helper, args=(video_id, candidates))
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

        # Prepend new candidates to items
        seen = [item['id']['videoId'] for item in items]
        for candidate in candidates:
            vid = candidate['id']['videoId']
            if vid not in seen:
                seen.append(vid)
                candidate['plugin_created_date'] = datetime_parser.now().strftime('%Y-%m-%dT%H:%M:%SZ')
                items.insert(0, candidate)

        # Truncate items to keep it manageable, and cache
        items = items[:500]
        cache.set(cache_items_key, json.dumps(items))

        # Build the result set
        items.sort(
            key=lambda a: datetime_parser.parse(a['plugin_created_date']),
            reverse=True
        )
        sorted_items = []
        counter = 0
        channel_counts = {}
        while items:
            counter += 1

            # Hard stop on iteration. Good enough for our purposes.
            if counter >= 1000:
                break

            # Reset channel counts on a new page
            if counter % 50 == 0:
                channel_counts = {}

            # Ensure a single channel isn't hogging the page
            item = items.pop()
            channel_id = item.get('snippet', {}).get('channelId')
            if not channel_id:
                continue

            channel_counts.setdefault(channel_id, 0)
            if channel_counts[channel_id] <= 3:
                # Use the item
                channel_counts[channel_id] = channel_counts[channel_id] + 1
                item["page_number"] = counter // 50
                sorted_items.append(item)
            else:
                # Move the item to the end of the list
                items.append(item)

        # Finally sort items per page by date for a better distribution
        now = datetime_parser.now()
        sorted_items.sort(
            key=lambda a: (
                a['page_number'],
                datetime_parser.total_seconds(
                    now - datetime_parser.parse(a['snippet']['publishedAt'])
                )
            ),
        )

        # Finalize result
        payload['items'] = sorted_items
        """
        # TODO:
        # Enable pagination
        payload['pageInfo'] = {
            'resultsPerPage': 50,
            'totalResults': len(sorted_items)
        }
        """
        # Update cache
        cache.set(cache_home_key, json.dumps(payload))

        # If there are no sorted_items we fall back to default API behaviour
        return payload

    def get_activities(self, channel_id, page_token=''):
        params = {'part': 'snippet,contentDetails',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language}

        if channel_id == 'home':
            recommended = self._get_recommendations_for_home()
            if 'items' in recommended and recommended.get('items'):
                return recommended
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
        
    def get_parent_comments(self, video_id, page_token='', max_results=0):
        max_results = self._max_results if max_results <= 0 else max_results

        # prepare params
        params = {'part': 'snippet',
                  'videoId': video_id,
                  'order': 'relevance',
                  'textFormat': 'plainText',
                  'maxResults': str(max_results)}
        if page_token:
            params['pageToken'] = page_token
        
        return self.perform_v3_request(method='GET', path='commentThreads', params=params, no_login=True)
            
    def get_child_comments(self, parent_id, page_token='', max_results=0):
        max_results = self._max_results if max_results <= 0 else max_results

        # prepare params
        params = {'part': 'snippet',
                  'parentId': parent_id,
                  'textFormat': 'plainText',
                  'maxResults': str(max_results)}
        if page_token:
            params['pageToken'] = page_token
        
        return self.perform_v3_request(method='GET', path='comments', params=params, no_login=True)

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
        """
        modified by PureHemp, using YouTube RSS for fetching latest videos
        """

        if not page_token:
            page_token = ''

        result = {
            'items': [],
            'next_page_token': page_token,
            'offset': offset
        }

        def _perform(_page_token, _offset, _result):

            if not _result:
                _result = {
                    'items': []
                }

            cache = _context.get_data_cache()

            # if new uploads is cached
            cache_items_key = 'my-subscriptions-items'
            cached = cache.get_item(cache.ONE_HOUR, cache_items_key)
            if cache_items_key in cached:
                _result['items'] = cached[cache_items_key]

            """ no cache, get uploads data from web """
            if len(_result['items']) == 0:
                # get all subscriptions channel ids
                sub_page_token = True
                sub_channel_ids = []

                while sub_page_token:
                    if sub_page_token is True:
                        sub_page_token = ''

                    params = {
                        'part': 'snippet',
                        'maxResults': '50',
                        'order': 'alphabetical',
                        'mine': 'true'
                    }

                    if sub_page_token:
                        params['pageToken'] = sub_page_token

                    sub_json_data = self.perform_v3_request(method='GET', path='subscriptions', params=params)

                    if not sub_json_data:
                        sub_json_data = {}

                    items = sub_json_data.get('items', [])

                    for item in items:
                        item = item.get('snippet', {}).get('resourceId', {}).get('channelId', '')
                        sub_channel_ids.append(item)

                    # get next token if exists
                    sub_page_token = sub_json_data.get('nextPageToken', '')

                    # terminate loop when last page
                    if not sub_page_token:
                        break

                headers = {
                    'Host': 'www.youtube.com',
                    'Connection': 'keep-alive',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'DNT': '1',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'en-US,en;q=0.7,de;q=0.3'
                }

                responses = []

                def fetch_xml(_url, _responses):
                    try:
                        _response = requests.get(_url, {}, headers=headers, verify=self._verify, allow_redirects=True)
                    except:
                        _response = None
                        _context.log_error('Failed |%s|' % traceback.print_exc())

                    _responses.append(_response)

                threads = []
                for channel_id in sub_channel_ids:
                    thread = threading.Thread(
                        target=fetch_xml,
                        args=('https://www.youtube.com/feeds/videos.xml?channel_id=' + channel_id,
                              responses)
                    )
                    threads.append(thread)
                    thread.start()

                for thread in threads:
                    thread.join()

                for response in responses:
                    if response:
                        response.encoding = 'utf-8'
                        if PY3:
                            xml_data = to_unicode(response.content).replace('\n', '')
                        else:
                            xml_data = response.content.replace('\n', '')

                        root = ET.fromstring(xml_data)

                        ns = '{http://www.w3.org/2005/Atom}'
                        yt_ns = '{http://www.youtube.com/xml/schemas/2015}'
                        media_ns = '{http://search.yahoo.com/mrss/}'

                        for entry in root.findall(ns + "entry"):
                            # empty news dictionary 
                            entry_data = {
                                'id': entry.find(yt_ns + 'videoId').text,
                                'title': entry.find(media_ns + "group").find(media_ns + 'title').text,
                                'channel': entry.find(ns + "author").find(ns + "name").text,
                                'published': entry.find(ns + 'published').text,
                            }
                            # append items list 
                            _result['items'].append(entry_data)

                # sorting by publish date
                def _sort_by_date_time(e):
                    return datetime_parser.since_epoch(
                        datetime_parser.strptime(e["published"][0:19], "%Y-%m-%dT%H:%M:%S")
                    )

                _result['items'].sort(reverse=True, key=_sort_by_date_time)

                # Update cache
                cache.set(cache_items_key, json.dumps(_result['items']))
            """ no cache, get uploads data from web """

            # trim result
            if not _page_token:
                _page_token = 0

            _page_token = int(_page_token)

            if len(_result['items']) > self._max_results:
                _index_start = _page_token * self._max_results
                _index_end = _index_start + self._max_results

                _items = _result['items']
                _items = _items[_index_start:_index_end]
                _result['items'] = _items
                _result['next_page_token'] = _page_token + 1

            if len(_result['items']) < self._max_results:
                if 'continue' in _result:
                    del _result['continue']

                if 'next_page_token' in _result:
                    del _result['next_page_token']

                if 'offset' in _result:
                    del _result['offset']

            return _result

        return _perform(_page_token=page_token, _offset=offset, _result=result)

    def perform_v3_request(self, method='GET', headers=None, path=None, post_data=None, params=None,
                           allow_redirects=True, no_login=False):

        yt_config = self._config

        if not yt_config.get('key'):
            return {
                'error':
                    {
                        'errors': [{'reason': 'accessNotConfigured'}],
                        'message': 'No API keys provided'
                    }
            }

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
        if self._access_token and yt_config.get('token-allowed', True) and not no_login:
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

        _context.log_debug('[data] v3 response: |{0}| headers: |{1}|'.format(result.status_code, result.headers))

        if result is None:
            return {}

        if result.headers.get('content-type', '').startswith('application/json'):
            try:
                return result.json()
            except ValueError:
                return {
                    'status_code': result.status_code,
                    'payload': result.text
                }

        return {}
