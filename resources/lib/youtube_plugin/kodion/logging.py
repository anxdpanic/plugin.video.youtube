__author__ = 'bromix'

__all__ = ['log', 'log_debug', 'log_warning', 'log_error', 'log_notice', 'log_info']

from .impl import Logger
from . import constants

__LOGGER__ = Logger()


def log(text, log_level=constants.log.NOTICE):
    __LOGGER__.log(text, log_level)


def log_debug(text):
    log(text, constants.log.DEBUG)


def log_info(text):
    log(text, constants.log.INFO)


def log_notice(text):
    log(text, constants.log.NOTICE)


def log_warning(text):
    log(text, constants.log.WARNING)


def log_error(text):
    log(text, constants.log.ERROR)
