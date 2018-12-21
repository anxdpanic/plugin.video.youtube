# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from youtube_plugin.youtube.provider import Provider
from youtube_plugin.kodion.impl import Context
from youtube_plugin.youtube.helper import yt_login

# noinspection PyUnresolvedReferences
from youtube_plugin.youtube.youtube_exceptions import LoginException  # NOQA


SIGN_IN = 'in'
SIGN_OUT = 'out'


def __add_new_developer(addon_id):
    """

    :param addon_id: id of the add-on being added
    :return:
    """
    params = {'addon_id': addon_id}
    context = Context(params=params, plugin_id='plugin.video.youtube')

    access_manager = context.get_access_manager()
    developers = access_manager.get_developers()
    if not developers.get(addon_id, None):
        developers[addon_id] = access_manager.get_new_developer()
        access_manager.set_developers(developers)
        context.log_debug('Creating developer user: |%s|' % addon_id)


def __auth(addon_id, mode=SIGN_IN):
    """

    :param addon_id: id of the add-on being signed in
    :param mode: SIGN_IN or SIGN_OUT
    :return: addon provider, context and client
    """
    if not addon_id or addon_id == 'plugin.video.youtube':
        context = Context(plugin_id='plugin.video.youtube')
        context.log_error('Developer authentication: |%s| Invalid addon_id' % addon_id)
        return
    __add_new_developer(addon_id)
    params = {'addon_id': addon_id}
    provider = Provider()
    context = Context(params=params, plugin_id='plugin.video.youtube')

    _ = provider.get_client(context=context)  # NOQA
    logged_in = provider.is_logged_in()
    if mode == SIGN_IN:
        if logged_in:
            return True
        else:
            provider.reset_client()
            yt_login.process(mode, provider, context, sign_out_refresh=False)
    elif mode == SIGN_OUT:
        if not logged_in:
            return True
        else:
            provider.reset_client()
            try:
                yt_login.process(mode, provider, context, sign_out_refresh=False)
            except:
                reset_access_tokens(addon_id)
    else:
        raise Exception('Unknown mode: |%s|' % mode)

    _ = provider.get_client(context=context)  # NOQA
    if mode == SIGN_IN:
        return provider.is_logged_in()
    else:
        return not provider.is_logged_in()


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
    except youtube_authentication.LoginException as e:
        error_message = e.get_message()
        # handle error
        signed_in = False

    if signed_in:
        pass  # see youtube_registration.py and youtube_requests.py to use the signed in context
     ---

    :param addon_id: id of the add-on being signed in
    :return: boolean, True when signed in
    """

    return __auth(addon_id, mode=SIGN_IN)


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

    return __auth(addon_id, mode=SIGN_OUT)


def reset_access_tokens(addon_id):
    """

    :param addon_id: id of the add-on having it's access tokens reset
    :return:
    """
    if not addon_id or addon_id == 'plugin.video.youtube':
        context = Context(plugin_id='plugin.video.youtube')
        context.log_error('Developer reset access tokens: |%s| Invalid addon_id' % addon_id)
        return
    params = {'addon_id': addon_id}
    context = Context(params=params, plugin_id='plugin.video.youtube')

    access_manager = context.get_access_manager()
    access_manager.update_dev_access_token(addon_id, access_token='', refresh_token='')
