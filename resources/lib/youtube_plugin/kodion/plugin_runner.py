# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from . import logging
from .constants import CHECK_SETTINGS
from .context import XbmcContext
from .debug import Profiler
from .plugin import XbmcPlugin
from ..youtube import Provider


__all__ = ('run',)

_context = XbmcContext()
_log = logging.getLogger(__name__)
_plugin = XbmcPlugin()
_provider = Provider()
_profiler = Profiler(enabled=False, print_callees=False, num_lines=20)


def run(context=_context,
        log=_log,
        plugin=_plugin,
        provider=_provider,
        profiler=_profiler):

    if context.get_ui().pop_property(CHECK_SETTINGS):
        provider.reset_client()
        settings = context.get_settings(refresh=True)
    else:
        settings = context.get_settings()

    log_level = settings.log_level()
    if log_level:
        log.debugging = True
        if log_level & 2:
            log.stack_info = True
            log.verbose_logging = True
        else:
            log.stack_info = False
            log.verbose_logging = False
        profiler.enable(flush=True)
    else:
        log.debugging = False
        log.stack_info = False
        log.verbose_logging = False
        profiler.disable()

    current_uri = context.get_uri()
    current_path = context.get_path()
    current_params = context.get_params()
    context.init()
    new_uri = context.get_uri()
    new_params = context.get_params()
    new_handle = context.get_handle()

    forced = (new_handle != -1
              and ((current_uri == new_uri
                    and current_path != '/'
                    and current_params == new_params)
                   or (current_uri != new_uri
                       and current_path == '/'
                       and not current_params)
                   or (current_path == '/play/')))
    if forced:
        refresh = context.refresh_requested(force=True, off=True)
        if refresh:
            new_params['refresh'] = refresh

    log_params = new_params.copy()
    for key in ('api_key', 'client_id', 'client_secret'):
        if key in log_params:
            log_params[key] = '<redacted>'

    system_version = context.get_system_version()
    log.info(('Running v{version}',
              'Kodi:   v{kodi}',
              'Python: v{python}',
              'Handle: {handle}',
              'Path:   |{path}|',
              'Params: |{params}|'),
             version=context.get_version(),
             kodi=str(system_version),
             python=system_version.get_python_version(),
             handle=new_handle,
             path=context.get_path(),
             params=log_params)

    plugin.run(provider, context, forced=forced)

    if log_level:
        profiler.print_stats()
