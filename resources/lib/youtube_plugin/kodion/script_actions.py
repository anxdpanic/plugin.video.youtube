# -*- coding: utf-8 -*-
"""

    Copyright (C) 2024-present plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os

from .compatibility import parse_qsl, urlsplit, xbmc, xbmcaddon, xbmcvfs
from .constants import (
    DATA_PATH,
    DEFAULT_LANGUAGES,
    DEFAULT_REGIONS,
    RELOAD_ACCESS_MANAGER,
    SERVER_WAKEUP,
    TEMP_PATH,
    WAIT_END_FLAG,
)
from .context import XbmcContext
from .network import (
    Locator,
    get_client_ip_address,
    get_listen_addresses,
    httpd_status,
)
from .utils import rm_dir
from ..youtube import Provider


def _config_actions(context, action, *_args):
    localize = context.localize
    settings = context.get_settings()
    ui = context.get_ui()

    if action == 'youtube':
        xbmcaddon.Addon().openSettings()

    elif action == 'isa':
        if context.use_inputstream_adaptive(prompt=True):
            xbmcaddon.Addon('inputstream.adaptive').openSettings()
        else:
            settings.use_isa(False)

    elif action == 'inputstreamhelper':
        try:
            xbmcaddon.Addon('script.module.inputstreamhelper')
            ui.show_notification(localize('inputstreamhelper.is_installed'))
        except RuntimeError:
            xbmc.executebuiltin('InstallAddon(script.module.inputstreamhelper)')

    elif action == 'subtitles':
        kodi_sub_lang = context.get_subtitle_language()
        plugin_lang = settings.get_language()
        sub_selection = settings.get_subtitle_selection()

        if not kodi_sub_lang:
            preferred = (plugin_lang,)
        elif kodi_sub_lang.partition('-')[0] != plugin_lang.partition('-')[0]:
            preferred = (kodi_sub_lang, plugin_lang)
        else:
            preferred = (kodi_sub_lang,)

        fallback = ('ASR' if preferred[0].startswith('en') else
                    context.get_language_name('en'))
        preferred = '/'.join(map(context.get_language_name, preferred))
        preferred_no_asr = '%s (%s)' % (preferred, localize('subtitles.no_asr'))

        sub_opts = [
            localize('none'),
            localize('select'),
            localize('subtitles.with_fallback') % (preferred, fallback),
            localize('subtitles.with_fallback') % (preferred_no_asr, fallback),
            preferred_no_asr,
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
        addresses = get_listen_addresses()
        selected_address = ui.on_select(localize('select.listen.ip'), addresses)
        if selected_address != -1:
            settings.httpd_listen(addresses[selected_address])

    elif action == 'show_client_ip':
        context.wakeup(SERVER_WAKEUP, timeout=5)
        if httpd_status(context):
            client_ip = get_client_ip_address(context)
            if client_ip:
                ui.on_ok(context.get_name(),
                         context.localize('client.ip') % client_ip)
            else:
                ui.show_notification(context.localize('client.ip.failed'))
        else:
            ui.show_notification(context.localize('httpd.not.running'))

    elif action == 'geo_location':
        locator = Locator(context)
        locator.locate_requester()
        coords = locator.coordinates()
        if coords:
            context.get_settings().set_location(
                '{0[lat]},{0[lon]}'.format(coords)
            )

    elif action == 'language_region':
        client = Provider().get_client(context)
        settings = context.get_settings()

        plugin_language = settings.get_language()
        plugin_region = settings.get_region()

        kodi_language = context.get_language()
        base_kodi_language = kodi_language.partition('-')[0]

        json_data = client.get_supported_languages(kodi_language)
        items = json_data.get('items') or DEFAULT_LANGUAGES['items']

        selected_language = [None]

        def _get_selected_language(item):
            item_lang = item[1]
            base_item_lang = item_lang.partition('-')[0]
            if item_lang == kodi_language or item_lang == plugin_language:
                selected_language[0] = item
            elif (not selected_language[0]
                  and base_item_lang == base_kodi_language):
                selected_language.append(item)
            return item

        # Ignore es-419 as it causes hl not a valid language error
        # https://github.com/jdf76/plugin.video.youtube/issues/418
        invalid_ids = ('es-419',)
        language_list = sorted([
            (item['snippet']['name'], item['snippet']['hl'])
            for item in items
            if item['id'] not in invalid_ids
        ], key=_get_selected_language)

        if selected_language[0]:
            selected_language = language_list.index(selected_language[0])
        elif len(selected_language) > 1:
            selected_language = language_list.index(selected_language[1])
        else:
            selected_language = None

        language_id = ui.on_select(
            localize('setup_wizard.locale.language'),
            language_list,
            preselect=selected_language
        )
        if language_id == -1:
            return

        json_data = client.get_supported_regions(language=language_id)
        items = json_data.get('items') or DEFAULT_REGIONS['items']

        selected_region = [None]

        def _get_selected_region(item):
            item_region = item[1]
            if item_region == plugin_region:
                selected_region[0] = item
            return item

        region_list = sorted([
            (item['snippet']['name'], item['snippet']['gl'])
            for item in items
        ], key=_get_selected_region)

        if selected_region[0]:
            selected_region = region_list.index(selected_region[0])
        else:
            selected_region = None

        region_id = ui.on_select(
            localize('setup_wizard.locale.region'),
            region_list,
            preselect=selected_region
        )
        if region_id == -1:
            return

        # set new language id and region id
        settings = context.get_settings()
        settings.set_language(language_id)
        settings.set_region(region_id)


def _maintenance_actions(context, action, params):
    target = params.get('target')

    ui = context.get_ui()
    localize = context.localize

    if action == 'clear':
        targets = {
            'bookmarks': context.get_bookmarks_list,
            'data_cache': context.get_data_cache,
            'feed_history': context.get_feed_history,
            'function_cache': context.get_function_cache,
            'playback_history': context.get_playback_history,
            'search_history': context.get_search_history,
            'watch_later': context.get_watch_later_list,
        }
        if target not in targets:
            return

        if ui.on_clear_content(localize('maintenance.{0}'.format(target))):
            targets[target]().clear()
            ui.show_notification(localize('completed'))

    elif action == 'refresh':
        targets = {
            'settings_xml': 'settings.xml',
        }
        path = targets.get(target)
        if not path:
            return

        if target == 'settings_xml' and ui.on_yes_no_input(
                context.get_name(), localize('refresh.settings.check')
        ):
            if not context.get_system_version().compatible(20):
                ui.show_notification(localize('failed'))
                return

            import xml.etree.ElementTree as ET

            path = xbmcvfs.translatePath(os.path.join(DATA_PATH, path))
            xml = ET.parse(path)
            settings = xml.getroot()

            marker = settings.find('setting[@id="|end_settings_marker|"]')
            if marker is None:
                ui.show_notification(localize('failed'))
                return

            removed = 0
            for setting in reversed(settings.findall('setting')):
                if setting == marker:
                    break
                settings.remove(setting)
                removed += 1
            else:
                ui.show_notification(localize('failed'))
                return

            if removed:
                xml.write(path)
            ui.show_notification(localize('succeeded'))
        else:
            return

    elif action == 'delete':
        path = params.get('path')
        targets = {
            'bookmarks': 'bookmarks.sqlite',
            'data_cache': 'data_cache.sqlite',
            'feed_history': 'feeds.sqlite',
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
    reload = False

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
            reload = True

    elif action == 'add':
        user, details = add_user()
        if user is not None:
            result = ui.on_yes_no_input(
                localize('user.switch'),
                localize('user.switch.now') % details.get('name')
            )
            if result:
                switch_to_user(user)
                reload = True

    elif action == 'remove':
        result, user_index_map = select_user(localize('user.remove'))
        if result == -1:
            return False

        user = user_index_map[result]
        username = access_manager.get_username(user)
        if ui.on_remove_content(username):
            access_manager.remove_user(user)
            ui.show_notification(localize('removed') % username,
                                 localize('remove'))
            if user == 0:
                access_manager.add_user(username=localize('user.default'),
                                        user=0)
            if user == access_manager.get_current_user():
                switch_to_user(0)
            reload = True

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
        reload = True

    if reload:
        ui.set_property(RELOAD_ACCESS_MANAGER)
        context.send_notification(RELOAD_ACCESS_MANAGER)
    return True


def run(argv):
    context = XbmcContext()
    ui = context.get_ui()
    try:
        category = action = params = None
        args = argv[1:]
        if args:
            args = urlsplit(args[0])

            path = args.path.rstrip('/')
            if path:
                path = path.split('/')
                category = path[0]
                if len(path) >= 2:
                    action = path[1]

            params = args.query
            if params:
                params = dict(parse_qsl(args.query))

        system_version = context.get_system_version()
        context.log_notice('Script: Running v{version}'
                           '\n\tKodi:     v{kodi}'
                           '\n\tPython:   v{python}'
                           '\n\tCategory: |{category}|'
                           '\n\tAction:   |{action}|'
                           '\n\tParams:   |{params}|'
                           .format(version=context.get_version(),
                                   kodi=str(system_version),
                                   python=system_version.get_python_version(),
                                   category=category,
                                   action=action,
                                   params=params))

        if not category:
            xbmcaddon.Addon().openSettings()
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
        ui.set_property(WAIT_END_FLAG)
