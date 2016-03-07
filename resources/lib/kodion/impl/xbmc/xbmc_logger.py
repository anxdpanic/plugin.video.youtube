__author__ = 'bromix'

import xbmc

from ... import constants
from ..abstract_logger import AbstractLogger


class XbmcLogger(AbstractLogger):
    def __init__(self):
        AbstractLogger.__init__(self)
        pass

    def log(self, text, log_level=constants.log.NOTICE):
        xbmc.log(msg=text, level=log_level)
        pass

    pass
