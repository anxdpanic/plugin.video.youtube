# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..abstract_progress_dialog import AbstractProgressDialog
from ...compatibility import xbmcgui


class XbmcProgressDialog(AbstractProgressDialog):
    def __init__(self, heading, text):
        super(XbmcProgressDialog, self).__init__(xbmcgui.DialogProgress,
                                                 heading,
                                                 text,
                                                 100)

    def is_aborted(self):
        return self._dialog.iscanceled()


class XbmcProgressDialogBG(AbstractProgressDialog):
    def __init__(self, heading, text):
        super(XbmcProgressDialogBG, self).__init__(xbmcgui.DialogProgressBG,
                                                   heading,
                                                   text,
                                                   100)

    def is_aborted(self):
        return False
