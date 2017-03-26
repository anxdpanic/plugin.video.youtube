__author__ = 'bromix'


class AbstractProviderRunner(object):
    def __init__(self):
        pass

    def run(self, provider, context=None):
        raise NotImplementedError()

    pass