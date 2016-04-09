__author__ = 'bromix'


def _process_language(provider, context):
    if not context.get_ui().on_yes_no_input(context.localize(provider.LOCAL_MAP['youtube.setup_wizard.adjust']),
                                            context.localize(provider.LOCAL_MAP[
                                                'youtube.setup_wizard.adjust.language_and_region'])):
        return

    client = provider.get_client(context)

    kodi_language = context.get_language()
    json_data = client.get_supported_languages(kodi_language)
    items = json_data['items']
    language_list = []
    for item in items:
        language_id = item['id']
        language_name = item['snippet']['name']
        language_list.append((language_name, language_id))
        pass
    language_list = sorted(language_list, key=lambda x: x[0])
    language_id = context.get_ui().on_select(
        context.localize(provider.LOCAL_MAP['youtube.setup_wizard.select_language']), language_list)
    if language_id == -1:
        return

    json_data = client.get_supported_regions(language=language_id)
    items = json_data['items']
    region_list = []
    for item in items:
        region_id = item['id']
        region_name = item['snippet']['name']
        region_list.append((region_name, region_id))
        pass
    region_list = sorted(region_list, key=lambda x: x[0])
    region_id = context.get_ui().on_select(context.localize(provider.LOCAL_MAP['youtube.setup_wizard.select_region']),
                                           region_list)
    if region_id == -1:
        return

    # set new language id and region id
    context.get_settings().set_string('youtube.language', language_id)
    context.get_settings().set_string('youtube.region', region_id)
    provider.reset_client()
    pass


def process(provider, context):
    _process_language(provider, context)
    pass
