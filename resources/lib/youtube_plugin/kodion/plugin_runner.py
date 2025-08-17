# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import gc
from . import logging
from .constants import CHECK_SETTINGS, PATHS
from .context import XbmcContext
from .debug import Profiler
from .plugin import XbmcPlugin
from ..youtube import Provider


__all__ = ('run',)

_context = XbmcContext()
_log = logging.getLogger(__name__)
_plugin = XbmcPlugin()
_provider = Provider()
_profiler = Profiler(enabled=False,
                     timer=Profiler.elapsed_timer,
                     print_callees=False,
                     num_lines=20)


def run(context=_context,
        log=_log,
        plugin=_plugin,
        provider=_provider,
        profiler=_profiler):
    gc.disable()
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

    current_path = context.get_path().rstrip('/')
    current_params = context.get_original_params()
    current_handle = context.get_handle()
    context.init()
    new_path = context.get_path().rstrip('/')
    new_params = context.get_original_params()
    new_handle = context.get_handle()

    forced = False
    if new_handle != -1:
        if current_path == PATHS.PLAY:
            forced = True
        elif current_path == new_path:
            if current_path:
                if current_params == new_params:
                    forced = True
        # The following conditions will be true in some forced refresh scenarios
        # e.g. addon disabling/enabling, but will also be true for a number of
        # non-forced refreshes such as when a new language invoker thread starts
        # for a non-plugin context.
        #     elif not current_params:
        #         forced = True
        # elif current_handle == -1 and not current_path and not current_params:
        #     forced = True

    new_params = {}
    if forced:
        refresh = context.refresh_requested(force=True, off=True)
        new_params['refresh'] = refresh if refresh else 0
    if new_params:
        context.set_params(**new_params)

    log_params = context.get_params().copy()
    for key in ('api_key', 'client_id', 'client_secret'):
        if key in log_params:
            log_params[key] = '<redacted>'

    system_version = context.get_system_version()
    log.info(('Running v{version}',
              'Kodi:   v{kodi}',
              'Python: v{python}',
              'Handle: {handle}',
              'Path:   {path!r}',
              'Params: {params!r}',
              'Forced: {forced!r}'),
             version=context.get_version(),
             kodi=str(system_version),
             python=system_version.get_python_version(),
             handle=new_handle,
             path=new_path,
             params=log_params,
             forced=forced)

    plugin.run(provider, context, forced=forced)

    if log_level:
        profiler.print_stats()
    gc.enable()
    gc.collect()
