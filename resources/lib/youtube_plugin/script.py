# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os
import socket
import sys

from kodion.compatibility import parse_qsl, xbmc, xbmcaddon, xbmcvfs
from kodion.constants import DATA_PATH, TEMP_PATH
from kodion.context import Context
from kodion.network import get_client_ip_address, is_httpd_live
from kodion.utils import rm_dir


def _config_actions(action, *_args):
    context = Context()
    localize = context.localize
    settings = context.get_settings()
    ui = context.get_ui()

    if action == 'youtube':
        xbmcaddon.Addon().openSettings()
        xbmc.executebuiltin('Container.Refresh')

    elif action == 'isa':
        if context.use_inputstream_adaptive():
            xbmcaddon.Addon(id='inputstream.adaptive').openSettings()
        else:
            settings.set_bool('kodion.video.quality.isa', False)

    elif action == 'inputstreamhelper':
        try:
            xbmcaddon.Addon('script.module.inputstreamhelper')
            ui.show_notification(localize('inputstreamhelper.is_installed'))
        except RuntimeError:
            xbmc.executebuiltin('InstallAddon(script.module.inputstreamhelper)')

    elif action == 'subtitles':
        language = settings.get_string('youtube.language', 'en-US')
        sub_setting = settings.subtitle_languages()

        sub_opts = [
            localize('none'),
            localize('prompt'),
            (localize('subtitles.with_fallback') % (
                ('en', 'en-US/en-GB') if language.startswith('en') else
                (language, 'en')
            )),
            language,
            '%s (%s)' % (language, localize('subtitles.no_auto_generated'))
        ]
        sub_opts[sub_setting] = ui.bold(sub_opts[sub_setting])

        result = ui.on_select(localize('subtitles.language'), sub_opts)
        if result > -1:
            settings.set_subtitle_languages(result)

        result = ui.on_yes_no_input(
            localize('subtitles.download'),
            localize('subtitles.download.pre')
        )
        if result > -1:
            settings.set_subtitle_download(result == 1)

    elif action == 'listen_ip':
        local_ranges = ('10.', '172.16.', '192.168.')
        addresses = [iface[4][0]
                     for iface in socket.getaddrinfo(socket.gethostname(), None)
                     if iface[4][0].startswith(local_ranges)]
        addresses += ['127.0.0.1', '0.0.0.0']
        selected_address = ui.on_select(localize('select.listen.ip'), addresses)
        if selected_address != -1:
            settings.set_httpd_listen(addresses[selected_address])

    elif action == 'show_client_ip':
        port = settings.httpd_port()

        if is_httpd_live(port=port):
            client_ip = get_client_ip_address(port=port)
            if client_ip:
                ui.on_ok(context.get_name(),
                         context.localize('client.ip') % client_ip)
            else:
                ui.show_notification(context.localize('client.ip.failed'))
        else:
            ui.show_notification(context.localize('httpd.not.running'))


def _maintenance_actions(action, target):
    context = Context()
    ui = context.get_ui()
    localize = context.localize

    if action == 'clear':
        if target == 'function_cache':
            if ui.on_remove_content(localize('cache.function')):
                context.get_function_cache().clear()
                ui.show_notification(localize('succeeded'))
        elif target == 'data_cache':
            if ui.on_remove_content(localize('cache.data')):
                context.get_data_cache().clear()
                ui.show_notification(localize('succeeded'))
        elif target == 'search_cache':
            if ui.on_remove_content(localize('search.history')):
                context.get_search_history().clear()
                ui.show_notification(localize('succeeded'))
        elif (target == 'playback_history' and ui.on_remove_content(
            localize('playback.history')
        )):
            context.get_playback_history().clear()
            ui.show_notification(localize('succeeded'))

    elif action == 'delete':
        _maint_files = {'function_cache': 'cache.sqlite',
                        'search_cache': 'search.sqlite',
                        'data_cache': 'data_cache.sqlite',
                        'playback_history': 'playback_history',
                        'settings_xml': 'settings.xml',
                        'api_keys': 'api_keys.json',
                        'access_manager': 'access_manager.json',
                        'temp_files': TEMP_PATH}
        _file = _maint_files.get(target)
        succeeded = False

        if not _file:
            return

        data_path = xbmcvfs.translatePath(DATA_PATH)
        if 'sqlite' in _file:
            _file_w_path = os.path.join(data_path, 'kodion', _file)
        elif target == 'temp_files':
            _file_w_path = _file
        elif target == 'playback_history':
            _file = ''.join((
                context.get_access_manager().get_current_user_id(),
                '.sqlite'
            ))
            _file_w_path = os.path.join(data_path, 'playback', _file)
        else:
            _file_w_path = os.path.join(data_path, _file)

        if not ui.on_delete_content(_file):
            return

        if target == 'temp_files':
            succeeded = rm_dir(_file_w_path)

        elif _file_w_path:
            succeeded = xbmcvfs.delete(_file_w_path)

        if succeeded:
            ui.show_notification(localize('succeeded'))
        else:
            ui.show_notification(localize('failed'))


def _user_actions(action, params):
    context = Context()
    if params:
        context.parse_params(dict(parse_qsl(params)))
    localize = context.localize
    access_manager = context.get_access_manager()
    ui = context.get_ui()

    def select_user(reason, new_user=False):
        current_users = access_manager.get_users()
        current_user = access_manager.get_current_user()
        usernames = []
        for user, details in sorted(current_users.items()):
            username = details.get('name') or localize('user.unnamed')
            if user == current_user:
                username = '> ' + ui.bold(username)
            if details.get('access_token') or details.get('refresh_token'):
                username = ui.color('limegreen', username)
            usernames.append(username)
        if new_user:
            usernames.append(ui.italic(localize('user.new')))
        return ui.on_select(reason, usernames), sorted(current_users.keys())

    def add_user():
        results = ui.on_keyboard_input(localize('user.enter_name'))
        if results[0] is False:
            return None, None
        new_username = results[1].strip()
        if not new_username:
            new_username = localize('user.unnamed')
        return access_manager.add_user(new_username)

    def switch_to_user(user):
        access_manager.set_user(user, switch_to=True)
        ui.show_notification(
            localize('user.changed') % access_manager.get_username(user),
            localize('user.switch')
        )
        context.get_data_cache().clear()
        context.get_function_cache().clear()
        if context.get_param('refresh') is not False:
            ui.refresh_container()

    if action == 'switch':
        result, user_index_map = select_user(localize('user.switch'),
                                             new_user=True)
        if result == -1:
            return False
        if result == len(user_index_map):
            user, _ = add_user()
        else:
            user = user_index_map[result]

        if user is not None and user != access_manager.get_current_user():
            switch_to_user(user)

    elif action == 'add':
        user, details = add_user()
        if user is not None:
            result = ui.on_yes_no_input(
                localize('user.switch'),
                localize('user.switch.now') % details.get('name')
            )
            if result:
                switch_to_user(user)

    elif action == 'remove':
        result, user_index_map = select_user(localize('user.remove'))
        if result == -1:
            return False

        user = user_index_map[result]
        username = access_manager.get_username(user)
        if ui.on_remove_content(username):
            access_manager.remove_user(user)
            if user == 0:
                access_manager.add_user(username=localize('user.default'),
                                        user=0)
            if user == access_manager.get_current_user():
                access_manager.set_user(0, switch_to=True)
            ui.show_notification(localize('removed') % username,
                                 localize('remove'))

    elif action == 'rename':
        result, user_index_map = select_user(localize('user.rename'))
        if result == -1:
            return False

        user = user_index_map[result]
        old_username = access_manager.get_username(user)
        results = ui.on_keyboard_input(localize('user.enter_name'),
                                       default=old_username)
        if results[0] is False:
            return False
        new_username = results[1].strip()
        if not new_username:
            new_username = localize('user.unnamed')
        if old_username == new_username:
            return False

        if access_manager.set_username(user, new_username):
            ui.show_notification(
                localize('renamed') % (old_username, new_username),
                localize('rename')
            )

    return True


if __name__ == '__main__':
    args = sys.argv[1:]
    if args:
        args = args[0].split('/')
    num_args = len(args)
    category = args[0] if num_args else None
    action = args[1] if num_args > 1 else None
    params = args[2] if num_args > 2 else None

    if not category:
        xbmcaddon.Addon().openSettings()
    elif action == 'refresh':
        xbmc.executebuiltin('Container.Refresh')
    elif category == 'config':
        _config_actions(action, params)
    elif category == 'maintenance':
        _maintenance_actions(action, params)
    elif category == 'users':
        _user_actions(action, params)
