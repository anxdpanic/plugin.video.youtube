__author__ = 'bromix'

from .. import constants


class AbstractLogger(object):
    def __init__(self):
        pass

    def log(self, text, log_level=constants.log.NOTICE):
        """
        Needs to be implemented by a mock for testing or the real deal.
        Logging.
        :param text:
        :param log_level:
        :return:
        """
        raise NotImplementedError()