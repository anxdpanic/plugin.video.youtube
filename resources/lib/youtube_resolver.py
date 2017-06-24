from youtube_plugin.youtube.provider import Provider
from youtube_plugin.kodion.impl import Context


def get_core_components():
    provider = Provider()
    context = Context(plugin_id='plugin.video.youtube')
    client = provider.get_client(context=context)

    return provider, context, client


def resolve(video_id, sort=True):
    """

    :param video_id: video id
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
