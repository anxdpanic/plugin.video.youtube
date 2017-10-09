import re

from .video_item import VideoItem

__RE_IMDB__ = re.compile(r'(http(s)?://)?www.imdb.(com|de)/title/(?P<imdbid>[t0-9]+)(/)?')


class AudioVideoItem(VideoItem):
    def __init__(self, name, uri, image=u'', fanart=u''):
        VideoItem.__init__(self, name, uri, image, fanart)

    def get_mediatype(self):
        if self._mediatype not in ['song']:
            self._mediatype = 'song'
        return self._mediatype
