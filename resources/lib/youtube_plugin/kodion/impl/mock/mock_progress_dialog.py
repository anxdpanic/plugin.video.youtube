__author__ = 'bromix'

from ..abstract_progress_dialog import AbstractProgressDialog


class MockProgressDialog(AbstractProgressDialog):
    def __init__(self, heading, text):
        AbstractProgressDialog.__init__(self, 100)

    def close(self):
        print('Closing progress dialog')

    def update(self, steps=1, text=None):
        self._position += steps

        print('Progress: %d/%d - %s' % (self._position, self._total, text))

    def is_aborted(self):
        return False
