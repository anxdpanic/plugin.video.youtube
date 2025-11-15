# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import sys
import threading
import time
from atexit import register as atexit_register
from cProfile import Profile
from functools import wraps
from inspect import getargvalues
from os.path import normpath
import pstats
from traceback import extract_stack, format_list
from weakref import ref

from . import logging
from .compatibility import StringIO


def debug_here(host='localhost'):
    import os
    import sys

    for comp in sys.path:
        if comp.find('addons') != -1:
            pydevd_path = os.path.normpath(os.path.join(
                comp,
                os.pardir,
                'script.module.pydevd',
                'lib',
            ))
            sys.path.append(pydevd_path)
            break

    # noinspection PyUnresolvedReferences,PyPackageRequirements
    import pydevd

    pydevd.settrace(host, stdoutToServer=True, stderrToServer=True)


class ProfilerProxy(ref):
    def __call__(self, *args, **kwargs):
        return super(ProfilerProxy, self).__call__().__call__(
            *args, **kwargs
        )

    def __enter__(self, *args, **kwargs):
        return super(ProfilerProxy, self).__call__().__enter__(
            *args, **kwargs
        )

    def __exit__(self, *args, **kwargs):
        return super(ProfilerProxy, self).__call__().__exit__(
            *args, **kwargs
        )

    def disable(self, *args, **kwargs):
        return super(ProfilerProxy, self).__call__().disable(
            *args, **kwargs
        )

    def enable(self, *args, **kwargs):
        return super(ProfilerProxy, self).__call__().enable(
            *args, **kwargs
        )

    def get_stats(self, *args, **kwargs):
        return super(ProfilerProxy, self).__call__().get_stats(
            *args, **kwargs
        )

    def print_stats(self, *args, **kwargs):
        return super(ProfilerProxy, self).__call__().print_stats(
            *args, **kwargs
        )

    def tear_down(self, *args, **kwargs):
        return super(ProfilerProxy, self).__call__().tear_down(
            *args, **kwargs
        )


class Profiler(object):
    """Class used to profile a block of code"""

    __slots__ = (
        '__weakref__',
        '_enabled',
        '_num_lines',
        '_print_callees',
        '_profiler',
        '_reuse',
        '_timer',
    )

    log = logging.getLogger(__name__)

    _instances = set()

    def __new__(cls, *args, **kwargs):
        self = super(Profiler, cls).__new__(cls)
        cls._instances.add(self)
        if not kwargs.get('enabled') or kwargs.get('lazy'):
            self.__init__(*args, **kwargs)
            return ProfilerProxy(self)
        return self

    def __init__(self,
                 enabled=True,
                 lazy=True,
                 num_lines=20,
                 print_callees=False,
                 reuse=False,
                 timer=None):
        self._enabled = enabled
        self._num_lines = num_lines
        self._print_callees = print_callees
        self._profiler = None
        self._reuse = reuse
        self._timer = timer

        if enabled and not lazy:
            self._create_profiler()

        atexit_register(self.tear_down)

    def __enter__(self):
        if not self._enabled:
            return

        if not self._profiler:
            self._create_profiler()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        if not self._enabled:
            return

        self.print_stats()
        if not self._reuse:
            self.tear_down()

    def __call__(self, func=None, name=__name__, reuse=False):
        """Decorator used to profile function calls"""

        if not func:
            self._reuse = reuse
            return self

        @wraps(func)
        def wrapper(*args, **kwargs):
            """
            Wrapper to:
               1) create a new Profiler instance;
               2) run the function being profiled;
               3) print out profiler result to the log; and
               4) return result of function call
            """
            with self:
                result = func(*args, **kwargs)
            return result

        if not self._enabled:
            self.tear_down()
            return func
        return wrapper

    def _create_profiler(self):
        if self._timer:
            self._profiler = Profile(timer=self._timer)
        else:
            self._profiler = Profile()
        self._profiler.enable()

    try:
        elapsed_timer = time.perf_counter
        process_timer = time.process_time
    except AttributeError:
        elapsed_timer = time.clock
        process_timer = time.clock

    def disable(self):
        if self._profiler:
            self._profiler.disable()

    def enable(self, flush=False):
        self._enabled = True
        if flush or not self._profiler:
            self._create_profiler()
        else:
            self._profiler.enable()

    def get_stats(self,
                  flush=True,
                  num_lines=20,
                  print_callees=False,
                  reuse=False):
        if not (self._enabled and self._profiler):
            return None

        self.disable()

        output_stream = StringIO()
        try:
            stats = Stats(
                self._profiler,
                stream=output_stream
            )
            stats.strip_dirs()
            if print_callees:
                stats.sort_stats('cumulative')
                stats.print_callees(num_lines)
            else:
                stats.sort_stats('cumpercall')
                stats.print_stats(num_lines)
                stats.sort_stats('totalpercall')
                stats.print_stats(num_lines)
            output = output_stream.getvalue()
        # Occurs when no stats were able to be generated from profiler
        except TypeError:
            output = 'Profiler: unable to generate stats'
        finally:
            output_stream.close()

        if reuse:
            # If stats are accumulating then enable existing/new profiler
            self.enable(flush)

        return output

    def print_stats(self):
        self.log.info('Profiling stats: %s',
                      self.get_stats(
                          num_lines=self._num_lines,
                          print_callees=self._print_callees,
                          reuse=self._reuse,
                      ),
                      stacklevel=3)

    def tear_down(self):
        self.__class__._instances.discard(self)


class Stats(pstats.Stats):
    """
    Custom Stats class that adds functionality to sort by
      - Cumulative time per call ("cumpercall")
      - Total time per call ("totalpercall")
    Code by alexnvdias from https://bugs.python.org/issue18795
    """

    sort_arg_dict_default = {
        "calls"       : (((1,-1),              ), "call count"),
        "ncalls"      : (((1,-1),              ), "call count"),
        "cumtime"     : (((4,-1),              ), "cumulative time"),
        "cumulative"  : (((4,-1),              ), "cumulative time"),
        "filename"    : (((6, 1),              ), "file name"),
        "line"        : (((7, 1),              ), "line number"),
        "module"      : (((6, 1),              ), "file name"),
        "name"        : (((8, 1),              ), "function name"),
        "nfl"         : (((8, 1),(6, 1),(7, 1),), "name/file/line"),
        "pcalls"      : (((0,-1),              ), "primitive call count"),
        "stdname"     : (((9, 1),              ), "standard name"),
        "time"        : (((2,-1),              ), "internal time"),
        "tottime"     : (((2,-1),              ), "internal time"),
        "cumpercall"  : (((5,-1),              ), "cumulative time per call"),
        "totalpercall": (((3,-1),              ), "total time per call"),
    }

    def sort_stats(self, *field):
        if not field:
            self.fcn_list = 0
            return self
        if len(field) == 1 and isinstance(field[0], int):
            # Be compatible with old profiler
            field = [{-1: "stdname",
                      0: "calls",
                      1: "time",
                      2: "cumulative"}[field[0]]]
        elif len(field) >= 2:
            for arg in field[1:]:
                if type(arg) != type(field[0]):
                    raise TypeError("Can't have mixed argument type")

        sort_arg_defs = self.get_sort_arg_defs()

        sort_tuple = ()
        self.sort_type = ""
        connector = ""
        for word in field:
            if isinstance(word, pstats.SortKey):
                word = word.value
            sort_tuple = sort_tuple + sort_arg_defs[word][0]
            self.sort_type += connector + sort_arg_defs[word][1]
            connector = ", "

        stats_list = []
        for func, (cc, nc, tt, ct, callers) in self.stats.items():
            if nc == 0:
                npc = 0
            else:
                npc = float(tt) / nc

            if cc == 0:
                cpc = 0
            else:
                cpc = float(ct) / cc

            stats_list.append((cc, nc, tt, npc, ct, cpc) + func +
                              (pstats.func_std_string(func), func))

        stats_list.sort(key=pstats.cmp_to_key(pstats.TupleComp(sort_tuple).compare))

        self.fcn_list = fcn_list = []
        for tuple in stats_list:
            fcn_list.append(tuple[-1])
        return self


class ExecTimeout(object):
    log = logging.getLogger('__name__')
    src_file = None

    def __init__(self,
                 seconds,
                 log_only=False,
                 trace_opcodes=False,
                 trace_threads=False,
                 log_locals=False,
                 callback=None,
                 skip_paths=('\\python\\lib\\',
                             '\\logging.py',
                             '\\addons\\script.')):
        self._interval = seconds
        self._log_only = log_only
        self._last_event = (None, None, None)
        self._timed_out = False

        self._trace_opcodes = trace_opcodes
        self._trace_threads = trace_threads
        self._log_locals = log_locals
        self._callback = callback if callable(callback) else None

        self._skip_paths = skip_paths

    def __call__(self, function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            timer = threading.Timer(self._interval, self.set_timed_out)
            timer.daemon = True

            if self._trace_threads:
                threading.settrace(self.timeout_trace)
            sys.settrace(self.timeout_trace)
            timer.start()
            try:
                return function(*args, **kwargs)
            finally:
                timer.cancel()
                if self._trace_threads:
                    threading.settrace(None)
                sys.settrace(None)
                if self._callback:
                    self._callback()
                self._last_event = (None, None, None)

        return wrapper

    def timeout_trace(self, frame, event, arg):
        if self._trace_opcodes and hasattr(frame, 'f_trace_opcodes'):
            frame.f_trace_opcodes = True
        if self._timed_out:
            if not self._log_only:
                raise RuntimeError('Python execution timed out')
        else:
            filename = normpath(frame.f_code.co_filename).lower()
            skip_event = (
                    filename == self.src_file
                    or (self._skip_paths
                        and any(skip_path in filename
                                for skip_path in self._skip_paths))
            )
            if not skip_event:
                self._last_event = (event, frame, arg)
        return self.timeout_trace

    def set_timed_out(self):
        msg, kwargs = self._get_msg(to_log=True)
        self.log.error(msg, **kwargs)
        self._timed_out = True

    def _get_msg(self, to_log=False):
        event, frame, arg = self._last_event
        out = (
            'Python execution timed out',
            'Event:  {event!r}',
            'Frame:  {frame!r}',
            'Arg:    {arg!r}',
            'Locals: {locals!r}',
            '',
            'Stack (most recent call last):',
            '{stack_trace}',
        )
        log_locals = self._log_locals
        if log_locals:
            _locals = getargvalues(frame).locals
            if log_locals is not True:
                _locals = dict(tuple(_locals.items())[slice(*log_locals)])
        else:
            _locals = None
        kwargs = {
            'event': event,
            'frame': frame,
            'arg': arg,
            'locals': _locals,
            'stack_trace': ''.join(format_list(extract_stack(frame))),
        }
        if to_log:
            return out, kwargs
        return '\n'.join(out).format(**kwargs)


ExecTimeout.src_file = normpath(
    ExecTimeout.__init__.__code__.co_filename
).lower()
