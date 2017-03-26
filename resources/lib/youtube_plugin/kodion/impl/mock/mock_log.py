__author__ = 'bromix'

from ... import constants
from ..abstract_logger import AbstractLogger


class MockLogger(AbstractLogger):
    def __init__(self):
        AbstractLogger.__init__(self)
        pass

    def log(self, text, log_level=constants.log.NOTICE):
        log_level_2_string = {constants.log.DEBUG: 'DEBUG',
                              constants.log.INFO: 'INFO',
                              constants.log.NOTICE: 'NOTICE',
                              constants.log.WARNING: 'WARNING',
                              constants.log.ERROR: 'ERROR',
                              constants.log.SEVERE: 'SEVERE',
                              constants.log.FATAL: 'FATAL',
                              constants.log.NONE: 'NONE'}

        log_text = "[%s] %s" % (log_level_2_string.get(log_level, 'UNKNOWN'), text)
        print log_text.encode('utf-8')
        pass
