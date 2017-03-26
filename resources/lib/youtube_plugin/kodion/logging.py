__author__ = 'bromix'

__all__ = ['log', 'log_debug', 'log_warning', 'log_error', 'log_notice', 'log_info']

from .impl import Logger
from . import constants

__LOGGER__ = Logger()


def log(text, log_level=constants.log.NOTICE):
    __LOGGER__.log(text, log_level)
    pass


def log_debug(text):
    log(text, constants.log.DEBUG)
    pass


def log_info(text):
    log(text, constants.log.INFO)
    pass


def log_notice(text):
    log(text, constants.log.NOTICE)
    pass


def log_warning(text):
    log(text, constants.log.WARNING)
    pass


def log_error(text):
    log(text, constants.log.ERROR)
    pass
