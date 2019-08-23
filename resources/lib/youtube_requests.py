# -*- coding: utf-8 -*-
"""

    Copyright (C) 2017-2019 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import re

from youtube_plugin.youtube.provider import Provider
from youtube_plugin.kodion.impl import Context


def __get_core_components(addon_id=None):
    """
    :param addon_id: addon id associated with developer keys to use for requests
    :return: addon provider, context and client 
    """
    provider = Provider()
    if addon_id is not None:
        context = Context(params={'addon_id': addon_id}, plugin_id='plugin.video.youtube')
    else:
        context = Context(plugin_id='plugin.video.youtube')
    client = provider.get_client(context=context)

    return provider, context, client


def handle_error(context, json_data):
    if json_data and 'error' in json_data:
        message = json_data['error'].get('message', '')
        reason = json_data['error']['errors'][0].get('reason', '')
        context.log_error('Error reason: |%s| with message: |%s|' % (reason, message))

        return False

    return True


def v3_request(method='GET', headers=None, path=None, post_data=None, params=None, allow_redirects=True, addon_id=None):
    """
        https://developers.google.com/youtube/v3/docs/
        :param method:
        :param headers:
        :param path:
        :param post_data:
        :param params:
        :param allow_redirects:
        :param addon_id: addon id associated with developer keys to use for requests
        :type addon_id: str
    """
    provider, context, client = __get_core_components(addon_id)
    return client.perform_v3_request(method=method, headers=headers, path=path, post_data=post_data, params=params, allow_redirects=allow_redirects)


def _append_missing_page_token(items):
    if items and isinstance(items, list) and (items[-1].get('nextPageToken') is None):
        items.append({'nextPageToken': ''})

    return items


def get_videos(video_id, addon_id=None):
    """

    :param video_id: video id(s)
    :param addon_id: addon id associated with developer keys to use for requests
    :type video_id: str | list
    :type addon_id: str
    :return: list of <kind: youtube#video> <parts: ['snippet', 'contentDetails']> for the given video id(s)
                see also https://developers.google.com/youtube/v3/docs/videos#resource
    :rtype: list of dict
    """
    provider, context, client = __get_core_components(addon_id)

    json_data = client.get_videos(video_id)
    if not handle_error(context, json_data):
        return [json_data]

    return [item for item in json_data.get('items', [])]


def get_activities(channel_id, page_token='', all_pages=False, addon_id=None):
    """
    :param channel_id: channel id
    :param page_token: nextPageToken for starting page
    :param all_pages: return all pages(starting at page_token) or single page
    :param addon_id: addon id associated with developer keys to use for requests
    :type channel_id: str
    :type page_token: str
    :type all_pages: bool
    :type addon_id: str
    :return: list of <kind: youtube#activity> <parts: ['snippet', 'contentDetails']> for the given channel id
                see also https://developers.google.com/youtube/v3/docs/activities#resource
             last item contains nextPageToken
    :rtype: list of dict
    """
    provider, context, client = __get_core_components(addon_id)

    items = []

    def get_items(_page_token=''):
        json_data = client.get_activities(channel_id, page_token=_page_token)
        if not handle_error(context, json_data):
            return [json_data]

        for item in json_data.get('items', []):
            items.append(item)

        next_page_token = json_data.get('nextPageToken')
        if all_pages and (next_page_token is not None):
            get_items(_page_token=next_page_token)
        elif next_page_token is not None:
            items.append({'nextPageToken': next_page_token})

    get_items(_page_token=page_token)

    items = _append_missing_page_token(items)

    return items


def get_playlist_items(playlist_id, page_token='', all_pages=False, addon_id=None):
    """

    :param playlist_id: playlist id
    :param page_token: nextPageToken for starting page
    :param all_pages: return all pages(starting at page_token) or single page
    :param addon_id: addon id associated with developer keys to use for requests
    :type playlist_id: str
    :type page_token: str
    :type all_pages: bool
    :type addon_id: str
    :return: list of <kind: youtube#playlistItem> <parts: ['snippet', 'contentDetails']> for the given playlist id
                see also https://developers.google.com/youtube/v3/docs/playlistItems#resource
             last item contains nextPageToken
    :rtype: list of dict
    """
    provider, context, client = __get_core_components(addon_id)

    items = []

    def get_items(_page_token=''):
        json_data = client.get_playlist_items(playlist_id, page_token=_page_token)
        if not handle_error(context, json_data):
            return [json_data]

        for item in json_data.get('items', []):
            items.append(item)

        next_page_token = json_data.get('nextPageToken')
        if all_pages and (next_page_token is not None):
            get_items(_page_token=next_page_token)
        elif next_page_token is not None:
            items.append({'nextPageToken': next_page_token})

    get_items(_page_token=page_token)

    items = _append_missing_page_token(items)

    return items


def get_channel_id(channel_name, addon_id=None):
    """

    :param channel_name: channel name
    :param addon_id: addon id associated with developer keys to use for requests
    :type channel_name: str
    :type addon_id: str
    :return: list of <kind: youtube#channel> <parts: ['id']> for the given channel name
                see also https://developers.google.com/youtube/v3/docs/channels#resource
    :rtype: list of dict
    """
    provider, context, client = __get_core_components(addon_id)

    json_data = client.get_channel_by_username(channel_name)
    if not handle_error(context, json_data):
        return [json_data]

    return [item for item in json_data.get('items', [])]


def get_channels(channel_id, addon_id=None):
    """

    :param channel_id: channel id(s)
    :param addon_id: addon id associated with developer keys to use for requests
    :type channel_id: str | list
    :type addon_id: str
    :return: list of <kind: youtube#channel> <parts: ['snippet', 'contentDetails', 'brandingSettings']> for the given channel id(s)
                see also https://developers.google.com/youtube/v3/docs/channels#resource
    :rtype: list of dict
    """
    provider, context, client = __get_core_components(addon_id)

    json_data = client.get_channels(channel_id)
    if not handle_error(context, json_data):
        return [json_data]

    return [item for item in json_data.get('items', [])]


def get_channel_sections(channel_id, addon_id=None):
    """

    :param channel_id: channel id
    :param addon_id: addon id associated with developer keys to use for requests
    :type channel_id: str
    :type addon_id: str
    :return: list of <kind: youtube#channelSections> <parts: ['snippet', 'contentDetails']> for the given channel id
                see also https://developers.google.com/youtube/v3/docs/channelSections#resource
    :rtype: list of dict
    """
    provider, context, client = __get_core_components(addon_id)

    json_data = client.get_channel_sections(channel_id)
    if not handle_error(context, json_data):
        return [json_data]

    return [item for item in json_data.get('items', [])]


def get_playlists_of_channel(channel_id, page_token='', all_pages=False, addon_id=None):
    """

    :param channel_id: channel id
    :param page_token: nextPageToken for starting page
    :param all_pages: return all pages(starting at page_token) or single page
    :param addon_id: addon id associated with developer keys to use for requests
    :type channel_id: str
    :type page_token: str
    :type all_pages: bool
    :type addon_id: str
    :return: list of <kind: youtube#playlists> <parts: ['snippet']> for the given channel id
                see also https://developers.google.com/youtube/v3/docs/playlists#resource
             last item contains nextPageToken
    :rtype: list of dict
    """
    provider, context, client = __get_core_components(addon_id)

    items = []

    def get_items(_page_token=''):
        json_data = client.get_playlists_of_channel(channel_id, page_token=_page_token)
        if not handle_error(context, json_data):
            return [json_data]

        for item in json_data.get('items', []):
            items.append(item)

        next_page_token = json_data.get('nextPageToken')
        if all_pages and (next_page_token is not None):
            get_items(_page_token=next_page_token)
        elif next_page_token is not None:
            items.append({'nextPageToken': next_page_token})

    get_items(_page_token=page_token)

    items = _append_missing_page_token(items)

    return items


def get_playlists(playlist_id, addon_id=None):
    """

    :param playlist_id: playlist id(s)
    :param addon_id: addon id associated with developer keys to use for requests
    :type playlist_id: str | list
    :type addon_id: str
    :return: list of <kind: youtube#playlists> <parts: ['snippet', 'contentDetails']> for the given playlist id(s)
                see also https://developers.google.com/youtube/v3/docs/playlists#resource
    :rtype: list of dict
    """
    provider, context, client = __get_core_components(addon_id)

    json_data = client.get_playlists(playlist_id)
    if not handle_error(context, json_data):
        return [json_data]

    return [item for item in json_data.get('items', [])]


def get_related_videos(video_id, page_token='', addon_id=None):
    """

    :param video_id: video id
    :param page_token: nextPageToken for page
    :param addon_id: addon id associated with developer keys to use for requests
    :type video_id: str
    :type page_token: str
    :type addon_id: str
    :return: list of <kind: youtube#searchResult> <parts: ['snippet']> for the given video id
                see also https://developers.google.com/youtube/v3/docs/search#resource
             last item contains nextPageToken
    :rtype: list of dict
    :note: this is a search api request with high cost
    """
    provider, context, client = __get_core_components(addon_id)

    items = []

    def get_items(_page_token=''):
        json_data = client.get_related_videos(video_id, page_token=_page_token)
        if not handle_error(context, json_data):
            return [json_data]

        for item in json_data.get('items', []):
            if 'snippet' in item:
                items.append(item)

        next_page_token = json_data.get('nextPageToken')
        if next_page_token is not None:
            items.append({'nextPageToken': next_page_token})

    get_items(_page_token=page_token)

    items = _append_missing_page_token(items)

    return items


def get_search(q, search_type='', event_type='', channel_id='', order='relevance', safe_search='moderate', page_token='', addon_id=None):
    """

    :param q: search query
    :param search_type: acceptable values are: 'video' | 'channel' | 'playlist', defaults to ['video', 'channel', 'playlist']
    :param event_type: 'live', 'completed', 'upcoming'
    :param channel_id: limit search to channel id
    :param order: one of: 'date', 'rating', 'relevance', 'title', 'videoCount', 'viewCount'
    :param safe_search: one of: 'moderate', 'none', 'strict'
    :param page_token: nextPageToken for page
    :param addon_id: addon id associated with developer keys to use for requests
    :type q: str
    :type search_type: str | list
    :type event_type: str
    :type channel_id: str
    :type order: str
    :type safe_search: str
    :type page_token: str
    :type addon_id: str
    :return: list of <kind: youtube#searchResult> <parts: ['snippet']> for the given parameters,
                see also https://developers.google.com/youtube/v3/docs/search#resource
             last item contains nextPageToken
    :rtype: list of dict
    :note: this is a search api request with high cost
    """
    search_type = search_type or ['video', 'channel', 'playlist']
    provider, context, client = __get_core_components(addon_id)

    items = []

    def get_items(_page_token=''):
        json_data = client.search(q, search_type=search_type, event_type=event_type, channel_id=channel_id,
                                  order=order, safe_search=safe_search, page_token=_page_token)
        if not handle_error(context, json_data):
            return [json_data]

        for item in json_data.get('items', []):
            items.append(item)

        next_page_token = json_data.get('nextPageToken')
        if next_page_token is not None:
            items.append({'nextPageToken': next_page_token})

    get_items(_page_token=page_token)

    items = _append_missing_page_token(items)

    return items


def get_live(channel_id=None, user=None, url=None, addon_id=None):
    """

    :param channel_id: a channel id
        One of channel_id, user, or url required
        ex. UCLA_DiR1FfKNvjuUpBHmylQ
    :param user: a channel username
        One of channel_id, user, or url required
        ex. NASAtelevision
    :param url: a channel url
        One of channel_id, channel_id, or url required
        ex.
        https://www.youtube.com/channel/UCLA_DiR1FfKNvjuUpBHmylQ
        https://www.youtube.com/channel/UCLA_DiR1FfKNvjuUpBHmylQ/live
        https://www.youtube.com/user/NASAtelevision
        https://www.youtube.com/user/NASAtelevision/live
    :param addon_id: addon id associated with developer keys to use for requests
    :type channel_id: str, optional
    :type user: str, optional
    :type url: str, optional
    :type addon_id: str, optional
    :return: all live stream items for the given channel
    :rtype: list of dicts, or None
    """

    if not channel_id and not user and not url:
        return None

    matched_id = None
    matched_type = None
    live_content = []

    if channel_id:
        matched_id = channel_id
        matched_type = 'channel'

    elif user:
        matched_id = user
        matched_type = 'user'

    elif url:
        patterns = [r'^(?:http)*s*:*[/]{0,2}(?:w{3}\.|m\.)*youtu(?:\.be|be\.com)/'
                    r'(?P<type>channel|user)/(?P<channel_id>[^/]+)(?:/live)*$']

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                matched_id = match.group('channel_id')
                matched_type = match.group('type')
                break

    if not matched_id or not matched_type:
        return None

    if matched_type == 'user':
        items = get_channel_id(matched_id, addon_id=addon_id)
        if not items or not isinstance(items, list):
            return None

        matched_id = items[0]['id']

    search_results = get_search(q='', search_type='video', event_type='live',
                                channel_id=matched_id, safe_search='none', addon_id=addon_id)

    if not search_results:
        return None

    for search_result in search_results:
        if 'id' in search_result and 'videoId' in search_result['id'] and 'snippet' in search_result:
            search_result['snippet']['videoId'] = search_result['id']['videoId']
            live_content.append(search_result['snippet'])

    return live_content
