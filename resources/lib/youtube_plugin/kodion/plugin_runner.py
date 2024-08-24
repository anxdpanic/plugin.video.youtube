# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from platform import python_version

from .context import XbmcContext
from .plugin import XbmcPlugin
from ..youtube import Provider


__all__ = ('run',)

_context = XbmcContext()
_plugin = XbmcPlugin()
_provider = Provider()

_profiler = _context.get_infobool('System.GetBool(debug.showloginfo)')
if _profiler:
    from .debug import Profiler

    _profiler = Profiler(enabled=False, print_callees=False, num_lines=20)


def run(context=_context,
        plugin=_plugin,
        provider=_provider,
        profiler=_profiler):
    if profiler:
        profiler.enable(flush=True)

    context.log_debug('Starting Kodion framework by bromix...')

    current_uri = context.get_uri()
    context.init()
    new_uri = context.get_uri()

    params = context.get_params().copy()
    for key in ('api_key', 'client_id', 'client_secret'):
        if key in params:
            params[key] = '<redacted>'

    context.log_notice('Running: {plugin} ({version})'
                       ' on {kodi} with Python {python}\n'
                       'Path: {path}\n'
                       'Params: {params}'
                       .format(plugin=context.get_name(),
                               version=context.get_version(),
                               kodi=context.get_system_version(),
                               python=python_version(),
                               path=context.get_path(),
                               params=params))

    plugin.run(provider, context, focused=(current_uri == new_uri))

    if profiler:
        profiler.print_stats()
