# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from ...kodion.utils import ip_api


DEFAULT_LANGUAGES = {u'items': [{u'snippet': {u'name': u'Afrikaans', u'hl': u'af'}, u'id': u'af'}, {u'snippet': {u'name': u'Azerbaijani', u'hl': u'az'}, u'id': u'az'}, {u'snippet': {u'name': u'Indonesian', u'hl': u'id'}, u'id': u'id'}, {u'snippet': {u'name': u'Malay', u'hl': u'ms'}, u'id': u'ms'},
                                {u'snippet': {u'name': u'Catalan', u'hl': u'ca'}, u'id': u'ca'}, {u'snippet': {u'name': u'Czech', u'hl': u'cs'}, u'id': u'cs'}, {u'snippet': {u'name': u'Danish', u'hl': u'da'}, u'id': u'da'}, {u'snippet': {u'name': u'German', u'hl': u'de'}, u'id': u'de'},
                                {u'snippet': {u'name': u'Estonian', u'hl': u'et'}, u'id': u'et'}, {u'snippet': {u'name': u'English (United Kingdom)', u'hl': u'en-GB'}, u'id': u'en-GB'}, {u'snippet': {u'name': u'English', u'hl': u'en'}, u'id': u'en'},
                                {u'snippet': {u'name': u'Spanish (Spain)', u'hl': u'es'}, u'id': u'es'}, {u'snippet': {u'name': u'Spanish (Latin America)', u'hl': u'es-419'}, u'id': u'es-419'}, {u'snippet': {u'name': u'Basque', u'hl': u'eu'}, u'id': u'eu'},
                                {u'snippet': {u'name': u'Filipino', u'hl': u'fil'}, u'id': u'fil'}, {u'snippet': {u'name': u'French', u'hl': u'fr'}, u'id': u'fr'}, {u'snippet': {u'name': u'French (Canada)', u'hl': u'fr-CA'}, u'id': u'fr-CA'}, {u'snippet': {u'name': u'Galician', u'hl': u'gl'}, u'id': u'gl'},
                                {u'snippet': {u'name': u'Croatian', u'hl': u'hr'}, u'id': u'hr'}, {u'snippet': {u'name': u'Zulu', u'hl': u'zu'}, u'id': u'zu'}, {u'snippet': {u'name': u'Icelandic', u'hl': u'is'}, u'id': u'is'}, {u'snippet': {u'name': u'Italian', u'hl': u'it'}, u'id': u'it'},
                                {u'snippet': {u'name': u'Swahili', u'hl': u'sw'}, u'id': u'sw'}, {u'snippet': {u'name': u'Latvian', u'hl': u'lv'}, u'id': u'lv'}, {u'snippet': {u'name': u'Lithuanian', u'hl': u'lt'}, u'id': u'lt'}, {u'snippet': {u'name': u'Hungarian', u'hl': u'hu'}, u'id': u'hu'},
                                {u'snippet': {u'name': u'Dutch', u'hl': u'nl'}, u'id': u'nl'}, {u'snippet': {u'name': u'Norwegian', u'hl': u'no'}, u'id': u'no'}, {u'snippet': {u'name': u'Uzbek', u'hl': u'uz'}, u'id': u'uz'}, {u'snippet': {u'name': u'Polish', u'hl': u'pl'}, u'id': u'pl'},
                                {u'snippet': {u'name': u'Portuguese (Portugal)', u'hl': u'pt-PT'}, u'id': u'pt-PT'}, {u'snippet': {u'name': u'Portuguese (Brazil)', u'hl': u'pt'}, u'id': u'pt'}, {u'snippet': {u'name': u'Romanian', u'hl': u'ro'}, u'id': u'ro'},
                                {u'snippet': {u'name': u'Albanian', u'hl': u'sq'}, u'id': u'sq'}, {u'snippet': {u'name': u'Slovak', u'hl': u'sk'}, u'id': u'sk'}, {u'snippet': {u'name': u'Slovenian', u'hl': u'sl'}, u'id': u'sl'}, {u'snippet': {u'name': u'Finnish', u'hl': u'fi'}, u'id': u'fi'},
                                {u'snippet': {u'name': u'Swedish', u'hl': u'sv'}, u'id': u'sv'}, {u'snippet': {u'name': u'Vietnamese', u'hl': u'vi'}, u'id': u'vi'}, {u'snippet': {u'name': u'Turkish', u'hl': u'tr'}, u'id': u'tr'}, {u'snippet': {u'name': u'Bulgarian', u'hl': u'bg'}, u'id': u'bg'},
                                {u'snippet': {u'name': u'Kyrgyz', u'hl': u'ky'}, u'id': u'ky'}, {u'snippet': {u'name': u'Kazakh', u'hl': u'kk'}, u'id': u'kk'}, {u'snippet': {u'name': u'Macedonian', u'hl': u'mk'}, u'id': u'mk'}, {u'snippet': {u'name': u'Mongolian', u'hl': u'mn'}, u'id': u'mn'},
                                {u'snippet': {u'name': u'Russian', u'hl': u'ru'}, u'id': u'ru'}, {u'snippet': {u'name': u'Serbian', u'hl': u'sr'}, u'id': u'sr'}, {u'snippet': {u'name': u'Ukrainian', u'hl': u'uk'}, u'id': u'uk'}, {u'snippet': {u'name': u'Greek', u'hl': u'el'}, u'id': u'el'},
                                {u'snippet': {u'name': u'Armenian', u'hl': u'hy'}, u'id': u'hy'}, {u'snippet': {u'name': u'Hebrew', u'hl': u'iw'}, u'id': u'iw'}, {u'snippet': {u'name': u'Urdu', u'hl': u'ur'}, u'id': u'ur'}, {u'snippet': {u'name': u'Arabic', u'hl': u'ar'}, u'id': u'ar'},
                                {u'snippet': {u'name': u'Persian', u'hl': u'fa'}, u'id': u'fa'}, {u'snippet': {u'name': u'Nepali', u'hl': u'ne'}, u'id': u'ne'}, {u'snippet': {u'name': u'Marathi', u'hl': u'mr'}, u'id': u'mr'}, {u'snippet': {u'name': u'Hindi', u'hl': u'hi'}, u'id': u'hi'},
                                {u'snippet': {u'name': u'Bengali', u'hl': u'bn'}, u'id': u'bn'}, {u'snippet': {u'name': u'Punjabi', u'hl': u'pa'}, u'id': u'pa'}, {u'snippet': {u'name': u'Gujarati', u'hl': u'gu'}, u'id': u'gu'}, {u'snippet': {u'name': u'Tamil', u'hl': u'ta'}, u'id': u'ta'},
                                {u'snippet': {u'name': u'Telugu', u'hl': u'te'}, u'id': u'te'}, {u'snippet': {u'name': u'Kannada', u'hl': u'kn'}, u'id': u'kn'}, {u'snippet': {u'name': u'Malayalam', u'hl': u'ml'}, u'id': u'ml'}, {u'snippet': {u'name': u'Sinhala', u'hl': u'si'}, u'id': u'si'},
                                {u'snippet': {u'name': u'Thai', u'hl': u'th'}, u'id': u'th'}, {u'snippet': {u'name': u'Lao', u'hl': u'lo'}, u'id': u'lo'}, {u'snippet': {u'name': u'Myanmar (Burmese)', u'hl': u'my'}, u'id': u'my'}, {u'snippet': {u'name': u'Georgian', u'hl': u'ka'}, u'id': u'ka'},
                                {u'snippet': {u'name': u'Amharic', u'hl': u'am'}, u'id': u'am'}, {u'snippet': {u'name': u'Khmer', u'hl': u'km'}, u'id': u'km'}, {u'snippet': {u'name': u'Chinese', u'hl': u'zh-CN'}, u'id': u'zh-CN'}, {u'snippet': {u'name': u'Chinese (Taiwan)', u'hl': u'zh-TW'}, u'id': u'zh-TW'},
                                {u'snippet': {u'name': u'Chinese (Hong Kong)', u'hl': u'zh-HK'}, u'id': u'zh-HK'}, {u'snippet': {u'name': u'Japanese', u'hl': u'ja'}, u'id': u'ja'}, {u'snippet': {u'name': u'Korean', u'hl': u'ko'}, u'id': u'ko'}]}
DEFAULT_REGIONS = {u'items': [{u'snippet': {u'gl': u'DZ', u'name': u'Algeria'}, u'id': u'DZ'}, {u'snippet': {u'gl': u'AR', u'name': u'Argentina'}, u'id': u'AR'}, {u'snippet': {u'gl': u'AU', u'name': u'Australia'}, u'id': u'AU'}, {u'snippet': {u'gl': u'AT', u'name': u'Austria'}, u'id': u'AT'},
                              {u'snippet': {u'gl': u'AZ', u'name': u'Azerbaijan'}, u'id': u'AZ'}, {u'snippet': {u'gl': u'BH', u'name': u'Bahrain'}, u'id': u'BH'}, {u'snippet': {u'gl': u'BY', u'name': u'Belarus'}, u'id': u'BY'}, {u'snippet': {u'gl': u'BE', u'name': u'Belgium'}, u'id': u'BE'},
                              {u'snippet': {u'gl': u'BA', u'name': u'Bosnia and Herzegovina'}, u'id': u'BA'}, {u'snippet': {u'gl': u'BR', u'name': u'Brazil'}, u'id': u'BR'}, {u'snippet': {u'gl': u'BG', u'name': u'Bulgaria'}, u'id': u'BG'}, {u'snippet': {u'gl': u'CA', u'name': u'Canada'}, u'id': u'CA'},
                              {u'snippet': {u'gl': u'CL', u'name': u'Chile'}, u'id': u'CL'}, {u'snippet': {u'gl': u'CO', u'name': u'Colombia'}, u'id': u'CO'}, {u'snippet': {u'gl': u'HR', u'name': u'Croatia'}, u'id': u'HR'}, {u'snippet': {u'gl': u'CZ', u'name': u'Czech Republic'}, u'id': u'CZ'},
                              {u'snippet': {u'gl': u'DK', u'name': u'Denmark'}, u'id': u'DK'}, {u'snippet': {u'gl': u'EG', u'name': u'Egypt'}, u'id': u'EG'}, {u'snippet': {u'gl': u'EE', u'name': u'Estonia'}, u'id': u'EE'}, {u'snippet': {u'gl': u'FI', u'name': u'Finland'}, u'id': u'FI'},
                              {u'snippet': {u'gl': u'FR', u'name': u'France'}, u'id': u'FR'}, {u'snippet': {u'gl': u'GE', u'name': u'Georgia'}, u'id': u'GE'}, {u'snippet': {u'gl': u'DE', u'name': u'Germany'}, u'id': u'DE'}, {u'snippet': {u'gl': u'GH', u'name': u'Ghana'}, u'id': u'GH'},
                              {u'snippet': {u'gl': u'GR', u'name': u'Greece'}, u'id': u'GR'}, {u'snippet': {u'gl': u'HK', u'name': u'Hong Kong'}, u'id': u'HK'}, {u'snippet': {u'gl': u'HU', u'name': u'Hungary'}, u'id': u'HU'}, {u'snippet': {u'gl': u'IS', u'name': u'Iceland'}, u'id': u'IS'},
                              {u'snippet': {u'gl': u'IN', u'name': u'India'}, u'id': u'IN'}, {u'snippet': {u'gl': u'ID', u'name': u'Indonesia'}, u'id': u'ID'}, {u'snippet': {u'gl': u'IQ', u'name': u'Iraq'}, u'id': u'IQ'}, {u'snippet': {u'gl': u'IE', u'name': u'Ireland'}, u'id': u'IE'},
                              {u'snippet': {u'gl': u'IL', u'name': u'Israel'}, u'id': u'IL'}, {u'snippet': {u'gl': u'IT', u'name': u'Italy'}, u'id': u'IT'}, {u'snippet': {u'gl': u'JM', u'name': u'Jamaica'}, u'id': u'JM'}, {u'snippet': {u'gl': u'JP', u'name': u'Japan'}, u'id': u'JP'},
                              {u'snippet': {u'gl': u'JO', u'name': u'Jordan'}, u'id': u'JO'}, {u'snippet': {u'gl': u'KZ', u'name': u'Kazakhstan'}, u'id': u'KZ'}, {u'snippet': {u'gl': u'KE', u'name': u'Kenya'}, u'id': u'KE'}, {u'snippet': {u'gl': u'KW', u'name': u'Kuwait'}, u'id': u'KW'},
                              {u'snippet': {u'gl': u'LV', u'name': u'Latvia'}, u'id': u'LV'}, {u'snippet': {u'gl': u'LB', u'name': u'Lebanon'}, u'id': u'LB'}, {u'snippet': {u'gl': u'LY', u'name': u'Libya'}, u'id': u'LY'}, {u'snippet': {u'gl': u'LT', u'name': u'Lithuania'}, u'id': u'LT'},
                              {u'snippet': {u'gl': u'LU', u'name': u'Luxembourg'}, u'id': u'LU'}, {u'snippet': {u'gl': u'MK', u'name': u'Macedonia'}, u'id': u'MK'}, {u'snippet': {u'gl': u'MY', u'name': u'Malaysia'}, u'id': u'MY'}, {u'snippet': {u'gl': u'MX', u'name': u'Mexico'}, u'id': u'MX'},
                              {u'snippet': {u'gl': u'ME', u'name': u'Montenegro'}, u'id': u'ME'}, {u'snippet': {u'gl': u'MA', u'name': u'Morocco'}, u'id': u'MA'}, {u'snippet': {u'gl': u'NP', u'name': u'Nepal'}, u'id': u'NP'}, {u'snippet': {u'gl': u'NL', u'name': u'Netherlands'}, u'id': u'NL'},
                              {u'snippet': {u'gl': u'NZ', u'name': u'New Zealand'}, u'id': u'NZ'}, {u'snippet': {u'gl': u'NG', u'name': u'Nigeria'}, u'id': u'NG'}, {u'snippet': {u'gl': u'NO', u'name': u'Norway'}, u'id': u'NO'}, {u'snippet': {u'gl': u'OM', u'name': u'Oman'}, u'id': u'OM'},
                              {u'snippet': {u'gl': u'PK', u'name': u'Pakistan'}, u'id': u'PK'}, {u'snippet': {u'gl': u'PE', u'name': u'Peru'}, u'id': u'PE'}, {u'snippet': {u'gl': u'PH', u'name': u'Philippines'}, u'id': u'PH'}, {u'snippet': {u'gl': u'PL', u'name': u'Poland'}, u'id': u'PL'},
                              {u'snippet': {u'gl': u'PT', u'name': u'Portugal'}, u'id': u'PT'}, {u'snippet': {u'gl': u'PR', u'name': u'Puerto Rico'}, u'id': u'PR'}, {u'snippet': {u'gl': u'QA', u'name': u'Qatar'}, u'id': u'QA'}, {u'snippet': {u'gl': u'RO', u'name': u'Romania'}, u'id': u'RO'},
                              {u'snippet': {u'gl': u'RU', u'name': u'Russia'}, u'id': u'RU'}, {u'snippet': {u'gl': u'SA', u'name': u'Saudi Arabia'}, u'id': u'SA'}, {u'snippet': {u'gl': u'SN', u'name': u'Senegal'}, u'id': u'SN'}, {u'snippet': {u'gl': u'RS', u'name': u'Serbia'}, u'id': u'RS'},
                              {u'snippet': {u'gl': u'SG', u'name': u'Singapore'}, u'id': u'SG'}, {u'snippet': {u'gl': u'SK', u'name': u'Slovakia'}, u'id': u'SK'}, {u'snippet': {u'gl': u'SI', u'name': u'Slovenia'}, u'id': u'SI'}, {u'snippet': {u'gl': u'ZA', u'name': u'South Africa'}, u'id': u'ZA'},
                              {u'snippet': {u'gl': u'KR', u'name': u'South Korea'}, u'id': u'KR'}, {u'snippet': {u'gl': u'ES', u'name': u'Spain'}, u'id': u'ES'}, {u'snippet': {u'gl': u'LK', u'name': u'Sri Lanka'}, u'id': u'LK'}, {u'snippet': {u'gl': u'SE', u'name': u'Sweden'}, u'id': u'SE'},
                              {u'snippet': {u'gl': u'CH', u'name': u'Switzerland'}, u'id': u'CH'}, {u'snippet': {u'gl': u'TW', u'name': u'Taiwan'}, u'id': u'TW'}, {u'snippet': {u'gl': u'TZ', u'name': u'Tanzania'}, u'id': u'TZ'}, {u'snippet': {u'gl': u'TH', u'name': u'Thailand'}, u'id': u'TH'},
                              {u'snippet': {u'gl': u'TN', u'name': u'Tunisia'}, u'id': u'TN'}, {u'snippet': {u'gl': u'TR', u'name': u'Turkey'}, u'id': u'TR'}, {u'snippet': {u'gl': u'UG', u'name': u'Uganda'}, u'id': u'UG'}, {u'snippet': {u'gl': u'UA', u'name': u'Ukraine'}, u'id': u'UA'},
                              {u'snippet': {u'gl': u'AE', u'name': u'United Arab Emirates'}, u'id': u'AE'}, {u'snippet': {u'gl': u'GB', u'name': u'United Kingdom'}, u'id': u'GB'}, {u'snippet': {u'gl': u'US', u'name': u'United States'}, u'id': u'US'}, {u'snippet': {u'gl': u'VN', u'name': u'Vietnam'}, u'id': u'VN'},
                              {u'snippet': {u'gl': u'YE', u'name': u'Yemen'}, u'id': u'YE'}, {u'snippet': {u'gl': u'ZW', u'name': u'Zimbabwe'}, u'id': u'ZW'}]}


def _process_language(provider, context):
    if not context.get_ui().on_yes_no_input(context.localize(provider.LOCAL_MAP['youtube.setup_wizard.adjust']),
                                            context.localize(provider.LOCAL_MAP['youtube.setup_wizard.adjust.language_and_region'])):
        return

    client = provider.get_client(context)

    kodi_language = context.get_language()
    json_data = client.get_supported_languages(kodi_language)
    if 'items' not in json_data:
        items = DEFAULT_LANGUAGES['items']
    else:
        items = json_data['items']
    language_list = []
    invalid_ids = [u'es-419']  # causes hl not a valid language error. Issue #418
    for item in items:
        if item['id'] in invalid_ids:
            continue
        language_name = item['snippet']['name']
        hl = item['snippet']['hl']
        language_list.append((language_name, hl))
    language_list = sorted(language_list, key=lambda x: x[0])
    language_id = context.get_ui().on_select(
        context.localize(provider.LOCAL_MAP['youtube.setup_wizard.select_language']), language_list)
    if language_id == -1:
        return

    json_data = client.get_supported_regions(language=language_id)
    if 'items' not in json_data:
        items = DEFAULT_REGIONS['items']
    else:
        items = json_data['items']
    region_list = []
    for item in items:
        region_name = item['snippet']['name']
        gl = item['snippet']['gl']
        region_list.append((region_name, gl))
    region_list = sorted(region_list, key=lambda x: x[0])
    region_id = context.get_ui().on_select(context.localize(provider.LOCAL_MAP['youtube.setup_wizard.select_region']),
                                           region_list)
    if region_id == -1:
        return

    # set new language id and region id
    context.get_settings().set_string('youtube.language', language_id)
    context.get_settings().set_string('youtube.region', region_id)
    provider.reset_client()


def _process_geo_location(provider, context):
    settings = context.get_settings()
    if not context.get_ui().on_yes_no_input(context.get_name(), context.localize(provider.LOCAL_MAP['youtube.perform.geolocation'])):
        return

    locator = ip_api.Locator(context)
    locator.locate_requester()
    coordinates = locator.coordinates()
    if coordinates:
        settings.set_location('{lat},{lon}'.format(lat=coordinates[0], lon=coordinates[1]))


def process(provider, context):
    _process_language(provider, context)
    _process_geo_location(provider, context)
