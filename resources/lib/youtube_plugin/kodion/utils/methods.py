__author__ = 'bromix'

__all__ = ['create_path', 'create_uri_path', 'strip_html_from_text', 'print_items', 'find_best_fit', 'to_utf8',
           'to_unicode', 'select_stream']

import urllib
import re
from ..constants import localize
import xbmcaddon


def loose_version(v):
    filled = []
    for point in v.split("."):
        filled.append(point.zfill(8))
    return tuple(filled)


def to_utf8(text):
    result = text
    if isinstance(text, unicode):
        result = text.encode('utf-8')

    return result


def to_unicode(text):
    result = text
    if isinstance(text, str):
        result = text.decode('utf-8')

    return result


def find_best_fit(data, compare_method=None):
    try:
        return next(item for item in data if item['container'] == 'mpd')
    except StopIteration:
        pass

    result = None

    last_fit = -1
    if isinstance(data, dict):
        for key in data.keys():
            item = data[key]
            fit = abs(compare_method(item))
            if last_fit == -1 or fit < last_fit:
                last_fit = fit
                result = item
    elif isinstance(data, list):
        for item in data:
            fit = abs(compare_method(item))
            if last_fit == -1 or fit < last_fit:
                last_fit = fit
                result = item

    return result


def select_stream(context, stream_data_list, quality_map_override=None):
    # sort - best stream first
    def _sort_stream_data(_stream_data):
        return _stream_data.get('sort', 0)

    settings = context.get_settings()
    use_dash = settings.use_dash()
    ask_for_quality = context.get_settings().ask_for_video_quality()
    video_quality = settings.get_video_quality(quality_map_override=quality_map_override)
    audio_only = False if ask_for_quality else settings.audio_only()  # don't filter streams to audio only if we're asking for quality

    if audio_only:  # check for live stream, audio only not supported
        for item in stream_data_list:
            if item.get('Live', False):
                audio_only = False
                break

    if audio_only:
        use_dash = False
        stream_data_list = [item for item in stream_data_list
                            if (item.get('dash/audio', False) and
                                not item.get('dash/video', False))]

    if use_dash:
        if settings.dash_support_addon() and not context.addon_enabled('inputstream.adaptive'):
            if context.get_ui().on_yes_no_input(context.get_name(), context.localize(30579)):
                use_dash = context.set_addon_enabled('inputstream.adaptive')
            else:
                use_dash = False

    try:
        inputstream_version = xbmcaddon.Addon('inputstream.adaptive').getAddonInfo('version')
        live_dash_supported = loose_version(inputstream_version) >= loose_version('2.0.12')
    except RuntimeError:
        live_dash_supported = False

    if not live_dash_supported:
        stream_data_list = [item for item in stream_data_list
                            if ((item['container'] != 'mpd') or
                                ((item['container'] == 'mpd') and
                                 (item.get('Live') is not True)))]

    if not use_dash:
        stream_data_list = [item for item in stream_data_list if (item['container'] != 'mpd')]

    def _find_best_fit_video(_stream_data):
        if audio_only:
            return video_quality - _stream_data.get('sort', [0, 0])[0]
        else:
            return video_quality - _stream_data.get('video', {}).get('height', 0)

    sorted_stream_data_list = sorted(stream_data_list, key=_sort_stream_data, reverse=True)

    context.log_debug('selectable streams: %d' % len(sorted_stream_data_list))
    for sorted_stream_data in sorted_stream_data_list:
        context.log_debug('selectable stream: %s' % sorted_stream_data)

    selected_stream_data = None
    if ask_for_quality and len(sorted_stream_data_list) > 1:
        items = []
        for sorted_stream_data in sorted_stream_data_list:
            items.append((sorted_stream_data['title'], sorted_stream_data))

        result = context.get_ui().on_select(context.localize(localize.SELECT_VIDEO_QUALITY), items)
        if result != -1:
            selected_stream_data = result
    else:
        selected_stream_data = find_best_fit(sorted_stream_data_list, _find_best_fit_video)

    if selected_stream_data is not None:
        context.log_debug('selected stream: %s' % selected_stream_data)

    return selected_stream_data


def create_path(*args):
    comps = []
    for arg in args:
        if isinstance(arg, list):
            return create_path(*arg)

        comps.append(unicode(arg.strip('/').replace('\\', '/').replace('//', '/')))

    uri_path = '/'.join(comps)
    if uri_path:
        return u'/%s/' % uri_path

    return '/'


def create_uri_path(*args):
    comps = []
    for arg in args:
        if isinstance(arg, list):
            return create_uri_path(*arg)

        comps.append(arg.strip('/').replace('\\', '/').replace('//', '/').encode('utf-8'))

    uri_path = '/'.join(comps)
    if uri_path:
        return urllib.quote('/%s/' % uri_path)

    return '/'


def strip_html_from_text(text):
    """
    Removes html tags
    :param text: html text
    :return:
    """
    return re.sub('<[^<]+?>', '', text)


def print_items(items):
    """
    Prints the given test_items. Basically for tests
    :param items: list of instances of base_item
    :return:
    """
    if not items:
        items = []

    for item in items:
        print item
