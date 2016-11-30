__author__ = 'bromix'


class RegisterProviderPath(object):
    def __init__(self, re_path):
        self._kodion_re_path = re_path
        pass

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # only use a wrapper if you need extra code to be run here
            return func(*args, **kwargs)

        wrapper.kodion_re_path = self._kodion_re_path
        return wrapper

    pass
