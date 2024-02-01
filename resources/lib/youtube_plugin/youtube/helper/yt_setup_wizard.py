# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ...kodion.network import Locator


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


def _process_language(provider, context):
    if not context.get_ui().on_yes_no_input(
        context.localize('setup_wizard.adjust'),
        context.localize('setup_wizard.adjust.language_and_region')
    ):
        return

    client = provider.get_client(context)

    kodi_language = context.get_language()
    json_data = client.get_supported_languages(kodi_language)
    items = json_data.get('items') or DEFAULT_LANGUAGES['items']
    invalid_ids = ['es-419']  # causes hl not a valid language error. Issue #418
    language_list = sorted([
        (item['snippet']['name'], item['snippet']['hl'])
        for item in items
        if item['id'] not in invalid_ids
    ])
    language_id = context.get_ui().on_select(
        context.localize('setup_wizard.select_language'),
        language_list,
    )
    if language_id == -1:
        return

    json_data = client.get_supported_regions(language=language_id)
    items = json_data.get('items') or DEFAULT_REGIONS['items']
    region_list = sorted([
        (item['snippet']['name'], item['snippet']['gl'])
        for item in items
    ])
    region_id = context.get_ui().on_select(
        context.localize('setup_wizard.select_region'),
        region_list,
    )
    if region_id == -1:
        return

    # set new language id and region id
    context.get_settings().set_string('youtube.language', language_id)
    context.get_settings().set_string('youtube.region', region_id)
    provider.reset_client()


def _process_geo_location(context):
    if not context.get_ui().on_yes_no_input(
        context.get_name(), context.localize('perform_geolocation')
    ):
        return

    locator = Locator()
    locator.locate_requester()
    coords = locator.coordinates()
    if coords:
        context.get_settings().set_location('{0[lat]},{0[lon]}'.format(coords))


def process(provider, context):
    _process_language(provider, context)
    _process_geo_location(context)
