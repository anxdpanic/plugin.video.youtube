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
from base64 import urlsafe_b64decode
from datetime import timedelta
from math import floor, log
from re import MULTILINE, compile as re_compile

from .. import logging
from ..compatibility import (
    byte_string_type,
    parse_qs,
    string_type,
    urlencode,
    urlsplit,
    urlunsplit,
    xbmc,
    xbmcvfs,
)


__all__ = (
    'duration_to_seconds',
    'find_video_id',
    'fix_subtitle_stream',
    'friendly_number',
    'get_kodi_setting_bool',
    'get_kodi_setting_value',
    'jsonrpc',
    'loose_version',
    'make_dirs',
    'merge_dicts',
    'parse_and_redact_uri',
    'redact_auth_header',
    'redact_ip_in_uri',
    'redact_params',
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
        logging.debug('Audio only')
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
        logging.debug('No streams found')
        return None

    def _stream_sort(_stream):
        return _stream.get('sort', [0, 0, 0])

    stream_list.sort(key=_stream_sort, reverse=True)
    num_streams = len(stream_list)
    ask_for_quality = ask_for_quality and num_streams >= 1
    logging.debug('%d available stream(s)', num_streams)

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
            log_data['url'] = redact_ip_in_uri(original_value)

        logging.debug(('Stream {idx}:',
                       '{stream_details}'),
                      idx=idx,
                      stream_details=log_data)

    if ask_for_quality:
        selected_stream = context.get_ui().on_select(
            context.localize('select_video_quality'),
            [stream['title'] for stream in stream_list],
        )
        if selected_stream == -1:
            logging.debug('No stream selected')
            return None
    else:
        selected_stream = 0

    logging.debug('Stream %d selected', selected_stream)
    return stream_list[selected_stream]


def strip_html_from_text(text, tag_re=re_compile('<[^<]+?>')):
    """
    Removes html tags
    :param text: html text
    :param tag_re: RE pattern object used to match html tags
    :return:
    """
    return tag_re.sub('', text)


def make_dirs(path):
    if not path.endswith('/'):
        path = ''.join((path, '/'))
    path = xbmcvfs.translatePath(path)

    if xbmcvfs.exists(path) or xbmcvfs.mkdirs(path):
        return path

    try:
        os.makedirs(path)
    except OSError:
        if not xbmcvfs.exists(path):
            logging.exception(('Failed', 'Path: |%s|'), path)
            return False
    return path


def rm_dir(path):
    if not path.endswith('/'):
        path = ''.join((path, '/'))
    path = xbmcvfs.translatePath(path)

    if not xbmcvfs.exists(path) or xbmcvfs.rmdir(path, force=True):
        return True

    try:
        shutil.rmtree(path)
    except OSError:
        logging.exception(('Failed', 'Path: |%s|'), path)
    return not xbmcvfs.exists(path)


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


def timedelta_to_timestamp(delta, offset=None, multiplier=1.0):
    if isinstance(delta, timedelta):
        pass
    elif isinstance(delta, (list, tuple)) and len(delta) == 3:
        delta = timedelta(hours=int(delta[0]),
                          minutes=int(delta[1]),
                          seconds=float(delta[2]))
    else:
        return None

    if offset is not None:
        if isinstance(offset, timedelta):
            delta += offset
        elif isinstance(offset, (list, tuple)) and len(offset) == 3:
            delta += timedelta(hours=int(offset[0]),
                               minutes=int(offset[1]),
                               seconds=float(offset[2]))
        elif isinstance(offset, dict):
            delta += timedelta(**offset)

    total_seconds = delta.total_seconds() * multiplier
    hrs, rem = divmod(total_seconds, 3600)
    mins, secs = divmod(rem, 60)
    return '{0:02.0f}:{1:02.0f}:{2:06.3f}'.format(hrs, mins, secs)


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


def redact_ip_in_uri(
    url,
    _re=re_compile(r'([?&/]|%3F|%26|%2F)ip([=/]|%3D|%2F)[^?&/%]+'),
):
    return _re.sub(r'\g<1>ip\g<2><redacted>', url)


def redact_auth_header(header_string,
                       _re=re_compile(r'"Authorization": "[^"]+"')):
    return _re.sub(r'"Authorization": "<redacted>"', header_string)


def redact_params(params):
    log_params = params.copy()
    for param, value in params.items():
        if param in {'key', 'api_key', 'api_secret', 'client_secret'}:
            log_value = (
                ['...'.join((val[:3], val[-3:]))
                 if len(val) > 9 else
                 '...'
                 for val in value]
                if isinstance(value, (list, tuple)) else
                '...'.join((value[:3], value[-3:]))
                if len(value) > 9 else
                '...'
            )
        elif param in {'api_id', 'client_id'}:
            log_value = (
                ['...'.join((val[:3], val[-5:]))
                 if len(val) > 11 else
                 '...'
                 for val in value]
                if isinstance(value, (list, tuple)) else
                '...'.join((value[:3], value[-5:]))
                if len(value) > 11 else
                '...'
            )
        elif param in {'access_token', 'refresh_token', 'token'}:
            log_value = (
                ['<redacted>' for _ in value]
                if isinstance(value, (list, tuple)) else
                '<redacted>'
            )
        elif param == 'url':
            log_value = (
                [redact_ip_in_uri(val) for val in value]
                if isinstance(value, (list, tuple)) else
                redact_ip_in_uri(value)
            )
        elif param == 'ip':
            log_value = (
                ['<redacted>' for _ in value]
                if isinstance(value, (list, tuple)) else
                '<redacted>'
            )
        elif param == 'location':
            log_value = (
                ['|xx.xxxx,xx.xxxx|' for _ in value]
                if isinstance(value, (list, tuple)) else
                '|xx.xxxx,xx.xxxx|'
            )
        elif param == '__headers':
            log_value = (
                [redact_auth_header(val) for val in value]
                if isinstance(value, (list, tuple)) else
                redact_auth_header(value)
            )
        else:
            continue
        log_params[param] = log_value
    return log_params


def parse_and_redact_uri(uri, redact_only=False):
    parts = urlsplit(uri)
    if parts.query:
        params = parse_qs(parts.query, keep_blank_values=True)
        headers = params.get('__headers', [None])[0]
        if headers:
            params['__headers'] = [urlsafe_b64decode(headers).decode('utf-8')]
        log_params = redact_params(params)
        log_uri = urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(log_params, doseq=True),
            '',
        ))
    else:
        params = log_params = None
        log_uri = uri
    if redact_only:
        return log_uri
    return parts, params, log_uri, log_params


def _srt_to_vtt(content,
                srt_re=re_compile(
                    br'\d+[\r\n]'
                    br'(?P<start>\d+:\d+:\d+,\d+) --> '
                    br'(?P<end>\d+:\d+:\d+,\d+)[\r\n]'
                    br'(?P<text>.+)(?=[\r\n]{2,})',
                    flags=MULTILINE,
                )):
    subtitle_iter = srt_re.finditer(content)
    try:
        subtitle = next(subtitle_iter).groupdict()
        start = subtitle['start'].replace(b',', b'.')
        end = subtitle['end'].replace(b',', b'.')
        text = subtitle['text']
    except StopIteration:
        return content
    next_subtitle = next_start = next_end = next_text = None
    output = [b'WEBVTT\n\n']
    while 1:
        if next_start and next_end:
            start = next_start
            end = next_end
        if next_subtitle:
            subtitle = next_subtitle
            text = next_text
        elif not subtitle:
            break

        try:
            next_subtitle = next(subtitle_iter).groupdict()
            next_start = next_subtitle['start'].replace(b',', b'.')
            next_end = next_subtitle['end'].replace(b',', b'.')
            next_text = next_subtitle['text']
        except StopIteration:
            if subtitle == next_subtitle:
                break
            next_subtitle = None

        if next_subtitle and end > next_start:
            if end > next_end:
                fill_start, fill_end = next_start, next_end
                end, next_start, next_end = fill_start, fill_end, end
                next_subtitle = None
            else:
                fill_start, fill_end = next_start, end
                end, next_start = fill_start, fill_end
                subtitle = None
            output.append(b'%s --> %s\n%s\n\n'
                          b'%s --> %s\n%s\n%s\n\n'
                          % (
                              start, end, text,
                              fill_start, fill_end, text, next_text,
                          ))
        elif end > start:
            output.append(b'%s --> %s\n%s\n\n' % (start, end, text))
    return b''.join(output)


def fix_subtitle_stream(stream_type,
                        content,
                        vtt_re=re_compile(
                            br'(\d+:\d+:\d+\.\d+ --> \d+:\d+:\d+\.\d+)'
                            br'(?: (?:'
                            br'align:start'
                            br'|position:0%'
                            br'|position:63%'
                            br'|line:0%'
                            br'))+'
                        ),
                        vtt_repl=br'\1'):
    content_type, sub_format, sub_type = stream_type
    if content_type != 'track':
        pass
    elif sub_format == 'vtt':
        content = vtt_re.sub(vtt_repl, content)
    elif sub_format == 'srt':
        content = _srt_to_vtt(content)
    return content
