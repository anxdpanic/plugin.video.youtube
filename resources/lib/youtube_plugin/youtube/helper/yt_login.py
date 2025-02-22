# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ..youtube_exceptions import LoginException


def process(mode, provider, context, sign_out_refresh=True):
    addon_id = context.get_param('addon_id', None)
    access_manager = context.get_access_manager()
    localize = context.localize
    ui = context.get_ui()

    def _do_logout():
        refresh_tokens = access_manager.get_refresh_token()
        client = provider.get_client(context)
        if any(refresh_tokens):
            for _refresh_token in frozenset(refresh_tokens):
                try:
                    if _refresh_token:
                        client.revoke(_refresh_token)
                except LoginException:
                    pass
        access_manager.update_access_token(
            addon_id, access_token='', expiry=-1, refresh_token='',
        )
        provider.reset_client()

    def _do_login(token_type):
        _client = provider.get_client(context)

        try:
            json_data = _client.request_device_and_user_code(token_type)
            if not json_data:
                return None
        except LoginException:
            _do_logout()
            raise

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
            localize('sign.go_to') % ui.bold(verification_url),
            '[CR]',
            localize('sign.enter_code'),
            ' ',
            ui.bold(user_code),
        ))

        with ui.create_progress_dialog(
                heading=localize('sign.in'), message=message, background=False
        ) as progress_dialog:
            steps = ((10 * 60) // interval)  # 10 Minutes
            progress_dialog.set_total(steps)
            for _ in range(steps):
                progress_dialog.update()
                try:
                    json_data = _client.request_access_token(token_type,
                                                             device_code)
                    if not json_data:
                        break
                except LoginException:
                    _do_logout()
                    raise

                log_data = json_data.copy()
                if 'access_token' in log_data:
                    log_data['access_token'] = '<redacted>'
                if 'refresh_token' in log_data:
                    log_data['refresh_token'] = '<redacted>'
                context.log_debug('Requesting access token: |{data}|'.format(
                    data=log_data
                ))

                if 'error' not in json_data:
                    _access_token = json_data.get('access_token', '')
                    _refresh_token = json_data.get('refresh_token', '')
                    if not _access_token and not _refresh_token:
                        _expiry = 0
                    else:
                        _expiry = int(json_data.get('expires_in', 3600))
                    return _access_token, _expiry, _refresh_token

                if json_data['error'] != 'authorization_pending':
                    message = json_data['error']
                    title = '%s: %s' % (context.get_name(), message)
                    ui.show_notification(message, title)
                    context.log_error('Error requesting access token: |error|'
                                      .format(error=message))

                if progress_dialog.is_aborted():
                    break

                context.sleep(interval)
        return None

    if mode == 'out':
        _do_logout()
        if sign_out_refresh:
            ui.refresh_container()

    elif mode == 'in':
        ui.on_ok(localize('sign.multi.title'), localize('sign.multi.text'))

        tokens = ['tv', 'personal']
        for token_type, token in enumerate(tokens):
            new_token = _do_login(token_type) or ('', -1, '')
            tokens[token_type] = new_token

            context.log_debug('YouTube Login:'
                              '\n\tType:          |{0}|'
                              '\n\tAccess token:  |{1}|'
                              '\n\tRefresh token: |{2}|'
                              '\n\tExpires:       |{3}|'
                              .format(token,
                                      bool(new_token[0]),
                                      bool(new_token[2]),
                                      new_token[1]))

        provider.reset_client()
        access_manager.update_access_token(addon_id, *zip(*tokens))
        ui.refresh_container()
