__author__ = 'bromix'

from ..abstract_progress_dialog import AbstractProgressDialog


class MockProgressDialog(AbstractProgressDialog):
    def __init__(self, heading, text):
        AbstractProgressDialog.__init__(self, 100)
        pass

    def close(self):
        print 'Closing progress dialog'
        pass

    def update(self, steps=1, text=None):
        self._position += steps

        print 'Progress: %d/%d - %s' % (self._position, self._total, text)
        pass

    def is_aborted(self):
        return False

    pass
