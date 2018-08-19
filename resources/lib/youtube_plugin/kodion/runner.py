__author__ = 'bromix'

__all__ = ['run']

import copy
import json
import os
import timeit

from .impl import Runner
from .impl import Context


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
        if not __DEBUG_RUNTIME_SINGLE_FILE:
            filename_path_part = context.get_path().lstrip('/').rstrip('/').replace('/', '_')
            debug_file_name = 'runtime_%s-%s.json' % (filename_path_part, addon_version)
            default_contents = {"runtimes": []}
        else:
            debug_file_name = 'runtime-%s.json' % addon_version
            default_contents = {"runtimes": {}}

        debug_file = os.path.join(context.get_debug_path(), debug_file_name)
        with open(debug_file, 'a') as f:
            pass  # touch

        with open(debug_file, 'r') as f:
            contents = f.read()

        with open(debug_file, 'w') as f:
            if not contents:
                contents = default_contents
            else:
                contents = json.loads(contents)
            if not __DEBUG_RUNTIME_SINGLE_FILE:
                items = contents.get('runtimes', [])
                items.append({"path": context.get_path(), "parameters": context.get_params(), "runtime": round(elapsed, 4)})
                contents['runtimes'] = items
            else:
                items = contents.get('runtimes', {}).get(context.get_path(), [])
                items.append({"parameters": context.get_params(), "runtime": round(elapsed, 4)})
                contents['runtimes'][context.get_path()] = items
            f.write(json.dumps(contents, indent=4))

    context.log_debug('Shutdown of Kodion after |%s| seconds' % str(round(elapsed, 4)))
