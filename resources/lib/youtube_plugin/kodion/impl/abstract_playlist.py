# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""


class AbstractPlaylist(object):
    def __init__(self):
        pass

    def clear(self):
        raise NotImplementedError()

    def add(self, base_item):
        raise NotImplementedError()

    def shuffle(self):
        raise NotImplementedError()

    def unshuffle(self):
        raise NotImplementedError()
