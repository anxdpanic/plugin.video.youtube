__author__ = 'bromix'

from six import string_types

import xbmcgui
from ..abstract_progress_dialog import AbstractProgressDialog


class XbmcProgressDialogBG(AbstractProgressDialog):
    def __init__(self, heading, text):
        AbstractProgressDialog.__init__(self, 100)
        self._dialog = xbmcgui.DialogProgressBG()
        self._dialog.create(heading, text)

        # simple reset because KODI won't do it :(
        self._position = 1
        self.update(steps=-1)

    def close(self):
        if self._dialog:
            self._dialog.close()
            self._dialog = None

    def update(self, steps=1, text=None):
        self._position += steps
        position = int(float((100.0 // self._total)) * self._position)

        if isinstance(text, string_types):
            self._dialog.update(percent=position, message=text)
        else:
            self._dialog.update(percent=position)

    def is_aborted(self):
        return False
