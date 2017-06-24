from youtube_plugin.youtube.provider import Provider
from youtube_plugin.kodion.impl import Context


def get_core_components():
    provider = Provider()
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


def v3_request(method='GET', headers=None, path=None, post_data=None, params=None, allow_redirects=True):
    """
        https://developers.google.com/youtube/v3/docs/
    """
    provider, context, client = get_core_components()
    return client._perform_v3_request(method=method, headers=headers, path=path, post_data=post_data, params=params, allow_redirects=allow_redirects)


def _append_missing_page_token(items):
    if items and isinstance(items, list) and (items[-1].get('nextPageToken') is None):
        items.append({'nextPageToken': ''})

    return items


def get_videos(video_id):
    """

    :param video_id: video id(s)
    :type video_id: str | list
    :return: list of <kind: youtube#video> <parts: ['snippet', 'contentDetails']> for the given video id(s)
                see also https://developers.google.com/youtube/v3/docs/videos#resource
    :rtype: list of dict
    """
    provider, context, client = get_core_components()

    json_data = client.get_videos(video_id)
    if not handle_error(context, json_data):
        return [json_data]

    return [item for item in json_data.get('items', [])]


def get_activities(channel_id, page_token='', all_pages=False):
    """
    :param channel_id: channel id
    :param page_token: nextPageToken for starting page
    :param all_pages: return all pages(starting at page_token) or single page
    :type channel_id: str
    :type page_token: str
    :type all_pages: bool
    :return: list of <kind: youtube#activity> <parts: ['snippet', 'contentDetails']> for the given channel id
                see also https://developers.google.com/youtube/v3/docs/activities#resource
             last item contains nextPageToken
    :rtype: list of dict
    """
    provider, context, client = get_core_components()

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


def get_playlist_items(playlist_id, page_token='', all_pages=False):
    """

    :param playlist_id: playlist id
    :param page_token: nextPageToken for starting page
    :param all_pages: return all pages(starting at page_token) or single page
    :type playlist_id: str
    :type page_token: str
    :type all_pages: bool
    :return: list of <kind: youtube#playlistItem> <parts: ['snippet', 'contentDetails']> for the given playlist id
                see also https://developers.google.com/youtube/v3/docs/playlistItems#resource
             last item contains nextPageToken
    :rtype: list of dict
    """
    provider, context, client = get_core_components()

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


def get_channel_id(channel_name):
    """

    :param channel_name: channel name
    :type channel_name: str
    :return: list of <kind: youtube#channel> <parts: ['id']> for the given channel name
                see also https://developers.google.com/youtube/v3/docs/channels#resource
    :rtype: list of dict
    """
    provider, context, client = get_core_components()

    json_data = client.get_channel_by_username(channel_name)
    if not handle_error(context, json_data):
        return [json_data]

    return [item for item in json_data.get('items', [])]


def get_channels(channel_id):
    """

    :param channel_id: channel id(s)
    :type channel_id: str | list
    :return: list of <kind: youtube#channel> <parts: ['snippet', 'contentDetails', 'brandingSettings']> for the given channel id(s)
                see also https://developers.google.com/youtube/v3/docs/channels#resource
    :rtype: list of dict
    """
    provider, context, client = get_core_components()

    json_data = client.get_channels(channel_id)
    if not handle_error(context, json_data):
        return [json_data]

    return [item for item in json_data.get('items', [])]


def get_channel_sections(channel_id):
    """

    :param channel_id: channel id
    :type channel_id: str
    :return: list of <kind: youtube#channelSections> <parts: ['snippet', 'contentDetails']> for the given channel id
                see also https://developers.google.com/youtube/v3/docs/channelSections#resource
    :rtype: list of dict
    """
    provider, context, client = get_core_components()

    json_data = client.get_channel_sections(channel_id)
    if not handle_error(context, json_data):
        return [json_data]

    return [item for item in json_data.get('items', [])]


def get_playlists_of_channel(channel_id, page_token='', all_pages=False):
    """

    :param channel_id: channel id
    :param page_token: nextPageToken for starting page
    :param all_pages: return all pages(starting at page_token) or single page
    :type channel_id: str
    :type page_token: str
    :type all_pages: bool
    :return: list of <kind: youtube#playlists> <parts: ['snippet']> for the given channel id
                see also https://developers.google.com/youtube/v3/docs/playlists#resource
             last item contains nextPageToken
    :rtype: list of dict
    """
    provider, context, client = get_core_components()

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


def get_playlists(playlist_id):
    """

    :param playlist_id: playlist id(s)
    :type playlist_id: str | list
    :return: list of <kind: youtube#playlists> <parts: ['snippet', 'contentDetails']> for the given playlist id(s)
                see also https://developers.google.com/youtube/v3/docs/playlists#resource
    :rtype: list of dict
    """
    provider, context, client = get_core_components()

    json_data = client.get_playlists(playlist_id)
    if not handle_error(context, json_data):
        return [json_data]

    return [item for item in json_data.get('items', [])]


def get_related_videos(video_id, page_token=''):
    """

    :param video_id: video id
    :param page_token: nextPageToken for page
    :type video_id: str
    :type page_token: str
    :return: list of <kind: youtube#searchResult> <parts: ['snippet']> for the given video id
                see also https://developers.google.com/youtube/v3/docs/search#resource
             last item contains nextPageToken
    :rtype: list of dict
    :note: this is a search api request with high cost
    """
    provider, context, client = get_core_components()

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


def get_search(q, search_type='', event_type='', channel_id='', order='relevance', safe_search='moderate', page_token=''):
    """

    :param q: search query
    :param search_type: acceptable values are: 'video' | 'channel' | 'playlist', defaults to ['video', 'channel', 'playlist']
    :param event_type: 'live', 'completed', 'upcoming'
    :param channel_id: limit search to channel id
    :param order: one of: 'date', 'rating', 'relevance', 'title', 'videoCount', 'viewCount'
    :param safe_search: one of: 'moderate', 'none', 'strict'
    :param page_token: nextPageToken for page
    :type q: str
    :type search_type: str | list
    :type event_type: str
    :type channel_id: str
    :type order: str
    :type safe_search: str
    :type page_token: str
    :return: list of <kind: youtube#searchResult> <parts: ['snippet']> for the given parameters,
                see also https://developers.google.com/youtube/v3/docs/search#resource
             last item contains nextPageToken
    :rtype: list of dict
    :note: this is a search api request with high cost
    """
    search_type = search_type or ['video', 'channel', 'playlist']
    provider, context, client = get_core_components()

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
