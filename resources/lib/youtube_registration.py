# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from base64 import b64encode
from youtube_plugin.kodion.json_store import APIKeyStore
from youtube_plugin.kodion.impl import Context


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

    context = Context(plugin_id='plugin.video.youtube')

    if not addon_id or addon_id == 'plugin.video.youtube':
        context.log_error('Register API Keys: |%s| Invalid addon_id' % addon_id)
        return

    api_jstore = APIKeyStore()
    json_api = api_jstore.get_data()

    access_manager = context.get_access_manager()

    jkeys = json_api['keys']['developer'].get(addon_id, {})

    api_key = b64encode(bytes(api_key, 'utf-8')).decode('ascii')
    client_id = b64encode(bytes(client_id, 'utf-8')).decode('ascii')
    client_secret = b64encode(bytes(client_secret, 'utf-8')).decode('ascii')

    api_keys = {
        'origin': addon_id, 'main': {
            'system': 'JSONStore', 'key': api_key, 'id': client_id, 'secret': client_secret
        }
    }

    if jkeys and jkeys == api_keys:
        context.log_debug('Register API Keys: |%s| No update required' % addon_id)
    else:
        json_api['keys']['developer'][addon_id] = api_keys
        api_jstore.save(json_api)
        context.log_debug('Register API Keys: |%s| Keys registered' % addon_id)

    developers = access_manager.get_developers()
    if not developers.get(addon_id, None):
        developers[addon_id] = access_manager.get_new_developer()
        access_manager.set_developers(developers)
        context.log_debug('Creating developer user: |%s|' % addon_id)
