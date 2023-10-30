# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import sys
from xbmcplugin import __dict__ as xbmcplugin


namespace = sys.modules[__name__]
names = [
    # 'NONE',
    'LABEL',
    'LABEL_IGNORE_THE',
    'DATE',
    'SIZE',
    'FILE',
    'DRIVE_TYPE',
    'TRACKNUM',
    'DURATION',
    'TITLE',
    'TITLE_IGNORE_THE',
    'ARTIST',
    # 'ARTIST_AND_YEAR',
    'ARTIST_IGNORE_THE',
    'ALBUM',
    'ALBUM_IGNORE_THE',
    'GENRE',
    'COUNTRY',
    # 'YEAR',
    'VIDEO_YEAR',
    'VIDEO_RATING',
    'VIDEO_USER_RATING',
    'DATEADDED',
    'PROGRAM_COUNT',
    'PLAYLIST_ORDER',
    'EPISODE',
    'VIDEO_TITLE',
    'VIDEO_SORT_TITLE',
    'VIDEO_SORT_TITLE_IGNORE_THE',
    'PRODUCTIONCODE',
    'SONG_RATING',
    'SONG_USER_RATING',
    'MPAA_RATING',
    'VIDEO_RUNTIME',
    'STUDIO',
    'STUDIO_IGNORE_THE',
    'FULLPATH',
    'LABEL_IGNORE_FOLDERS',
    'LASTPLAYED',
    'PLAYCOUNT',
    'LISTENERS',
    'UNSORTED',
    'CHANNEL',
    'CHANNEL_NUMBER',
    'BITRATE',
    'DATE_TAKEN',
    'CLIENT_CHANNEL_ORDER',
    'TOTAL_DISCS',
    'ORIG_DATE',
    'BPM',
    'VIDEO_ORIGINAL_TITLE',
    'VIDEO_ORIGINAL_TITLE_IGNORE_THE',
    'PROVIDER',
    'USER_PREFERENCE',
    # 'MAX',
]

for name in names:
    fullname = 'SORT_METHOD_' + name
    setattr(namespace, name,
            xbmcplugin[fullname] if fullname in xbmcplugin else -1)

del sys, xbmcplugin, namespace, names, name, fullname
