__author__ = 'bromix'

from ... import kodion
from ...kodion.items import DirectoryItem, UriItem
from ...youtube.helper import v3, tv, extract_urls, UrlResolver, UrlToItemConverter
from . import utils


def _process_related_videos(provider, context, re_match):
    result = []

    provider.set_content_type(context, kodion.constants.content_type.VIDEOS)

    page_token = context.get_param('page_token', '')
    video_id = context.get_param('video_id', '')
    if video_id:
        json_data = provider.get_client(context).get_related_videos(video_id=video_id, page_token=page_token)
        if not v3.handle_error(provider, context, json_data):
            return False
        result.extend(v3.response_to_items(provider, context, json_data, process_next_page=False))
        pass

    return result


def _process_recommendations(provider, context, re_match):
    provider.set_content_type(context, kodion.constants.content_type.VIDEOS)
    result = []

    page_token = context.get_param('page_token', '')
    json_data = provider.get_client(context).get_activities('home', page_token=page_token)
    if not v3.handle_error(provider, context, json_data):
        return False
    result.extend(v3.response_to_items(provider, context, json_data))
    return result


def _process_popular_right_now(provider, context, re_match):
    provider.set_content_type(context, kodion.constants.content_type.VIDEOS)

    result = []

    page_token = context.get_param('page_token', '')
    json_data = provider.get_client(context).get_popular_videos(page_token=page_token)
    if not v3.handle_error(provider, context, json_data):
        return False
    result.extend(v3.response_to_items(provider, context, json_data))

    return result


def _process_browse_channels(provider, context, re_match):
    result = []

    page_token = context.get_param('page_token', '')
    guide_id = context.get_param('guide_id', '')
    if guide_id:
        json_data = provider.get_client(context).get_guide_category(guide_id)
        if not v3.handle_error(provider, context, json_data):
            return False
        result.extend(v3.response_to_items(provider, context, json_data))
        pass
    else:
        json_data = provider.get_client(context).get_guide_categories()
        if not v3.handle_error(provider, context, json_data):
            return False
        result.extend(v3.response_to_items(provider, context, json_data))
        pass

    return result


def _process_disliked_videos(provider, context, re_match):
    provider.set_content_type(context, kodion.constants.content_type.VIDEOS)
    result = []

    page_token = context.get_param('page_token', '')
    json_data = provider.get_client(context).get_disliked_videos(page_token=page_token)
    if not v3.handle_error(provider, context, json_data):
        return False
    result.extend(v3.response_to_items(provider, context, json_data))
    return result


def _process_live_events(provider, context, re_match):
    def _sort(x):
        return x.get_aired()

    provider.set_content_type(context, kodion.constants.content_type.VIDEOS)

    result = []

    # TODO: cache result
    page_token = context.get_param('page_token', '')
    json_data = provider.get_client(context).get_live_events(event_type='live', page_token=page_token)
    if not v3.handle_error(provider, context, json_data):
        return False
    result.extend(v3.response_to_items(provider, context, json_data, sort=_sort, reverse_sort=True))

    return result


def _process_description_links(provider, context, re_match):
    def _extract_urls(_video_id):
        provider.set_content_type(context, kodion.constants.content_type.VIDEOS)

        result = []

        progress_dialog = context.get_ui().create_progress_dialog(
            heading=context.localize(kodion.constants.localize.COMMON_PLEASE_WAIT), background=False)

        resource_manager = provider.get_resource_manager(context)

        video_data = resource_manager.get_videos([_video_id])
        yt_item = video_data[_video_id]
        snippet = yt_item['snippet']  # crash if not conform
        description = kodion.utils.strip_html_from_text(snippet['description'])

        urls = extract_urls(description)

        progress_dialog.set_total(len(urls))

        url_resolver = UrlResolver(context)
        res_urls = []
        for url in urls:
            context.log_debug('Resolving url "%s"' % url)
            progress_dialog.update(steps=1, text=url)
            resolved_url = url_resolver.resolve(url)
            context.log_debug('Resolved url "%s"' % resolved_url)
            res_urls.append(resolved_url)

            if progress_dialog.is_aborted():
                context.log_debug('Resolving urls aborted')
                break

            context.sleep(50)
            pass

        url_to_item_converter = UrlToItemConverter()
        url_to_item_converter.add_urls(res_urls, provider, context)

        result.extend(url_to_item_converter.get_items(provider, context))

        progress_dialog.close()

        if len(result) == 0:
            progress_dialog.close()
            context.get_ui().on_ok(title=context.localize(provider.LOCAL_MAP['youtube.video.description.links']),
                                   text=context.localize(
                                       provider.LOCAL_MAP['youtube.video.description.links.not_found']))
            return False

        return result

    def _display_channels(_channel_ids):
        _channel_id_dict = {}

        for channel_id in _channel_ids:
            channel_item = DirectoryItem('', context.create_uri(['channel', channel_id]))
            channel_item.set_fanart(provider.get_fanart(context))
            _channel_id_dict[channel_id] = channel_item
            pass

        _channel_item_dict = {}
        utils.update_channel_infos(provider, context, _channel_id_dict, channel_items_dict=_channel_item_dict)
        utils.update_fanarts(provider, context, _channel_item_dict)

        # clean up - remove empty entries
        _result = []
        for key in _channel_id_dict:
            _channel_item = _channel_id_dict[key]
            if _channel_item.get_name():
                _result.append(_channel_item)
                pass
            pass
        return _result

    def _display_playlists(_playlist_ids):
        _playlist_id_dict = {}
        for playlist_id in _playlist_ids:
            playlist_item = DirectoryItem('', context.create_uri(['playlist', playlist_id]))
            playlist_item.set_fanart(provider.get_fanart(context))
            _playlist_id_dict[playlist_id] = playlist_item
            pass

        _channel_item_dict = {}
        utils.update_playlist_infos(provider, context, _playlist_id_dict, _channel_item_dict)
        utils.update_fanarts(provider, context, _channel_item_dict)

        # clean up - remove empty entries
        _result = []
        for key in _playlist_id_dict:
            _playlist_item = _playlist_id_dict[key]
            if _playlist_item.get_name():
                _result.append(_playlist_item)
            pass

        return _result

    video_id = context.get_param('video_id', '')
    if video_id:
        return _extract_urls(video_id)

    channel_ids = context.get_param('channel_ids', '')
    if channel_ids:
        channel_ids = channel_ids.split(',')
        if len(channel_ids) > 0:
            return _display_channels(channel_ids)
        pass

    playlist_ids = context.get_param('playlist_ids', '')
    if playlist_ids:
        playlist_ids = playlist_ids.split(',')
        if len(playlist_ids) > 0:
            return _display_playlists(playlist_ids)
        pass

    context.log_error('Missing video_id or playlist_ids for description links')

    return False


def _process_new_uploaded_videos_tv(provider, context, re_match):
    provider.set_content_type(context, kodion.constants.content_type.VIDEOS)

    result = []
    next_page_token = context.get_param('next_page_token', '')
    offset = int(context.get_param('offset', 0))
    json_data = provider.get_client(context).get_my_subscriptions(page_token=next_page_token, offset=offset)
    result.extend(tv.my_subscriptions_to_items(provider, context, json_data))

    return result


def _process_new_uploaded_videos_tv_filtered(provider, context, re_match):
    provider.set_content_type(context, kodion.constants.content_type.VIDEOS)

    result = []
    next_page_token = context.get_param('next_page_token', '')
    offset = int(context.get_param('offset', 0))
    json_data = provider.get_client(context).get_my_subscriptions(page_token=next_page_token, offset=offset)
    result.extend(tv.my_subscriptions_to_items(provider, context, json_data, do_filter=True))

    return result

def process(category, provider, context, re_match):
    result = []

    # we need a login
    client = provider.get_client(context)
    if not provider.is_logged_in() and category in ['new_uploaded_videos_tv', 'new_uploaded_videos_tv_filtered', 'disliked_videos']:
        return UriItem(context.create_uri(['sign', 'in']))

    if category == 'related_videos':
        return _process_related_videos(provider, context, re_match)
    elif category == 'popular_right_now':
        return _process_popular_right_now(provider, context, re_match)
    elif category == 'recommendations':
        return _process_recommendations(provider, context, re_match)
    elif category == 'browse_channels':
        return _process_browse_channels(provider, context, re_match)
    elif category == 'new_uploaded_videos_tv':
        return _process_new_uploaded_videos_tv(provider, context, re_match)
    elif category == 'new_uploaded_videos_tv_filtered':
        return _process_new_uploaded_videos_tv_filtered(provider, context, re_match)
    elif category == 'disliked_videos':
        return _process_disliked_videos(provider, context, re_match)
    elif category == 'live':
        return _process_live_events(provider, context, re_match)
    elif category == 'description_links':
        return _process_description_links(provider, context, re_match)
    else:
        raise kodion.KodionException("YouTube special category '%s' not found" % category)
