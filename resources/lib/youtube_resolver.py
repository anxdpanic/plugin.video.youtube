from youtube_plugin.youtube.provider import Provider
from youtube_plugin.kodion.impl import Context
from youtube_plugin.youtube.helper import v3


def get_core_components():
    provider = Provider()
    context = Context(plugin_id='plugin.video.youtube')
    client = provider.get_client(context=context)

    return provider, context, client


def resolve(video_id, sort=True):
    """

    :param video_id: video id to resolve
    :param sort: sort results by quality highest->lowest
    :type video_id: str
    :type sort: bool
    :return: all video items (resolved urls and metadata) for the given video id
    :rtype: list of dict
    """
    provider, context, client = get_core_components()

    streams = client.get_video_streams(context=context, video_id=video_id)

    if sort:
        streams = sorted(streams, key=lambda x: x.get('sort', 0), reverse=True)

    return streams


def get_playlist_items(playlist_id, page_token='', all_pages=False):
    """

    :param playlist_id: playlist id to get items for
    :param page_token: nextPageToken for starting page
    :param all_pages: return all pages(starting at page_token) or single page
    :type playlist_id: str
    :type page_token: str
    :type all_pages: bool
    :return: playlist items (ids and metadata) for the given playlist id, the last item contains nextPageToken
    :rtype: list of dict
    """
    provider, context, client = get_core_components()

    playlist_items = []

    def get_items(_page_token=''):
        json_data = client.get_playlist_items(playlist_id, page_token=_page_token)
        if not v3.handle_error(provider, context, json_data):
            return [json_data]

        items = json_data.get('items', [])
        for item in items:
            if 'snippet' in item:
                playlist_items.append(item['snippet'])

        next_page_token = json_data.get('nextPageToken')
        if all_pages and (next_page_token is not None):
            get_items(_page_token=next_page_token)
        elif next_page_token is not None:
            playlist_items.append({'nextPageToken': next_page_token})

    get_items(_page_token=page_token)

    if playlist_items and (playlist_items[-1].get('nextPageToken') is None):
        playlist_items.append({'nextPageToken': ''})

    return playlist_items
