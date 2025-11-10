# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import threading
from functools import partial
from itertools import chain, islice
from random import randint
from re import compile as re_compile
from xml.etree.ElementTree import Element as ET_Element, XML as ET_XML

from .login_client import YouTubeLoginClient
from ..helper.utils import channel_filter_split
from ..helper.v3 import pre_fill
from ..youtube_exceptions import InvalidJSON, YouTubeException
from ...kodion import logging
from ...kodion.compatibility import available_cpu_count, string_type
from ...kodion.constants import CHANNEL_ID, PLAYLIST_ID
from ...kodion.items import DirectoryItem
from ...kodion.utils.convert_format import strip_html_from_text
from ...kodion.utils.datetime import (
    since_epoch,
    strptime,
    yt_datetime_offset,
)


class YouTubeDataClient(YouTubeLoginClient):
    log = logging.getLogger(__name__)

    _max_results = 50
    _VIRTUAL_LISTS = frozenset(('WL', 'LL', 'HL'))
    JSON_PATHS = {
        'tv_grid': {
            'items': (
                'contents',
                'tvBrowseRenderer',
                'content',
                'tvSurfaceContentRenderer',
                'content',
                'gridRenderer',
                'items',
            ),
            'item_id': (
                'tileRenderer',
                'contentId',
            ),
            'title': (
                'tileRenderer',
                'metadata',
                'tileMetadataRenderer',
                'title',
                'simpleText',
            ),
            'thumbnails': (
                'tileRenderer',
                'header',
                'tileHeaderRenderer',
                'thumbnail',
                'thumbnails',
            ),
            'channel_id': (
                'tileRenderer',
                'onLongPressCommand',
                'showMenuCommand',
                'menu',
                'menuRenderer',
                'items',
                slice(None),
                None,
                'menuNavigationItemRenderer',
                'navigationEndpoint',
                'browseEndpoint',
                'browseId',
            ),
            'continuation': (
                'contents',
                'tvBrowseRenderer',
                'content',
                'tvSurfaceContentRenderer',
                'content',
                'sectionListRenderer',
                (
                    (
                        'contents',
                        slice(None),
                        None,
                        'shelfRenderer',
                        'content',
                        ('horizontalListRenderer', 'verticalListRenderer'),
                        'continuations',
                        0,
                        'nextContinuationData',
                    ),
                    (
                        'continuations',
                        0,
                        'nextContinuationData'
                    )
                ),
            ),
            'continuation_items': (
                'continuationContents',
                ('horizontalListContinuation', 'sectionListContinuation'),
                'items',
            ),
            'continuation_continuation': (
                'continuationContents',
                ('horizontalListContinuation', 'sectionListContinuation'),
                'continuations',
                0,
                'nextContinuationData',
            ),
        },
        'tv_playlist': {
            'items': (
                'contents',
                'tvBrowseRenderer',
                'content',
                'tvSurfaceContentRenderer',
                'content',
                'twoColumnRenderer',
                'rightColumn',
                'playlistVideoListRenderer',
                'contents',
            ),
            'item_id': (
                'tileRenderer',
                'onSelectCommand',
                'watchEndpoint',
                'videoId',
            ),
            'title': (
                'tileRenderer',
                'metadata',
                'tileMetadataRenderer',
                'title',
                'simpleText',
            ),
            'thumbnails': (
                'tileRenderer',
                'header',
                'tileHeaderRenderer',
                'thumbnail',
                'thumbnails',
            ),
            'channel_id': (
                'tileRenderer',
                'onLongPressCommand',
                'showMenuCommand',
                'menu',
                'menuRenderer',
                'items',
                -1,
                'menuNavigationItemRenderer',
                'navigationEndpoint',
                'browseEndpoint',
                'browseId',
            ),
            'playlist_id': (
                'tileRenderer',
                'onSelectCommand',
                'watchEndpoint',
                'playlistId',
            ),
            'continuation': (
                'contents',
                'tvBrowseRenderer',
                'content',
                'tvSurfaceContentRenderer',
                'content',
                'twoColumnRenderer',
                'rightColumn',
                'playlistVideoListRenderer',
                'continuations',
                0,
                'nextContinuationData',
            ),
            'continuation_items': (
                'continuationContents',
                'playlistVideoListContinuation',
                'contents',
            ),
            'continuation_continuation': (
                'continuationContents',
                'playlistVideoListContinuation',
                'continuations',
                0,
                'nextContinuationData',
            ),
        },
        'tv_shelf_horizontal': {
            'items': (
                'contents',
                'tvBrowseRenderer',
                'content',
                'tvSurfaceContentRenderer',
                'content',
                'sectionListRenderer',
                'contents',
                slice(None),
                'shelfRenderer',
                'content',
                ('horizontalListRenderer', 'verticalListRenderer'),
                'items',
            ),
            'item_id': (
                'tileRenderer',
                'onSelectCommand',
                'watchEndpoint',
                'videoId',
            ),
            'title': (
                'tileRenderer',
                'metadata',
                'tileMetadataRenderer',
                'title',
                'simpleText',
            ),
            'thumbnails': (
                'tileRenderer',
                'header',
                'tileHeaderRenderer',
                'thumbnail',
                'thumbnails',
            ),
            'channel_id': (
                'tileRenderer',
                'onLongPressCommand',
                'showMenuCommand',
                'menu',
                'menuRenderer',
                'items',
                slice(None),
                None,
                'menuNavigationItemRenderer',
                'navigationEndpoint',
                'browseEndpoint',
                'browseId',
            ),
            'continuation': (
                'contents',
                'tvBrowseRenderer',
                'content',
                'tvSurfaceContentRenderer',
                'content',
                'sectionListRenderer',
                (
                    (
                        'contents',
                        slice(None),
                        None,
                        'shelfRenderer',
                        'content',
                        ('horizontalListRenderer', 'verticalListRenderer'),
                        'continuations',
                        0,
                        'nextContinuationData',
                    ),
                    (
                        'continuations',
                        0,
                        'nextContinuationData'
                    )
                ),
            ),
            'continuation_items': (
                'continuationContents',
                ('horizontalListContinuation', 'sectionListContinuation'),
                (
                    ('items',),
                    (
                        'contents',
                        slice(None),
                        'shelfRenderer',
                        'content',
                        ('horizontalListRenderer', 'verticalListRenderer'),
                        'items',
                    ),
                ),
            ),
            'continuation_continuation': (
                'continuationContents',
                ('horizontalListContinuation', 'sectionListContinuation'),
                'continuations',
                0,
                'nextContinuationData',
            ),
        },
        'vr_shelf': {
            'items': (
                'contents',
                'singleColumnBrowseResultsRenderer',
                'tabs',
                0,
                'tabRenderer',
                'content',
                'sectionListRenderer',
                'contents',
                slice(None),
                'shelfRenderer',
                'content',
                ('horizontalListRenderer', 'verticalListRenderer'),
                'items',
                slice(None),
                (
                    'gridVideoRenderer',
                    'compactVideoRenderer',
                    'tileRenderer',
                ),
                # 'videoId',
            ),
            'continuation': (
                'contents',
                'singleColumnBrowseResultsRenderer',
                'tabs',
                0,
                'tabRenderer',
                'content',
                'sectionListRenderer',
                'continuations',
                0,
                'nextContinuationData',
            ),
            'continuation_items': (
                'continuationContents',
                'sectionListContinuation',
                'contents',
                slice(None),
                'shelfRenderer',
                'content',
                ('horizontalListRenderer', 'verticalListRenderer'),
                'items',
                slice(None),
                (
                    'gridVideoRenderer',
                    'compactVideoRenderer',
                    'tileRenderer',
                ),
                # 'videoId',
            ),
            'continuation_continuation': (
                'continuationContents',
                'sectionListContinuation',
                'continuations',
                0,
                'nextContinuationData',
            ),
        },
    }

    def __init__(self, context, items_per_page=None, **kwargs):
        self.channel_id = None

        if items_per_page is None:
            items_per_page = context.get_settings().items_per_page()

        super(YouTubeDataClient, self).__init__(context=context, **kwargs)
        YouTubeDataClient.init(items_per_page=items_per_page)

    @classmethod
    def init(cls, items_per_page=50, **_kwargs):
        cls._max_results = items_per_page

    def reinit(self, **kwargs):
        super(YouTubeDataClient, self).reinit(**kwargs)

    def set_access_token(self, access_tokens=None):
        super(YouTubeDataClient, self).set_access_token(access_tokens)
        if self.logged_in:
            context = self._context
            function_cache = context.get_function_cache()
            self.channel_id = function_cache.run(
                self.get_channel_by_identifier,
                function_cache.ONE_MONTH,
                _refresh=context.refresh_requested(),
                identifier='mine',
                do_search=False,
                notify=False,
            )
        else:
            self.channel_id = None

    def max_results(self):
        return self._context.get_param('items_per_page') or self._max_results

    def update_watch_history(self, video_id, url, status=None):
        if status is None:
            cmt = st = et = state = None
        else:
            cmt, st, et, state = status

        self.log.debug('Playback reported [{video_id}]:'
                       ' current time={cmt},'
                       ' segment start={st},'
                       ' segment end={et},'
                       ' state={state}',
                       video_id=video_id,
                       cmt=cmt,
                       st=st,
                       et=et,
                       state=state)

        client_data = {
            '_video_id': video_id,
            'url': url,
            'error_title': 'Failed to update watch history',
        }

        params = {}
        if cmt is not None:
            params['cmt'] = format(cmt, '.3f')
        if st is not None:
            params['st'] = format(st, '.3f')
        if et is not None:
            params['et'] = format(et, '.3f')
        if state is not None:
            params['state'] = state

        self.api_request('watch_history', 'GET',
                         client_data=client_data,
                         params=params,
                         no_content=True,
                         do_auth=True,
                         cache=False)

    def remove_playlist(self, playlist_id, **kwargs):
        params = {'id': playlist_id,
                  'mine': True}
        return self.api_request(method='DELETE', path='playlists',
                                params=params,
                                do_auth=True,
                                no_content=True,
                                **kwargs)

    def get_supported_languages(self, language=None, **kwargs):
        params = {
            'part': 'snippet',
            'hl': (
                language.replace('-', '_')
                if language else
                self._language
            ),
        }
        return self.api_request(method='GET', path='i18nLanguages',
                                params=params,
                                **kwargs)

    def get_supported_regions(self, language=None, **kwargs):
        params = {
            'part': 'snippet',
            'hl': (
                language.replace('-', '_')
                if language else
                self._language
            ),
        }
        return self.api_request(method='GET', path='i18nRegions',
                                params=params,
                                **kwargs)

    def rename_playlist(self,
                        playlist_id,
                        new_title,
                        privacy_status='private',
                        **kwargs):
        params = {'part': 'snippet,id,status'}
        post_data = {'kind': 'youtube#playlist',
                     'id': playlist_id,
                     'snippet': {'title': new_title},
                     'status': {'privacyStatus': privacy_status}}
        return self.api_request(method='PUT', path='playlists',
                                params=params,
                                post_data=post_data,
                                **kwargs)

    def create_playlist(self, title, privacy_status='private', **kwargs):
        params = {'part': 'snippet,status'}
        post_data = {'kind': 'youtube#playlist',
                     'snippet': {'title': title},
                     'status': {'privacyStatus': privacy_status}}
        return self.api_request(method='POST', path='playlists',
                                params=params,
                                post_data=post_data,
                                **kwargs)

    def get_video_rating(self, video_id, **kwargs):
        params = {
            'id': (
                video_id
                if isinstance(video_id, string_type) else
                ','.join(video_id)
            ),
        }
        return self.api_request(method='GET', path='videos/getRating',
                                params=params,
                                do_auth=True,
                                **kwargs)

    def rate_video(self, video_id, rating='like', **kwargs):
        """
        Rate a video
        :param video_id: if of the video
        :param rating: [like|dislike|none]
        :return:
        """
        params = {'id': video_id,
                  'rating': rating}
        return self.api_request(method='POST', path='videos/rate',
                                params=params,
                                do_auth=True,
                                no_content=True,
                                **kwargs)

    def rate_playlist(self, playlist_id, rating='like', **kwargs):
        if rating == 'like':
            post_data = {
                'status': 'LIKE',
                'target': {
                    'playlistId': playlist_id,
                },
            }
            path = 'like/like'
        else:
            post_data = {
                'status': 'INDIFFERENT',
                'target': {
                    'playlistId': playlist_id,
                },
            }
            path = 'like/removelike'

        return self.api_request('tv', 'POST', path=path,
                                post_data=post_data,
                                do_auth=True,
                                **kwargs)

    def add_video_to_playlist(self, playlist_id, video_id, **kwargs):
        playlist_id_upper = playlist_id.upper()
        if playlist_id_upper not in self._VIRTUAL_LISTS:
            params = {'part': 'snippet',
                      'mine': True}
            post_data = {'kind': 'youtube#playlistItem',
                         'snippet': {'playlistId': playlist_id,
                                     'resourceId': {'kind': 'youtube#video',
                                                    'videoId': video_id}}}
            return self.api_request(method='POST', path='playlistItems',
                                    params=params,
                                    post_data=post_data,
                                    **kwargs)

        if playlist_id_upper == 'WL':
            post_data = {
                'playlistId': playlist_id_upper,
                'actions': [{
                    'addedVideoId': video_id,
                    # 'setVideoId': '',
                    'action': 'ACTION_ADD_VIDEO',
                }],
            }
            path = 'browse/edit_playlist'

        else:
            return False

        return self.api_request('tv', 'POST', path=path,
                                post_data=post_data,
                                do_auth=True,
                                **kwargs)

    # noinspection PyUnusedLocal
    def remove_video_from_playlist(self,
                                   playlist_id,
                                   playlist_item_id,
                                   video_id,
                                   **kwargs):
        playlist_id_upper = playlist_id.upper() if playlist_id else ''
        if playlist_id_upper not in self._VIRTUAL_LISTS:
            params = {'id': playlist_item_id}
            return self.api_request(method='DELETE', path='playlistItems',
                                    params=params,
                                    do_auth=True,
                                    no_content=True,
                                    **kwargs)

        if playlist_id_upper == 'WL':
            post_data = {
                'playlistId': playlist_id_upper,
                'actions': [{
                    'removedVideoId': video_id,
                    'action': 'ACTION_REMOVE_VIDEO_BY_VIDEO_ID',
                }],
            }
            path = 'browse/edit_playlist'

        elif playlist_id_upper == 'LL':
            post_data = {
                'target': {
                    'videoId': video_id,
                },
            }
            path = 'like/removelike'

        else:
            return False

        return self.api_request('tv', 'POST', path=path,
                                post_data=post_data,
                                do_auth=True,
                                **kwargs)

    def unsubscribe(self, subscription_id, **kwargs):
        params = {'id': subscription_id}
        return self.api_request(method='DELETE', path='subscriptions',
                                params=params,
                                do_auth=True,
                                no_content=True,
                                **kwargs)

    def unsubscribe_channel(self, channel_id, **kwargs):
        post_data = {'channelIds': [channel_id]}
        return self.api_request('tv', 'POST', path='subscription/unsubscribe',
                                post_data=post_data,
                                **kwargs)

    def subscribe(self, channel_id, **kwargs):
        params = {'part': 'snippet'}
        post_data = {'kind': 'youtube#subscription',
                     'snippet': {'resourceId': {'kind': 'youtube#channel',
                                                'channelId': channel_id}}}
        return self.api_request(method='POST', path='subscriptions',
                                params=params,
                                post_data=post_data,
                                **kwargs)

    def get_subscription(self,
                         channel_id,
                         order='alphabetical',
                         page_token='',
                         **kwargs):
        """
        :param channel_id: [channel-id|'mine']
        :param order: ['alphabetical'|'relevance'|'unread']
        :param page_token:
        :return:
        """
        params = {'part': 'snippet',
                  'maxResults': self.max_results(),
                  'order': order}
        if channel_id == 'mine':
            params['mine'] = True
        else:
            params['channelId'] = channel_id
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET', path='subscriptions',
                                params=params,
                                **kwargs)

    def get_guide_category(self, guide_category_id, page_token='', **kwargs):
        params = {'part': 'snippet,contentDetails,brandingSettings',
                  'maxResults': self.max_results(),
                  'categoryId': guide_category_id,
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token
        return self.api_request(method='GET', path='channels',
                                params=params,
                                **kwargs)

    def get_guide_categories(self, page_token='', **kwargs):
        params = {'part': 'snippet',
                  'maxResults': self.max_results(),
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET', path='guideCategories',
                                params=params,
                                **kwargs)

    def get_trending_videos(self, page_token='', **kwargs):
        params = {'part': 'snippet,status',
                  'maxResults': self.max_results(),
                  'regionCode': self._region,
                  'hl': self._language,
                  'chart': 'mostPopular'}
        if page_token:
            params['pageToken'] = page_token
        return self.api_request(method='GET', path='videos',
                                params=params,
                                **kwargs)

    def get_video_category(self, video_category_id, page_token='', **kwargs):
        params = {'part': 'snippet,contentDetails,status',
                  'maxResults': self.max_results(),
                  'videoCategoryId': video_category_id,
                  'chart': 'mostPopular',
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token
        return self.api_request(method='GET', path='videos',
                                params=params,
                                **kwargs)

    def get_video_categories(self, page_token='', **kwargs):
        params = {'part': 'snippet',
                  'maxResults': self.max_results(),
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET', path='videoCategories',
                                params=params,
                                **kwargs)

    def get_related_for_home(self, page_token='', refresh=False):
        """
        YouTube has deprecated this API, so we use history and related items to
        form a recommended set.
        We cache aggressively because searches can be slow.
        Note this is a naive implementation and can be refined a lot more.
        """

        payload = {
            'kind': 'youtube#activityListResponse',
            'items': []
        }

        # Related videos are retrieved for the following num_items from history
        num_items = 10
        video_ids = []

        history_id = self._context.get_access_manager().get_watch_history_id()
        if history_id:
            history = self.get_playlist_items(history_id,
                                              max_results=num_items,
                                              do_auth=True)
            history_items = history and history.get('items')
            if history_items:
                for item in history_items:
                    try:
                        video_id = item['snippet']['resourceId']['videoId']
                    except KeyError:
                        continue
                    video_ids.append(video_id)

        remaining_items = num_items - len(video_ids)
        local_history = self._context.get_settings().use_local_history()
        if local_history and remaining_items:
            history = self._context.get_playback_history()
            history_items = history.get_items(limit=remaining_items,
                                              excluding=video_ids)
            if history_items:
                video_ids.extend(history_items)

        if not video_ids:
            return payload

        # Fetch existing list of items, if any
        data_cache = self._context.get_data_cache()
        cache_items_key = 'get-activities-home-items-v2'
        if refresh:
            cached = []
        else:
            cached = data_cache.get_item(cache_items_key) or []

        # Increase value to recursively retrieve recommendations for the first
        # recommended video, up to the set maximum recursion depth
        max_depth = 2
        items_per_page = self.max_results()
        diversity_limits = items_per_page // (num_items * max_depth)
        items = [[] for _ in range(max_depth * len(video_ids))]
        counts = {
            '_counter': 0,
            '_pages': {},
            '_related': {},
        }

        def index_items(items, index,
                        item_store=None,
                        original_ids=None,
                        group=None,
                        depth=1,
                        original_related=None,
                        original_channel=None):
            if original_ids is not None:
                original_ids = list(original_ids)

            running = 0
            threads = []

            for idx, item in enumerate(items):
                if original_related is not None:
                    related = item['_related_video_id'] = original_related
                else:
                    related = item['_related_video_id']
                if original_channel is not None:
                    channel = item['_related_channel_id'] = original_channel
                else:
                    channel = item['_related_channel_id']
                video_id = item['id']

                index['_related'].setdefault(related, 0)
                index['_related'][related] += 1

                if video_id in index:
                    item_count = index[video_id]
                    item_count['_related'].setdefault(related, 0)
                    item_count['_related'][related] += 1
                    item_count['_channels'].setdefault(channel, 0)
                    item_count['_channels'][channel] += 1
                    continue

                index[video_id] = {
                    '_related': {related: 1},
                    '_channels': {channel: 1}
                }

                if item_store is None:
                    if original_ids and related not in original_ids:
                        items[idx] = None
                    continue

                if group is not None:
                    pass
                elif original_ids and related in original_ids:
                    group = max_depth * original_ids.index(related)
                else:
                    group = 0

                num_stored = len(item_store[group])
                item['_order'] = items_per_page * group + num_stored
                item_store[group].append(item)

                if num_stored or depth <= 1:
                    continue

                running += 1
                thread = threading.Thread(
                    target=threaded_get_related,
                    args=(video_id, index_items, counts),
                    kwargs={'item_store': item_store,
                            'group': (group + 1),
                            'depth': (depth - 1),
                            'original_related': related,
                            'original_channel': channel},
                )
                thread.daemon = True
                threads.append(thread)
                thread.start()

            while running:
                for thread in threads:
                    thread.join(5)
                    if not thread.is_alive():
                        running -= 1

        index_items(cached, counts, original_ids=video_ids)

        # Fetch related videos. Use threads for faster execution.
        def threaded_get_related(video_id, func, *args, **kwargs):
            filler = partial(
                self.get_related_videos,
                video_id,
            )
            related = pre_fill(filler,
                               filler(),
                               max_results=items_per_page,
                               exclude=[])
            if related and 'items' in related:
                func(related['items'][:items_per_page], *args, **kwargs)

        running = 0
        threads = []
        candidates = []
        for video_id in video_ids:
            if video_id in counts['_related']:
                continue
            running += 1
            thread = threading.Thread(
                target=threaded_get_related,
                args=(video_id, candidates.extend),
            )
            thread.daemon = True
            threads.append(thread)
            thread.start()

        while running:
            for thread in threads:
                thread.join(5)
                if not thread.is_alive():
                    running -= 1

        num_items = items_per_page * num_items * max_depth
        index_items(candidates[:num_items], counts,
                    item_store=items,
                    original_ids=video_ids,
                    depth=max_depth)

        # Truncate items to keep it manageable, and cache
        items = list(chain.from_iterable(items))
        counts['_counter'] = len(items)
        remaining = num_items - counts['_counter']
        if remaining > 0:
            items.extend(islice(filter(None, cached), remaining))
        elif remaining:
            items = items[:num_items]

        # Finally sort items per page by rank and date for a better distribution
        def rank_and_sort(item):
            if '_order' not in item:
                counts['_counter'] += 1
                item['_order'] = counts['_counter']

            page = 1 + item['_order'] // (items_per_page * max_depth)
            page_count = counts['_pages'].setdefault(page, {'_counter': 0})
            while page_count['_counter'] < items_per_page and page > 1:
                page -= 1
                page_count = counts['_pages'].setdefault(page, {'_counter': 0})

            related_video = item['_related_video_id']
            related_channel = item['_related_channel_id']
            channel_id = item.get('snippet', {}).get('channelId')
            """
            # Video channel and related channel can be the same which can double
            # up the channel count. Checking for this allows more similar videos
            # in the recommendation, ignoring it allows for more variety.
            # Currently prefer not to check for this to allow more variety.
            if channel_id == related_channel:
                channel_id = None
            """
            while (page_count['_counter'] >= items_per_page
                   or (related_video in page_count
                       and page_count[related_video] >= diversity_limits)
                   or (related_channel and related_channel in page_count
                       and page_count[related_channel] >= diversity_limits)
                   or (channel_id and channel_id in page_count
                       and page_count[channel_id] >= diversity_limits)):
                page += 1
                page_count = counts['_pages'].setdefault(page, {'_counter': 0})

            page_count.setdefault(related_video, 0)
            page_count[related_video] += 1
            if related_channel:
                page_count.setdefault(related_channel, 0)
                page_count[related_channel] += 1
            if channel_id:
                page_count.setdefault(channel_id, 0)
                page_count[channel_id] += 1
            page_count['_counter'] += 1
            item['_page'] = page

            item_count = counts[item['id']]
            item['_rank'] = (2 * sum(item_count['_channels'].values())
                             + sum(item_count['_related'].values()))

            return (
                -item['_page'],
                item['_rank'],
                -randint(0, item['_order'])
            )

        items.sort(key=rank_and_sort, reverse=True)

        # Finalize result
        payload['items'] = items
        """
        # TODO:
        # Enable pagination
        payload['pageInfo'] = {
            'resultsPerPage': 50,
            'totalResults': len(sorted_items)
        }
        """

        # Update cache
        data_cache.set_item(cache_items_key, items)

        return payload

    def get_activities(self, channel_id, page_token='', **kwargs):
        params = {'part': 'snippet,contentDetails',
                  'maxResults': self.max_results(),
                  'regionCode': self._region,
                  'hl': self._language}

        if channel_id == 'home':
            params['home'] = True
        elif channel_id == 'mine':
            params['mine'] = True
        else:
            function_cache = self._context.get_function_cache()
            channel_id = function_cache.run(
                self.get_channel_by_identifier,
                function_cache.ONE_MONTH,
                _refresh=self._context.refresh_requested(),
                identifier=channel_id,
            )
            params['channelId'] = channel_id
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET', path='activities',
                                params=params,
                                **kwargs)

    def get_channel_sections(self, channel_id, **kwargs):
        params = {'part': 'snippet,contentDetails',
                  'regionCode': self._region,
                  'hl': self._language}
        if channel_id == 'mine':
            params['mine'] = True
        else:
            function_cache = self._context.get_function_cache()
            channel_id = function_cache.run(
                self.get_channel_by_identifier,
                function_cache.ONE_MONTH,
                _refresh=self._context.refresh_requested(),
                identifier=channel_id,
            )
            params['channelId'] = channel_id
        return self.api_request(method='GET', path='channelSections',
                                params=params,
                                **kwargs)

    def get_playlists_of_channel(self, channel_id, page_token='', **kwargs):
        params = {'part': 'snippet,status,contentDetails',
                  'maxResults': self.max_results()}
        if channel_id == 'mine':
            params['mine'] = True
        else:
            function_cache = self._context.get_function_cache()
            channel_id = function_cache.run(
                self.get_channel_by_identifier,
                function_cache.ONE_MONTH,
                _refresh=self._context.refresh_requested(),
                identifier=channel_id,
            )
            params['channelId'] = channel_id
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET', path='playlists',
                                params=params,
                                **kwargs)

    def get_playlist_item_id_of_video_id(self,
                                         playlist_id,
                                         video_id,
                                         do_auth=None,
                                         page_token=''):
        json_data = self.get_playlist_items(
            playlist_id=playlist_id,
            page_token=page_token,
            do_auth=do_auth,
            max_results=self.max_results(),
        )
        if not json_data:
            return None

        for item in json_data.get('items', []):
            if (item.get('snippet', {}).get('resourceId', {}).get('videoId')
                    == video_id):
                return item['id']

        next_page_token = json_data.get('nextPageToken')
        if next_page_token:
            return self.get_playlist_item_id_of_video_id(
                playlist_id=playlist_id,
                video_id=video_id,
                do_auth=do_auth,
                page_token=next_page_token,
            )
        return None

    def get_playlist_items(self,
                           playlist_id,
                           page_token='',
                           do_auth=None,
                           max_results=None,
                           **kwargs):
        playlist_id_upper = playlist_id.upper()
        if playlist_id_upper not in self._VIRTUAL_LISTS:
            params = {
                'part': 'snippet',
                'maxResults': (
                    self.max_results()
                    if max_results is None else
                    max_results
                ),
                'playlistId': playlist_id,
            }
            if page_token:
                params['pageToken'] = page_token

            return self.api_request(method='GET', path='playlistItems',
                                    params=params,
                                    do_auth=do_auth,
                                    **kwargs)

        if playlist_id_upper == 'HL':
            browse_id = 'FEhistory'
            json_path = self.JSON_PATHS['tv_grid']
            response_type = 'videos'
        else:
            browse_id = 'VL' + playlist_id_upper
            json_path = self.JSON_PATHS['tv_playlist']
            response_type = 'playlistItems'

        return self.get_browse_items(
            browse_id=browse_id,
            playlist_id=playlist_id,
            response_type=response_type,
            client='tv',
            do_auth=True,
            page_token=page_token,
            json_path=json_path,
            **kwargs
        )

    def get_channel_by_identifier(self,
                                  identifier,
                                  mine=False,
                                  handle=False,
                                  username=False,
                                  verify_id=False,
                                  do_search=False,
                                  as_json=False,
                                  id_re=re_compile('UC[A-Za-z0-9_-]{21}[AQgw]'),
                                  **kwargs):
        """
        Returns a collection of zero or more channel resources that match the request criteria.
        :param str identifier: channel username to retrieve channel ID for
        :param bool mine: treat identifier as request for authenticated user
        :param bool handle: treat identifier as request for handle
        :param bool username: treat identifier as request for username
        :return:
        """
        params = {'part': 'id'}
        if mine or identifier == 'mine':
            params['mine'] = True
            mine = True
        elif id_re.match(identifier):
            if not verify_id:
                return identifier
            params['id'] = identifier
        elif handle or identifier.startswith('@'):
            params['forHandle'] = identifier
        elif username:
            params['forUsername'] = identifier
        else:
            handle = True
            params['forHandle'] = identifier

        json_data = self.api_request(method='GET', path='channels',
                                     params=params,
                                     do_auth=True if mine else False,
                                     **kwargs)
        if as_json:
            return json_data

        try:
            return json_data['items'][0]['id']
        except (IndexError, KeyError, TypeError):
            self.log.warning(('Channel ID not found',
                              'Data:        {data}',
                              'Identifier:  {identifier!r}',
                              'mine:        {mine!r}',
                              'forHandle:   {handle!r}',
                              'forUsername: {username!r}'),
                             data=json_data,
                             identifier=identifier,
                             mine=mine,
                             handle=handle,
                             username=username,
                             exc_info=True,
                             stack_info=True,
                             stacklevel=2)
            if not do_search:
                return None

        _, json_data = self.search_with_params(
            params={
                'q': identifier,
                'type': 'channel',
                'safeSearch': 'none',
            },
        )

        try:
            return json_data['items'][0]['id']['channelId']
        except (IndexError, KeyError, TypeError):
            return None

    def get_channels_by_identifiers(self, identifiers, **kwargs):
        function_cache = self._context.get_function_cache()
        if self._context.refresh_requested():
            max_age = function_cache.ONE_DAY
        else:
            max_age = function_cache.ONE_MONTH

        return {
            function_cache.run(
                self.get_channel_by_identifier,
                max_age,
                identifier=identifier,
                **kwargs
            )
            for identifier in identifiers
        }

    def channel_match(self, identifier, identifiers, exclude=False):
        if not identifier or not identifiers:
            return False

        function_cache = self._context.get_function_cache()
        if self._context.refresh_requested():
            max_age = function_cache.ONE_DAY
            refresh = True
        else:
            max_age = function_cache.ONE_MONTH
            refresh = False
        result = False

        channel_id = function_cache.run(
            self.get_channel_by_identifier,
            max_age,
            identifier=identifier,
        )
        if channel_id:
            channel_ids = function_cache.run(
                self.get_channels_by_identifiers,
                function_cache.ONE_MONTH,
                _refresh=refresh,
                identifiers=identifiers,
                do_search=True,
            )
            if channel_id in channel_ids:
                result = True

        if not result and channel_id != identifier:
            identifiers = {
                channel.lower().replace(',', '')
                for channel in identifiers
            }
            result = identifier.lower().replace(',', '') in identifiers

        if exclude:
            return not result
        return result

    def get_channels(self, channel_id, max_results=None, **kwargs):
        """
        Returns a collection of zero or more channel resources that match the
        request criteria.
        :param channel_id: list or string of comma-separated YouTube channelIds
        :param max_results: the maximum number of items that should be returned
                            in the result set, from 0 to 50, inclusive
        :return:
        """
        if max_results is None:
            max_results = self.max_results()
        params = {
            'part': 'snippet,contentDetails,brandingSettings,statistics',
            'maxResults': max_results,
        }

        if channel_id == 'mine':
            params['mine'] = True
        elif isinstance(channel_id, string_type):
            params['id'] = channel_id
        else:
            params['id'] = ','.join(channel_id)

        return self.api_request(method='GET', path='channels',
                                params=params,
                                **kwargs)

    def get_disliked_videos(self, page_token='', **kwargs):
        # prepare page token
        if not page_token:
            page_token = ''

        # prepare params
        params = {'part': 'snippet,status',
                  'myRating': 'dislike',
                  'maxResults': self.max_results()}
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET', path='videos',
                                params=params,
                                do_auth=True,
                                **kwargs)

    def get_videos(self,
                   video_id,
                   live_details=False,
                   max_results=None,
                   **kwargs):
        """
        Returns a list of videos that match the API request parameters
        :param video_id: list of video ids
        :param live_details: also retrieve liveStreamingDetails
        :param max_results: the maximum number of items that should be returned
                            in the result set, from 0 to 50, inclusive
        :return:
        """
        params = {
            'part': (
                'snippet,contentDetails,status,statistics,liveStreamingDetails'
                if live_details else
                'snippet,contentDetails,status,statistics'
            ),
            'id': (
                video_id
                if isinstance(video_id, string_type) else
                ','.join(video_id)
            ),
            'maxResults': (
                self.max_results()
                if max_results is None else
                max_results
            ),
        }
        return self.api_request(method='GET', path='videos',
                                params=params,
                                **kwargs)

    def get_playlists(self, playlist_id, max_results=None, **kwargs):
        params = {
            'part': 'snippet,status,contentDetails',
            'id': (
                playlist_id
                if isinstance(playlist_id, string_type) else
                ','.join(playlist_id)
            ),
            'maxResults': (
                self.max_results()
                if max_results is None else
                max_results
            ),
        }
        return self.api_request(method='GET', path='playlists',
                                params=params,
                                **kwargs)

    def get_browse_items(self,
                         browse_id=None,
                         channel_id=None,
                         playlist_id=None,
                         skip_ids=None,
                         params=None,
                         route=None,
                         _route={
                             'featured': 'EghmZWF0dXJlZPIGBAoCMgA%3D',
                             'videos': 'EgZ2aWRlb3PyBgQKAjoA',
                             'shorts': 'EgZzaG9ydHPyBgUKA5oBAA%3D%3D',
                             'streams': 'EgdzdHJlYW1z8gYECgJ6AA%3D%3D',
                             'podcasts': 'Eghwb2RjYXN0c_IGBQoDugEA',
                             'courses': 'Egdjb3Vyc2Vz8gYFCgPCAQA%3D',
                             'playlists': 'EglwbGF5bGlzdHPyBgQKAkIA',
                             'community': 'Egljb21tdW5pdHnyBgQKAkoA',
                             'search': 'EgZzZWFyY2jyBgQKAloA',
                         },
                         response_type='videos',
                         _response_types={
                             'videos': (
                                     'youtube#videoListResponse',
                                     'youtube#video',
                                     'videoId',
                             ),
                             'playlists': (
                                     'youtube#playlistListResponse',
                                     'youtube#playlist',
                                     'contentId',
                             ),
                             'playlistItems': (
                                     'youtube#playlistItemListResponse',
                                     'youtube#playlistItem',
                                     'contentId',
                             ),
                         },
                         data=None,
                         client=None,
                         do_auth=False,
                         page_token=None,
                         click_tracking=None,
                         visitor=None,
                         items_per_page=None,
                         json_path=None):
        response_type = _response_types.get(response_type)
        if not response_type:
            return None

        if channel_id:
            function_cache = self._context.get_function_cache()
            channel_id = function_cache.run(
                self.get_channel_by_identifier,
                function_cache.ONE_MONTH,
                _refresh=self._context.refresh_requested(),
                identifier=channel_id,
            )
        browse_id = browse_id or channel_id
        if not browse_id:
            return None

        post_data = {
            'browseId': browse_id,
        }

        if channel_id and route:
            params = _route.get(route)
        if params:
            post_data['params'] = params

        if data:
            post_data.update(data)

        if page_token:
            post_data['continuation'] = page_token

        if click_tracking or visitor:
            context = {}
            if click_tracking:
                context['clickTracking'] = {
                    'clickTrackingParams': click_tracking,
                }
            if visitor:
                context['client'] = {
                    'visitorData': visitor,
                }
            post_data['context'] = context

        result = self.api_request(client or 'web', 'POST', path='browse',
                                  url=self.V1_API_URL,
                                  post_data=post_data,
                                  do_auth=do_auth,
                                  cache=True)
        if not result:
            return {}

        if not json_path:
            return result

        if page_token:
            item_path = json_path.get('continuation_items')
        else:
            item_path = json_path.get('items')
        if not item_path:
            return result

        response_kind, item_kind, item_id_kind = response_type

        v3_response = {
            'kind': response_kind,
            'items': None,
        }

        nodes = self.json_traverse(result, path=item_path, default=())
        items = []
        for content in nodes:
            if not isinstance(content, (list, tuple)):
                content = (content,)
            for item in content:
                if not item:
                    continue
                item_id = self.json_traverse(
                    item,
                    json_path.get('item_id') or (item_id_kind,),
                )
                if not item_id or skip_ids and item_id in skip_ids:
                    continue
                if channel_id:
                    _channel_id = channel_id
                else:
                    _channel_id = self.json_traverse(
                        item,
                        json_path.get('channel_id') or (
                            ('longBylineText', 'shortBylineText'),
                            'runs',
                            0,
                            'navigationEndpoint',
                            'browseEndpoint',
                            'browseId',
                        ),
                    )
                    if skip_ids and _channel_id in skip_ids:
                        continue
                if playlist_id:
                    _playlist_id = playlist_id
                else:
                    _playlist_id = self.json_traverse(
                        item,
                        json_path.get('playlist_id'),
                    )
                items.append({
                    'kind': item_kind,
                    'id': item_id,
                    '_partial': True,
                    'snippet': {
                        'title': self.json_traverse(
                            item,
                            json_path.get('title') or (
                                (
                                    ('title', 'runs', 0, 'text'),
                                    ('headline', 'simpleText'),
                                ),
                            ),
                        ),
                        'thumbnails': self.json_traverse(
                            item,
                            json_path.get('thumbnails') or (
                                'thumbnail',
                                'thumbnails'
                            ),
                        ),
                        'channelId': _channel_id,
                        'playlistId': _playlist_id,
                    }
                })
        if not items:
            v3_response['items'] = items
            return v3_response

        continuation = self.json_traverse(
            result,
            (json_path.get('continuation_continuation')
             or json_path.get('continuation'))
            if page_token else
            json_path.get('continuation'),
        )
        if continuation:
            click_tracking = continuation.get('clickTrackingParams')

            next_page_token = self.json_traverse(
                continuation,
                json_path.get('page_token') or (
                    (
                        (
                            'continuationCommand',
                            'token',
                        ),
                        (
                            'continuation',
                        ),
                    ),
                ),
            )
            if next_page_token == page_token:
                next_page_token = None

            visitor = self.json_traverse(
                result,
                json_path.get('visitor_data') or (
                    'responseContext',
                    'visitorData',
                ),
            ) or visitor
        else:
            next_page_token = None

        if items_per_page:
            if items_per_page is True:
                items_per_page = len(items)
            max_results = self.max_results() - items_per_page
            while next_page_token and len(items) <= max_results:
                next_response = self.get_browse_items(
                    browse_id=browse_id,
                    channel_id=channel_id,
                    skip_ids=skip_ids,
                    params=params,
                    route=route,
                    data=data,
                    client=client,
                    do_auth=do_auth,
                    page_token=next_page_token,
                    click_tracking=click_tracking,
                    visitor=visitor,
                    items_per_page=None,
                    json_path=json_path,
                )
                if not next_response:
                    break
                next_items = next_response.get('items')
                if next_items:
                    items.extend(next_items)
                next_page_token = next_response.get('nextPageToken')
                click_tracking = next_response.get('clickTracking')
                visitor = next_response.get('visitorData')

        v3_response['nextPageToken'] = next_page_token
        v3_response['items'] = items
        if click_tracking:
            v3_response['clickTracking'] = click_tracking
        if visitor:
            v3_response['visitorData'] = visitor
        return v3_response

    def get_live_events(self,
                        event_type='live',
                        order='date',
                        page_token='',
                        location=False,
                        after=None,
                        **kwargs):
        """
        :param event_type: one of: 'live', 'completed', 'upcoming'
        :param order: one of: 'date', 'rating', 'relevance', 'title', 'videoCount', 'viewCount'
        :param page_token:
        :param location: bool, use geolocation
        :param after: str, RFC 3339 formatted date-time value (1970-01-01T00:00:00Z)
        :return:
        """
        # prepare params
        params = {'part': 'snippet',
                  'type': 'video',
                  'q': '-|',
                  'order': order,
                  'eventType': event_type,
                  'regionCode': self._region,
                  'hl': self._language,
                  'relevanceLanguage': self._language,
                  'maxResults': self.max_results()}

        if location:
            settings = self._context.get_settings()
            location = settings.get_location()
            if location:
                params['location'] = location
                params['locationRadius'] = settings.get_location_radius()

        if page_token:
            params['pageToken'] = page_token

        if after:
            if isinstance(after, string_type) and after.startswith('{'):
                after = json.loads(after)
            params['publishedAfter'] = (
                yt_datetime_offset(**after)
                if isinstance(after, dict) else
                after
            )

        return self.api_request(method='GET', path='search',
                                params=params,
                                **kwargs)

    def get_related_videos(self,
                           video_id,
                           page_token=None,
                           click_tracking=None,
                           visitor=None,
                           retry=0,
                           **kwargs):
        post_data = {'videoId': video_id}

        if page_token:
            post_data['continuation'] = page_token

        if click_tracking or visitor:
            context = {}
            if click_tracking:
                context['clickTracking'] = {
                    'clickTrackingParams': click_tracking,
                }
            if visitor:
                context['client'] = {
                    'visitorData': visitor,
                }
            post_data['context'] = context

        related_client = (
            'tv'
            if retry == 1 else
            'tv_embed'
            if retry == 2 else
            'v1'
        )
        result = self.api_request(related_client, 'POST', path='next',
                                  post_data=post_data,
                                  do_auth=False)
        if not result:
            return None

        related_videos = self.json_traverse(result, path=(
            (
                'onResponseReceivedEndpoints',
                0,
                'appendContinuationItemsAction',
                'continuationItems',
            ) if page_token else (
                'contents',
                'singleColumnWatchNextResults',
                'pivot',
                'pivot',
                'contents',
                slice(0, None, None),
                'pivotShelfRenderer',
                'content',
                'pivotHorizontalListRenderer',
                'items',
            ) if retry == 1 else (
               'contents',
               'singleColumnWatchNextResults',
               'results',
               'results',
               'contents',
               2,
               'shelfRenderer',
               'content',
               ('horizontalListRenderer', 'verticalListRenderer'),
               'items',
            ) if retry == 2 else (
                'contents',
                'twoColumnWatchNextResults',
                'secondaryResults',
                'secondaryResults',
                'results',
            )
        ) + (
            slice(None),
            (
                'pivotVideoRenderer',
                # 'videoId',
            ) if retry == 1 else (
                'compactVideoRenderer',
                # 'videoId',
            ) if retry == 2 else (
                (
                    'lockupViewModel',
                    # 'contentId',
                ),
                (
                    'compactVideoRenderer',
                    # 'videoId',
                ),
                (
                    'continuationItemRenderer',
                    'continuationEndpoint',
                    # 'continuationCommand',
                    # 'token',
                ),
            ),
        ), default=())
        if not related_videos or not any(related_videos):
            return {} if retry > 1 else self.get_related_videos(
                video_id,
                page_token=page_token,
                retry=(retry + 1),
                **kwargs
            )

        channel_id = self.json_traverse(result, path=(
            'contents',
            'singleColumnWatchNextResults',
            'results',
            'results',
            'contents',
            1,
            'itemSectionRenderer',
            'contents',
            0,
            'videoOwnerRenderer',
            'navigationEndpoint',
            'browseEndpoint',
            'browseId'
        ) if retry else (
            'contents',
            'twoColumnWatchNextResults',
            'results',
            'results',
            'contents',
            1,
            'videoSecondaryInfoRenderer',
            'owner',
            'videoOwnerRenderer',
            'title',
            'runs',
            0,
            'navigationEndpoint',
            'browseEndpoint',
            'browseId'
        ))

        if retry == 1:
            related_videos = chain.from_iterable(related_videos)

        items = []
        for item in related_videos:
            if not item:
                continue
            new_video_id = item.get('videoId')
            new_content_id = item.get('contentId')
            if new_video_id:
                items.append({
                    'kind': 'youtube#video',
                    'id': new_video_id,
                    '_related_video_id': video_id,
                    '_related_channel_id': channel_id,
                    '_partial': True,
                    'snippet': {
                        'title': self.json_traverse(item, path=(
                            'title',
                            (
                                (
                                    'simpleText',
                                ),
                                (
                                    'runs',
                                    0,
                                    'text'
                                ),
                            )
                        )),
                        'thumbnails': item['thumbnail']['thumbnails'],
                        'channelId': self.json_traverse(item, path=(
                            ('longBylineText', 'shortBylineText'),
                            'runs',
                            0,
                            'navigationEndpoint',
                            'browseEndpoint',
                            'browseId',
                        )),
                    },
                })
            elif new_content_id:
                content_type = item.get('contentType')
                if content_type == 'LOCKUP_CONTENT_TYPE_VIDEO':
                    items.append({
                        'kind': 'youtube#video',
                        'id': new_content_id,
                        '_related_video_id': video_id,
                        '_related_channel_id': channel_id,
                        '_partial': True,
                        'snippet': {
                            'title': self.json_traverse(item, path=(
                                'metadata',
                                'lockupMetadataViewModel',
                                'title',
                                'content',
                            )),
                            'thumbnails': self.json_traverse(item, path=(
                                'contentImage',
                                'thumbnailViewModel',
                                'image',
                                'sources',
                            )),
                            'channelId': self.json_traverse(item, path=(
                                'metadata',
                                'lockupMetadataViewModel',
                                'image',
                                'decoratedAvatarViewModel',
                                'rendererContext',
                                'commandContext',
                                'onTap',
                                'innertubeCommand',
                                'browseEndpoint',
                                'browseId',
                            )),
                        },
                    })
                elif content_type in {'LOCKUP_CONTENT_TYPE_PLAYLIST',
                                      'LOCKUP_CONTENT_TYPE_PODCAST'}:
                    items.append({
                        'kind': 'youtube#playlist',
                        'id': new_content_id,
                        '_related_video_id': video_id,
                        '_related_channel_id': channel_id,
                        '_partial': True,
                        'snippet': {
                            'title': self.json_traverse(item, path=(
                                'metadata',
                                'lockupMetadataViewModel',
                                'title',
                                'content',
                            )),
                            'thumbnails': self.json_traverse(item, path=(
                                'contentImage',
                                'collectionThumbnailViewModel',
                                'primaryThumbnail',
                                'thumbnailViewModel',
                                'image',
                                'sources',
                            )),
                            'channelId': self.json_traverse(item, path=(
                                'metadata',
                                'lockupMetadataViewModel',
                                'image',
                                'decoratedAvatarViewModel',
                                'rendererContext',
                                'commandContext',
                                'onTap',
                                'innertubeCommand',
                                'browseEndpoint',
                                'browseId',
                            )),
                            'resourceId': {
                                'videoId': self.json_traverse(item, path=(
                                    'rendererContext',
                                    'commandContext',
                                    'onTap',
                                    'innertubeCommand',
                                    'watchEndpoint',
                                    'videoId',
                                )),
                            },
                        },
                    })

        if retry:
            next_page_token = None
            click_tracking = None
        else:
            continuation = related_videos[-1]
            next_page_token = self.json_traverse(continuation, path=(
                'continuationCommand',
                'token',
            ))
            if next_page_token and next_page_token != page_token:
                click_tracking = continuation.get('clickTrackingParams')
            else:
                next_page_token = None
                click_tracking = None

        v3_response = {
            'kind': 'youtube#videoListResponse',
            'items': items or [],
            'nextPageToken': next_page_token,
            'visitorData': self.json_traverse(result, path=(
                'responseContext',
                'visitorData',
            )),
            'clickTracking': click_tracking,
        }
        return v3_response

    def get_parent_comments(self,
                            video_id,
                            page_token='',
                            max_results=0,
                            **kwargs):
        # prepare params
        params = {
            'part': 'snippet',
            'videoId': video_id,
            'order': 'relevance',
            'textFormat': 'plainText',
            'maxResults': (
                self.max_results()
                if max_results <= 0 else
                max_results
            ),
        }
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET', path='commentThreads',
                                params=params,
                                **kwargs)

    def get_child_comments(self,
                           parent_id,
                           page_token='',
                           max_results=0,
                           **kwargs):

        # prepare params
        params = {
            'part': 'snippet',
            'parentId': parent_id,
            'textFormat': 'plainText',
            'maxResults': (
                self.max_results()
                if max_results <= 0 else
                max_results
            ),
        }
        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET', path='comments',
                                params=params,
                                **kwargs)

    def get_channel_videos(self, channel_id, page_token='', **kwargs):
        """
        Returns a collection of video search results for the specified channel_id
        """

        params = {'part': 'snippet',
                  'hl': self._language,
                  'maxResults': self.max_results(),
                  'type': 'video',
                  'safeSearch': 'none',
                  'order': 'date'}

        if channel_id == 'mine':
            params['forMine'] = True
        else:
            function_cache = self._context.get_function_cache()
            channel_id = function_cache.run(
                self.get_channel_by_identifier,
                function_cache.ONE_MONTH,
                _refresh=self._context.refresh_requested(),
                identifier=channel_id,
            )
            params['channelId'] = channel_id

        if page_token:
            params['pageToken'] = page_token

        return self.api_request(method='GET', path='search',
                                params=params,
                                **kwargs)

    def search(self,
               q,
               search_type=None,
               _search_type={'video', 'channel', 'playlist'},
               event_type=None,
               _event_type={'live', 'upcoming', 'completed'},
               channel_id=None,
               channel_type=None,
               _channel_type={'any', 'show'},
               order='relevance',
               safe_search='moderate',
               _safe_search={'moderate', 'none', 'strict'},
               video_type=None,
               _video_type={'any', 'episode', 'movie'},
               page_token='',
               location=False,
               **kwargs):
        """

        Returns a collection of search results that match the query parameters specified in the API request. By default,
        a search result set identifies matching video, channel, and playlist resources, but you can also configure
        queries to only retrieve a specific type of resource.

        :param str  q: The q parameter specifies the query term to search for. Query can also use the Boolean NOT (-)
            and OR (|) operators to exclude videos or to find videos that are associated with one of several search
            terms.
        :param str  search_type: Acceptable values are: 'video', 'channel' or 'playlist'
        :param str  event_type: Restricts a search to broadcast events. If you specify a value for this parameter, you
            must also set the type parameter's value to video.
            Acceptable values are:
                - `live`
                - `completed`
                - `upcoming`
        :param str  channel_id: limit search to channel id
        :param str  channel_type: Restrict a search to a particular type of channel.
            Acceptable values are:
                - `any`         : return all channels.
                - `show`        : only retrieve shows.
        :param str  order: Specifies the method that will be used to order resources in the API response. The default
            value is relevance.
            Acceptable values are:
                - `date`        : reverse chronological order based on the date created.
                - `rating`      : highest to lowest rating.
                - `relevance`   : sorted based on their relevance to the search query.
                - `title`       : alphabetically by title.
                - `videoCount`  : channels are sorted in descending order of their number of uploaded videos.
                - `viewCount`   : highest to lowest number of views or concurrent viewers for live broadcasts.
        :param str  safe_search: one of: 'moderate', 'none', 'strict'
        :param str  page_token: can be ''
        :param bool location: use geolocation
        :param str  video_type: Restrict a search to a particular type of videos. If you specify a value for this
            parameter, you must also set the type parameter's value to video.
            Acceptable values are:
                - `any`     : return all videos.
                - `episode` : only retrieve episodes of shows.
                - `movie`   : only retrieve movies.
        :return:
        """

        # prepare params
        params = {'q': q.replace('|', '%7C') if '|' in q else q,
                  'part': 'snippet',
                  'regionCode': self._region,
                  'hl': self._language,
                  'relevanceLanguage': self._language,
                  'maxResults': self.max_results()}

        if search_type and isinstance(search_type, (list, tuple)):
            search_type = ','.join(search_type)
        elif not search_type or search_type not in _search_type:
            search_type = ','.join(_search_type)
        if search_type:
            params['type'] = search_type

        if event_type and event_type in _event_type:
            params['eventType'] = event_type
            params['type'] = 'video'

        if channel_id:
            function_cache = self._context.get_function_cache()
            channel_id = function_cache.run(
                self.get_channel_by_identifier,
                function_cache.ONE_MONTH,
                _refresh=self._context.refresh_requested(),
                identifier=channel_id,
                do_search=False,
            )
            params['channelId'] = channel_id

        if channel_type and channel_type in _channel_type:
            params['channelType'] = channel_type

        if order:
            params['order'] = order

        if safe_search and safe_search in _safe_search:
            params['safeSearch'] = safe_search

        if video_type and video_type in _video_type:
            params['videoType'] = video_type
            params['type'] = 'video'

        if page_token:
            params['pageToken'] = page_token

        if location:
            settings = self._context.get_settings()
            location = settings.get_location()
            if location:
                params['location'] = location
                params['locationRadius'] = settings.get_location_radius()
                params['type'] = 'video'

        return self.api_request(method='GET', path='search',
                                params=params,
                                **kwargs)

    def search_with_params(self,
                           params,
                           _video_only_params={
                               'eventType',
                               'forMine',
                               'location',
                               'relatedToVideoId',
                               'videoCaption',
                               'videoCategoryId',
                               'videoDefinition',
                               'videoDimension',
                               'videoDuration',
                               'videoEmbeddable',
                               'videoLicense',
                               'videoSyndicated',
                               'videoType',
                           },
                           **kwargs):
        settings = self._context.get_settings()

        # prepare default params
        search_params = {
            'part': 'snippet',
            'regionCode': self._region,
            'hl': self._language,
            'relevanceLanguage': self._language,
        }

        search_query = params.get('q', '')
        if '|' in search_query:
            search_params['q'] = search_query.replace('|', '%7C')

        max_results = params.get('maxResults')
        if max_results is None:
            search_params['maxResults'] = self.max_results()

        search_type = params.get('type')
        if isinstance(search_type, (list, tuple)):
            search_params['type'] = ','.join(search_type)

        channel_id = params.get('channelId')
        if channel_id == 'mine':
            del params['channelId']
            params['forMine'] = True
        elif channel_id:
            function_cache = self._context.get_function_cache()
            channel_id = function_cache.run(
                self.get_channel_by_identifier,
                function_cache.ONE_MONTH,
                _refresh=self._context.refresh_requested(),
                identifier=channel_id,
                do_search=False,
            )
            params['channelId'] = channel_id

        location = params.get('location')
        if location is True:
            location = settings.get_location()
            if location:
                search_params['location'] = location
                search_params['locationRadius'] = settings.get_location_radius()

        safe_search = params.get('safeSearch')
        if safe_search is None:
            search_params['safeSearch'] = settings.safe_search()

        published = params.get('publishedBefore')
        if published:
            if isinstance(published, string_type) and published.startswith('{'):
                published = json.loads(published)
            search_params['publishedBefore'] = (
                yt_datetime_offset(**published)
                if isinstance(published, dict) else
                published
            )

        published = params.get('publishedAfter')
        if published:
            if isinstance(published, string_type) and published.startswith('{'):
                published = json.loads(published)
            search_params['publishedAfter'] = (
                yt_datetime_offset(**published)
                if isinstance(published, dict) else
                published
            )

        params = {
            param: value
            for param, value in params.items()
            if value
        }
        search_params.update([
            (param, value)
            for param, value in params.items()
            if param not in search_params
        ])

        if not _video_only_params.isdisjoint(search_params.keys()):
            search_params['type'] = 'video'

        return (params,
                self.api_request(method='GET', path='search',
                                 params=search_params,
                                 **kwargs))

    def get_my_subscriptions(self,
                             page_token=1,
                             do_filter=False,
                             feed_type='videos',
                             refresh=False,
                             force_cache=False,
                             progress_dialog=None,
                             **kwargs):
        """
        modified by PureHemp, using YouTube RSS for fetching latest videos
        """

        v3_response = {
            'kind': 'youtube#videoListResponse',
            'items': [],
            'pageInfo': {
                'totalResults': 0,
                'resultsPerPage': self.max_results(),
            },
            '_item_filter': None,
        }

        context = self._context
        feed_history = context.get_feed_history()
        function_cache = context.get_function_cache()
        settings = context.get_settings()

        if do_filter:
            _, filters_set, custom_filters = channel_filter_split(
                settings.subscriptions_filter()
            )
            item_filter = {
                'custom': custom_filters,
            }
            channel_filters = {
                'blacklist': settings.subscriptions_filter_blacklist(),
                'names': filters_set,
            }
        else:
            item_filter = None
            channel_filters = None

        page = page_token or 1
        totals = {
            'num': 0,
            'start': -self.max_results(),
            'end': page * self.max_results(),
            'video_ids': set(),
        }
        totals['start'] += totals['end']

        def _sort_by_date_time(item, limits):
            video_id = item['id']
            if video_id in limits['video_ids']:
                return -1
            limits['num'] += 1
            limits['video_ids'].add(video_id)
            if '_timestamp' in item:
                timestamp = item['_timestamp']
            else:
                timestamp = since_epoch(item['snippet'].get('publishedAt'))
                item['_timestamp'] = timestamp
            return timestamp

        threaded_output = {
            'channel_ids': [],
            'playlist_ids': [],
            'feeds': {},
            'to_refresh': [],
        }

        bookmarks = context.get_bookmarks_list().get_items()
        if bookmarks:
            channel_ids = threaded_output['channel_ids']
            playlist_ids = threaded_output['playlist_ids']
            for item_id, item in bookmarks.items():
                if isinstance(item, DirectoryItem):
                    item_id = getattr(item, PLAYLIST_ID, None)
                    if item_id:
                        playlist_ids.append(item_id)
                        continue
                    item_id = getattr(item, CHANNEL_ID, None)
                elif not isinstance(item, float):
                    continue
                if item_id:
                    channel_ids.append(item_id)

        headers = {
            'Host': 'www.youtube.com',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                          ' AppleWebKit/537.36 (KHTML, like Gecko)'
                          ' Chrome/87.0.4280.66'
                          ' Safari/537.36',
            'Accept': 'text/html,'
                      'application/xhtml+xml,'
                      'application/xml;q=0.9,'
                      'image/webp,*/*;q=0.8',
            'DNT': '1',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.7,de;q=0.3'
        }

        def _get_cached_feed(output,
                             inputs,
                             item_type,
                             feed_type=feed_type,
                             _refresh=refresh,
                             feed_history=feed_history,
                             ttl=feed_history.ONE_HOUR):
            feeds = output['feeds']
            to_refresh = output['to_refresh']
            if item_type == 'channel_id':
                channel_prefix = (
                    'UUSH' if feed_type == 'shorts' else
                    'UULV' if feed_type == 'live' else
                    'UULF'
                )
            else:
                channel_prefix = False
            for item_id in inputs:
                if channel_prefix:
                    channel_id = item_id
                    item_id = item_id.replace('UC', channel_prefix, 1)
                else:
                    channel_id = None
                cached = feed_history.get_item(item_id, seconds=ttl)

                if cached:
                    feed_details = cached['value']
                    feed_details['refresh'] = _refresh
                    if channel_id:
                        feed_details.setdefault('channel_id', channel_id)
                        if _refresh:
                            to_refresh.append({item_type: channel_id})
                    elif _refresh:
                        to_refresh.append({item_type: item_id})
                    if item_id in feeds:
                        feeds[item_id].update(feed_details)
                    else:
                        feeds[item_id] = feed_details
                elif channel_id:
                    to_refresh.append({item_type: channel_id})
                else:
                    to_refresh.append({item_type: item_id})
            del inputs[:]
            return True, False

        def _get_feed(output,
                      channel_id=None,
                      playlist_id=None,
                      feed_type=feed_type,
                      headers=headers):
            if channel_id:
                item_id = channel_id.replace(
                    'UC',
                    'UUSH' if feed_type == 'shorts' else
                    'UULV' if feed_type == 'live' else
                    'UULF',
                    1,
                )
            elif playlist_id:
                item_id = playlist_id
            else:
                return True, False

            response = self.request(
                ''.join((self.BASE_URL,
                         '/feeds/videos.xml?playlist_id=',
                         item_id)),
                headers=headers,
            )
            if response is None:
                return False, True
            with response:
                if response.status_code == 404:
                    content = None
                elif response.status_code == 429:
                    return False, True
                else:
                    response.encoding = 'utf-8'
                    content = response.content

            _output = {
                'channel_id': channel_id,
                'content': content,
                'refresh': True,
            }

            feeds = output['feeds']
            if item_id in feeds:
                feeds[item_id].update(_output)
            else:
                feeds[item_id] = _output
            return True, False

        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'yt': 'http://www.youtube.com/xml/schemas/2015',
            'media': 'http://search.yahoo.com/mrss/',
        }

        def _parse_feeds(feeds,
                         sort_method,
                         sort_limits,
                         progress_dialog=None,
                         filters=channel_filters,
                         ns=namespaces,
                         feed_history=feed_history,
                         function_cache=function_cache):
            if progress_dialog:
                total = len(feeds)
                progress_dialog.reset_total(
                    total,
                    _message=context.localize('feeds'),
                )

            dict_get = {}.get
            find = ET_Element.find
            findtext = ET_Element.findtext

            all_items = {}
            new_cache = {}
            for item_id, feed in feeds.items():
                channel_id = feed.get('channel_id')
                channel_name = feed.get('channel_name')
                cached_items = feed.get('cached_items')
                refresh_feed = feed.get('refresh')
                content = feed.get('content')

                if refresh_feed and content:
                    root = ET_XML(content)
                    channel_name = findtext(
                        root,
                        'atom:author/atom:name',
                        '',
                        ns,
                    )
                    channel_id = findtext(root, 'yt:channelId', '', ns)
                    if not channel_id.startswith('UC'):
                        channel_id = 'UC' + channel_id
                    playlist_id = findtext(root, 'yt:playlistId', '', ns)

                    feed_items = [{
                        'kind': ('youtube#video'
                                 if channel_id else
                                 'youtube#playlistitem'),
                        'id': (findtext(item, 'yt:videoId', '', ns)
                               if channel_id else
                               None),
                        'snippet': {
                            'videoOwnerChannelId': channel_id,
                            'playlistId': playlist_id,
                            'channelTitle': channel_name,
                            'resourceId': {
                                'videoId': findtext(item, 'yt:videoId', '', ns)
                            } if playlist_id else None,
                            'title': findtext(item, 'atom:title', '', ns),
                            'description': findtext(
                                item,
                                'media:group/media:description',
                                '',
                                ns,
                            ),
                            'publishedAt': strptime(
                                findtext(item, 'atom:published', '', ns)
                            ),
                        },
                        'statistics': {
                            'likeCount': getattr(find(
                                item,
                                'media:group/media:community/media:starRating',
                                ns,
                            ), 'get', dict_get)('count', 0),
                            'viewCount': getattr(find(
                                item,
                                'media:group/media:community/media:statistics',
                                ns,
                            ), 'get', dict_get)('views', 0),
                        },
                        '_partial': True,
                    } for item in root.findall('atom:entry', ns)]
                else:
                    feed_items = []

                if feed_items:
                    if cached_items:
                        feed_items.extend(cached_items)
                    feed_limits = {
                        'num': 0,
                        'video_ids': set(),
                    }
                    feed_items.sort(reverse=True,
                                    key=partial(sort_method,
                                                limits=feed_limits))
                    feed_items = feed_items[:min(1000, feed_limits['num'])]
                elif cached_items:
                    feed_items = cached_items

                if refresh_feed:
                    new_cache[item_id] = {
                        'channel_id': channel_id,
                        'channel_name': channel_name,
                        'cached_items': feed_items,
                    }
                if not feed_items:
                    continue

                if filters and filters['names']:
                    if channel_id and function_cache.run(
                            self.channel_match,
                            function_cache.ONE_MONTH,
                            _refresh=refresh_feed,
                            identifier=channel_id,
                            identifiers=filters['names'],
                            exclude=filters['blacklist'],
                    ):
                        all_items[item_id] = feed_items
                else:
                    all_items[item_id] = feed_items

                if progress_dialog:
                    progress_dialog.update(position=len(all_items))

            if new_cache:
                feed_history.set_items(new_cache)

            # filter, sorting by publish date and trim
            if all_items:
                return sorted(
                    chain.from_iterable(all_items.values()),
                    reverse=True,
                    key=partial(sort_method, limits=sort_limits),
                )
            return None

        def _threaded_fetch(kwargs,
                            do_batch,
                            output,
                            worker,
                            threads,
                            pool_id,
                            check_inputs,
                            **_kwargs):
            active_thread_ids = threads['active_thread_ids']
            thread_id = threading.current_thread().ident
            active_thread_ids.add(thread_id)
            counts = threads['counts']
            complete = False
            while not threads['balance'].is_set():
                threads['loop_enable'].set()
                if kwargs is True:
                    _kwargs = {}
                elif kwargs:
                    _kwargs = {'inputs': kwargs} if do_batch else kwargs.pop()
                elif check_inputs:
                    if check_inputs.wait(0.1) and kwargs:
                        continue
                    break
                else:
                    complete = True
                    break

                try:
                    success, complete = worker(output, **_kwargs)
                except Exception:
                    self.log.exception('Error')
                    continue

                if complete or not success or not counts[pool_id]:
                    break
            else:
                threads['balance'].clear()

            threads['counter'].release()
            if complete:
                counts[pool_id] = None
            elif counts[pool_id]:
                counts[pool_id] -= 1
            counts['all'] -= 1
            threads['active_thread_ids'].discard(thread_id)
            threads['loop_enable'].set()

        max_threads = min(32, 2 * (available_cpu_count() + 4))
        counts = {
            'all': 0,
        }
        active_thread_ids = set()
        counter = threading.Semaphore(max_threads)
        balance_enable = threading.Event()
        loop_enable = threading.Event()
        threads = {
            'balance': balance_enable,
            'loop_enable': loop_enable,
            'counter': counter,
            'counts': counts,
            'active_thread_ids': active_thread_ids,
        }

        payloads = {}
        if self.logged_in:
            function_cache = context.get_function_cache()

            channel_params = {
                'part': 'snippet,contentDetails',
                'maxResults': 50,
                'order': 'unread',
                'mine': True,
            }

            def _get_updated_subscriptions(new_data, old_data):
                items = new_data and new_data.get('items')
                if not items:
                    new_data['_abort'] = True
                    return new_data

                _items = old_data and old_data.get('items')
                if _items:
                    _items = {
                        item['snippet']['resourceId']['channelId']:
                            item['contentDetails']
                        for item in _items
                    }

                    updated_subscriptions = []
                    old_subscriptions = []

                    for item in items:
                        channel_id = item['snippet']['resourceId']['channelId']
                        counts = item['contentDetails']

                        if (counts['newItemCount']
                                or counts['totalItemCount']
                                > _items.get(channel_id, {})['totalItemCount']):
                            updated_subscriptions.append(
                                {
                                    'channel_id': channel_id,
                                }
                            )
                        else:
                            old_subscriptions.append(channel_id)

                    if old_subscriptions:
                        new_data['nextPageToken'] = None
                else:
                    updated_subscriptions = [
                        {
                            'channel_id':
                                item['snippet']['resourceId']['channelId'],
                        }
                        for item in items
                    ]
                    old_subscriptions = []

                new_data['_updated_subscriptions'] = updated_subscriptions
                new_data['_old_subscriptions'] = old_subscriptions
                return new_data

            def _get_channels(output,
                              _params=channel_params,
                              _refresh=refresh,
                              _force_cache=force_cache,
                              function_cache=function_cache):
                json_data = function_cache.run(
                    self.api_request, method='GET', path='subscriptions',
                    seconds=(function_cache.ONE_HOUR
                             if _force_cache or 'pageToken' in _params else
                             5 * function_cache.ONE_MINUTE),
                    _refresh=_refresh,
                    _process=_get_updated_subscriptions,
                    params=_params,
                    **kwargs
                )
                if not json_data or json_data.get('_abort'):
                    return False, True

                updated_subscriptions = json_data.get('_updated_subscriptions')
                if updated_subscriptions:
                    output['to_refresh'].extend(updated_subscriptions)

                old_subscriptions = json_data.get('_old_subscriptions')
                if old_subscriptions:
                    output['channel_ids'].extend(old_subscriptions)

                page_token = json_data.get('nextPageToken')
                if page_token:
                    _params['pageToken'] = page_token
                    return True, False
                if 'pageToken' in _params:
                    del _params['pageToken']
                return True, True

            # playlist_params = {
            #     'part': 'snippet',
            #     'maxResults': 50,
            #     'order': 'alphabetical',
            #     'mine': True,
            # }
            #
            # def _get_playlists(output,
            #                    _params=playlist_params,
            #                    _refresh=refresh,
            #                    _force_cache=force_cache,
            #                    function_cache=function_cache):
            #     json_data = function_cache.run(
            #         self.get_saved_playlists,
            #         function_cache.ONE_HOUR
            #         if _force_cache or 'pageToken' in _params else
            #         5 * function_cache.ONE_MINUTE,
            #         _refresh=_refresh,
            #         **kwargs
            #     )
            #     if not json_data:
            #         return False, True
            #
            #     output['playlist_ids'].extend([{
            #         'playlist_id': item['snippet']['resourceId']['playlistId']
            #     } for item in json_data.get('items', [])])
            #
            #     subs_page_token = json_data.get('nextPageToken')
            #     if subs_page_token:
            #         _params['pageToken'] = subs_page_token
            #         return True, False
            #     return True, True

            payloads[1] = {
                'worker': _get_channels,
                'kwargs': True,
                'do_batch': False,
                'output': threaded_output,
                'threads': threads,
                'limit': 1,
                'check_inputs': False,
                'inputs_to_check': None,
            }
            # payloads[2] = {
            #     'worker': _get_playlists,
            #     'kwargs': True,
            #     'output': threaded_output,
            #     'threads': threads,
            #     'limit': 1,
            #     'check_inputs': False,
            #     'inputs_to_check': None,
            # }
        payloads[3] = {
            'worker': partial(_get_cached_feed, item_type='channel_id'),
            'kwargs': threaded_output['channel_ids'],
            'do_batch': True,
            'output': threaded_output,
            'threads': threads,
            'limit': None,
            'check_inputs': threading.Event(),
            'inputs_to_check': {1},
        }
        payloads[4] = {
            'worker': partial(_get_cached_feed, item_type='playlist_id'),
            'kwargs': threaded_output['playlist_ids'],
            'do_batch': True,
            'output': threaded_output,
            'threads': threads,
            'limit': None,
            # 'check_inputs': threading.Event(),
            # 'inputs_to_check': {2},
            'check_inputs': False,
            'inputs_to_check': None,
        }
        payloads[5] = {
            'worker': _get_feed,
            'kwargs': threaded_output['to_refresh'],
            'do_batch': False,
            'output': threaded_output,
            'threads': threads,
            'limit': None,
            'check_inputs': threading.Event(),
            'inputs_to_check': {3, 4},
        }

        completed = []
        remaining = payloads.keys()
        iterator = iter(payloads)
        loop_enable.set()
        while loop_enable.wait(1) or active_thread_ids:
            try:
                pool_id = next(iterator)
            except StopIteration:
                if active_thread_ids:
                    loop_enable.clear()
                for pool_id in completed:
                    del payloads[pool_id]
                remaining = payloads.keys()
                if not remaining and not active_thread_ids:
                    break
                completed = []
                iterator = iter(payloads)
                if progress_dialog:
                    progress_dialog.grow_total(
                        len(threaded_output['channel_ids'])
                        + len(threaded_output['playlist_ids']),
                    )
                    progress_dialog.update(
                        position=len(threaded_output['feeds']),
                    )
                continue

            payload = payloads[pool_id]
            payload['pool_id'] = pool_id
            current_num = counts.setdefault(pool_id, 0)
            if current_num is None:
                completed.append(pool_id)
                continue

            check_inputs = payload['check_inputs']
            if check_inputs:
                if payload['kwargs']:
                    check_inputs.set()
                else:
                    inputs = payload['inputs_to_check']
                    if not inputs or inputs.isdisjoint(remaining):
                        check_inputs.set()
                        completed.append(pool_id)
                    continue

            available = max_threads - counts['all']
            limit = payload['limit']
            if limit:
                if current_num >= limit:
                    continue
                if available <= 0:
                    balance_enable.set()
            elif available <= 0:
                continue

            new_thread = threading.Thread(
                target=_threaded_fetch,
                kwargs=payload,
            )
            new_thread.daemon = True
            counts[pool_id] += 1
            counts['all'] += 1
            counter.acquire(True)
            new_thread.start()

        items = _parse_feeds(
            threaded_output['feeds'],
            sort_method=_sort_by_date_time,
            sort_limits=totals,
            progress_dialog=progress_dialog,
        )
        if not items:
            return None

        if totals['num'] > totals['end']:
            v3_response['nextPageToken'] = page + 1
        if totals['num'] > totals['start']:
            items = items[totals['start']:min(totals['num'], totals['end'])]
        else:
            return None

        v3_response['pageInfo']['totalResults'] = totals['num']
        v3_response['items'] = items
        v3_response['_item_filter'] = item_filter
        return v3_response

    def _auth_required(self, params):
        if params:
            if params.get('mine') or params.get('forMine'):
                return True
            request_channel_id = params.get('channelId')
            if request_channel_id == 'mine':
                return True
        else:
            request_channel_id = None

        uri_channel_id = self._context.get_param(CHANNEL_ID)
        if uri_channel_id == 'mine':
            return True

        channel_id = self.channel_id
        if channel_id and channel_id in (uri_channel_id, request_channel_id):
            return True
        return False

    def _request_response_hook(self, **kwargs):
        response = kwargs['response']
        if response is None:
            return None, None
        with response:
            headers = response.headers
            if kwargs.get('extended_debug'):
                self.log.debug(('Request response',
                                'Status:  {response.status_code!r}',
                                'Headers: {headers!r}',
                                'Content: {response.text}'),
                               response=response,
                               headers=headers._store if headers else None,
                               stacklevel=4)
            else:
                self.log.debug(('Request response',
                                'Status:  {response.status_code!r}',
                                'Headers: {headers!r}'),
                               response=response,
                               headers=headers._store if headers else None,
                               stacklevel=4)

            if response.status_code == 204 and 'no_content' in kwargs:
                return None, True

            try:
                json_data = response.json()
            except ValueError as exc:
                if kwargs.get('raise_exc') is None:
                    kwargs['raise_exc'] = True
                raise InvalidJSON(exc, **kwargs)

            if 'error' in json_data:
                kwargs.setdefault('pass_data', True)
                raise YouTubeException('"error" in response JSON data',
                                       json_data=json_data,
                                       **kwargs)

            response.raise_for_status()
        return json_data.get('etag'), json_data

    def _request_error_hook(self, **kwargs):
        exc = kwargs['exc']
        json_data = getattr(exc, 'json_data', None)
        if getattr(exc, 'pass_data', False):
            data = json_data
        else:
            data = kwargs['response']
        if getattr(exc, 'raise_exc', False):
            exception = YouTubeException
        else:
            exception = None

        if not json_data or 'error' not in json_data:
            return 'API request error', None, None, data, exception

        details = json_data['error']
        reason = details.get('errors', [{}])[0].get('reason', 'Unknown')
        message = strip_html_from_text(details.get('message', 'Unknown error'))

        if getattr(exc, 'notify', True):
            context = self._context
            ok_dialog = False
            if reason in {'accessNotConfigured', 'forbidden'}:
                notification = context.localize('key.requirement')
                ok_dialog = True
            elif reason == 'keyInvalid' and message == 'Bad Request':
                notification = context.localize('api.key.incorrect')
            elif reason in {'quotaExceeded', 'dailyLimitExceeded'}:
                notification = message
            elif reason == 'authError':
                auth_type = kwargs.get('_auth_type')
                if auth_type:
                    if auth_type in self._access_tokens:
                        self._access_tokens[auth_type] = None
                    self.set_access_token(self._access_tokens)
                    context.get_access_manager().update_access_token(
                        context.get_param('addon_id'),
                        access_token=self.convert_access_tokens(to_list=True),
                    )
                notification = message
            else:
                notification = message

            title = ': '.join((context.get_name(), reason))
            if ok_dialog:
                context.get_ui().on_ok(title, notification)
            else:
                context.get_ui().show_notification(notification, title)

        info = (
            'Reason:   {error_reason}',
            'Message:  {error_message}',
        )
        details = {
            'error_reason': reason,
            'error_message': message,
        }
        return 'API request error', info, details, data, exception

    def api_request(self,
                    client='v3',
                    method='GET',
                    client_data=None,
                    url=None,
                    path=None,
                    params=None,
                    post_data=None,
                    headers=None,
                    do_auth=None,
                    cache=None,
                    **kwargs):
        if not client_data:
            client_data = {}
        client_data.setdefault('method', method)
        if path:
            client_data['_endpoint'] = path.strip('/')
        if url:
            client_data['url'] = url
        if headers:
            client_data['headers'] = headers
        if method in {'POST', 'PUT'}:
            if post_data:
                client_data['json'] = post_data
            clear_data = False
            if do_auth is None:
                do_auth = True
        else:
            if do_auth is None and method == 'DELETE':
                do_auth = True
            clear_data = True
        if params:
            client_data['params'] = params

        if do_auth is None:
            do_auth = self._auth_required(params)
        if do_auth:
            abort = not self.logged_in
            client_data.setdefault('_auth_required', do_auth)
        else:
            abort = False

        client_data['_access_tokens'] = access_tokens = {}
        client_data['_api_keys'] = api_keys = {}
        for config_type, config in self._configs.items():
            if not config:
                continue

            key = config.get('key')
            if key:
                api_keys[config_type] = key

            if not config.get('token-allowed', True):
                continue
            access_token = self._access_tokens.get(config_type)
            if access_token:
                access_tokens[config_type] = access_token

        client = self.build_client(client, client_data)
        if not client:
            client = {}
            abort = True

        if clear_data and 'json' in client:
            del client['json']

        params = client.get('params')
        if params:
            log_params = params.copy()

            if 'key' in params:
                key = params['key']
                if key:
                    abort = False
                    log_params['key'] = ('...'.join((key[:3], key[-3:]))
                                         if len(key) > 9 else
                                         '...')
                elif not client['_has_auth']:
                    abort = True

            if 'location' in params:
                log_params['location'] = 'xx.xxxx,xx.xxxx'
        else:
            log_params = None

        headers = client.get('headers')
        if headers:
            log_headers = headers.copy()
            if 'Authorization' in log_headers:
                log_headers['Authorization'] = '<redacted>'
        else:
            log_headers = None

        context = self._context
        self.log.debug(('{request_name} API request',
                        'method:    {method!r}',
                        'path:      {path!r}',
                        'params:    {params!r}',
                        'post_data: {data!r}',
                        'headers:   {headers!r}'),
                       request_name=client.get('_name'),
                       method=method,
                       path=path,
                       params=log_params,
                       data=client.get('json'),
                       headers=log_headers,
                       stacklevel=2)
        if abort:
            if kwargs.get('notify', True):
                context.get_ui().on_ok(
                    context.get_name(),
                    context.localize('key.requirement'),
                )
            self.log.warning('Aborted', stacklevel=2)
            return {}
        if context.get_settings().log_level() & 2:
            kwargs.setdefault('extended_debug', True)
        if cache is None and 'no_content' in kwargs:
            cache = False
        elif cache is not False and self._context.refresh_requested():
            cache = 'refresh'
        return self.request(response_hook=self._request_response_hook,
                            event_hook_kwargs=kwargs,
                            error_hook=self._request_error_hook,
                            stacklevel=3,
                            cache=cache,
                            **client)
