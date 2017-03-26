__author__ = 'bromix'

from youtube_plugin.kodion import runner
from youtube_plugin import youtube

__provider__ = youtube.Provider()
runner.run(__provider__)
