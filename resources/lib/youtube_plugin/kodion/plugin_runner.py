# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .context import XbmcContext
from .plugin import XbmcPlugin
from ..youtube import Provider


__all__ = ('run',)

_context = XbmcContext()
_plugin = XbmcPlugin()
_provider = Provider()

_profiler = _context.get_infobool('System.GetBool(debug.showloginfo)')
_profiler = True
if _profiler:
    from .debug import Profiler

    _profiler = Profiler(enabled=False, print_callees=False, num_lines=20)


def run(context=_context,
        plugin=_plugin,
        provider=_provider,
        profiler=_profiler):
    if profiler:
        profiler.enable(flush=True)

    current_uri = context.get_uri()
    context.init()
    new_uri = context.get_uri()

    params = context.get_params().copy()
    for key in ('api_key', 'client_id', 'client_secret'):
        if key in params:
            params[key] = '<redacted>'

    system_version = context.get_system_version()
    context.log_notice('Plugin: Running |v{version}|\n'
                       'Kodi: |v{kodi}|\n'
                       'Python: |v{python}|\n'
                       'Path: |{path}|\n'
                       'Params: |{params}|'
                       .format(version=context.get_version(),
                               kodi=str(system_version),
                               python=system_version.get_python_version(),
                               path=context.get_path(),
                               params=params))

    plugin.run(provider, context, focused=(current_uri == new_uri))

    if profiler:
        profiler.print_stats()
