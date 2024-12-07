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
    def __init__(self,
                 heading,
                 message='',
                 background=False,
                 message_template=None,
                 template_params=None):
        super(XbmcProgressDialog, self).__init__(
            dialog=(xbmcgui.DialogProgressBG
                    if background else
                    xbmcgui.DialogProgress),
            heading=heading,
            message=message,
            total=0,
            message_template=message_template,
            template_params=template_params,
        )
