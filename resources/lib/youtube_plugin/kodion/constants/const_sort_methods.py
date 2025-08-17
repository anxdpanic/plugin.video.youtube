# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import sys

from ..compatibility import xbmc, xbmcplugin


xbmcplugin = xbmcplugin.__dict__
namespace = sys.modules[__name__]
methods = [
    ('UNSORTED',                        571,    0),
    ('NONE',                            16018,  None),
    ('LABEL',                           551,    1),
    ('LABEL_IGNORE_THE',                551,    None),
    ('DATE',                            552,    2),
    ('SIZE',                            553,    3),
    ('FILE',                            561,    4),
    ('FULLPATH',                        573,    5),
    ('DRIVE_TYPE',                      564,    6),
    ('TITLE',                           556,    7),
    ('TITLE_IGNORE_THE',                556,    None),
    ('TRACKNUM',                        554,    8),
    ('DURATION',                        180,    9),
    ('ARTIST',                          557,    10),
    ('ARTIST_IGNORE_THE',               557,    None),
    ('ALBUM',                           558,    12),
    ('ALBUM_IGNORE_THE',                558,    None),
    ('GENRE',                           515,    14),
    ('COUNTRY',                         574,    15),
    ('VIDEO_YEAR',                      562,    16),
    ('VIDEO_RATING',                    563,    17),
    ('VIDEO_USER_RATING',               38018,  18),
    ('PROGRAM_COUNT',                   567,    21),
    ('PLAYLIST_ORDER',                  559,    22),
    ('EPISODE',                         20359,  23),
    ('DATEADDED',                       570,    40),
    ('VIDEO_TITLE',                     556,    None),
    ('VIDEO_SORT_TITLE',                171,    29),
    ('VIDEO_SORT_TITLE_IGNORE_THE',     171,    None),
    ('VIDEO_RUNTIME',                   180,    None),
    ('PRODUCTIONCODE',                  20368,  30),
    ('SONG_RATING',                     563,    None),
    ('SONG_USER_RATING',                38018,  None),
    ('MPAA_RATING',                     20074,  31),
    ('STUDIO',                          572,    39),
    ('STUDIO_IGNORE_THE',               572,    None),
    ('LABEL_IGNORE_FOLDERS',            551,    None),
    ('LASTPLAYED',                      568,    41),
    ('PLAYCOUNT',                       567,    42),
    ('LISTENERS',                       20455,  43),
    ('BITRATE',                         623,    44),
    ('CHANNEL',                         19029,  46),
    ('DATE_TAKEN',                      577,    48),
    ('VIDEO_ORIGINAL_TITLE',            20376,  57),
    ('VIDEO_ORIGINAL_TITLE_IGNORE_THE', 20376,  None),
]
SORT_METHOD_MAPPING = {}

name = string_id = sort_id = fullname = None
for name, string_id, sort_id in methods:
    fullname = 'SORT_METHOD_' + name
    if fullname in xbmcplugin:
        setattr(namespace, name, xbmcplugin[fullname])
    else:
        setattr(namespace, name, -1)
        continue
    if sort_id is not None:
        SORT_METHOD_MAPPING[xbmc.getLocalizedString(string_id)] = sort_id

del (
    sys,
    xbmc,
    xbmcplugin,
    namespace,
    methods,
    name,
    string_id,
    sort_id,
    fullname,
)
