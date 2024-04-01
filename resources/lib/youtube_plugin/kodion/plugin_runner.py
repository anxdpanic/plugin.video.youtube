# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals


__all__ = ('run',)


def run(provider, context=None):
    from .compatibility import xbmc

    profiler = xbmc.getCondVisibility('System.GetBool(debug.showloginfo)')
    if profiler:
        from .debug import Profiler

        profiler = Profiler(enabled=True, lazy=False)

    from copy import deepcopy
    from platform import python_version

    from .plugin import XbmcPlugin

    plugin = XbmcPlugin()
    if not context:
        from .context import XbmcContext

        context = XbmcContext()

    context.log_debug('Starting Kodion framework by bromix...')

    addon_version = context.get_version()
    python_version = 'Python {0}'.format(python_version())

    redacted = '<redacted>'
    params = deepcopy(context.get_params())
    if 'api_key' in params:
        params['api_key'] = redacted
    if 'client_id' in params:
        params['client_id'] = redacted
    if 'client_secret' in params:
        params['client_secret'] = redacted

    context.log_notice('Running: {plugin} ({version}) on {kodi} with {python}\n'
                       'Path: {path}\n'
                       'Params: {params}'
                       .format(plugin=context.get_name(),
                               version=addon_version,
                               kodi=context.get_system_version(),
                               python=python_version,
                               path=context.get_path(),
                               params=params))

    try:
        plugin.run(provider, context)
    finally:
        if profiler:
            profiler.print_stats()

        provider.tear_down(context)
