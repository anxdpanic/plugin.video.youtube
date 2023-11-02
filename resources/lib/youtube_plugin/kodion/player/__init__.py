# -*- coding: utf-8 -*-
"""

    Copyright (C) 2023-present plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from .xbmc.xbmc_player import XbmcPlayer as Player
from .xbmc.xbmc_playlist import XbmcPlaylist as Playlist


__all__ = ('Player', 'Playlist', )