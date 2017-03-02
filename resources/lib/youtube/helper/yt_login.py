__author__ = 'bromix'

import time


def process(mode, provider, context, re_match, needs_tv_login=True):
    def _do_login(_for_tv=False):
        _client = provider.get_client(context)
        json_data = {}
        if _for_tv:
            json_data = _client.generate_user_code_tv()
            pass
        else:
            json_data = _client.generate_user_code()
            pass
        
        interval = int(json_data.get('interval', 5)) * 1000
        if interval > 60000:
            interval = 5000
            pass
        device_code = json_data['device_code']
        user_code = json_data['user_code']

        text = context.localize(provider.LOCAL_MAP['youtube.sign.go_to']) % '[B]youtube.com/activate[/B]'
        text += '[CR]%s [B]%s[/B]' % (context.localize(provider.LOCAL_MAP['youtube.sign.enter_code']), user_code)
        dialog = context.get_ui().create_progress_dialog(
            heading=context.localize(provider.LOCAL_MAP['youtube.sign.in']), text=text, background=False)
        
        steps = (10 * 60 * 1000) / interval  # 10 Minutes
        dialog.set_total(steps)
        for i in range(steps):
            dialog.update()
            json_data = {}
            if _for_tv:
                json_data = _client.get_device_token_tv(device_code)
                pass
            else:
                json_data = _client.get_device_token(device_code)
                pass

            if not 'error' in json_data:
                access_token = json_data.get('access_token', '')
                expires_in = time.time() + int(json_data.get('expires_in', 3600))
                refresh_token = json_data.get('refresh_token', '')
                if access_token and refresh_token:
                    dialog.close()
                    return access_token, expires_in, refresh_token
                    # provider.reset_client()
                    # context.get_access_manager().update_access_token(access_token, expires_in, refresh_token)
                    #context.get_ui().refresh_container()
            elif json_data['error'] != u'authorization_pending':
                message = json_data['error']
                title = '%s: %s' % (context.get_name(), message)
                context.get_ui().show_notification(message, title)
                context.log_error('Error: |%s|' % message)

            if dialog.is_aborted():
                dialog.close()
                return '', 0, ''

            context.sleep(interval)
            pass
        dialog.close()
        pass

    if mode == 'out':
        # we clear the cache, so none cached data of an old account will be displayed.
        context.get_function_cache().clear()

        access_manager = context.get_access_manager()
        client = provider.get_client(context)
        if access_manager.has_refresh_token():
            refresh_tokens = access_manager.get_refresh_token().split('|')
            refresh_tokens = list(set(refresh_tokens))
            for refresh_token in refresh_tokens:
                client.revoke(refresh_token)
                pass
            pass
        provider.reset_client()
        access_manager.update_access_token(access_token='', refresh_token='')
        context.get_ui().refresh_container()
        pass
    elif mode == 'in':
        access_token_tv = ''
        expires_in_tv = 0
        refresh_token_tv = ''
        requires_dual_login = context.get_settings().requires_dual_login()
        context.log_debug('Sign-in: Dual login required |%s|' % requires_dual_login)
        if needs_tv_login:
            context.get_ui().on_ok(context.localize(provider.LOCAL_MAP['youtube.sign.twice.title']),
                                   context.localize(provider.LOCAL_MAP['youtube.sign.twice.text']))

            access_token_tv, expires_in_tv, refresh_token_tv = _do_login(_for_tv=True)
            # abort tv login
            context.log_debug('YouTube-TV Login: Access Token |%s| Refresh Token |%s| Expires |%s|' % (access_token_tv != '', refresh_token_tv != '', expires_in_tv))
            if not access_token_tv and not refresh_token_tv:
                provider.reset_client()
                context.get_access_manager().update_access_token('')
                context.get_ui().refresh_container()
                return
            pass

        access_token_kodi, expires_in_kodi, refresh_token_kodi = _do_login(_for_tv=False)
        # abort kodi login
        context.log_debug('YouTube-Kodi Login: Access Token |%s| Refresh Token |%s| Expires |%s|' % (access_token_kodi != '', refresh_token_kodi != '', expires_in_kodi))
        if not access_token_kodi and not refresh_token_kodi:
            provider.reset_client()
            context.get_access_manager().update_access_token('')
            context.get_ui().refresh_container()
            return

        if not requires_dual_login:
            access_token_tv, expires_in_tv, refresh_token_tv = access_token_kodi, expires_in_kodi, refresh_token_kodi

        # if needs_tv_login:
        access_token = '%s|%s' % (access_token_tv, access_token_kodi)
        refresh_token = '%s|%s' % (refresh_token_tv, refresh_token_kodi)
        expires_in = min(expires_in_tv, expires_in_kodi)
        # else:
        #     access_token = access_token_kodi
        #     refresh_token = refresh_token_kodi
        #     expires_in = expires_in_kodi
        #     pass

        # we clear the cache, so none cached data of an old account will be displayed.
        context.get_function_cache().clear()

        major_version = context.get_system_version().get_version()[0]
        context.get_settings().set_int('youtube.login.version', major_version)

        provider.reset_client()
        context.get_access_manager().update_access_token(access_token, expires_in, refresh_token)
        context.get_ui().refresh_container()
        pass
    pass
