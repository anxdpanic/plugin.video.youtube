# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from six.moves import range

import copy
import json
import time
from ...youtube.youtube_exceptions import LoginException


def process(mode, provider, context, sign_out_refresh=True):
    addon_id = context.get_param('addon_id', None)

    def _do_logout():
        # we clear the cache, so none cached data of an old account will be displayed.
        provider.get_resource_manager(context).clear()

        signout_access_manager = context.get_access_manager()
        if addon_id:
            if signout_access_manager.developer_has_refresh_token(addon_id):
                refresh_tokens = signout_access_manager.get_dev_refresh_token(addon_id).split('|')
                refresh_tokens = list(set(refresh_tokens))
                for _refresh_token in refresh_tokens:
                    provider.get_client(context).revoke(_refresh_token)
        else:
            if signout_access_manager.has_refresh_token():
                refresh_tokens = signout_access_manager.get_refresh_token().split('|')
                refresh_tokens = list(set(refresh_tokens))
                for _refresh_token in refresh_tokens:
                    provider.get_client(context).revoke(_refresh_token)

        provider.reset_client()

        if addon_id:
            signout_access_manager.update_dev_access_token(addon_id, access_token='', refresh_token='')
        else:
            signout_access_manager.update_access_token(access_token='', refresh_token='')

    def _do_login():
        _client = provider.get_client(context)

        try:
            json_data = _client.request_device_and_user_code()
        except LoginException:
            _do_logout()
            raise

        interval = int(json_data.get('interval', 5)) * 1000
        if interval > 60000:
            interval = 5000
        device_code = json_data['device_code']
        user_code = json_data['user_code']
        verification_url = json_data.get('verification_url', 'youtube.com/activate').lstrip('https://www.')

        text = [context.localize(provider.LOCAL_MAP['youtube.sign.go_to']) % context.get_ui().bold(verification_url),
                '[CR]%s %s' % (context.localize(provider.LOCAL_MAP['youtube.sign.enter_code']),
                               context.get_ui().bold(user_code))]
        text = ''.join(text)
        dialog = context.get_ui().create_progress_dialog(
            heading=context.localize(provider.LOCAL_MAP['youtube.sign.in']), text=text, background=False)

        steps = ((10 * 60 * 1000) // interval)  # 10 Minutes
        dialog.set_total(steps)
        for i in range(steps):
            dialog.update()
            try:
                json_data = _client.request_access_token(device_code)
            except LoginException:
                _do_logout()
                raise

            log_data = copy.deepcopy(json_data)
            if 'access_token' in log_data:
                log_data['access_token'] = '<redacted>'
            if 'refresh_token' in log_data:
                log_data['refresh_token'] = '<redacted>'
            context.log_debug('Requesting access token: |%s|' % json.dumps(log_data))

            if 'error' not in json_data:
                _access_token = json_data.get('access_token', '')
                _expires_in = time.time() + int(json_data.get('expires_in', 3600))
                _refresh_token = json_data.get('refresh_token', '')
                dialog.close()
                if not _access_token and not _refresh_token:
                    _expires_in = 0
                return _access_token, _expires_in, _refresh_token

            elif json_data['error'] != u'authorization_pending':
                message = json_data['error']
                title = '%s: %s' % (context.get_name(), message)
                context.get_ui().show_notification(message, title)
                context.log_error('Error requesting access token: |%s|' % message)

            if dialog.is_aborted():
                dialog.close()
                return '', 0, ''

            context.sleep(interval)
        dialog.close()

    if mode == 'out':
        _do_logout()
        if sign_out_refresh:
            context.get_ui().refresh_container()

    elif mode == 'in':
        access_token, expires_in, refresh_token = _do_login()
        # abort kodi login
        context.log_debug('YouTube-Kodi Login: Access Token |%s| Refresh Token |%s| Expires |%s|' %
                          (access_token != '', refresh_token != '', expires_in))

        if not access_token and not refresh_token:
            provider.reset_client()
            if addon_id:
                context.get_access_manager().update_dev_access_token(addon_id, '')
            else:
                context.get_access_manager().update_access_token('')
            context.get_ui().refresh_container()
            return

        # we clear the cache, so none cached data of an old account will be displayed.
        provider.get_resource_manager(context).clear()

        provider.reset_client()

        if addon_id:
            context.get_access_manager().update_dev_access_token(addon_id, access_token, expires_in, refresh_token)
        else:
            context.get_access_manager().update_access_token(access_token, expires_in, refresh_token)

        context.get_ui().refresh_container()
