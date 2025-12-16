# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from datetime import timedelta
from math import floor, log
from re import DOTALL, compile as re_compile

from ..compatibility import byte_string_type


def to_unicode(text):
    if isinstance(text, byte_string_type):
        try:
            return text.decode('utf-8', 'ignore')
        except UnicodeError:
            pass
    return text


def strip_html_from_text(text, tag_re=re_compile('<[^<]+?>')):
    """
    Removes html tags
    :param text: html text
    :param tag_re: RE pattern object used to match html tags
    :return:
    """
    return tag_re.sub('', text)


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


def _srt_to_vtt(content,
                srt_re=re_compile(
                    br'\d+[\r\n]'
                    br'(?P<start>[\d:,]+) --> '
                    br'(?P<end>[\d:,]+)[\r\n]'
                    br'(?P<text>.+?)[\r\n][\r\n]',
                    flags=DOTALL,
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
            subtitle = None
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


def channel_filter_split(filters_string):
    custom_filters = []
    channel_filters = {
        filter_string
        for filter_string in filters_string.split(',')
        if filter_string and custom_filter_split(filter_string, custom_filters)
    }
    return filters_string, channel_filters, custom_filters


def custom_filter_split(filter_string,
                        custom_filters,
                        criteria_re=re_compile(
                            r'{?{([^}]+)}{([^}]+)}{([^}]+)}}?'
                        )):
    criteria = criteria_re.findall(filter_string)
    if not criteria:
        return True
    custom_filters.append(criteria)
    return False
