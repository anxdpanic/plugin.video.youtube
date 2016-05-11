__author__ = 'bromix'

import time


def process(mode, provider, context, re_match, needs_tv_login=True):
    def _do_login(_for_tv=False):
        _client = provider.get_client(context)
        json_data = {}
        if _for_tv:
            json_data = _client.generate_user_code_tv(context)
            pass
        else:
            json_data = _client.generate_user_code(context)
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
        
        i=0
        steps = (10 * 60 * 1000) / interval  # 10 Minutes
        dialog.set_total(steps)
        for i in range(steps):
            dialog.update()
            json_data = {}
            if _for_tv:
                json_data = _client.get_device_token_tv(device_code, context)
                pass
            else:
                json_data = _client.get_device_token(device_code, context)
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
                    break
                pass

            if dialog.is_aborted():
                dialog.close()
                if context.get_settings().get_bool('youtube.api.autologin', True):
                    context.get_settings().set_bool('youtube.api.autologin', False)
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
            for refresh_token in refresh_tokens:
                client.revoke(refresh_token, context)
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
        if needs_tv_login:
            context.get_ui().on_ok(context.localize(provider.LOCAL_MAP['youtube.sign.twice.title']),
                                   context.localize(provider.LOCAL_MAP['youtube.sign.twice.text']))

            access_token_tv, expires_in_tv, refresh_token_tv = _do_login(_for_tv=True)
            # abort tv login
            if not access_token_tv and not refresh_token_tv:
                provider.reset_client()
                context.get_access_manager().update_access_token('')
                context.get_ui().refresh_container()
                return
            pass

        access_token_kodi, expires_in_kodi, refresh_token_kodi = _do_login(_for_tv=False)
        # abort kodi login
        if not access_token_kodi and not refresh_token_kodi:
            provider.reset_client()
            context.get_access_manager().update_access_token('')
            context.get_ui().refresh_container()
            return

        if needs_tv_login:
            access_token = '%s|%s' % (access_token_tv, access_token_kodi)
            refresh_token = '%s|%s' % (refresh_token_tv, refresh_token_kodi)
            expires_in = min(expires_in_tv, expires_in_kodi)
            pass
        else:
            if context.get_settings().get_bool('youtube.api.autologin', True):
                access_manager = context.get_access_manager()
                access_tokens = access_manager.get_access_token()
                if access_tokens:
                    access_tokens = access_tokens.split('|')
                
                refresh_tokens = access_manager.get_refresh_token()
                if access_tokens:
                    refresh_tokens = refresh_tokens.split('|')
                 
                access_token = '%s|%s' % (access_tokens[0], access_token_kodi)
                refresh_token = '%s|%s' % (refresh_tokens[0], refresh_token_kodi)
                expires_in = context.get_settings().get_int('kodion.access_token.expires',0)
                context.get_settings().set_bool('youtube.api.autologin', False)
                pass
            else:
                access_token = access_token_kodi
                refresh_token = refresh_token_kodi
                expires_in = expires_in_kodi
                pass

        major_version = context.get_system_version().get_version()[0]
        context.get_settings().set_int('youtube.login.version', major_version)

        provider.reset_client()
        context.get_access_manager().update_access_token(access_token, expires_in, refresh_token)
        context.get_ui().refresh_container()
        pass
    pass
