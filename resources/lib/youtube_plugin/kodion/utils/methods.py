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
import re
import shutil
from datetime import timedelta
from math import floor, log

from ..compatibility import byte_string_type, string_type, xbmc, xbmcvfs
from ..logger import log_error


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


def select_stream(context,
                  stream_data_list,
                  ask_for_quality,
                  audio_only,
                  use_adaptive_formats=True):
    settings = context.get_settings()
    isa_capabilities = context.inputstream_adaptive_capabilities()
    use_adaptive = (use_adaptive_formats
                    and settings.use_isa()
                    and bool(isa_capabilities))
    live_type = ('live' in isa_capabilities
                 and settings.live_stream_type()) or 'hls'

    if audio_only:
        context.log_debug('Select stream: Audio only')
        stream_list = [item for item in stream_data_list
                       if 'video' not in item]
    else:
        stream_list = [
            item for item in stream_data_list
            if (not item.get('adaptive')
                or (not item.get('live') and use_adaptive)
                or (item.get('live')
                    and live_type.startswith('isa')
                    and ((live_type == 'isa_mpd' and item.get('dash/video'))
                         or item.get('hls/video'))))
        ]

    if not stream_list:
        context.log_debug('Select stream: no streams found')
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

        context.log_debug('Stream {0}:\n{1}'.format(idx, log_data))

    if ask_for_quality:
        selected_stream = context.get_ui().on_select(
            context.localize('select_video_quality'),
            [stream['title'] for stream in stream_list],
        )
        if selected_stream == -1:
            context.log_debug('Select stream: no stream selected')
            return None
    else:
        selected_stream = 0

    context.log_debug('Selected stream: Stream {0}'.format(selected_stream))
    return stream_list[selected_stream]


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
    match = re.search(r'.*video_id=(?P<video_id>[a-zA-Z0-9_\-]{11}).*',
                      plugin_path)
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


def validate_ip_address(ip_address):
    try:
        octets = [octet for octet in map(int, ip_address.split('.'))
                  if 0 <= octet <= 255]
        if len(octets) != 4:
            raise ValueError
    except ValueError:
        return 0, 0, 0, 0
    return tuple(octets)


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


def redact_ip(url):
    return re.sub(r'([?&/])ip([=/])[^?&/]+', r'\g<1>ip\g<2><redacted>', url)
