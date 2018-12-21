# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from six.moves import urllib
from six import next
from six import string_types

import os
import copy
import re

from ..constants import localize

import xbmc
import xbmcvfs


__all__ = ['create_path', 'create_uri_path', 'strip_html_from_text', 'print_items', 'find_best_fit', 'to_utf8',
           'to_unicode', 'select_stream', 'make_dirs', 'loose_version', 'find_video_id']


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


def select_stream(context, stream_data_list, quality_map_override=None, ask_for_quality=None, audio_only=None):
    # sort - best stream first
    def _sort_stream_data(_stream_data):
        return _stream_data.get('sort', 0)

    settings = context.get_settings()
    use_dash = settings.use_dash()
    ask_for_quality = context.get_settings().ask_for_video_quality() if ask_for_quality is None else ask_for_quality
    video_quality = settings.get_video_quality(quality_map_override=quality_map_override)
    audio_only = audio_only if audio_only is not None else settings.audio_only()

    if not ask_for_quality:
        stream_data_list = [item for item in stream_data_list
                            if ((item['container'] != 'mpd') or
                                ((item['container'] == 'mpd') and
                                 (item.get('dash/video', False))))]

    if not ask_for_quality and audio_only:  # check for live stream, audio only not supported
        context.log_debug('Select stream: Audio only')
        for item in stream_data_list:
            if item.get('Live', False):
                context.log_debug('Select stream: Live stream, audio only not available')
                audio_only = False
                break

    if not ask_for_quality and audio_only:
        audio_stream_data_list = [item for item in stream_data_list
                                  if (item.get('dash/audio', False) and
                                      not item.get('dash/video', False))]

        if audio_stream_data_list:
            use_dash = False
            stream_data_list = audio_stream_data_list
        else:
            context.log_debug('Select stream: Audio only, no audio only streams found')

    dash_live = settings.use_dash_live_streams() and 'live' in context.inputstream_adaptive_capabilities()
    dash_videos = settings.use_dash_videos()

    if use_dash and any([item['container'] == 'mpd' for item in stream_data_list]):
        use_dash = context.use_inputstream_adaptive()

    if not use_dash:
        stream_data_list = [item for item in stream_data_list if (item['container'] != 'mpd')]
    else:
        if not dash_live:
            stream_data_list = [item for item in stream_data_list
                                if ((item['container'] != 'mpd') or
                                    ((item['container'] == 'mpd') and
                                     (item.get('Live') is not True)))]

        if not dash_videos:
            stream_data_list = [item for item in stream_data_list
                                if ((item['container'] != 'mpd') or
                                    ((item['container'] == 'mpd') and
                                     (item.get('Live') is True)))]

    def _find_best_fit_video(_stream_data):
        if audio_only:
            return video_quality - _stream_data.get('sort', [0, 0])[0]
        else:
            return video_quality - _stream_data.get('video', {}).get('height', 0)

    sorted_stream_data_list = sorted(stream_data_list, key=_sort_stream_data, reverse=True)

    context.log_debug('selectable streams: %d' % len(sorted_stream_data_list))
    log_streams = list()
    for sorted_stream_data in sorted_stream_data_list:
        log_data = copy.deepcopy(sorted_stream_data)
        if 'license_info' in log_data:
            log_data['license_info']['url'] = '[not shown]' if log_data['license_info'].get('url') else None
            log_data['license_info']['token'] = '[not shown]' if log_data['license_info'].get('token') else None
        else:
            log_data['url'] = re.sub(r'ip=\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 'ip=xxx.xxx.xxx.xxx', log_data['url'])
        log_streams.append(log_data)
    context.log_debug('selectable streams: \n%s' % '\n'.join(str(stream) for stream in log_streams))

    selected_stream_data = None
    if ask_for_quality and len(sorted_stream_data_list) > 1:
        items = list()
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
        path = ''.join([path, '/'])
    path = xbmc.translatePath(path)
    if not xbmcvfs.exists(path):
        try:
            _ = xbmcvfs.mkdirs(path)
        except:
            pass
        if not xbmcvfs.exists(path):
            try:
                os.makedirs(path)
            except:
                pass
        return xbmcvfs.exists(path)

    return True


def find_video_id(plugin_path):
    match = re.search(r'.*video_id=(?P<video_id>[a-zA-Z0-9_\-]{11}).*', plugin_path)
    if match:
        return match.group('video_id')
    return ''
