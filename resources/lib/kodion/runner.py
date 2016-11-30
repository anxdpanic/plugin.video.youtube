__author__ = 'bromix'

__all__ = ['run']

from .impl import Runner
from .impl import Context

__RUNNER__ = Runner()


def run(provider, context=None):
    if not context:
        context = Context()
        pass

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
    context.log_notice(
        'Running: %s (%s) on %s with %s' % (context.get_name(), context.get_version(), version, python_version))
    context.log_debug('Path: "%s' % context.get_path())
    context.log_debug('Params: "%s"' % unicode(context.get_params()))
    __RUNNER__.run(provider, context)
    provider.tear_down(context)
    context.log_debug('Shutdown of Kodion')
    pass
