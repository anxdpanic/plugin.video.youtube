# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import logging
from os.path import normpath
from sys import exc_info as sys_exc_info
from traceback import extract_stack, format_list

from .compatibility import StringIO, string_type, to_str, xbmc
from .constants import ADDON_ID


__all__ = (
    'check_frame',
    'critical',
    'debug',
    'error',
    'exception',
    'info',
    'log',
    'warning',
    'CRITICAL',
    'DEBUG',
    'ERROR',
    'INFO',
    'WARNING',
)


class RecordFormatter(logging.Formatter):
    def formatMessage(self, record):
        try:
            return self._style.format(record)
        except AttributeError:
            try:
                return self._fmt % record.__dict__
            except UnicodeDecodeError as e:
                try:
                    record.name = record.name.decode('utf-8')
                    return self._fmt % record.__dict__
                except UnicodeDecodeError:
                    raise e

    def formatStack(self, stack_info):
        return stack_info

    def format(self, record):
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self.formatMessage(record)
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if record.stack_info:
                if s[-1:] != '\n':
                    s += '\n\n'
                s += self.formatStack(record.stack_info)
            if s[-1:] != '\n':
                s += '\n\n'
            s += record.exc_text
        elif record.stack_info:
            if s[-1:] != '\n':
                s += '\n\n'
            s += self.formatStack(record.stack_info)
        return s


class MessageFormatter(object):
    __slots__ = (
        'args',
        'kwargs',
        'msg',
    )

    def __init__(self, msg, *args, **kwargs):
        self.msg = msg
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return self.msg.format(*self.args, **self.kwargs)


class Handler(logging.Handler):
    LEVELS = {
        logging.NOTSET: xbmc.LOGNONE,
        logging.DEBUG: xbmc.LOGDEBUG,
        # logging.INFO: xbmc.LOGINFO,
        logging.INFO: xbmc.LOGNOTICE,
        logging.WARN: xbmc.LOGWARNING,
        logging.WARNING: xbmc.LOGWARNING,
        logging.ERROR: xbmc.LOGERROR,
        logging.CRITICAL: xbmc.LOGFATAL,
    }
    STANDARD_FORMATTER = RecordFormatter(
        fmt='[%(addon_id)s] %(module)s:%(lineno)d(%(funcName)s) - %(message)s',
    )
    DEBUG_FORMATTER = RecordFormatter(
        fmt='[%(addon_id)s] %(module)s, line %(lineno)d, in %(funcName)s'
            '\n\t%(message)s',
    )

    _stack_info = False

    def __init__(self, level):
        super(Handler, self).__init__(level=level)
        self.setFormatter(self.STANDARD_FORMATTER)

    def emit(self, record):
        record.addon_id = ADDON_ID
        xbmc.log(
            msg=self.format(record),
            level=self.LEVELS.get(record.levelno, xbmc.LOGDEBUG),
        )

    def format(self, record):
        if self.stack_info:
            fmt = self.DEBUG_FORMATTER
        else:
            fmt = self.STANDARD_FORMATTER
        return fmt.format(record)

    @property
    def stack_info(self):
        return self._stack_info

    @stack_info.setter
    def stack_info(self, value):
        type(self)._stack_info = value


class LogRecord(logging.LogRecord):
    def __init__(self, name, level, pathname, lineno, msg, args, exc_info,
                 func=None, **kwargs):
        stack_info = kwargs.pop('sinfo', None)
        super(LogRecord, self).__init__(name,
                                        level,
                                        pathname,
                                        lineno,
                                        msg,
                                        args,
                                        exc_info,
                                        func=func,
                                        **kwargs)
        self.stack_info = stack_info


class KodiLogger(logging.Logger):
    _verbose_logging = False
    _stack_info = False

    def __init__(self, name, level=logging.DEBUG):
        super(KodiLogger, self).__init__(name=name, level=level)
        self.propagate = False
        self.addHandler(Handler(level=logging.DEBUG))

    def _log(self,
             level,
             msg,
             args,
             exc_info=None,
             extra=None,
             stack_info=False,
             stacklevel=1,
             **kwargs):
        if isinstance(msg, (list, tuple)):
            msg = '\n\t'.join(map(to_str, msg))
        if kwargs:
            msg = MessageFormatter(msg, *args, **kwargs)
            args = ()
        elif args and args[0] == '*(' and args[-1] == ')':
            msg = MessageFormatter(msg, *args[1:-1], **kwargs)
            args = ()

        stack_info = stack_info and (exc_info or self.stack_info)
        sinfo = None
        if _srcfiles:
            try:
                fn, lno, func, sinfo = self.findCaller(stack_info, stacklevel)
            except ValueError:
                fn, lno, func = '(unknown file)', 0, '(unknown function)'
        else:
            fn, lno, func = '(unknown file)', 0, '(unknown function)'

        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys_exc_info()

        record = self.makeRecord(self.name, level, fn, lno, msg, args,
                                 exc_info, func, extra, sinfo)
        self.handle(record)

    def findCaller(self, stack_info=False, stacklevel=1):
        target_frame = logging.currentframe()
        if target_frame is None:
            return '(unknown file)', 0, '(unknown function)', None

        last_frame = None
        while stacklevel > 0:
            next_frame = target_frame.f_back
            if next_frame is None:
                break
            target_frame = next_frame
            stacklevel, is_internal = check_frame(target_frame, stacklevel)
            if is_internal:
                continue
            if last_frame is None:
                last_frame = target_frame
            stacklevel -= 1

        if stack_info:
            with StringIO() as output:
                output.write('Stack (most recent call last):\n')
                for item in format_list(extract_stack(last_frame)):
                    output.write(item)
                stack_info = output.getvalue()
                if stack_info[-1] == '\n':
                    stack_info = stack_info[:-1]
        else:
            stack_info = None

        target_frame_code = target_frame.f_code
        return (target_frame_code.co_filename,
                target_frame.f_lineno,
                target_frame_code.co_name,
                stack_info)

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None):
        rv = LogRecord(name,
                       level,
                       fn,
                       lno,
                       msg,
                       args,
                       exc_info,
                       func=func,
                       sinfo=sinfo)
        if extra is not None:
            for key in extra:
                if (key in ["message", "asctime"]) or (key in rv.__dict__):
                    raise KeyError("Attempt to overwrite %r in LogRecord" % key)
                rv.__dict__[key] = extra[key]
        return rv

    def exception(self, msg, *args, **kwargs):
        if self.isEnabledFor(ERROR):
            self._log(
                ERROR,
                msg,
                args,
                exc_info=kwargs.pop('exc_info', True),
                stack_info=kwargs.pop('stack_info', True),
                stacklevel=kwargs.pop('stacklevel', 1),
                **kwargs
            )

    def error_trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(ERROR):
            self._log(
                ERROR,
                msg,
                args,
                stack_info=kwargs.pop('stack_info', True),
                stacklevel=kwargs.pop('stacklevel', 1),
                **kwargs
            )

    def debug_trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(DEBUG):
            self._log(
                DEBUG,
                msg,
                args,
                stack_info=kwargs.pop('stack_info', True),
                stacklevel=kwargs.pop('stacklevel', 1),
                **kwargs
            )

    @property
    def debugging(self):
        return self.isEnabledFor(logging.DEBUG)

    @debugging.setter
    def debugging(self, value):
        if value:
            Handler.LEVELS[logging.DEBUG] = xbmc.LOGNOTICE
            self.setLevel(logging.DEBUG)
            root.setLevel(logging.DEBUG)
        else:
            Handler.LEVELS[logging.DEBUG] = xbmc.LOGDEBUG
            self.setLevel(logging.INFO)
            root.setLevel(logging.INFO)

    @property
    def stack_info(self):
        return self._stack_info

    @stack_info.setter
    def stack_info(self, value):
        if value:
            type(self)._stack_info = True
            Handler.stack_info = True
        else:
            type(self)._stack_info = False
            Handler.stack_info = False

    @property
    def verbose_logging(self):
        return self._verbose_logging

    @verbose_logging.setter
    def verbose_logging(self, value):
        cls = type(self)
        if value:
            cls._verbose_logging = True
            logging.root = root
            logging.Logger.root = root
            logging.Logger.manager = manager
            logging.Logger.manager.setLoggerClass(KodiLogger)
            logging.setLoggerClass(KodiLogger)
        else:
            if cls._verbose_logging:
                logging.root = logging.RootLogger(logging.WARNING)
                logging.Logger.root = logging.root
                logging.Logger.manager = logging.Manager(logging.root)
                logging.Logger.manager.setLoggerClass(logging.Logger)
                logging.setLoggerClass(logging.Logger)
            cls._verbose_logging = False


class RootLogger(KodiLogger):
    def __init__(self, level):
        super(RootLogger, self).__init__('root', level)

    def __reduce__(self):
        return getLogger, ()


root = RootLogger(logging.INFO)
KodiLogger.root = root
manager = logging.Manager(root)
KodiLogger.manager = manager
KodiLogger.manager.setLoggerClass(KodiLogger)

critical = root.critical
error = root.error
warning = root.warning
info = root.info
debug = root.debug
log = root.log

CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG


def exception(msg, *args, **kwargs):
    root.error(msg,
               *args,
               exc_info=kwargs.pop('exc_info', True),
               stack_info=kwargs.pop('stack_info', True),
               stacklevel=kwargs.pop('stacklevel', 1),
               **kwargs)


def error_trace(msg, *args, **kwargs):
    root.error(msg,
               *args,
               stack_info=kwargs.pop('stack_info', True),
               stacklevel=kwargs.pop('stacklevel', 1),
               **kwargs)


def debug_trace(msg, *args, **kwargs):
    root.debug(msg,
               *args,
               stack_info=kwargs.pop('stack_info', True),
               stacklevel=kwargs.pop('stacklevel', 1),
               **kwargs)


def getLogger(name=None):
    if not name or isinstance(name, string_type) and name == root.name:
        return root
    return KodiLogger.manager.getLogger(name)


_srcfiles = {
    normpath(getLogger.__code__.co_filename).lower(),
    normpath(logging.getLogger.__code__.co_filename).lower(),
}


def check_frame(frame, stacklevel=None, skip_paths=None):
    filename = normpath(frame.f_code.co_filename).lower()
    is_internal = (
            filename in _srcfiles
            or ('importlib' in filename and '_bootstrap' in filename)
            or (skip_paths
                and any(skip_path in filename for skip_path in skip_paths))
    )
    if stacklevel is None:
        return is_internal

    if (ADDON_ID in filename and filename.endswith((
            'function_cache.py',
            'abstract_settings.py',
            'xbmc_items.py',
    ))):
        stacklevel += 1
    return stacklevel, is_internal
