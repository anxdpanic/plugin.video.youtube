# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

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
        position = int((100.0 / float(self._total)) * float(self._position))

        if isinstance(text, str):
            self._dialog.update(percent=position, message=text)
        else:
            self._dialog.update(percent=position)

    def is_aborted(self):
        return False
