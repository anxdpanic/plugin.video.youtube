# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import copy
import platform

from .context import XbmcContext
from .plugin import XbmcPlugin


__all__ = ('run',)


__PLUGIN__ = XbmcPlugin()


def run(provider, context=None):

    if not context:
        context = XbmcContext()

    context.log_debug('Starting Kodion framework by bromix...')

    addon_version = context.get_version()
    python_version = 'Python {0}'.format(platform.python_version())

    redacted = '<redacted>'
    params = copy.deepcopy(context.get_params())
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

    __PLUGIN__.run(provider, context)
    provider.tear_down(context)

