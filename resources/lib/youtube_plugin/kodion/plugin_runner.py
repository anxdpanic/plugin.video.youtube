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
from .constants import (
    CHECK_SETTINGS,
    FOLDER_URI,
    PATHS,
)
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
    ui = context.get_ui()

    if ui.pop_property(CHECK_SETTINGS):
        provider.reset_client(context=context)
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

    old_path = context.get_path().rstrip('/')
    old_uri = ui.get_container_info(FOLDER_URI, container_id=None)
    old_handle = context.get_handle()
    context.init()
    current_path = context.get_path().rstrip('/')
    current_params = context.get_original_params()
    current_handle = context.get_handle()

    new_params = {}
    new_kwargs = {}

    params = context.get_params()
    refresh = context.refresh_requested(params=params)
    was_playing = old_path == PATHS.PLAY
    is_same_path = current_path == old_path and old_handle != -1

    if was_playing or is_same_path or refresh:
        old_path, old_params = context.parse_uri(
            old_uri,
            parse_params=False,
        )
        old_path = old_path.rstrip('/')
        is_same_path = current_path == old_path
        if was_playing and current_handle != -1:
            forced = True
        elif is_same_path and current_params == old_params:
            forced = True
        else:
            forced = False
    else:
        forced = False

    if forced:
        refresh = context.refresh_requested(force=True, off=True, params=params)
        new_params['refresh'] = refresh if refresh else 0

    if new_params:
        context.set_params(**new_params)

    system_version = context.get_system_version()
    log.info(('Running v{version}',
              'Kodi:   v{kodi}',
              'Python: v{python}',
              'Handle: {handle}',
              'Path:   {path!r} ({path_link})',
              'Params: {params!p}',
              'Forced: {forced!r}'),
             version=context.get_version(),
             kodi=str(system_version),
             python=system_version.get_python_version(),
             handle=current_handle,
             path=current_path,
             path_link='linked' if is_same_path else 'new',
             params=params,
             forced=forced)

    gc_threshold = gc.get_threshold()
    gc.set_threshold(0)
    try:
        plugin.run(provider,
                   context,
                   forced=forced,
                   is_same_path=is_same_path,
                   **new_kwargs)
    finally:
        if log_level:
            profiler.print_stats()
        gc.collect()
        gc.set_threshold(*gc_threshold)
