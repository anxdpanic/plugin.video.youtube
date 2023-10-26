# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from xbmc import log

from youtube_plugin import youtube
from youtube_plugin.kodion import runner
from youtube_plugin.kodion.debug import Profiler


profiler = Profiler(enabled=True, lazy=False)
__provider__ = youtube.Provider()
runner.run(__provider__)
log(profiler.get_stats(), 1)
