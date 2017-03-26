import os

__author__ = 'bromix'


def debug_here(host='localhost'):
    import sys

    for comp in sys.path:
        if comp.find('addons') != -1:
            pydevd_path = os.path.normpath(os.path.join(comp, os.pardir, 'script.module.pydevd', 'lib'))
            sys.path.append(pydevd_path)
            break
        pass

    import pydevd
    pydevd.settrace(host, stdoutToServer=True, stderrToServer=True)
    pass
