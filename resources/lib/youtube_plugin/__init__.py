# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals


key_sets = {
    'youtube-tv': {
        'api_key': 'QUl6YVN5QzZmdlpTSkhBN1Z6NWo4akNpS1J0N3RVSU9xakUyTjNn',
        'client_id': 'ODYxNTU2NzA4NDU0LWQ2ZGxtM2xoMDVpZGQ4bnBlazE4azZiZThiYTNvYzY4',
        'client_secret': 'U2JvVmhvRzlzMHJOYWZpeENTR0dLWEFU',
    },
    'youtube-vr': {
        'api_key': '',
        'client_id': 'NjUyNDY5MzEyMTY5LTRsdnM5Ym5ocjlscG5zOXY0NTFqNW9pdmQ4MXZqdnUx',
        'client_secret': 'M2ZUV3JCSkk1VW9qbTFUSzdfaUpDVzVa',
    },
    'provided': {
        '0': {
            'api_key': '',
            'client_id': '',
            'client_secret': '',
        }
    }
}

__all__ = ('kodion', 'youtube', 'key_sets',)
