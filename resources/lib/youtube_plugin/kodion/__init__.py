# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .abstract_provider import (
    # Abstract provider for implementation by the user
    AbstractProvider,
)
# import base exception of kodion directly into the kodion namespace
from .exceptions import KodionException


__all__ = (
    'AbstractProvider',
    'KodionException',
)

__version__ = '1.5.4'
