# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-present plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import atexit
import os

from .logger import Logger


def debug_here(host='localhost'):
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
        'name',
    )

    from cProfile import Profile as _Profile
    from pstats import Stats as _Stats

    try:
        from StringIO import StringIO as _StringIO
    except ImportError:
        from io import StringIO as _StringIO
    from functools import wraps as _wraps

    _wraps = staticmethod(_wraps)
    from weakref import ref as _ref

    class Proxy(_ref):
        def __call__(self, *args, **kwargs):
            return super(Profiler.Proxy, self).__call__().__call__(
                *args, **kwargs
            )

        def __enter__(self, *args, **kwargs):
            return super(Profiler.Proxy, self).__call__().__enter__(
                *args, **kwargs
            )

        def __exit__(self, *args, **kwargs):
            return super(Profiler.Proxy, self).__call__().__exit__(
                *args, **kwargs
            )

        def disable(self, *args, **kwargs):
            return super(Profiler.Proxy, self).__call__().disable(
                *args, **kwargs
            )

        def enable(self, *args, **kwargs):
            return super(Profiler.Proxy, self).__call__().enable(
                *args, **kwargs
            )

        def get_stats(self, *args, **kwargs):
            return super(Profiler.Proxy, self).__call__().get_stats(
                *args, **kwargs
            )

        def print_stats(self, *args, **kwargs):
            return super(Profiler.Proxy, self).__call__().print_stats(
                *args, **kwargs
            )

        def tear_down(self, *args, **kwargs):
            return super(Profiler.Proxy, self).__call__().tear_down(
                *args, **kwargs
            )

    _instances = set()

    def __new__(cls, *args, **kwargs):
        self = super(Profiler, cls).__new__(cls)
        cls._instances.add(self)
        if not kwargs.get('enabled') or kwargs.get('lazy'):
            self.__init__(*args, **kwargs)
            return cls.Proxy(self)
        return self

    def __init__(self,
                 enabled=True,
                 lazy=True,
                 name=__name__,
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
        self.name = name

        if enabled and not lazy:
            self._create_profiler()

        atexit.register(self.tear_down)

    def __enter__(self):
        if not self._enabled:
            return

        if not self._profiler:
            self._create_profiler()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        if not self._enabled:
            return

        Logger.log_debug('Profiling stats: {0}'.format(self.get_stats(
            num_lines=self._num_lines,
            print_callees=self._print_callees,
            reuse=self._reuse,
        )))
        if not self._reuse:
            self.tear_down()

    def __call__(self, func=None, name=__name__, reuse=False):
        """Decorator used to profile function calls"""

        if not func:
            self._reuse = reuse
            self.name = name
            return self

        @self.__class__._wraps(func)  # pylint: disable=protected-access
        def wrapper(*args, **kwargs):
            """Wrapper to:
               1) create a new Profiler instance;
               2) run the function being profiled;
               3) print out profiler result to the log; and
               4) return result of function call"""

            name = getattr(func, '__qualname__', None)
            if name:
                # If __qualname__ is available (Python 3.3+) then use it
                pass

            elif args and getattr(args[0], func.__name__, None):
                if isinstance(args[0], type):
                    class_name = args[0].__name__
                else:
                    class_name = args[0].__class__.__name__
                name = '.'.join((
                    class_name,
                    func.__name__,
                ))

            elif (func.__class__
                  and not isinstance(func.__class__, type)
                  and func.__class__.__name__ != 'function'):
                name = '.'.join((
                    func.__class__.__name__,
                    func.__name__,
                ))

            elif func.__module__:
                name = '.'.join((
                    func.__module__,
                    func.__name__,
                ))

            else:
                name = func.__name__

            self.name = name
            with self:
                result = func(*args, **kwargs)

            return result

        if not self._enabled:
            self.tear_down()
            return func
        return wrapper

    def _create_profiler(self):
        if self._timer:
            self._profiler = self._Profile(timer=self._timer)
        else:
            self._profiler = self._Profile()
        self._profiler.enable()

    @classmethod
    def wait_timer(cls):
        times = os.times()
        return times.elapsed - (times.system + times.user)

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

        output_stream = self._StringIO()
        try:
            stats = self._Stats(
                self._profiler,
                stream=output_stream
            )
            stats.strip_dirs().sort_stats('cumulative', 'time')
            if print_callees:
                stats.print_callees(num_lines)
            else:
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
        Logger.log_debug('Profiling stats: {0}'.format(self.get_stats(
            num_lines=self._num_lines,
            print_callees=self._print_callees,
            reuse=self._reuse,
        )))

    def tear_down(self):
        self.__class__._instances.discard(self)
