# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import atexit
from copy import deepcopy
from platform import python_version

from .plugin import XbmcPlugin
from .context import XbmcContext
from ..youtube import Provider


__all__ = ('run',)

context = XbmcContext()
plugin = XbmcPlugin()
provider = Provider()

profiler = context.get_infobool('System.GetBool(debug.showloginfo)')
if profiler:
    from .debug import Profiler

    profiler = Profiler(enabled=False)

atexit.register(provider.tear_down)
atexit.register(context.tear_down)


def run():
    if profiler:
        profiler.enable(flush=True)

    context.log_debug('Starting Kodion framework by bromix...')
    context.init()

    params = deepcopy(context.get_params())
    for key in ('api_key', 'client_id', 'client_secret'):
        if key in params:
            params[key] = '<redacted>'

    context.log_notice('Running: {plugin} ({version}) on {kodi} with {python}\n'
                       'Path: {path}\n'
                       'Params: {params}'
                       .format(plugin=context.get_name(),
                               version=context.get_version(),
                               kodi=context.get_system_version(),
                               python='Python {0}'.format(python_version()),
                               path=context.get_path(),
                               params=params))

    plugin.run(provider, context)

    if profiler:
        profiler.print_stats()
