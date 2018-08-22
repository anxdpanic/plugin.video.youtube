import os
import json

__author__ = 'bromix'


def debug_here(host='localhost'):
    import sys

    for comp in sys.path:
        if comp.find('addons') != -1:
            pydevd_path = os.path.normpath(os.path.join(comp, os.pardir, 'script.module.pydevd', 'lib'))
            sys.path.append(pydevd_path)
            break

    import pydevd
    pydevd.settrace(host, stdoutToServer=True, stderrToServer=True)


def runtime(context, addon_version, elapsed, single_file=True):
    if not single_file:
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
        if not single_file:
            items = contents.get('runtimes', [])
            items.append({"path": context.get_path(), "parameters": context.get_params(), "runtime": round(elapsed, 4)})
            contents['runtimes'] = items
        else:
            items = contents.get('runtimes', {}).get(context.get_path(), [])
            items.append({"parameters": context.get_params(), "runtime": round(elapsed, 4)})
            contents['runtimes'][context.get_path()] = items
        f.write(json.dumps(contents, indent=4))
