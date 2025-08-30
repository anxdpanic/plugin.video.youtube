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
    SORT_DIR,
    SORT_METHOD,
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
    gc.disable()

    ui = context.get_ui()

    if ui.pop_property(CHECK_SETTINGS):
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

    old_path, old_params = context.parse_uri(
        ui.get_container_info(FOLDER_URI, strict=False),
        parse_params=False,
    )
    old_path = old_path.rstrip('/')
    context.init()
    current_path = context.get_path().rstrip('/')
    current_params = context.get_original_params()
    current_handle = context.get_handle()

    new_params = {}
    new_kwargs = {}
    params = context.get_params()

    refresh = context.refresh_requested(params=params)
    is_same_path = refresh != 0 and current_path == old_path
    forced = (current_handle != -1
              and (old_path == PATHS.PLAY
                   or (is_same_path and current_params == old_params)))
    if forced:
        refresh = context.refresh_requested(force=True, off=True, params=params)
        new_params['refresh'] = refresh if refresh else 0

    sort_method = (
            params.get(SORT_METHOD)
            or ui.get_infolabel('Container.SortMethod')
    )
    if sort_method:
        new_kwargs[SORT_METHOD] = sort_method.lower()

    sort_dir = (
            params.get(SORT_DIR)
            or ui.get_infolabel('Container.SortOrder')
    )
    if sort_dir:
        new_kwargs[SORT_DIR] = sort_dir.lower()

    if new_params:
        context.set_params(**new_params)

    log_params = params.copy()
    for key in ('api_key', 'client_id', 'client_secret'):
        if key in log_params:
            log_params[key] = '<redacted>'

    system_version = context.get_system_version()
    log.info(('Running v{version}',
              'Kodi:   v{kodi}',
              'Python: v{python}',
              'Handle: {handle}',
              'Path:   {path!r} ({path_link})',
              'Params: {params!r}',
              'Forced: {forced!r}'),
             version=context.get_version(),
             kodi=str(system_version),
             python=system_version.get_python_version(),
             handle=current_handle,
             path=current_path,
             path_link='linked' if is_same_path else 'new',
             params=log_params,
             forced=forced)

    plugin.run(provider,
               context,
               forced=forced,
               is_same_path=is_same_path,
               **new_kwargs)

    if log_level:
        profiler.print_stats()

    gc.enable()
    gc.collect()
