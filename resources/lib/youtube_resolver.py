from youtube_plugin.youtube.provider import Provider
from youtube_plugin.kodion.impl import Context


def resolve(video_id):
    provider = Provider()
    context = Context(plugin_id='plugin.video.youtube')
    client = provider.get_client(context=context)
    streams = client.get_video_streams(context=context, video_id=video_id)
    sorted_streams = sorted(streams, key=lambda x: x.get('sort', 0), reverse=True)
    return sorted_streams
