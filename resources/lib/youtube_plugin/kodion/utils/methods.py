# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import os
import shutil
from datetime import timedelta
from math import floor, log
from re import (
    compile as re_compile,
)

from ..compatibility import byte_string_type, string_type, xbmc, xbmcvfs
from ..logger import Logger


__all__ = (
    'duration_to_seconds',
    'find_video_id',
    'friendly_number',
    'get_kodi_setting_bool',
    'get_kodi_setting_value',
    'jsonrpc',
    'loose_version',
    'make_dirs',
    'merge_dicts',
    'print_items',
    'redact_auth',
    'redact_ip',
    'rm_dir',
    'seconds_to_duration',
    'select_stream',
    'strip_html_from_text',
    'to_unicode',
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


def select_stream(context,
                  stream_data_list,
                  ask_for_quality,
                  audio_only,
                  use_mpd=True):
    settings = context.get_settings()
    if settings.use_isa():
        isa_capabilities = context.inputstream_adaptive_capabilities()
        use_adaptive = bool(isa_capabilities)
        use_live_adaptive = use_adaptive and 'live' in isa_capabilities
        use_live_mpd = use_live_adaptive and settings.use_mpd_live_streams()
    else:
        use_adaptive = False
        use_live_adaptive = False
        use_live_mpd = False

    if audio_only:
        context.log_debug('Select stream - Audio only')
        stream_list = [item for item in stream_data_list
                       if 'video' not in item]
    else:
        stream_list = [
            item for item in stream_data_list
            if (not item.get('adaptive')
                or (not item.get('live')
                    and ((use_mpd and item.get('dash/video'))
                         or (use_adaptive and item.get('hls/video'))))
                or (item.get('live')
                    and ((use_live_mpd and item.get('dash/video'))
                         or (use_live_adaptive and item.get('hls/video')))))
        ]

    if not stream_list:
        context.log_debug('Select stream - No streams found')
        return None

    def _stream_sort(_stream):
        return _stream.get('sort', [0, 0, 0])

    stream_list.sort(key=_stream_sort, reverse=True)
    num_streams = len(stream_list)
    ask_for_quality = ask_for_quality and num_streams >= 1
    context.log_debug('Available streams: {0}'.format(num_streams))

    for idx, stream in enumerate(stream_list):
        log_data = stream.copy()

        if 'license_info' in log_data:
            license_info = log_data['license_info'].copy()
            for detail in ('url', 'token'):
                original_value = license_info.get(detail)
                if original_value:
                    license_info[detail] = '<redacted>'
            log_data['license_info'] = license_info

        original_value = log_data.get('url')
        if original_value:
            log_data['url'] = redact_ip(original_value)

        context.log_debug('Stream {idx}:'
                          '\n\t{stream_details}'
                          .format(idx=idx, stream_details=log_data))

    if ask_for_quality:
        selected_stream = context.get_ui().on_select(
            context.localize('select_video_quality'),
            [stream['title'] for stream in stream_list],
        )
        if selected_stream == -1:
            context.log_debug('Select stream - No stream selected')
            return None
    else:
        selected_stream = 0

    context.log_debug('Selected stream: Stream {0}'.format(selected_stream))
    return stream_list[selected_stream]


def strip_html_from_text(text, tag_re=re_compile('<[^<]+?>')):
    """
    Removes html tags
    :param text: html text
    :param tag_re: RE pattern object used to match html tags
    :return:
    """
    return tag_re.sub('', text)


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
    Logger.log_error('utils.make_dirs - Failed to create directory'
                     '\n\tPath: {path}'.format(path=path))
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
    Logger.log_error('utils.rm_dir - Failed to remove directory'
                     '\n\tPath: {path}'.format(path=path))
    return False


def find_video_id(plugin_path,
                  video_id_re=re_compile(
                      r'.*video_id=(?P<video_id>[a-zA-Z0-9_\-]{11}).*'
                  )):
    match = video_id_re.search(plugin_path)
    if match:
        return match.group('video_id')
    return ''


def friendly_number(value, precision=3, scale=('', 'K', 'M', 'B'), as_str=True):
    value = float('{value:.{precision}g}'.format(
        value=float(value),
        precision=precision,
    ))
    abs_value = abs(value)
    magnitude = 0 if abs_value < 1000 else int(log(floor(abs_value), 1000))
    output = '{output:f}'.format(
        output=value / 1000 ** magnitude
    ).rstrip('0').rstrip('.') + scale[magnitude]
    return output if as_str else (output, value)


def duration_to_seconds(duration,
                        periods_seconds_map={
                            '': 1,       # 1 second for unitless period
                            's': 1,      # 1 second
                            'm': 60,     # 1 minute
                            'h': 3600,   # 1 hour
                            'd': 86400,  # 1 day
                        },
                        periods_re=re_compile(r'([\d.]+)(d|h|m|s|$)')):
    if ':' in duration:
        seconds = 0
        for part in duration.split(':'):
            seconds = seconds * 60 + (float(part) if '.' in part else int(part))
        return seconds
    return sum(
        (float(number) if '.' in number else int(number))
        * periods_seconds_map.get(period, 1)
        for number, period in periods_re.findall(duration.lower())
    )


def seconds_to_duration(seconds):
    return str(timedelta(seconds=seconds))


def merge_dicts(item1, item2, templates=None, compare_str=False, _=Ellipsis):
    if not isinstance(item1, dict) or not isinstance(item2, dict):
        if (compare_str
                and isinstance(item1, string_type)
                and isinstance(item2, string_type)):
            return item1 if len(item1) > len(item2) else item2
        return (
            item1 if item2 is _ else
            _ if (item1 is KeyError or item2 is KeyError) else
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
    return xbmc.getCondVisibility(setting.join(('System.GetBool(', ')')))


def jsonrpc(batch=None, **kwargs):
    """
    Perform JSONRPC calls
    """

    if not batch and not kwargs:
        return None

    do_response = False
    for request_id, kwargs in enumerate(batch or (kwargs,)):
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


def redact_ip(url,
              ip_re=re_compile(r'([?&/]|%3F|%26|%2F)ip([=/]|%3D|%2F)[^?&/%]+')):
    return ip_re.sub(r'\g<1>ip\g<2><redacted>', url)


def redact_auth(header_string,
                ip_re=re_compile(r'"Authorization": "[^"]+"')):
    return ip_re.sub(r'"Authorization": "<redacted>"', header_string)
