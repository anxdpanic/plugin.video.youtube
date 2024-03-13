# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import re
from datetime import date, datetime, time as dt_time, timedelta
from importlib import import_module
from sys import modules

from ..exceptions import KodionException
from ..logger import log_error

try:
    from datetime import timezone
except ImportError:
    timezone = None


__RE_MATCH_TIME_ONLY__ = re.compile(
    r'^(?P<hour>[0-9]{2})(:?(?P<minute>[0-9]{2})(:?(?P<second>[0-9]{2}))?)?$'
)
__RE_MATCH_DATE_ONLY__ = re.compile(
    r'^(?P<year>[0-9]{4})[-/.]?(?P<month>[0-9]{2})[-/.]?(?P<day>[0-9]{2})$'
)
__RE_MATCH_DATETIME__ = re.compile(
    r'^(?P<year>[0-9]{4})[-/.]?(?P<month>[0-9]{2})[-/.]?(?P<day>[0-9]{2})'
    r'["T ](?P<hour>[0-9]{2}):?(?P<minute>[0-9]{2}):?(?P<second>[0-9]{2})'
)
__RE_MATCH_PERIOD__ = re.compile(
    r'P((?P<years>\d+)Y)?((?P<months>\d+)M)?((?P<days>\d+)D)?'
    r'(T((?P<hours>\d+)H)?((?P<minutes>\d+)M)?((?P<seconds>\d+)S)?)?'
)
__RE_MATCH_ABBREVIATED__ = re.compile(
    r'\w+, (?P<day>\d+) (?P<month>\w+) (?P<year>\d+)'
    r' (?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+)'
)

__INTERNAL_CONSTANTS__ = {
    'epoch_dt': (
        datetime.fromtimestamp(0, tz=timezone.utc) if timezone
        else datetime.fromtimestamp(0)
    ),
    'local_offset': None,
    'Jan': 1,
    'Feb': 2,
    'Mar': 3,
    'Apr': 4,
    'May': 5,
    'June': 6,
    'Jun': 6,
    'July': 7,
    'Jul': 7,
    'Aug': 8,
    'Sept': 9,
    'Sep': 9,
    'Oct': 10,
    'Nov': 11,
    'Dec': 12,
}

now = datetime.now
fromtimestamp = datetime.fromtimestamp


def parse(datetime_string):
    if not datetime_string:
        return None

    # match time only "00:45:10"
    match = __RE_MATCH_TIME_ONLY__.match(datetime_string)
    if match:
        match = {
            group: int(value)
            for group, value in match.groupdict().items()
            if value
        }
        if timezone:
            match['tzinfo'] = timezone.utc
        return datetime.combine(
            date=date.today(),
            time=dt_time(**match)
        ).time()

    # match date only '2014-11-08'
    match = __RE_MATCH_DATE_ONLY__.match(datetime_string)
    if match:
        match = {
            group: int(value)
            for group, value in match.groupdict().items()
            if value
        }
        if timezone:
            match['tzinfo'] = timezone.utc
        return datetime(**match)

    # full date time
    match = __RE_MATCH_DATETIME__.match(datetime_string)
    if match:
        match = {
            group: int(value)
            for group, value in match.groupdict().items()
            if value
        }
        if timezone:
            match['tzinfo'] = timezone.utc
        return datetime(**match)

    # period - at the moment we support only hours, minutes and seconds
    # e.g. videos and audio
    match = __RE_MATCH_PERIOD__.match(datetime_string)
    if match:
        match = {
            group: int(value)
            for group, value in match.groupdict().items()
            if value
        }
        return timedelta(**match)

    # abbreviated match
    match = __RE_MATCH_ABBREVIATED__.match(datetime_string)
    if match:
        match = {
            group: (
                __INTERNAL_CONSTANTS__.get(value, 0) if group == 'month'
                else int(value)
            )
            for group, value in match.groupdict().items()
            if value
        }
        if timezone:
            match['tzinfo'] = timezone.utc
        return datetime(**match)

    raise KodionException('Could not parse |{datetime}| as ISO 8601'
                          .format(datetime=datetime_string))


def get_scheduled_start(context, datetime_object, local=True):
    if timezone:
        _now = now(tz=timezone.utc)
        if local:
            _now = _now.astimezone(None)
    else:
        _now = now() if local else datetime.utcnow()

    if datetime_object.date() == _now.date():
        return '@ {start_time}'.format(
            start_time=context.format_time(datetime_object.time())
        )
    return '@ {start_date}, {start_time}'.format(
        start_time=context.format_time(datetime_object.time()),
        start_date=context.format_date_short(datetime_object.date())
    )


def utc_to_local(dt):
    if timezone:
        return dt.astimezone(None)

    if __INTERNAL_CONSTANTS__['local_offset']:
        offset = __INTERNAL_CONSTANTS__['local_offset']
    else:
        offset = now() - datetime.utcnow()
        __INTERNAL_CONSTANTS__['local_offset'] = offset

    return dt + offset


def datetime_to_since(context, dt, local=True):
    if timezone:
        _now = now(tz=timezone.utc)
        if local:
            _now = _now.astimezone(None)
    else:
        _now = now() if local else datetime.utcnow()

    diff = _now - dt
    yesterday = _now - timedelta(days=1)
    yyesterday = _now - timedelta(days=2)
    use_yesterday = (_now - yesterday).total_seconds() > 10800
    today = _now.date()
    tomorrow = today + timedelta(days=1)
    seconds = diff.total_seconds()

    if seconds > 0:
        if seconds < 60:
            return context.localize('datetime.just_now')
        if 60 <= seconds < 120:
            return context.localize('datetime.a_minute_ago')
        if 120 <= seconds < 3600:
            return context.localize('datetime.recently')
        if 3600 <= seconds < 7200:
            return context.localize('datetime.an_hour_ago')
        if 7200 <= seconds < 10800:
            return context.localize('datetime.two_hours_ago')
        if 10800 <= seconds < 14400:
            return context.localize('datetime.three_hours_ago')
        if use_yesterday and dt.date() == yesterday.date():
            return ' '.join((context.localize('datetime.yesterday_at'),
                             context.format_time(dt)))
        if dt.date() == yyesterday.date():
            return context.localize('datetime.two_days_ago')
        if 5400 <= seconds < 86400:
            return ' '.join((context.localize('datetime.today_at'),
                             context.format_time(dt)))
        if 86400 <= seconds < 172800:
            return ' '.join((context.localize('datetime.yesterday_at'),
                             context.format_time(dt)))
    else:
        seconds *= -1
        if seconds < 60:
            return context.localize('datetime.airing_now')
        if 60 <= seconds < 120:
            return context.localize('datetime.in_a_minute')
        if 120 <= seconds < 3600:
            return context.localize('datetime.airing_soon')
        if 3600 <= seconds < 7200:
            return context.localize('datetime.in_over_an_hour')
        if 7200 <= seconds < 10800:
            return context.localize('datetime.in_over_two_hours')
        if dt.date() == today:
            return ' '.join((context.localize('datetime.airing_today_at'),
                             context.format_time(dt)))
        if dt.date() == tomorrow:
            return ' '.join((context.localize('datetime.tomorrow_at'),
                             context.format_time(dt)))

    return ' '.join((context.format_date_short(dt), context.format_time(dt)))


def strptime(datetime_str, fmt=None):
    if fmt is None:
        fmt = '%Y-%m-%d%H%M%S'

    if ' ' in datetime_str:
        date_part, time_part = datetime_str.split(' ')
    elif 'T' in datetime_str:
        date_part, time_part = datetime_str.split('T')
    else:
        date_part = None
        time_part = datetime_str

    if ':' in time_part:
        time_part = time_part.replace(':', '')

    if '+' in time_part:
        time_part, offset, timezone_part = time_part.partition('+')
    elif '-' in time_part:
        time_part, offset, timezone_part = time_part.partition('+')
    else:
        offset = timezone_part = ''

    if timezone and timezone_part and offset:
        fmt = fmt.replace('%S', '%S%z')
    else:
        fmt = fmt.replace('%S%z', '%S')

    if '.' in time_part:
        fmt = fmt.replace('%S', '%S.%f')
    else:
        fmt = fmt.replace('%S.%f', '%S')

    if timezone and timezone_part and offset:
        time_part = offset.join((time_part, timezone_part))
    datetime_str = ''.join((date_part, time_part)) if date_part else time_part

    try:
        return datetime.strptime(datetime_str, fmt)
    except TypeError:
        log_error('Python strptime bug workaround.\n'
                  'Refer to https://github.com/python/cpython/issues/71587')

        if '_strptime' not in modules:
            modules['_strptime'] = import_module('_strptime')
        _strptime = modules['_strptime']

        if timezone:
            return _strptime._strptime_datetime(datetime, datetime_str, fmt)
        return datetime(*(_strptime._strptime(datetime_str, fmt)[0][0:6]))


def since_epoch(dt_object=None):
    if dt_object is None:
        dt_object = now(tz=timezone.utc) if timezone else datetime.utcnow()
    return (dt_object - __INTERNAL_CONSTANTS__['epoch_dt']).total_seconds()


def yt_datetime_offset(**kwargs):
    if timezone:
        _now = now(tz=timezone.utc)
    else:
        _now = datetime.utcnow()

    return (_now - timedelta(**kwargs)).strftime('%Y-%m-%dT%H:%M:%SZ')
