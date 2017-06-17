__author__ = 'bromix'

from ... import kodion
from ...youtube.helper import utils
from ...kodion.items.video_item import VideoItem


def my_subscriptions_to_items(provider, context, json_data, do_filter=False):
    result = []
    video_id_dict = {}

    filter_list = []
    black_list = False
    if do_filter:
        black_list = context.get_settings().get_bool('youtube.filter.my_subscriptions_filtered.blacklist', False)
        filter_list = context.get_settings().get_string('youtube.filter.my_subscriptions_filtered.list', '')
        filter_list = filter_list.replace(', ', ',')
        filter_list = filter_list.split(',')
        filter_list = [x.lower() for x in filter_list]

    items = json_data.get('items', [])
    for item in items:
        channel = item['channel'].lower()
        channel = channel.replace(',', '')
        if not do_filter or (do_filter and (not black_list) and (channel in filter_list)) or \
                (do_filter and black_list and (channel not in filter_list)):
            video_id = item['id']
            video_item = VideoItem(item['title'],
                                   uri=context.create_uri(['play'], {'video_id': video_id}))
            result.append(video_item)

            video_id_dict[video_id] = video_item
        pass

    channel_item_dict = {}
    utils.update_video_infos(provider, context, video_id_dict, channel_items_dict=channel_item_dict)
    utils.update_fanarts(provider, context, channel_item_dict)

    # next page
    next_page_token = json_data.get('next_page_token', '')
    if next_page_token or json_data.get('continue', False):
        new_params = {}
        new_params.update(context.get_params())
        new_params['next_page_token'] = next_page_token
        new_params['offset'] = int(json_data.get('offset', 0))

        new_context = context.clone(new_params=new_params)

        current_page = int(new_context.get_param('page', 1))
        next_page_item = kodion.items.NextPageItem(new_context, current_page, fanart=provider.get_fanart(new_context))
        result.append(next_page_item)
        pass

    return result
