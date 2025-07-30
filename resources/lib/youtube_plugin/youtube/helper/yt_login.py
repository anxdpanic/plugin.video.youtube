# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..youtube_exceptions import LoginException
from ...kodion import logging


SIGN_IN = 'in'
SIGN_OUT = 'out'


def _do_logout(provider, context, client=None, refresh=True, **kwargs):
    if not client:
        client = provider.get_client(context)

    access_manager = context.get_access_manager()
    addon_id = context.get_param('addon_id', None)

    success = True
    refresh_tokens = access_manager.get_refresh_token()
    if any(refresh_tokens):
        for refresh_token in frozenset(refresh_tokens):
            try:
                if refresh_token:
                    client.revoke(refresh_token)
            except LoginException:
                success = False

    provider.reset_client(**kwargs)
    access_manager.update_access_token(
        addon_id, access_token='', expiry=-1, refresh_token='',
    )
    if refresh:
        context.get_ui().refresh_container()
    return success


def _do_login(provider, context, client=None, **kwargs):
    if not client:
        client = provider.get_client(context)

    access_manager = context.get_access_manager()
    addon_id = context.get_param('addon_id', None)
    localize = context.localize
    ui = context.get_ui()

    ui.on_ok(localize('sign.multi.title'), localize('sign.multi.text'))

    tokens = ['tv', 'user']
    for token_type, token in enumerate(tokens):
        new_token = ('', -1, '')
        try:
            json_data = client.request_device_and_user_code(token_type)
            if not json_data:
                continue

            interval = int(json_data.get('interval', 5))
            if interval > 60:
                interval = 5
            device_code = json_data['device_code']
            user_code = json_data['user_code']
            verification_url = json_data.get('verification_url')
            if verification_url:
                if verification_url.startswith('https://www.'):
                    verification_url = verification_url[12:]
            else:
                verification_url = 'youtube.com/activate'

            message = ''.join((
                localize('sign.go_to', ui.bold(verification_url)),
                '[CR]',
                localize('sign.enter_code'),
                ' ',
                ui.bold(user_code),
            ))

            with ui.create_progress_dialog(
                    heading=localize('sign.in'),
                    message=message,
                    background=False
            ) as progress_dialog:
                steps = ((10 * 60) // interval)  # 10 Minutes
                progress_dialog.set_total(steps)
                for _ in range(steps):
                    progress_dialog.update()
                    json_data = client.request_access_token(
                        token_type, device_code
                    )
                    if not json_data:
                        break

                    log_data = json_data.copy()
                    if 'access_token' in log_data:
                        log_data['access_token'] = '<redacted>'
                    if 'refresh_token' in log_data:
                        log_data['refresh_token'] = '<redacted>'
                    logging.debug('Requesting access token: {data!r}',
                                  data=log_data)

                    if 'error' not in json_data:
                        access_token = json_data.get('access_token', '')
                        refresh_token = json_data.get('refresh_token', '')
                        if not access_token and not refresh_token:
                            expiry = 0
                        else:
                            expiry = int(json_data.get('expires_in', 3600))
                        new_token = (access_token, expiry, refresh_token)
                        break

                    if json_data['error'] != 'authorization_pending':
                        message = json_data['error']
                        title = '%s: %s' % (context.get_name(), message)
                        ui.show_notification(message, title)
                        logging.error_trace('Access token request error - %s',
                                            message)
                        break

                    if progress_dialog.is_aborted():
                        break

                    context.sleep(interval)
        except LoginException:
            _do_logout(provider, context, client=client)
            break
        finally:
            tokens[token_type] = new_token
            logging.debug(('YouTube Login:',
                           'Type:          {token!r}',
                           'Access token:  {has_access_token!r}',
                           'Expires:       {expiry!r}',
                           'Refresh token: {has_refresh_token!r}'),
                          token=token,
                          has_access_token=bool(new_token[0]),
                          expiry=new_token[1],
                          has_refresh_token=bool(new_token[2]))
    else:
        provider.reset_client(**kwargs)
        access_manager.update_access_token(addon_id, *zip(*tokens))
        ui.refresh_container()
        return True
    return False


def process(mode, provider, context, client=None, refresh=True, **kwargs):
    if mode == SIGN_OUT:
        return _do_logout(
            provider,
            context,
            client=client,
            refresh=refresh,
            **kwargs
        )

    if mode == SIGN_IN:
        return _do_login(
            provider,
            context,
            client=client,
            **kwargs
        )

    return None
