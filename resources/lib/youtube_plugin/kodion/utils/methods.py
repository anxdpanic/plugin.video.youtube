__author__ = 'bromix'

__all__ = ['create_path', 'create_uri_path', 'strip_html_from_text', 'print_items', 'find_best_fit', 'to_utf8',
           'to_unicode', 'select_stream', 'make_dirs']

from six.moves import urllib
from six import next
from six import string_types

import os
import copy
import re

from ..constants import localize

import xbmc
import xbmcaddon
import xbmcvfs


def loose_version(v):
    filled = []
    for point in v.split("."):
        filled.append(point.zfill(8))
    return tuple(filled)


def to_utf8(text):
    result = text
    if isinstance(text, string_types):
        try:
            result = text.encode('utf-8', 'ignore')
        except UnicodeDecodeError:
            pass

    return result


def to_unicode(text):
    result = text
    if isinstance(text, string_types) or isinstance(text, bytes):
        try:
            result = text.decode('utf-8', 'ignore')
        except (AttributeError, UnicodeEncodeError):
            pass

    return result


def find_best_fit(data, compare_method=None):
    try:
        return next(item for item in data if item['container'] == 'mpd')
    except StopIteration:
        pass

    result = None

    last_fit = -1
    if isinstance(data, dict):
        for key in list(data.keys()):
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


def select_stream(context, stream_data_list, quality_map_override=None, ask_for_quality=None):
    # sort - best stream first
    def _sort_stream_data(_stream_data):
        return _stream_data.get('sort', 0)

    settings = context.get_settings()
    use_dash = settings.use_dash()
    ask_for_quality = context.get_settings().ask_for_video_quality() if ask_for_quality is None else ask_for_quality
    video_quality = settings.get_video_quality(quality_map_override=quality_map_override)
    audio_only = False if ask_for_quality else settings.audio_only()  # don't filter streams to audio only if we're asking for quality

    if audio_only:  # check for live stream, audio only not supported
        context.log_debug('Select stream: Audio only')
        for item in stream_data_list:
            if item.get('Live', False):
                context.log_debug('Select stream: Live stream, audio only not available')
                audio_only = False
                break

    if audio_only:
        use_dash = False
        audio_stream_data_list = [item for item in stream_data_list
                                  if (item.get('dash/audio', False) and
                                      not item.get('dash/video', False))]

        if audio_stream_data_list:
            stream_data_list = audio_stream_data_list
        else:
            context.log_debug('Select stream: Audio only, no audio only streams found')

    if use_dash:
        use_dash = context.use_inputstream_adaptive()

    live_dash_supported = 'live' in context.inputstream_adaptive_capabilities()

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
        log_data = copy.deepcopy(sorted_stream_data)
        if 'license_info' in log_data:
            log_data['license_info']['url'] = '[not shown]' if log_data['license_info'].get('url') else None
            log_data['license_info']['token'] = '[not shown]' if log_data['license_info'].get('token') else None
        context.log_debug('selectable stream: %s' % log_data)

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
        log_data = copy.deepcopy(selected_stream_data)
        if 'license_info' in log_data:
            log_data['license_info']['url'] = '[not shown]' if log_data['license_info'].get('url') else None
            log_data['license_info']['token'] = '[not shown]' if log_data['license_info'].get('token') else None
        context.log_debug('selected stream: %s' % log_data)

    return selected_stream_data


def create_path(*args):
    comps = []
    for arg in args:
        if isinstance(arg, list):
            return create_path(*arg)

        comps.append(str(arg.strip('/').replace('\\', '/').replace('//', '/')))

    uri_path = '/'.join(comps)
    if uri_path:
        return u'/%s/' % uri_path

    return '/'


def create_uri_path(*args):
    comps = []
    for arg in args:
        if isinstance(arg, list):
            return create_uri_path(*arg)

        comps.append(str(arg.strip('/').replace('\\', '/').replace('//', '/')))

    uri_path = '/'.join(comps)
    if uri_path:
        return urllib.parse.quote('/%s/' % uri_path)

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
        print(item)


def make_dirs(path):
    if not path.endswith('/'):
        path += '/'
    path = xbmc.translatePath(path)
    if not xbmcvfs.exists(path):
        try:
            r = xbmcvfs.mkdirs(path)
        except:
            pass
        if not xbmcvfs.exists(path):
            try:
                os.makedirs(path)
            except:
                pass
        return xbmcvfs.exists(path)

    return True
