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


def _do_logout(provider, context, client=None, **kwargs):
    ui = context.get_ui()
    if not context.get_param('confirmed') and not ui.on_yes_no_input(
            context.localize('sign.out'),
            context.localize('are_you_sure')
    ):
        return False

    if not client:
        client = provider.get_client(context)

    access_manager = context.get_access_manager()
    addon_id = context.get_param('addon_id', None)

    success = True
    refresh_tokens, num_refresh_tokens = access_manager.get_refresh_tokens()
    if num_refresh_tokens:
        for refresh_token in frozenset(refresh_tokens):
            try:
                if refresh_token:
                    client.revoke(refresh_token)
            except LoginException:
                success = False

    provider.reset_client(context=context, **kwargs)
    access_manager.update_access_token(
        addon_id, access_token='', expiry=-1, refresh_token='',
    )
    return success


def _do_login(provider, context, client=None, **kwargs):
    if not client:
        client = provider.get_client(context)

    access_manager = context.get_access_manager()
    addon_id = context.get_param('addon_id', None)
    localize = context.localize
    function_cache = context.get_function_cache()
    ui = context.get_ui()

    ui.on_ok(localize('sign.multi.title'), localize('sign.multi.text'))

    (
        access_tokens,
        num_access_tokens,
        expiry_timestamp,
    ) = access_manager.get_access_tokens()
    (
        refresh_tokens,
        num_refresh_tokens,
    ) = access_manager.get_refresh_tokens()
    token_types = ['tv', 'user', 'vr', 'dev']
    new_access_tokens = dict.fromkeys(token_types, None)
    for token_idx, token_type in enumerate(token_types):
        try:
            access_token = access_tokens[token_idx]
            refresh_token = refresh_tokens[token_idx]
            if access_token and refresh_token:
                new_access_tokens[token_type] = access_token
                new_token = (access_token, expiry_timestamp, refresh_token)
                token_types[token_idx] = new_token
                continue
        except IndexError:
            pass

        if not function_cache.run(
                client.internet_available,
                function_cache.ONE_MINUTE * 5,
                _refresh=True,
        ):
            break

        new_token = ('', expiry_timestamp, '')
        try:
            json_data = client.request_device_and_user_code(token_idx)
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
                        token_idx, device_code
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
            new_access_tokens[token_type] = new_token[0]
            token_types[token_idx] = new_token
            logging.debug(('YouTube Login:',
                           'Type:          {token!r}',
                           'Access token:  {has_access_token!r}',
                           'Expires:       {expiry!r}',
                           'Refresh token: {has_refresh_token!r}'),
                          token=token_type,
                          has_access_token=bool(new_token[0]),
                          expiry=new_token[1],
                          has_refresh_token=bool(new_token[2]))
    else:
        provider.reset_client(
            context=context,
            access_tokens=new_access_tokens,
            **kwargs
        )
        access_manager.update_access_token(addon_id, *zip(*token_types))
        return True
    return False


def process(mode, provider, context, client=None, refresh=True, **kwargs):
    if mode == SIGN_OUT:
        signed_out = _do_logout(
            provider,
            context,
            client=client,
            **kwargs
        )
        return signed_out, {provider.FORCE_REFRESH: refresh}

    if mode == SIGN_IN:
        signed_in = _do_login(
            provider,
            context,
            client=client,
            **kwargs
        )
        return signed_in, {provider.FORCE_REFRESH: refresh and signed_in}

    return None, None
