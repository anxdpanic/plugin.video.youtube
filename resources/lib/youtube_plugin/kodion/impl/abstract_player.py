# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""


class AbstractPlayer(object):
    def __init__(self):
        pass

    def play(self, playlist_index=-1):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def pause(self):
        raise NotImplementedError()
