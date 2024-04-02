# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import copy
import json
import os
import re
import shutil
from datetime import timedelta
from math import floor, log

from ..compatibility import byte_string_type, quote, string_type, xbmc, xbmcvfs
from ..logger import log_error


__all__ = (
    'create_path',
    'duration_to_seconds',
    'find_best_fit',
    'find_video_id',
    'friendly_number',
    'get_kodi_setting_bool',
    'get_kodi_setting_value',
    'jsonrpc',
    'loose_version',
    'make_dirs',
    'merge_dicts',
    'print_items',
    'rm_dir',
    'seconds_to_duration',
    'select_stream',
    'strip_html_from_text',
    'to_unicode',
    'validate_ip_address',
    'wait',
)


def loose_version(v):
    return [point.zfill(8) for point in v.split('.')]


def to_unicode(text):
    if isinstance(text, byte_string_type):
        try:
            return text.decode('utf-8', 'ignore')
        except UnicodeError:
            pass
    return text


def find_best_fit(data, compare_method=None):
    if isinstance(data, dict):
        data = data.values()

    try:
        return next(item for item in data if item.get('container') == 'mpd')
    except StopIteration:
        pass

    if not compare_method:
        return None

    result = None
    last_fit = -1
    for item in data:
        fit = abs(compare_method(item))
        if last_fit == -1 or fit < last_fit:
            last_fit = fit
            result = item

    return result


def select_stream(context,
                  stream_data_list,
                  quality_map_override=None,
                  ask_for_quality=None,
                  audio_only=None):
    # sort - best stream first
    def _sort_stream_data(_stream_data):
        return _stream_data.get('sort', (0, 0))

    settings = context.get_settings()
    use_adaptive = context.use_inputstream_adaptive()
    if ask_for_quality is None:
        ask_for_quality = context.get_settings().ask_for_video_quality()
    video_quality = settings.get_video_quality(quality_map_override)
    if audio_only is None:
        audio_only = settings.audio_only()
    adaptive_live = settings.use_isa_live_streams() and context.inputstream_adaptive_capabilities('live')

    if not ask_for_quality:
        stream_data_list = [item for item in stream_data_list
                            if (item['container'] not in {'mpd', 'hls'} or
                                item.get('hls/video') or
                                item.get('dash/video'))]

    if not ask_for_quality and audio_only:  # check for live stream, audio only not supported
        context.log_debug('Select stream: Audio only')
        for item in stream_data_list:
            if item.get('Live'):
                context.log_debug('Select stream: Live stream, audio only not available')
                audio_only = False
                break

    if not ask_for_quality and audio_only:
        audio_stream_data_list = [item for item in stream_data_list
                                  if (item.get('dash/audio') and
                                      not item.get('dash/video') and
                                      not item.get('hls/video'))]

        if audio_stream_data_list:
            use_adaptive = False
            stream_data_list = audio_stream_data_list
        else:
            context.log_debug('Select stream: Audio only, no audio only streams found')

    if not adaptive_live:
        stream_data_list = [item for item in stream_data_list
                            if (item['container'] != 'mpd' or
                                not item.get('Live'))]
    elif not use_adaptive:
        stream_data_list = [item for item in stream_data_list
                            if item['container'] != 'mpd']

    def _find_best_fit_video(_stream_data):
        if audio_only:
            return video_quality - _stream_data.get('sort', (0, 0))[0]
        return video_quality - _stream_data.get('video', {}).get('height', 0)

    sorted_stream_data_list = sorted(stream_data_list, key=_sort_stream_data)

    context.log_debug('selectable streams: %d' % len(sorted_stream_data_list))
    log_streams = []
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
        items = [
            (sorted_stream_data['title'], sorted_stream_data)
            for sorted_stream_data in sorted_stream_data_list
        ]

        result = context.get_ui().on_select(context.localize('select_video_quality'), items)
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


def create_path(*args, **kwargs):
    path = '/'.join([
        part
        for part in [
            str(arg).strip('/').replace('\\', '/').replace('//', '/')
            for arg in args
        ] if part
    ])
    if path:
        path = path.join(('/', '/'))
    else:
        return '/'

    if kwargs.get('is_uri', False):
        return quote(path)
    return path


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
        path = ''.join((path, '/'))
    path = xbmcvfs.translatePath(path)

    succeeded = xbmcvfs.exists(path) or xbmcvfs.mkdirs(path)
    if succeeded:
        return path

    try:
        os.makedirs(path)
        succeeded = True
    except OSError:
        succeeded = xbmcvfs.exists(path)

    if succeeded:
        return path
    log_error('Failed to create directory: |{0}|'.format(path))
    return False


def rm_dir(path):
    if not path.endswith('/'):
        path = ''.join((path, '/'))
    path = xbmcvfs.translatePath(path)

    succeeded = (not xbmcvfs.exists(path)
                 or xbmcvfs.rmdir(path, force=True))
    if not succeeded:
        try:
            shutil.rmtree(path)
        except OSError:
            pass
        succeeded = not xbmcvfs.exists(path)

    if succeeded:
        return True
    log_error('Failed to remove directory: {0}'.format(path))
    return False


def find_video_id(plugin_path):
    match = re.search(r'.*video_id=(?P<video_id>[a-zA-Z0-9_\-]{11}).*', plugin_path)
    if match:
        return match.group('video_id')
    return ''


def friendly_number(input, precision=3, scale=('', 'K', 'M', 'B'), as_str=True):
    _input = float('{input:.{precision}g}'.format(
        input=float(input), precision=precision
    ))
    _abs_input = abs(_input)
    magnitude = 0 if _abs_input < 1000 else int(log(floor(_abs_input), 1000))
    output = '{output:f}'.format(
        output=_input / 1000 ** magnitude
    ).rstrip('0').rstrip('.') + scale[magnitude]
    return output if as_str else (output, _input)


_RE_PERIODS = re.compile(r'([\d.]+)(d|h|m|s|$)')
_SECONDS_IN_PERIODS = {
    '': 1,       # 1 second for unitless period
    's': 1,      # 1 second
    'm': 60,     # 1 minute
    'h': 3600,   # 1 hour
    'd': 86400,  # 1 day
}


def duration_to_seconds(duration):
    if ':' in duration:
        seconds = 0
        for part in duration.split(':'):
            seconds = seconds * 60 + (float(part) if '.' in part else int(part))
        return seconds
    return sum(
        (float(number) if '.' in number else int(number))
        * _SECONDS_IN_PERIODS.get(period, 1)
        for number, period in re.findall(_RE_PERIODS, duration.lower())
    )


def seconds_to_duration(seconds):
    return str(timedelta(seconds=seconds))


def merge_dicts(item1, item2, templates=None, _=Ellipsis):
    if not isinstance(item1, dict) or not isinstance(item2, dict):
        return (
            item1 if item2 is _ else
            _ if KeyError in (item1, item2) else
            item2
        )
    new = {}
    keys = set(item1)
    keys.update(item2)
    for key in keys:
        value = merge_dicts(item1.get(key, _), item2.get(key, _), templates)
        if value is _:
            continue
        if (templates is not None
                and isinstance(value, string_type) and '{' in value):
            templates['{0}.{1}'.format(id(new), key)] = (new, key, value)
        new[key] = value
    return new or _


def get_kodi_setting_value(setting, process=None):
    response = jsonrpc(method='Settings.GetSettingValue',
                       params={'setting': setting})
    try:
        value = response['result']['value']
        if process:
            return process(value)
    except (KeyError, TypeError, ValueError):
        return None
    return value


def get_kodi_setting_bool(setting):
    return xbmc.getCondVisibility('System.GetBool({0})'.format(setting))


def validate_ip_address(ip_address):
    try:
        octets = [octet for octet in map(int, ip_address.split('.'))
                  if 0 <= octet <= 255]
        if len(octets) != 4:
            raise ValueError
    except ValueError:
        return (0, 0, 0, 0)
    return tuple(octets)


def jsonrpc(batch=None, **kwargs):
    """
    Perform JSONRPC calls
    """

    if not batch and not kwargs:
        return None

    do_response = False
    for request_id, kwargs in enumerate(batch or (kwargs, )):
        do_response = (not kwargs.pop('no_response', False)) or do_response
        if do_response and 'id' not in kwargs:
            kwargs['id'] = request_id
        kwargs['jsonrpc'] = '2.0'

    request = json.dumps(batch or kwargs, default=tuple, ensure_ascii=False)
    response = xbmc.executeJSONRPC(request)
    return json.loads(response) if do_response else None


def wait(timeout=None):
    if not timeout:
        timeout = 0
    elif timeout < 0:
        timeout = 0.1
    return xbmc.Monitor().waitForAbort(timeout)
