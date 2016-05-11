__author__ = 'bromix'

from resources.lib.kodion import simple_requests as requests
from .login_client import LoginClient
from ..helper.video_info import VideoInfo

class YouTube(LoginClient):
    def __init__(self, config={}, language='en-US', region='US', items_per_page=50, access_token='', access_token_tv=''):
        
        LoginClient.__init__(self, config=config, language=language, region=region, access_token=access_token,
                             access_token_tv=access_token_tv)

        self._max_results = items_per_page
        pass

    def get_max_results(self):
        return self._max_results

    def get_language(self):
        return self._language

    def get_region(self):
        return self._region

    def calculate_next_page_token(self, page, max_result):
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
            pass
        low_iteration = position % len_low

        # at this position the iteration starts with 'I' again (after 'P')
        if position >= 256:
            multiplier = (position // 128) - 1
            position -= 128 * multiplier
            pass
        high_iteration = (position / len_low) % len_high

        return 'C%s%s%sAA' % (high[high_iteration], low[low_iteration], overflow_token)

    def update_watch_history(self, video_id):
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
            pass

        url = 'https://www.youtube.com/user_watch'

        result = requests.get(url, params=params, headers=headers, verify=False, allow_redirects=True)
        pass

    def get_video_streams(self, context, video_id):
        video_info = VideoInfo(context, access_token=self._access_token, language=self._language)

        video_streams = video_info.load_stream_infos(video_id)

        # update title
        for video_stream in video_streams:
            title = '[B]%s[/B] (%s;%s / %s@%d)' % (
                video_stream['title'], video_stream['container'], video_stream['video']['encoding'],
                video_stream['audio']['encoding'], video_stream['audio']['bitrate'])
            video_stream['title'] = title
            pass
        return video_streams

    def remove_playlist(self, playlist_id):
        params = {'id': playlist_id,
                  'mine': 'true'}
        return self._perform_v3_request(method='DELETE', path='playlists', params=params)

    def get_supported_languages(self, language=None):
        _language = language
        if not _language:
            _language = self._language
            pass
        _language = _language.replace('-', '_')
        params = {'part': 'snippet',
                  'hl': _language}
        return self._perform_v3_request(method='GET', path='i18nLanguages', params=params)

    def get_supported_regions(self, language=None):
        _language = language
        if not _language:
            _language = self._language
            pass
        _language = _language.replace('-', '_')
        params = {'part': 'snippet',
                  'hl': _language}
        return self._perform_v3_request(method='GET', path='i18nRegions', params=params)

    def rename_playlist(self, playlist_id, new_title, privacy_status='private'):
        params = {'part': 'snippet,id,status'}
        post_data = {'kind': 'youtube#playlist',
                     'id': playlist_id,
                     'snippet': {'title': new_title},
                     'status': {'privacyStatus': privacy_status}}
        return self._perform_v3_request(method='PUT', path='playlists', params=params, post_data=post_data)

    def create_playlist(self, title, privacy_status='private'):
        params = {'part': 'snippet,status'}
        post_data = {'kind': 'youtube#playlist',
                     'snippet': {'title': title},
                     'status': {'privacyStatus': privacy_status}}
        return self._perform_v3_request(method='POST', path='playlists', params=params, post_data=post_data)

    def get_video_rating(self, video_id):
        if isinstance(video_id, list):
            video_id = ','.join(video_id)
            pass

        params = {'id': video_id}
        return self._perform_v3_request(method='GET', path='videos/getRating', params=params)

    def rate_video(self, video_id, rating='like'):
        """
        Rate a video
        :param video_id: if of the video
        :param rating: [like|dislike|none]
        :return:
        """
        params = {'id': video_id,
                  'rating': rating}
        return self._perform_v3_request(method='POST', path='videos/rate', params=params)

    def add_video_to_playlist(self, playlist_id, video_id):
        params = {'part': 'snippet',
                  'mine': 'true'}
        post_data = {'kind': 'youtube#playlistItem',
                     'snippet': {'playlistId': playlist_id,
                                 'resourceId': {'kind': 'youtube#video',
                                                'videoId': video_id}}}
        return self._perform_v3_request(method='POST', path='playlistItems', params=params, post_data=post_data)

    def remove_video_from_playlist(self, playlist_id, playlist_item_id):
        params = {'id': playlist_item_id}
        return self._perform_v3_request(method='DELETE', path='playlistItems', params=params)

    def unsubscribe(self, subscription_id):
        params = {'id': subscription_id}
        return self._perform_v3_request(method='DELETE', path='subscriptions', params=params)

    def subscribe(self, channel_id):
        params = {'part': 'snippet'}
        post_data = {'kind': 'youtube#subscription',
                     'snippet': {'resourceId': {'kind': 'youtube#channel',
                                                'channelId': channel_id}}}
        return self._perform_v3_request(method='POST', path='subscriptions', params=params, post_data=post_data)

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
            pass
        else:
            params['channelId'] = channel_id
            pass
        if page_token:
            params['pageToken'] = page_token
            pass

        return self._perform_v3_request(method='GET', path='subscriptions', params=params)

    def get_guide_category(self, guide_category_id, page_token=''):
        params = {'part': 'snippet,contentDetails,brandingSettings',
                  'maxResults': str(self._max_results),
                  'categoryId': guide_category_id,
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token
            pass
        return self._perform_v3_request(method='GET', path='channels', params=params)

    def get_guide_categories(self, page_token=''):
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token
            pass

        return self._perform_v3_request(method='GET', path='guideCategories', params=params)

    def get_popular_videos(self, page_token=''):
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language,
                  'chart': 'mostPopular'}
        if page_token:
            params['pageToken'] = page_token
            pass
        return self._perform_v3_request(method='GET', path='videos', params=params)

    def get_video_category(self, video_category_id, page_token=''):
        params = {'part': 'snippet,contentDetails',
                  'maxResults': str(self._max_results),
                  'videoCategoryId': video_category_id,
                  'chart': 'mostPopular',
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token
            pass
        return self._perform_v3_request(method='GET', path='videos', params=params)

    def get_video_categories(self, page_token=''):
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language}
        if page_token:
            params['pageToken'] = page_token
            pass

        return self._perform_v3_request(method='GET', path='videoCategories', params=params)

    def get_activities(self, channel_id, page_token=''):
        params = {'part': 'snippet,contentDetails',
                  'maxResults': str(self._max_results),
                  'regionCode': self._region,
                  'hl': self._language}
        if channel_id == 'home':
            params['home'] = 'true'
            pass
        elif channel_id == 'mine':
            params['mine'] = 'true'
            pass
        else:
            params['channelId'] = channel_id
            pass
        if page_token:
            params['pageToken'] = page_token
            pass

        return self._perform_v3_request(method='GET', path='activities', params=params)

    def get_channel_sections(self, channel_id):
        params = {'part': 'snippet,contentDetails',
                  'regionCode': self._region,
                  'hl': self._language}
        if channel_id == 'mine':
            params['mine'] = 'true'
            pass
        else:
            params['channelId'] = channel_id
            pass
        return self._perform_v3_request(method='GET', path='channelSections', params=params)

    def get_playlists_of_channel(self, channel_id, page_token=''):
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results)}
        if channel_id != 'mine':
            params['channelId'] = channel_id
            pass
        else:
            params['mine'] = 'true'
            pass
        if page_token:
            params['pageToken'] = page_token
            pass

        return self._perform_v3_request(method='GET', path='playlists', params=params)

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
            pass

        next_page_token = json_data.get('nextPageToken', '')
        if next_page_token:
            return self.get_playlist_item_id_of_video_id(playlist_id=playlist_id, video_id=video_id,
                                                         page_token=next_page_token)

        return None

    def get_playlist_items(self, playlist_id, page_token=''):
        # prepare params
        params = {'part': 'snippet',
                  'maxResults': str(self._max_results),
                  'playlistId': playlist_id}
        if page_token:
            params['pageToken'] = page_token
            pass

        return self._perform_v3_request(method='GET', path='playlistItems', params=params)

    def get_channel_by_username(self, username):
        """
        Returns a collection of zero or more channel resources that match the request criteria.
        :param channel_id: list or comma-separated list of the YouTube channel ID(s)
        :return:
        """
        params = {'part': 'id',
                  'forUsername': username}

        return self._perform_v3_request(method='GET', path='channels', params=params)

    def get_channels(self, channel_id):
        """
        Returns a collection of zero or more channel resources that match the request criteria.
        :param channel_id: list or comma-separated list of the YouTube channel ID(s)
        :return:
        """
        if isinstance(channel_id, list):
            channel_id = ','.join(channel_id)
            pass

        params = {'part': 'snippet,contentDetails,brandingSettings'}
        if channel_id != 'mine':
            params['id'] = channel_id
            pass
        else:
            params['mine'] = 'true'
            pass
        return self._perform_v3_request(method='GET', path='channels', params=params, quota_optimized=False)

    def get_disliked_videos(self, page_token=''):
        # prepare page token
        if not page_token:
            page_token = ''
            pass

        # prepare params
        params = {'part': 'snippet',
                  'myRating': 'dislike',
                  'maxResults': str(self._max_results)}
        if page_token:
            params['pageToken'] = page_token
            pass

        return self._perform_v3_request(method='GET', path='videos', params=params)

    def get_videos(self, video_id):
        """
        Returns a list of videos that match the API request parameters
        :param video_id: list of video ids
        :return:
        """
        if isinstance(video_id, list):
            video_id = ','.join(video_id)
            pass

        params = {'part': 'snippet,contentDetails',
                  'id': video_id}
        return self._perform_v3_request(method='GET', path='videos', params=params)

    def get_playlists(self, playlist_id):
        if isinstance(playlist_id, list):
            playlist_id = ','.join(playlist_id)
            pass

        params = {'part': 'snippet,contentDetails',
                  'id': playlist_id}
        return self._perform_v3_request(method='GET', path='playlists', params=params)

    def get_live_events(self, event_type='live', order='relevance', page_token=''):
        """

        :param event_type: one of: 'live', 'completed', 'upcoming'
        :param order: one of: 'date', 'rating', 'relevance', 'title', 'videoCount', 'viewCount'
        :param page_token:
        :return:
        """
        # prepare page token
        if not page_token:
            page_token = ''
            pass

        # prepare params
        params = {'part': 'snippet',
                  'type': 'video',
                  'order': order,
                  'eventType': event_type,
                  'regionCode': self._region,
                  'hl': self._language,
                  'maxResults': str(self._max_results)}
        if page_token:
            params['pageToken'] = page_token
            pass

        return self._perform_v3_request(method='GET', path='search', params=params, quota_optimized=True)

    def get_related_videos(self, video_id, page_token=''):
        # prepare page token
        if not page_token:
            page_token = ''
            pass

        # prepare params
        params = {'relatedToVideoId': video_id,
                  'part': 'snippet',
                  'type': 'video',
                  'regionCode': self._region,
                  'hl': self._language,
                  'maxResults': str(self._max_results)}
        if page_token:
            params['pageToken'] = page_token
            pass

        return self._perform_v3_request(method='GET', path='search', params=params, quota_optimized=True)

    def search(self, q, search_type=['video', 'channel', 'playlist'], event_type='', page_token=''):
        """
        Returns a collection of search results that match the query parameters specified in the API request. By default,
        a search result set identifies matching video, channel, and playlist resources, but you can also configure
        queries to only retrieve a specific type of resource.
        :param q:
        :param search_type: acceptable values are: 'video' | 'channel' | 'playlist'
        :param event_type: 'live', 'completed', 'upcoming'
        :param page_token: can be ''
        :return:
        """

        # prepare search type
        if not search_type:
            search_type = ''
            pass
        if isinstance(search_type, list):
            search_type = ','.join(search_type)
            pass

        # prepare page token
        if not page_token:
            page_token = ''
            pass

        # prepare params
        params = {'q': q,
                  'part': 'snippet',
                  'regionCode': self._region,
                  'hl': self._language,
                  'maxResults': str(self._max_results)}
        if event_type and event_type in ['live', 'upcoming', 'completed']:
            params['eventType'] = event_type
            pass
        if search_type:
            params['type'] = search_type
            pass
        if page_token:
            params['pageToken'] = page_token
            pass

        return self._perform_v3_request(method='GET', path='search', params=params, quota_optimized=False)

    def get_my_subscriptions(self, page_token=None, offset=0):
        if not page_token:
            page_token = ''
            pass

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
                pass

            _json_data = self._perform_v1_tv_request(method='POST', path='browse', post_data=_post_data)
            _data = _json_data.get('contents', {}).get('sectionListRenderer', {}).get('contents', [{}])[0].get(
                'shelfRenderer', {}).get('content', {}).get('horizontalListRenderer', {})
            if not _data:
                _data = _json_data.get('continuationContents', {}).get('horizontalListContinuation', {})
                pass
            _items = _data.get('items', [])
            if not _result:
                _result = {'items': []}
                pass

            _new_offset = self._max_results - len(_result['items']) + _offset
            if _offset > 0:
                _items = _items[_offset:]
                pass
            _result['offset'] = _new_offset

            for _item in _items:
                _item = _item.get('gridVideoRenderer', {})
                if _item:
                    _video_item = {'id': _item['videoId'],
                                   'title': _item.get('title', {}).get('runs', [{}])[0].get('text', '')}
                    _result['items'].append(_video_item)
                    pass
                pass

            _continuations = _data.get('continuations', [{}])[0].get('nextContinuationData', {}).get('continuation', '')
            if _continuations and len(_result['items']) <= self._max_results:
                _result['next_page_token'] = _continuations

                if len(_result['items']) < self._max_results:
                    _result = _perform(_page_token=_continuations, _offset=0, _result=_result)
                    pass
                pass

            # trim result
            if len(_result['items']) > self._max_results:
                _items = _result['items']
                _items = _items[:self._max_results]
                _result['items'] = _items
                _result['continue'] = True
                pass

            if len(_result['items']) < self._max_results:
                if 'continue' in _result:
                    del _result['continue']
                    pass

                if 'next_page_token' in _result:
                    del _result['next_page_token']
                    pass

                if 'offset' in _result:
                    del _result['offset']
                    pass
                pass
            return _result

        return _perform(_page_token=page_token, _offset=offset, _result=result)

    def _perform_v3_request(self, method='GET', headers=None, path=None, post_data=None, params=None,
                            allow_redirects=True, quota_optimized=True):

        # first set the config for the corresponding system (Frodo, Gotham, Helix, ...)
        yt_config = self._config
        # in any case of these APIs we change the config to a common key to save some quota
        if quota_optimized and path in ['channels', 'search']:
            yt_config = self.CONFIGS['youtube-for-kodi-quota']
            pass

        # params
        if not params:
            params = {}
            pass
        _params = {'key': yt_config['key']}
        _params.update(params)

        # headers
        if not headers:
            headers = {}
            pass
        _headers = {'Host': 'www.googleapis.com',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
                    'Accept-Encoding': 'gzip, deflate'}
        # a config can decide if a token is allowed
        if self._access_token and yt_config.get('token-allowed', True):
            _headers['Authorization'] = 'Bearer %s' % self._access_token
            pass
        _headers.update(headers)

        # url
        _url = 'https://www.googleapis.com/youtube/v3/%s' % path.strip('/')

        result = None

        if method == 'GET':
            result = requests.get(_url, params=_params, headers=_headers, verify=False, allow_redirects=allow_redirects)
            pass
        elif method == 'POST':
            _headers['content-type'] = 'application/json'
            result = requests.post(_url, json=post_data, params=_params, headers=_headers, verify=False,
                                   allow_redirects=allow_redirects)
            pass
        elif method == 'PUT':
            _headers['content-type'] = 'application/json'
            result = requests.put(_url, json=post_data, params=_params, headers=_headers, verify=False,
                                  allow_redirects=allow_redirects)
            pass
        elif method == 'DELETE':
            result = requests.delete(_url, params=_params, headers=_headers, verify=False,
                                     allow_redirects=allow_redirects)
            pass

        if result is None:
            return {}

        if result.headers.get('content-type', '').startswith('application/json'):
            return result.json()
        pass

    def _perform_v1_tv_request(self, method='GET', headers=None, path=None, post_data=None, params=None,
                               allow_redirects=True):
        # params
        if not params:
            params = {}
            pass
        _params = {'key': self._config_tv['key']}
        _params.update(params)

        # headers
        if not headers:
            headers = {}
            pass
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
            pass
        _headers.update(headers)

        # url
        _url = 'https://www.googleapis.com/youtubei/v1/%s' % path.strip('/')

        result = None

        if method == 'GET':
            result = requests.get(_url, params=_params, headers=_headers, verify=False, allow_redirects=allow_redirects)
            pass
        elif method == 'POST':
            _headers['content-type'] = 'application/json'
            result = requests.post(_url, json=post_data, params=_params, headers=_headers, verify=False,
                                   allow_redirects=allow_redirects)
            pass
        elif method == 'PUT':
            _headers['content-type'] = 'application/json'
            result = requests.put(_url, json=post_data, params=_params, headers=_headers, verify=False,
                                  allow_redirects=allow_redirects)
            pass
        elif method == 'DELETE':
            result = requests.delete(_url, params=_params, headers=_headers, verify=False,
                                     allow_redirects=allow_redirects)
            pass

        if result is None:
            return {}

        if result.headers.get('content-type', '').startswith('application/json'):
            return result.json()
        pass

    pass
