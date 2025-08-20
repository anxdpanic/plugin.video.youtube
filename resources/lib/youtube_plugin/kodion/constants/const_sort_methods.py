# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import sys

from ..compatibility import (
    xbmcplugin,
)


# Sort methods exposed via xbmcplugin vary by Kodi version.
# Rather than try to access them directly they are hardcoded here and checked
# against what is defined in xbmcplugin.
# IDs of sort methods exposed via xbmcplugin are defined in SortMethod
# https://github.com/xbmc/xbmc/blob/master/xbmc/SortFileItem.h
# IDs of sort methods used by the Kodi GUI and builtins are defined in SortBy
# https://github.com/xbmc/xbmc/blob/master/xbmc/utils/SortUtils.h
# The IDs don't match...
# As a workaround they are mapped here using the localised label used in the GUI
# to allow the sort methods to be set by the addon and then changed dynamically
# using infolabels and builtins
methods = [
    # Sort method name,                 Label ID, SortBy ID
    ('UNSORTED',                        571,      0),
    ('NONE',                            16018,    0),
    ('LABEL',                           551,      1),
    ('LABEL_IGNORE_THE',                551,      None),
    ('DATE',                            552,      2),
    ('SIZE',                            553,      3),
    ('FILE',                            561,      4),
    ('FULLPATH',                        573,      5),
    ('DRIVE_TYPE',                      564,      6),
    ('TITLE',                           556,      7),
    ('TITLE_IGNORE_THE',                556,      None),
    ('TRACKNUM',                        554,      8),
    ('DURATION',                        180,      9),
    ('ARTIST',                          557,      10),
    ('ARTIST_IGNORE_THE',               557,      None),
    ('ALBUM',                           558,      12),
    ('ALBUM_IGNORE_THE',                558,      None),
    ('GENRE',                           515,      14),
    ('COUNTRY',                         574,      15),
    ('VIDEO_YEAR',                      562,      16),
    ('VIDEO_RATING',                    563,      17),
    ('VIDEO_USER_RATING',               38018,    18),
    ('PROGRAM_COUNT',                   567,      21),
    ('PLAYLIST_ORDER',                  559,      22),
    ('EPISODE',                         20359,    23),
    ('DATEADDED',                       570,      40),
    ('VIDEO_TITLE',                     556,      7),
    ('VIDEO_SORT_TITLE',                171,      29),
    ('VIDEO_SORT_TITLE_IGNORE_THE',     171,      None),
    ('VIDEO_RUNTIME',                   180,      9),
    ('PRODUCTIONCODE',                  20368,    30),
    ('SONG_RATING',                     563,      17),
    ('SONG_USER_RATING',                38018,    18),
    ('MPAA_RATING',                     20074,    31),
    ('STUDIO',                          572,      39),
    ('STUDIO_IGNORE_THE',               572,      None),
    ('LABEL_IGNORE_FOLDERS',            551,      None),
    ('LASTPLAYED',                      568,      41),
    ('PLAYCOUNT',                       567,      42),
    ('LISTENERS',                       20455,    43),
    ('BITRATE',                         623,      44),
    ('CHANNEL',                         19029,    46),
    ('DATE_TAKEN',                      577,      48),
    ('VIDEO_ORIGINAL_TITLE',            20376,    57),
    ('VIDEO_ORIGINAL_TITLE_IGNORE_THE', 20376,    None),
]

SORT = sys.modules[__name__]
name = label_id = sort_by = sort_method = None
for name, label_id, sort_by in methods:
    sort_method = getattr(xbmcplugin, 'SORT_METHOD_' + name, 0)
    setattr(SORT, name, sort_method)

del (
    sys,
    xbmcplugin,
    methods,
    SORT,
    name,
    label_id,
    sort_by,
    sort_method,
)
