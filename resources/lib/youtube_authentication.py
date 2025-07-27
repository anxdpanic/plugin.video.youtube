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
from youtube_plugin.youtube.helper import yt_login
from youtube_plugin.youtube.provider import Provider
from youtube_plugin.youtube.youtube_exceptions import LoginException


__all__ = (
    'LoginException',
    'reset_access_tokens',
    'sign_in',
    'sign_out',
)


def _auth(addon_id, mode=yt_login.SIGN_IN):
    """

    :param addon_id: id of the add-on being signed in
    :param mode: SIGN_IN or SIGN_OUT
    :return: addon provider, context and client
    """
    if not addon_id or addon_id == ADDON_ID:
        logging.error_trace('Invalid addon_id: %r', addon_id)
        return False

    provider = Provider()
    context = XbmcContext(params={'addon_id': addon_id})

    access_manager = context.get_access_manager()
    if access_manager.add_new_developer(addon_id):
        logging.debug('Creating developer user: %r', addon_id)

    client = provider.get_client(context=context)

    if mode == yt_login.SIGN_IN:
        if client.logged_in:
            yt_login.process(yt_login.SIGN_OUT,
                             provider,
                             context,
                             client=client,
                             refresh=False)
            client = None
    elif mode != yt_login.SIGN_OUT:
        raise Exception('Unknown mode: %r' % mode)

    yt_login.process(mode, provider, context, client=client, refresh=False)

    logged_in = provider.get_client(context=context).logged_in
    if mode == yt_login.SIGN_IN:
        return logged_in
    return not logged_in


def sign_in(addon_id):
    """
    To use the signed in context, see youtube_registration.py and youtube_requests.py
    Usage:

    addon.xml
    ---
    <import addon="plugin.video.youtube" version="6.1.0"/>
    ---

    .py
    ---
    import youtube_registration
    import youtube_authentication

    youtube_registration.register_api_keys(addon_id='plugin.video.example',
                                           api_key='A1zaSyA0b5sTjgxzTzYLmVtradlFVBfSHNOJKS0',
                                           client_id='825419953561-ert5tccq1r0upsuqdf5nm3le39czk23a.apps.googleusercontent.com',
                                           client_secret='Y5cE1IKzJQe1NZ0OsOoEqpu3')

    try:
        signed_in = youtube_authentication.sign_in(addon_id='plugin.video.example')  # refreshes access tokens if already signed in
    except youtube_authentication.LoginException as exc:
        error_message = exc.get_message()
        # handle error
        signed_in = False

    if signed_in:
        pass  # see youtube_registration.py and youtube_requests.py to use the signed in context
     ---

    :param addon_id: id of the add-on being signed in
    :return: boolean, True when signed in
    """

    return _auth(addon_id, mode=yt_login.SIGN_IN)


def sign_out(addon_id):
    """
    Usage:

    addon.xml
    ---
    <import addon="plugin.video.youtube" version="6.1.0"/>
    ---

    .py
    ---
    import youtube_registration
    import youtube_authentication

    youtube_registration.register_api_keys(addon_id='plugin.video.example',
                                           api_key='A1zaSyA0b5sTjgxzTzYLmVtradlFVBfSHNOJKS0',
                                           client_id='825419953561-ert5tccq1r0upsuqdf5nm3le39czk23a.apps.googleusercontent.com',
                                           client_secret='Y5cE1IKzJQe1NZ0OsOoEqpu3')

    signed_out = youtube_authentication.sign_out(addon_id='plugin.video.example')
    if signed_out:
        pass
     ---

    :param addon_id: id of the add-on being signed out
    :return: boolean, True when signed out
    """

    return _auth(addon_id, mode=yt_login.SIGN_OUT)


def reset_access_tokens(addon_id):
    """

    :param addon_id: id of the add-on having it's access tokens reset
    :return:
    """
    if not addon_id or addon_id == ADDON_ID:
        logging.error_trace('Invalid addon_id: %r', addon_id)
        return

    context = XbmcContext(params={'addon_id': addon_id})
    context.get_access_manager().update_access_token(
        addon_id, access_token='', expiry=-1, refresh_token=''
    )
