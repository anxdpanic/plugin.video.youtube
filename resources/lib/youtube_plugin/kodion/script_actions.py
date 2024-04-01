# -*- coding: utf-8 -*-
"""

    Copyright (C) 2024-present plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os
import socket

from .compatibility import parse_qsl, urlsplit, xbmc, xbmcaddon, xbmcvfs
from .constants import DATA_PATH, TEMP_PATH, WAIT_FLAG
from .context import XbmcContext
from .network import get_client_ip_address, httpd_status
from .utils import rm_dir, validate_ip_address


def _config_actions(context, action, *_args):
    localize = context.localize
    settings = context.get_settings()
    ui = context.get_ui()

    if action == 'youtube':
        xbmcaddon.Addon().openSettings()

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
        sub_lang = context.get_subtitle_language()
        plugin_lang = settings.get_language()
        sub_selection = settings.get_subtitle_selection()

        if not sub_lang:
            preferred = (plugin_lang,)
        elif sub_lang.partition('-')[0] != plugin_lang.partition('-')[0]:
            preferred = (sub_lang, plugin_lang)
        else:
            preferred = (sub_lang,)

        fallback = ('ASR' if preferred[0].startswith('en') else
                    context.get_language_name('en'))
        preferred = '/'.join(map(context.get_language_name, preferred))

        sub_opts = [
            localize('none'),
            localize('prompt'),
            localize('subtitles.with_fallback') % (preferred, fallback),
            preferred,
            '%s (%s)' % (preferred, localize('subtitles.no_asr')),
        ]

        if settings.use_mpd_videos():
            sub_opts.append(localize('subtitles.all'))
        elif sub_selection == 5:
            sub_selection = 0
            settings.set_subtitle_selection(sub_selection)

        sub_opts[sub_selection] = ui.bold(sub_opts[sub_selection])

        result = ui.on_select(localize('subtitles.language'),
                              sub_opts,
                              preselect=sub_selection)
        if result > -1:
            sub_selection = result
            settings.set_subtitle_selection(sub_selection)

        if not sub_selection or sub_selection == 5:
            settings.set_subtitle_download(False)
        else:
            result = ui.on_yes_no_input(
                localize('subtitles.download'),
                localize('subtitles.download.pre')
            )
            if result > -1:
                settings.set_subtitle_download(result == 1)

    elif action == 'listen_ip':
        local_ranges = (
            ((10, 0, 0, 0), (10, 255, 255, 255)),
            ((172, 16, 0, 0), (172, 31, 255, 255)),
            ((192, 168, 0, 0), (192, 168, 255, 255)),
        )
        addresses = [xbmc.getIPAddress()]
        for interface in socket.getaddrinfo(socket.gethostname(), None):
            address = interface[4][0]
            if interface[0] != socket.AF_INET or address in addresses:
                continue
            octets = validate_ip_address(address)
            if not any(octets):
                continue
            if any(lo <= octets <= hi for lo, hi in local_ranges):
                addresses.append(address)
        addresses += ['127.0.0.1', '0.0.0.0']
        selected_address = ui.on_select(localize('select.listen.ip'), addresses)
        if selected_address != -1:
            settings.httpd_listen(addresses[selected_address])

    elif action == 'show_client_ip':
        if httpd_status():
            client_ip = get_client_ip_address()
            if client_ip:
                ui.on_ok(context.get_name(),
                         context.localize('client.ip') % client_ip)
            else:
                ui.show_notification(context.localize('client.ip.failed'))
        else:
            ui.show_notification(context.localize('httpd.not.running'))


def _maintenance_actions(context, action, params):
    target = params.get('target')

    ui = context.get_ui()
    localize = context.localize

    if action == 'clear':
        targets = {
            'data_cache': context.get_data_cache,
            'function_cache': context.get_function_cache,
            'playback_history': context.get_playback_history,
            'search_history': context.get_search_history,
            'watch_later': context.get_watch_later_list,
        }
        if target not in targets:
            return

        if ui.on_clear_content(
            localize('maintenance.{0}'.format(target))
        ):
            targets[target]().clear()
            ui.show_notification(localize('succeeded'))

    elif action == 'delete':
        path = params.get('path')
        targets = {
            'data_cache': 'data_cache.sqlite',
            'function_cache': 'cache.sqlite',
            'playback_history': 'history.sqlite',
            'search_history': 'search.sqlite',
            'watch_later': 'watch_later.sqlite',
            'api_keys': 'api_keys.json',
            'access_manager': 'access_manager.json',
            'settings_xml': 'settings.xml',
            'temp_dir': (TEMP_PATH,),
            'other_file': ('', path) if path else None,
            'other_dir': (path,) if path else None,
        }
        path = targets.get(target)
        if not path:
            return

        if target == 'temp_dir':
            target = path[0]
        elif target == 'other_dir':
            target = os.path.basename(os.path.dirname(path[0]))
        elif target == 'other_file':
            target = os.path.basename(path[1])
        else:
            target = path
        if not ui.on_delete_content(target):
            return

        if isinstance(path, tuple):
            pass
        elif path.endswith('.sqlite'):
            path = (
                DATA_PATH,
                context.get_access_manager().get_current_user_id(),
                path,
            )
        else:
            path = (
                DATA_PATH,
                path,
            )

        if len(path) == 1:
            succeeded = rm_dir(path[0])
        else:
            succeeded = xbmcvfs.delete(os.path.join(*path))
        ui.show_notification(localize('succeeded' if succeeded else 'failed'))


def _user_actions(context, action, params):
    if params:
        context.parse_params(params)

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
        return (
            ui.on_select(reason, usernames, preselect=current_user),
            sorted(current_users.keys()),
        )

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


def run(argv):
    context = XbmcContext()
    ui = context.get_ui()
    ui.set_property(WAIT_FLAG, 'true')
    try:
        category = action = params = None
        args = argv[1:]
        if args:
            args = urlsplit(args[0])

            path = args.path
            if path:
                path = path.split('/')
                category = path[0]
                if len(path) >= 2:
                    action = path[1]

            params = args.query
            if params:
                params = dict(parse_qsl(args.query))

        if not category:
            xbmcaddon.Addon().openSettings()
            return

        if action == 'refresh':
            xbmc.executebuiltin('Container.Refresh')
            return

        if category == 'config':
            _config_actions(context, action, params)
            return

        if category == 'maintenance':
            _maintenance_actions(context, action, params)
            return

        if category == 'users':
            _user_actions(context, action, params)
            return
    finally:
        context.tear_down()
        ui.clear_property(WAIT_FLAG)
