__author__ = 'bromix'

from resources.lib.kodion import runner
from resources.lib import youtube

__provider__ = youtube.Provider()
runner.run(__provider__)
