# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import logging
import sys
from os.path import normpath
from pprint import PrettyPrinter
from string import Formatter
from sys import exc_info as sys_exc_info
from traceback import extract_stack, format_list

from .compatibility import StringIO, string_type, to_str, xbmc
from .constants import ADDON_ID
from .utils.convert_format import to_unicode
from .utils.redact import (
    parse_and_redact_uri,
    redact_auth_header,
    redact_params,
)
from .utils.system_version import current_system_version


# noinspection PyUnresolvedReferences
__all__ = (
    'check_frame',
    'critical',
    'debug',
    'debugging',
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
        record.__dict__.setdefault(
            '__sep__',
            '\n' if record.stack_info or '\n' in record.message else ' - ',
        )
        try:
            return self._style.format(record)
        except AttributeError:
            try:
                return self._fmt % record.__dict__
            except UnicodeDecodeError as e:
                record.__dict__ = {
                    key: to_unicode(value)
                    for key, value in record.__dict__.items()
                }
                try:
                    return self._fmt % record.__dict__
                except UnicodeDecodeError:
                    raise e

    def formatStack(self, stack_info):
        return stack_info

    def format(self, record):
        record.message = to_unicode(record.getMessage())
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


class StreamWrapper(object):
    OPEN = frozenset(('(', '[', '{'))
    CLOSE = frozenset((')', ']', '}'))

    def __init__(self, stream, indent_per_level, level, indent):
        self.stream = stream
        self.indent_per_level = indent_per_level
        self.level = level
        self.indent = indent
        self.previous_indent = 0
        self.previous_out = ''

    def update_level(self, level, indent):
        self.level = level
        self.indent = indent

    def write(self, out):
        write = self.stream.write
        indent = self.indent
        out = to_unicode(out)
        if '\n' in out:
            write(to_str(out))
        elif out in self.OPEN:
            write(to_str(out))
            write('\n' + (1 + indent) * ' ')
        elif out in self.CLOSE:
            if self.previous_out not in self.CLOSE:
                if indent == self.previous_indent:
                    indent = (self.level - 1) * self.indent_per_level
                write('\n' + indent * ' ')
            write(to_str(out))
        else:
            write(to_str(out))
        self.previous_indent = indent
        self.previous_out = out


class VariableWidthPrettyPrinter(PrettyPrinter, object):
    def _format(self, object, stream, indent, allowance, context, level):
        if not isinstance(object, string_type):
            indent = level * self._indent_per_level

        if level:
            stream.update_level(level, indent)
        else:
            stream = StreamWrapper(
                stream,
                self._indent_per_level,
                level,
                indent,
            )

        super(VariableWidthPrettyPrinter, self)._format(
            object=object,
            stream=stream,
            indent=indent,
            allowance=allowance,
            context=context,
            level=level,
        )


class PrettyPrintFormatter(Formatter):
    _pretty_printer = VariableWidthPrettyPrinter(indent=4, width=160)

    def convert_field(self, value, conversion):
        # redact headers
        if conversion == 'h':
            return self._pretty_printer.pformat(redact_auth_header(value))
        # redact setting
        if conversion == 'q':
            return self._pretty_printer.pformat(redact_params(value))[1:-1]
        # pretty printed repr
        if conversion == 'r':
            return self._pretty_printer.pformat(value)
        # redact params
        if conversion == 'p':
            return self._pretty_printer.pformat(redact_params(value))
        if conversion in {'d', 'e', 't', 'u', 'w'}:
            _sort_dicts = sort_dicts = getattr(self._pretty_printer,
                                               '_sort_dicts',
                                               None)
            width = self._pretty_printer._width
            # __dict__
            if conversion == 'd':
                if sort_dicts:
                    _sort_dicts = False
                try:
                    value = getattr(value, '__repr_data__')()
                except AttributeError:
                    if not isinstance(value, dict):
                        value = {
                            attr: getattr(value, attr, None)
                            for attr in dir(value)
                        }
            # eval iterators
            elif conversion == 'e':
                if (getattr(value, '__iter__', None)
                        and not getattr(value, '__len__', None)):
                    value = tuple(value)
                if sort_dicts:
                    _sort_dicts = False
            # text representation
            elif conversion == 't':
                try:
                    value = getattr(value, '__str_parts__')(as_dict=True)
                    if sort_dicts:
                        _sort_dicts = False
                except AttributeError:
                    pass
            # redact uri
            elif conversion == 'u':
                value = parse_and_redact_uri(value, redact_only=True)
                if sort_dicts:
                    _sort_dicts = False
            # wide output
            elif conversion == 'w':
                self._pretty_printer._width = 2 * width
            if _sort_dicts != sort_dicts:
                self._pretty_printer._sort_dicts = _sort_dicts
            out = self._pretty_printer.pformat(value)
            if sort_dicts:
                self._pretty_printer._sort_dicts = sort_dicts
            self._pretty_printer._width = width
            return out
        return super(PrettyPrintFormatter, self).convert_field(
            value,
            conversion,
        )

    if not current_system_version.compatible(19):
        def parse(self, *args, **kwargs):
            output = super(PrettyPrintFormatter, self).parse(*args, **kwargs)
            return (
                (to_str(literal_text), field_name, format_spec, conversion)
                for literal_text, field_name, format_spec, conversion in output
            )

        def format_field(self, *args, **kwargs):
            return to_str(
                super(PrettyPrintFormatter, self).format_field(*args, **kwargs)
            )


class MessageFormatter(object):
    _formatter = PrettyPrintFormatter()

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
        return self._formatter.vformat(self.msg, self.args, self.kwargs)


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
        fmt='[%(addon_id)s] %(module)s:%(lineno)d(%(funcName)s)'
            '%(__sep__)s%(message)s',
    )
    DEBUG_FORMATTER = RecordFormatter(
        fmt='[%(addon_id)s] %(module)s, line %(lineno)d, in %(funcName)s'
            '%(__sep__)s%(message)s',
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

    if not current_system_version.compatible(19):
        def getMessage(self):
            msg = self.msg
            if isinstance(msg, MessageFormatter):
                msg = msg.__str__()
            else:
                msg = to_str(msg)
            if self.args:
                msg = msg % self.args
            return msg


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
            msg = '\n'.join(map(to_str, msg))
        if kwargs:
            msg = MessageFormatter(msg, *args, **kwargs)
            args = ()
        elif args and args[0] == '*(' and args[-1] == ')':
            msg = MessageFormatter(msg, *args[1:-1], **kwargs)
            args = ()

        if stack_info:
            if exc_info or self.stack_info:
                pass
            elif stack_info == 'forced':
                stack_info = True
            else:
                stack_info = False
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

    def warning_trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(WARNING):
            self._log(
                WARNING,
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


def warning_trace(msg, *args, **kwargs):
    root.warning(msg,
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


__original_module__ = sys.modules[__name__]


class ModuleProperties(__original_module__.__class__, object):
    __name__ = __original_module__.__name__
    __file__ = __original_module__.__file__
    __getattribute__ = __original_module__.__getattribute__

    def __getattr__(self, item):
        if item == 'debugging':
            return root.isEnabledFor(logging.DEBUG)
        raise AttributeError(
            'module \'{}\' has no attribute \'{}\''.format(__name__, item)
        )


sys.modules[__name__] = ModuleProperties(__name__, __doc__)
