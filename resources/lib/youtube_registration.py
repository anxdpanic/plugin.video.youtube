# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from youtube_plugin.kodion import logging
from youtube_plugin.kodion.constants import ADDON_ID
from youtube_plugin.kodion.context import XbmcContext


def register_api_keys(addon_id, api_key, client_id, client_secret):
    """
    Usage:

    addon.xml
    ---
    <import addon="plugin.video.youtube" version="6.0.0"/>
    ---

    .py
    ---
    import youtube_registration
    youtube_registration.register_api_keys(addon_id='plugin.video.example',
                                           api_key='A1zaSyA0b5sTjgxzTzYLmVtradlFVBfSHNOJKS0',
                                           client_id='825419953561-ert5tccq1r0upsuqdf5nm3le39czk23a.apps.googleusercontent.com',
                                           client_secret='Y5cE1IKzJQe1NZ0OsOoEqpu3')
    # then use your keys by appending an addon_id param to the plugin url
    xbmc.executebuiltin('RunPlugin(plugin://plugin.video.youtube/channel/UCaBf1a-dpIsw8OxqH4ki2Kg/?addon_id=plugin.video.example)')
    # addon_id will be passed to all following calls
    # also see youtube_authentication.py and youtube_requests.py
    ---

    :param addon_id: id of the add-on being registered
    :param api_key: YouTube Data v3 API key
    :param client_id: YouTube Data v3 Client id
    :param client_secret: YouTube Data v3 Client secret
    """

    if not addon_id or addon_id == ADDON_ID:
        logging.error_trace('Invalid addon_id: %r', addon_id)
        return

    context = XbmcContext()

    access_manager = context.get_access_manager()
    if access_manager.add_new_developer(addon_id):
        logging.debug('Creating developer user: %r', addon_id)

    api_store = context.get_api_store()
    if api_store.update_developer_config(
            addon_id, api_key, client_id, client_secret
    ):
        logging.debug('Keys registered: %r', addon_id)
    else:
        logging.debug('No update performed: %r', addon_id)
