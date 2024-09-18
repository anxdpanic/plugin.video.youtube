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
from .constants import (
    DATA_PATH,
    RELOAD_ACCESS_MANAGER,
    TEMP_PATH,
    WAIT_END_FLAG,
)
from .context import XbmcContext
from .network import Locator, get_client_ip_address, httpd_status
from .utils import current_system_version, rm_dir, validate_ip_address
from ..youtube import Provider


DEFAULT_LANGUAGES = {'items': [
    {'snippet': {'name': 'Afrikaans', 'hl': 'af'}, 'id': 'af'},
    {'snippet': {'name': 'Azerbaijani', 'hl': 'az'}, 'id': 'az'},
    {'snippet': {'name': 'Indonesian', 'hl': 'id'}, 'id': 'id'},
    {'snippet': {'name': 'Malay', 'hl': 'ms'}, 'id': 'ms'},
    {'snippet': {'name': 'Catalan', 'hl': 'ca'}, 'id': 'ca'},
    {'snippet': {'name': 'Czech', 'hl': 'cs'}, 'id': 'cs'},
    {'snippet': {'name': 'Danish', 'hl': 'da'}, 'id': 'da'},
    {'snippet': {'name': 'German', 'hl': 'de'}, 'id': 'de'},
    {'snippet': {'name': 'Estonian', 'hl': 'et'}, 'id': 'et'},
    {'snippet': {'name': 'English (United Kingdom)', 'hl': 'en-GB'}, 'id': 'en-GB'},
    {'snippet': {'name': 'English', 'hl': 'en'}, 'id': 'en'},
    {'snippet': {'name': 'Spanish (Spain)', 'hl': 'es'}, 'id': 'es'},
    {'snippet': {'name': 'Spanish (Latin America)', 'hl': 'es-419'}, 'id': 'es-419'},
    {'snippet': {'name': 'Basque', 'hl': 'eu'}, 'id': 'eu'},
    {'snippet': {'name': 'Filipino', 'hl': 'fil'}, 'id': 'fil'},
    {'snippet': {'name': 'French', 'hl': 'fr'}, 'id': 'fr'},
    {'snippet': {'name': 'French (Canada)', 'hl': 'fr-CA'}, 'id': 'fr-CA'},
    {'snippet': {'name': 'Galician', 'hl': 'gl'}, 'id': 'gl'},
    {'snippet': {'name': 'Croatian', 'hl': 'hr'}, 'id': 'hr'},
    {'snippet': {'name': 'Zulu', 'hl': 'zu'}, 'id': 'zu'},
    {'snippet': {'name': 'Icelandic', 'hl': 'is'}, 'id': 'is'},
    {'snippet': {'name': 'Italian', 'hl': 'it'}, 'id': 'it'},
    {'snippet': {'name': 'Swahili', 'hl': 'sw'}, 'id': 'sw'},
    {'snippet': {'name': 'Latvian', 'hl': 'lv'}, 'id': 'lv'},
    {'snippet': {'name': 'Lithuanian', 'hl': 'lt'}, 'id': 'lt'},
    {'snippet': {'name': 'Hungarian', 'hl': 'hu'}, 'id': 'hu'},
    {'snippet': {'name': 'Dutch', 'hl': 'nl'}, 'id': 'nl'},
    {'snippet': {'name': 'Norwegian', 'hl': 'no'}, 'id': 'no'},
    {'snippet': {'name': 'Uzbek', 'hl': 'uz'}, 'id': 'uz'},
    {'snippet': {'name': 'Polish', 'hl': 'pl'}, 'id': 'pl'},
    {'snippet': {'name': 'Portuguese (Portugal)', 'hl': 'pt-PT'}, 'id': 'pt-PT'},
    {'snippet': {'name': 'Portuguese (Brazil)', 'hl': 'pt'}, 'id': 'pt'},
    {'snippet': {'name': 'Romanian', 'hl': 'ro'}, 'id': 'ro'},
    {'snippet': {'name': 'Albanian', 'hl': 'sq'}, 'id': 'sq'},
    {'snippet': {'name': 'Slovak', 'hl': 'sk'}, 'id': 'sk'},
    {'snippet': {'name': 'Slovenian', 'hl': 'sl'}, 'id': 'sl'},
    {'snippet': {'name': 'Finnish', 'hl': 'fi'}, 'id': 'fi'},
    {'snippet': {'name': 'Swedish', 'hl': 'sv'}, 'id': 'sv'},
    {'snippet': {'name': 'Vietnamese', 'hl': 'vi'}, 'id': 'vi'},
    {'snippet': {'name': 'Turkish', 'hl': 'tr'}, 'id': 'tr'},
    {'snippet': {'name': 'Bulgarian', 'hl': 'bg'}, 'id': 'bg'},
    {'snippet': {'name': 'Kyrgyz', 'hl': 'ky'}, 'id': 'ky'},
    {'snippet': {'name': 'Kazakh', 'hl': 'kk'}, 'id': 'kk'},
    {'snippet': {'name': 'Macedonian', 'hl': 'mk'}, 'id': 'mk'},
    {'snippet': {'name': 'Mongolian', 'hl': 'mn'}, 'id': 'mn'},
    {'snippet': {'name': 'Russian', 'hl': 'ru'}, 'id': 'ru'},
    {'snippet': {'name': 'Serbian', 'hl': 'sr'}, 'id': 'sr'},
    {'snippet': {'name': 'Ukrainian', 'hl': 'uk'}, 'id': 'uk'},
    {'snippet': {'name': 'Greek', 'hl': 'el'}, 'id': 'el'},
    {'snippet': {'name': 'Armenian', 'hl': 'hy'}, 'id': 'hy'},
    {'snippet': {'name': 'Hebrew', 'hl': 'iw'}, 'id': 'iw'},
    {'snippet': {'name': 'Urdu', 'hl': 'ur'}, 'id': 'ur'},
    {'snippet': {'name': 'Arabic', 'hl': 'ar'}, 'id': 'ar'},
    {'snippet': {'name': 'Persian', 'hl': 'fa'}, 'id': 'fa'},
    {'snippet': {'name': 'Nepali', 'hl': 'ne'}, 'id': 'ne'},
    {'snippet': {'name': 'Marathi', 'hl': 'mr'}, 'id': 'mr'},
    {'snippet': {'name': 'Hindi', 'hl': 'hi'}, 'id': 'hi'},
    {'snippet': {'name': 'Bengali', 'hl': 'bn'}, 'id': 'bn'},
    {'snippet': {'name': 'Punjabi', 'hl': 'pa'}, 'id': 'pa'},
    {'snippet': {'name': 'Gujarati', 'hl': 'gu'}, 'id': 'gu'},
    {'snippet': {'name': 'Tamil', 'hl': 'ta'}, 'id': 'ta'},
    {'snippet': {'name': 'Telugu', 'hl': 'te'}, 'id': 'te'},
    {'snippet': {'name': 'Kannada', 'hl': 'kn'}, 'id': 'kn'},
    {'snippet': {'name': 'Malayalam', 'hl': 'ml'}, 'id': 'ml'},
    {'snippet': {'name': 'Sinhala', 'hl': 'si'}, 'id': 'si'},
    {'snippet': {'name': 'Thai', 'hl': 'th'}, 'id': 'th'},
    {'snippet': {'name': 'Lao', 'hl': 'lo'}, 'id': 'lo'},
    {'snippet': {'name': 'Myanmar (Burmese)', 'hl': 'my'}, 'id': 'my'},
    {'snippet': {'name': 'Georgian', 'hl': 'ka'}, 'id': 'ka'},
    {'snippet': {'name': 'Amharic', 'hl': 'am'}, 'id': 'am'},
    {'snippet': {'name': 'Khmer', 'hl': 'km'}, 'id': 'km'},
    {'snippet': {'name': 'Chinese', 'hl': 'zh-CN'}, 'id': 'zh-CN'},
    {'snippet': {'name': 'Chinese (Taiwan)', 'hl': 'zh-TW'}, 'id': 'zh-TW'},
    {'snippet': {'name': 'Chinese (Hong Kong)', 'hl': 'zh-HK'}, 'id': 'zh-HK'},
    {'snippet': {'name': 'Japanese', 'hl': 'ja'}, 'id': 'ja'},
    {'snippet': {'name': 'Korean', 'hl': 'ko'}, 'id': 'ko'},
]}
DEFAULT_REGIONS = {'items': [
    {'snippet': {'gl': 'DZ', 'name': 'Algeria'}, 'id': 'DZ'},
    {'snippet': {'gl': 'AR', 'name': 'Argentina'}, 'id': 'AR'},
    {'snippet': {'gl': 'AU', 'name': 'Australia'}, 'id': 'AU'},
    {'snippet': {'gl': 'AT', 'name': 'Austria'}, 'id': 'AT'},
    {'snippet': {'gl': 'AZ', 'name': 'Azerbaijan'}, 'id': 'AZ'},
    {'snippet': {'gl': 'BH', 'name': 'Bahrain'}, 'id': 'BH'},
    {'snippet': {'gl': 'BY', 'name': 'Belarus'}, 'id': 'BY'},
    {'snippet': {'gl': 'BE', 'name': 'Belgium'}, 'id': 'BE'},
    {'snippet': {'gl': 'BA', 'name': 'Bosnia and Herzegovina'}, 'id': 'BA'},
    {'snippet': {'gl': 'BR', 'name': 'Brazil'}, 'id': 'BR'},
    {'snippet': {'gl': 'BG', 'name': 'Bulgaria'}, 'id': 'BG'},
    {'snippet': {'gl': 'CA', 'name': 'Canada'}, 'id': 'CA'},
    {'snippet': {'gl': 'CL', 'name': 'Chile'}, 'id': 'CL'},
    {'snippet': {'gl': 'CO', 'name': 'Colombia'}, 'id': 'CO'},
    {'snippet': {'gl': 'HR', 'name': 'Croatia'}, 'id': 'HR'},
    {'snippet': {'gl': 'CZ', 'name': 'Czech Republic'}, 'id': 'CZ'},
    {'snippet': {'gl': 'DK', 'name': 'Denmark'}, 'id': 'DK'},
    {'snippet': {'gl': 'EG', 'name': 'Egypt'}, 'id': 'EG'},
    {'snippet': {'gl': 'EE', 'name': 'Estonia'}, 'id': 'EE'},
    {'snippet': {'gl': 'FI', 'name': 'Finland'}, 'id': 'FI'},
    {'snippet': {'gl': 'FR', 'name': 'France'}, 'id': 'FR'},
    {'snippet': {'gl': 'GE', 'name': 'Georgia'}, 'id': 'GE'},
    {'snippet': {'gl': 'DE', 'name': 'Germany'}, 'id': 'DE'},
    {'snippet': {'gl': 'GH', 'name': 'Ghana'}, 'id': 'GH'},
    {'snippet': {'gl': 'GR', 'name': 'Greece'}, 'id': 'GR'},
    {'snippet': {'gl': 'HK', 'name': 'Hong Kong'}, 'id': 'HK'},
    {'snippet': {'gl': 'HU', 'name': 'Hungary'}, 'id': 'HU'},
    {'snippet': {'gl': 'IS', 'name': 'Iceland'}, 'id': 'IS'},
    {'snippet': {'gl': 'IN', 'name': 'India'}, 'id': 'IN'},
    {'snippet': {'gl': 'ID', 'name': 'Indonesia'}, 'id': 'ID'},
    {'snippet': {'gl': 'IQ', 'name': 'Iraq'}, 'id': 'IQ'},
    {'snippet': {'gl': 'IE', 'name': 'Ireland'}, 'id': 'IE'},
    {'snippet': {'gl': 'IL', 'name': 'Israel'}, 'id': 'IL'},
    {'snippet': {'gl': 'IT', 'name': 'Italy'}, 'id': 'IT'},
    {'snippet': {'gl': 'JM', 'name': 'Jamaica'}, 'id': 'JM'},
    {'snippet': {'gl': 'JP', 'name': 'Japan'}, 'id': 'JP'},
    {'snippet': {'gl': 'JO', 'name': 'Jordan'}, 'id': 'JO'},
    {'snippet': {'gl': 'KZ', 'name': 'Kazakhstan'}, 'id': 'KZ'},
    {'snippet': {'gl': 'KE', 'name': 'Kenya'}, 'id': 'KE'},
    {'snippet': {'gl': 'KW', 'name': 'Kuwait'}, 'id': 'KW'},
    {'snippet': {'gl': 'LV', 'name': 'Latvia'}, 'id': 'LV'},
    {'snippet': {'gl': 'LB', 'name': 'Lebanon'}, 'id': 'LB'},
    {'snippet': {'gl': 'LY', 'name': 'Libya'}, 'id': 'LY'},
    {'snippet': {'gl': 'LT', 'name': 'Lithuania'}, 'id': 'LT'},
    {'snippet': {'gl': 'LU', 'name': 'Luxembourg'}, 'id': 'LU'},
    {'snippet': {'gl': 'MK', 'name': 'Macedonia'}, 'id': 'MK'},
    {'snippet': {'gl': 'MY', 'name': 'Malaysia'}, 'id': 'MY'},
    {'snippet': {'gl': 'MX', 'name': 'Mexico'}, 'id': 'MX'},
    {'snippet': {'gl': 'ME', 'name': 'Montenegro'}, 'id': 'ME'},
    {'snippet': {'gl': 'MA', 'name': 'Morocco'}, 'id': 'MA'},
    {'snippet': {'gl': 'NP', 'name': 'Nepal'}, 'id': 'NP'},
    {'snippet': {'gl': 'NL', 'name': 'Netherlands'}, 'id': 'NL'},
    {'snippet': {'gl': 'NZ', 'name': 'New Zealand'}, 'id': 'NZ'},
    {'snippet': {'gl': 'NG', 'name': 'Nigeria'}, 'id': 'NG'},
    {'snippet': {'gl': 'NO', 'name': 'Norway'}, 'id': 'NO'},
    {'snippet': {'gl': 'OM', 'name': 'Oman'}, 'id': 'OM'},
    {'snippet': {'gl': 'PK', 'name': 'Pakistan'}, 'id': 'PK'},
    {'snippet': {'gl': 'PE', 'name': 'Peru'}, 'id': 'PE'},
    {'snippet': {'gl': 'PH', 'name': 'Philippines'}, 'id': 'PH'},
    {'snippet': {'gl': 'PL', 'name': 'Poland'}, 'id': 'PL'},
    {'snippet': {'gl': 'PT', 'name': 'Portugal'}, 'id': 'PT'},
    {'snippet': {'gl': 'PR', 'name': 'Puerto Rico'}, 'id': 'PR'},
    {'snippet': {'gl': 'QA', 'name': 'Qatar'}, 'id': 'QA'},
    {'snippet': {'gl': 'RO', 'name': 'Romania'}, 'id': 'RO'},
    {'snippet': {'gl': 'RU', 'name': 'Russia'}, 'id': 'RU'},
    {'snippet': {'gl': 'SA', 'name': 'Saudi Arabia'}, 'id': 'SA'},
    {'snippet': {'gl': 'SN', 'name': 'Senegal'}, 'id': 'SN'},
    {'snippet': {'gl': 'RS', 'name': 'Serbia'}, 'id': 'RS'},
    {'snippet': {'gl': 'SG', 'name': 'Singapore'}, 'id': 'SG'},
    {'snippet': {'gl': 'SK', 'name': 'Slovakia'}, 'id': 'SK'},
    {'snippet': {'gl': 'SI', 'name': 'Slovenia'}, 'id': 'SI'},
    {'snippet': {'gl': 'ZA', 'name': 'South Africa'}, 'id': 'ZA'},
    {'snippet': {'gl': 'KR', 'name': 'South Korea'}, 'id': 'KR'},
    {'snippet': {'gl': 'ES', 'name': 'Spain'}, 'id': 'ES'},
    {'snippet': {'gl': 'LK', 'name': 'Sri Lanka'}, 'id': 'LK'},
    {'snippet': {'gl': 'SE', 'name': 'Sweden'}, 'id': 'SE'},
    {'snippet': {'gl': 'CH', 'name': 'Switzerland'}, 'id': 'CH'},
    {'snippet': {'gl': 'TW', 'name': 'Taiwan'}, 'id': 'TW'},
    {'snippet': {'gl': 'TZ', 'name': 'Tanzania'}, 'id': 'TZ'},
    {'snippet': {'gl': 'TH', 'name': 'Thailand'}, 'id': 'TH'},
    {'snippet': {'gl': 'TN', 'name': 'Tunisia'}, 'id': 'TN'},
    {'snippet': {'gl': 'TR', 'name': 'Turkey'}, 'id': 'TR'},
    {'snippet': {'gl': 'UG', 'name': 'Uganda'}, 'id': 'UG'},
    {'snippet': {'gl': 'UA', 'name': 'Ukraine'}, 'id': 'UA'},
    {'snippet': {'gl': 'AE', 'name': 'United Arab Emirates'}, 'id': 'AE'},
    {'snippet': {'gl': 'GB', 'name': 'United Kingdom'}, 'id': 'GB'},
    {'snippet': {'gl': 'US', 'name': 'United States'}, 'id': 'US'},
    {'snippet': {'gl': 'VN', 'name': 'Vietnam'}, 'id': 'VN'},
    {'snippet': {'gl': 'YE', 'name': 'Yemen'}, 'id': 'YE'},
    {'snippet': {'gl': 'ZW', 'name': 'Zimbabwe'}, 'id': 'ZW'},
]}


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
            ui.show_notification(localize('succeeded'))

    elif action == 'refresh':
        targets = {
            'settings_xml': 'settings.xml',
        }
        path = targets.get(target)
        if not path:
            return

        if target == 'settings_xml' and ui.on_yes_no_input(
                context.get_name(), localize('refresh.settings.confirm')
        ):
            if not current_system_version.compatible(20, 0):
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
            ui.show_notification(localize('removed') % '"%s"' % username,
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
