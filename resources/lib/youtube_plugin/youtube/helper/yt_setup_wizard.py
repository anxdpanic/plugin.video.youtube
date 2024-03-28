# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os

from ...kodion.compatibility import urlencode, xbmcvfs
from ...kodion.constants import ADDON_ID, DATA_PATH, WAIT_FLAG
from ...kodion.network import Locator, httpd_status
from ...kodion.sql_store import PlaybackHistory, SearchHistory
from ...kodion.utils.datetime_parser import strptime
from ...kodion.utils.methods import to_unicode


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


def process_language(provider, context, step, steps):
    localize = context.localize
    ui = context.get_ui()

    step += 1
    if not ui.on_yes_no_input(
        localize('setup_wizard') + ' ({0}/{1})'.format(step, steps),
        (localize('setup_wizard.prompt')
         % localize('setup_wizard.prompt.locale')),
    ):
        return step

    client = provider.get_client(context)
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
        elif not selected_language[0] and base_item_lang == base_kodi_language:
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
        return step

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
        return step

    # set new language id and region id
    settings = context.get_settings()
    settings.set_string(settings.LANGUAGE, language_id)
    settings.set_string(settings.REGION, region_id)
    provider.reset_client()
    return step


def process_geo_location(_provider, context, step, steps):
    localize = context.localize

    step += 1
    if context.get_ui().on_yes_no_input(
        localize('setup_wizard') + ' ({0}/{1})'.format(step, steps),
        (localize('setup_wizard.prompt')
         % localize('setup_wizard.prompt.my_location')),
    ):
        locator = Locator()
        locator.locate_requester()
        coords = locator.coordinates()
        if coords:
            context.get_settings().set_location(
                '{0[lat]},{0[lon]}'.format(coords)
            )
    return step


def process_default_settings(_provider, context, step, steps):
    localize = context.localize
    settings = context.get_settings()

    step += 1
    if context.get_ui().on_yes_no_input(
        localize('setup_wizard') + ' ({0}/{1})'.format(step, steps),
        (localize('setup_wizard.prompt')
         % localize('setup_wizard.prompt.settings.defaults'))
    ):
        settings.client_selection(0)
        settings.use_isa(True)
        settings.use_mpd_videos(True)
        settings.stream_select(4 if settings.ask_for_video_quality() else 3)
        settings.live_stream_type(2)
        if not xbmcvfs.exists('special://profile/playercorefactory.xml'):
            settings.alternative_player_web_urls(False)
        if settings.cache_size() < 20:
            settings.cache_size(20)
        if settings.use_isa() and not httpd_status():
            settings.httpd_listen('0.0.0.0')
    return step


def process_list_detail_settings(_provider, context, step, steps):
    localize = context.localize
    settings = context.get_settings()

    step += 1
    if context.get_ui().on_yes_no_input(
        localize('setup_wizard') + ' ({0}/{1})'.format(step, steps),
        (localize('setup_wizard.prompt')
         % localize('setup_wizard.prompt.settings.list_details'))
    ):
        settings.show_detailed_description(False)
        settings.show_detailed_labels(False)
    else:
        settings.show_detailed_description(True)
        settings.show_detailed_labels(True)
    return step


def process_performance_settings(_provider, context, step, steps):
    localize = context.localize
    settings = context.get_settings()
    ui = context.get_ui()

    step += 1
    if ui.on_yes_no_input(
        localize('setup_wizard') + ' ({0}/{1})'.format(step, steps),
        (localize('setup_wizard.prompt')
         % localize('setup_wizard.prompt.settings.performance'))
    ):
        device_types = {
            '720p30': {
                'max_resolution': 3,  # 720p
                'stream_features': ('avc1', 'mp4a', 'filter'),
                'num_items': 10,
                'settings': (
                    (settings.use_isa, (True,)),
                    (settings.use_mpd_videos, (False,)),
                    (settings.live_stream_type, (2,)),
                ),
            },
            '1080p30': {
                'max_resolution': 4,  # 1080p
                'stream_features': ('avc1', 'vp9', 'vorbis', 'mp4a', 'ssa', 'ac-3', 'ec-3', 'dts', 'filter'),
                'num_items': 20,
            },
            '1080p60': {
                'max_resolution': 4,  # 1080p
                'stream_features': ('avc1', 'vp9', 'hfr', 'vorbis', 'mp4a', 'ssa', 'ac-3', 'ec-3', 'dts', 'filter'),
                'num_items': 30,
            },
            '4k30': {
                'max_resolution': 6,  # 4k
                'stream_features': ('avc1', 'vp9', 'hdr', 'hfr', 'no_hfr_max', 'vorbis', 'mp4a', 'ssa', 'ac-3', 'ec-3', 'dts', 'filter'),
                'num_items': 50,
            },
            '4k60': {
                'max_resolution': 6,  # 4k
                'stream_features': ('avc1', 'vp9', 'hdr', 'hfr', 'vorbis', 'mp4a', 'ssa', 'ac-3', 'ec-3', 'dts', 'filter'),
                'num_items': 50,
            },
            '4k60_av1': {
                'max_resolution': 6,  # 4k
                'stream_features': ('avc1', 'vp9', 'av01', 'hdr', 'hfr', 'vorbis', 'mp4a', 'ssa', 'ac-3', 'ec-3', 'dts', 'filter'),
                'num_items': 50,
            },
            'max': {
                'max_resolution': 7,  # 8k
                'stream_features': ('avc1', 'vp9', 'av01', 'hdr', 'hfr', 'vorbis', 'mp4a', 'ssa', 'ac-3', 'ec-3', 'dts', 'filter'),
                'num_items': 50,
            },
        }
        items = [
            localize('setup_wizard.capabilities.' + item).split(' | ') + [item]
            for item in device_types
        ]
        device_type = ui.on_select(
            localize('setup_wizard.capabilities'),
            items=items,
            use_details=True,
        )
        if device_type == -1:
            return step

        device_type = device_types[device_type]
        settings.mpd_video_qualities(device_type['max_resolution'])
        settings.stream_features(device_type['stream_features'])
        settings.items_per_page(device_type['num_items'])
        if 'settings' in device_type:
            for setting in device_type['settings']:
                setting[0](*setting[1])
    return step


def process_subtitles(_provider, context, step, steps):
    localize = context.localize

    step += 1
    if context.get_ui().on_yes_no_input(
        localize('setup_wizard') + ' ({0}/{1})'.format(step, steps),
        (localize('setup_wizard.prompt')
         % localize('setup_wizard.prompt.subtitles'))
    ):
        context.execute('RunScript({addon_id},config/subtitles)'.format(
            addon_id=ADDON_ID
        ), wait_for=WAIT_FLAG)
    return step


def process_old_search_db(_provider, context, step, steps):
    localize = context.localize
    ui = context.get_ui()

    search_db_path = os.path.join(
        DATA_PATH,
        'kodion',
        'search.sqlite'
    )
    step += 1
    if xbmcvfs.exists(search_db_path) and ui.on_yes_no_input(
        localize('setup_wizard') + ' ({0}/{1})'.format(step, steps),
        localize('setup_wizard.prompt.import_search_history'),
    ):
        def _convert_old_search_item(value, item):
            return {
                'text': to_unicode(value),
                'timestamp': strptime(item[1]).timestamp(),
            }

        search_history = context.get_search_history()
        old_search_db = SearchHistory(
            xbmcvfs.translatePath(search_db_path),
            migrate='storage',
        )
        items = old_search_db.get_items(process=_convert_old_search_item)
        for search in items:
            search_history.update(search['text'], search['timestamp'])

        ui.show_notification(localize('succeeded'))
        context.execute(
            'RunScript({addon},maintenance/{action}?{query})'
            .format(addon=ADDON_ID,
                    action='delete',
                    query=urlencode({'target': 'other_file',
                                     'path': search_db_path})),
            wait_for=WAIT_FLAG,
        )
    return step


def process_old_history_db(_provider, context, step, steps):
    localize = context.localize
    ui = context.get_ui()

    history_db_path = os.path.join(
        DATA_PATH,
        'playback',
        context.get_access_manager().get_current_user_id() + '.sqlite',
    )
    step += 1
    if xbmcvfs.exists(history_db_path) and ui.on_yes_no_input(
        localize('setup_wizard') + ' ({0}/{1})'.format(step, steps),
        localize('setup_wizard.prompt.import_playback_history'),
    ):
        def _convert_old_history_item(value, item):
            values = value.split(',')
            return {
                'play_count': int(values[0]),
                'total_time': float(values[1]),
                'played_time': float(values[2]),
                'played_percent': int(values[3]),
                'timestamp': strptime(item[1]).timestamp(),
            }

        playback_history = context.get_playback_history()
        old_history_db = PlaybackHistory(
            xbmcvfs.translatePath(history_db_path),
            migrate='storage',
        )
        items = old_history_db.get_items(process=_convert_old_history_item)
        for video_id, history in items.items():
            timestamp = history.pop('timestamp', None)
            playback_history.update(video_id, history, timestamp)

        ui.show_notification(localize('succeeded'))
        context.execute(
            'RunScript({addon},maintenance/{action}?{query})'
            .format(addon=ADDON_ID,
                    action='delete',
                    query=urlencode({'target': 'other_file',
                                     'path': history_db_path})),
            wait_for=WAIT_FLAG,
        )
    return step
