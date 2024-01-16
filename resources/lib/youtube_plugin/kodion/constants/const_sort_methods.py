# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import sys

from ..compatibility import xbmcplugin


xbmcplugin = xbmcplugin.__dict__
namespace = sys.modules[__name__]
names = [
    'NONE',                             # 0
    'LABEL',                            # 1
    'LABEL_IGNORE_THE',                 # 2
    'DATE',                             # 3
    'SIZE',                             # 4
    'FILE',                             # 5
    'DRIVE_TYPE',                       # 6
    'TRACKNUM',                         # 7
    'DURATION',                         # 8
    'TITLE',                            # 9
    'TITLE_IGNORE_THE',                 # 10
    'ARTIST',                           # 11
    'ARTIST_IGNORE_THE',                # 13
    'ALBUM',                            # 14
    'ALBUM_IGNORE_THE',                 # 15
    'GENRE',                            # 16
    'COUNTRY',                          # 17
    'VIDEO_YEAR',                       # 18
    'VIDEO_RATING',                     # 19
    'VIDEO_USER_RATING',                # 20
    'DATEADDED',                        # 21
    'PROGRAM_COUNT',                    # 22
    'PLAYLIST_ORDER',                   # 23
    'EPISODE',                          # 24
    'VIDEO_TITLE',                      # 25
    'VIDEO_SORT_TITLE',                 # 26
    'VIDEO_SORT_TITLE_IGNORE_THE',      # 27
    'PRODUCTIONCODE',                   # 28
    'SONG_RATING',                      # 29
    'SONG_USER_RATING',                 # 30
    'MPAA_RATING',                      # 31
    'VIDEO_RUNTIME',                    # 32
    'STUDIO',                           # 33
    'STUDIO_IGNORE_THE',                # 34
    'FULLPATH',                         # 35
    'LABEL_IGNORE_FOLDERS',             # 36
    'LASTPLAYED',                       # 37
    'PLAYCOUNT',                        # 38
    'LISTENERS',                        # 39
    'UNSORTED',                         # 40
    'CHANNEL',                          # 41
    'BITRATE',                          # 43
    'DATE_TAKEN',                       # 44
    'VIDEO_ORIGINAL_TITLE',             # 49
    'VIDEO_ORIGINAL_TITLE_IGNORE_THE',  # 50
]

for name in names:
    fullname = 'SORT_METHOD_' + name
    setattr(namespace, name,
            xbmcplugin[fullname] if fullname in xbmcplugin else -1)

del sys, xbmcplugin, namespace, names, name, fullname
