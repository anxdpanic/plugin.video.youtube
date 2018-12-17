# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import copy
import timeit

from .impl import Runner
from .impl import Context

from . import debug

__all__ = ['run']

__DEBUG_RUNTIME = False
__DEBUG_RUNTIME_SINGLE_FILE = False

__RUNNER__ = Runner()


def run(provider, context=None):
    start_time = timeit.default_timer()

    if not context:
        context = Context(plugin_id='plugin.video.youtube')

    context.log_debug('Starting Kodion framework by bromix...')
    python_version = 'Unknown version of Python'
    try:
        import platform

        python_version = str(platform.python_version())
        python_version = 'Python %s' % python_version
    except:
        # do nothing
        pass

    version = context.get_system_version()
    name = context.get_name()
    addon_version = context.get_version()
    redacted = '<redacted>'
    context_params = copy.deepcopy(context.get_params())
    if 'api_key' in context_params:
        context_params['api_key'] = redacted
    if 'client_id' in context_params:
        context_params['client_id'] = redacted
    if 'client_secret' in context_params:
        context_params['client_secret'] = redacted

    context.log_notice('Running: %s (%s) on %s with %s\n\tPath: %s\n\tParams: %s' %
                       (name, addon_version, version, python_version,
                        context.get_path(), str(context_params)))

    __RUNNER__.run(provider, context)
    provider.tear_down(context)

    elapsed = timeit.default_timer() - start_time

    if __DEBUG_RUNTIME:
        debug.runtime(context, addon_version, elapsed, single_file=__DEBUG_RUNTIME_SINGLE_FILE)

    context.log_debug('Shutdown of Kodion after |%s| seconds' % str(round(elapsed, 4)))
