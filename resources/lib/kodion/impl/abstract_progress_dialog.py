__author__ = 'bromix'


class AbstractProgressDialog(object):
    def __init__(self, total=100):
        self._total = int(total)
        self._position = 0
        pass

    def get_total(self):
        return self._total

    def get_position(self):
        return self._position

    def close(self):
        raise NotImplementedError()

    def set_total(self, total):
        self._total = int(total)
        pass

    def update(self, steps=1, text=None):
        raise NotImplementedError()

    def is_aborted(self):
        raise NotImplementedError()

    pass
