# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

# import base exception of kodion directly into the kodion namespace
from .exceptions import KodionException

# decorator for registering paths for navigating of a provider
from .register_provider_path import RegisterProviderPath

# Abstract provider for implementation by the user
from .abstract_provider import AbstractProvider

# import specialized implementation into the kodion namespace
from .context import Context

from . import logger


__all__ = (
    'AbstractProvider',
    'Context',
    'KodionException',
    'RegisterProviderPath',
    'json_store',
    'logger',
    'utils',
)

__version__ = '1.5.4'
