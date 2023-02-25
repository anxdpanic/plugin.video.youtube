# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import re
import time
from datetime import date, datetime, timedelta
from datetime import time as dt_time

from ..exceptions import KodionException

__RE_MATCH_TIME_ONLY__ = re.compile(r'^(?P<hour>[0-9]{2})([:]?(?P<minute>[0-9]{2})([:]?(?P<second>[0-9]{2}))?)?$')
__RE_MATCH_DATE_ONLY__ = re.compile(r'^(?P<year>[0-9]{4})[-]?(?P<month>[0-9]{2})[-]?(?P<day>[0-9]{2})$')
__RE_MATCH_DATETIME__ = re.compile(r'^(?P<year>[0-9]{4})[-]?(?P<month>[0-9]{2})[-]?(?P<day>[0-9]{2})["T ](?P<hour>[0-9]{2})[:]?(?P<minute>[0-9]{2})[:]?(?P<second>[0-9]{2})')
__RE_MATCH_PERIOD__ = re.compile(r'P((?P<years>\d+)Y)?((?P<months>\d+)M)?((?P<days>\d+)D)?(T((?P<hours>\d+)H)?((?P<minutes>\d+)M)?((?P<seconds>\d+)S)?)?')
__RE_MATCH_ABBREVIATED__ = re.compile(r'(\w+), (?P<day>\d+) (?P<month>\w+) (?P<year>\d+) (?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+)')

now = datetime.now


def py2_utf8(text):
    return text


def parse(datetime_string, localize=True):
    _utc_to_local = utc_to_local if localize else lambda x: x

    def _to_int(value):
        if value is None:
            return 0
        return int(value)

    # match time only '00:45:10'
    time_only_match = __RE_MATCH_TIME_ONLY__.match(datetime_string)
    if time_only_match:
        return _utc_to_local(datetime.combine(date.today(),
                                              dt_time(hour=_to_int(time_only_match.group('hour')),
                                                      minute=_to_int(time_only_match.group('minute')),
                                                      second=_to_int(time_only_match.group('second'))))
                             ).time()

    # match date only '2014-11-08'
    date_only_match = __RE_MATCH_DATE_ONLY__.match(datetime_string)
    if date_only_match:
        return _utc_to_local(date(_to_int(date_only_match.group('year')),
                                  _to_int(date_only_match.group('month')),
                                  _to_int(date_only_match.group('day'))))

    # full date time
    date_time_match = __RE_MATCH_DATETIME__.match(datetime_string)
    if date_time_match:
        return _utc_to_local(datetime(_to_int(date_time_match.group('year')),
                                      _to_int(date_time_match.group('month')),
                                      _to_int(date_time_match.group('day')),
                                      _to_int(date_time_match.group('hour')),
                                      _to_int(date_time_match.group('minute')),
                                      _to_int(date_time_match.group('second'))))

    # period - at the moment we support only hours, minutes and seconds (e.g. videos and audio)
    period_match = __RE_MATCH_PERIOD__.match(datetime_string)
    if period_match:
        return timedelta(hours=_to_int(period_match.group('hours')),
                         minutes=_to_int(period_match.group('minutes')),
                         seconds=_to_int(period_match.group('seconds')))

    # abbreviated match
    abbreviated_match = __RE_MATCH_ABBREVIATED__.match(datetime_string)
    if abbreviated_match:
        month = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'June': 6, 'Jun': 6, 'July': 7, 'Jul': 7, 'Aug': 8,
                 'Sept': 9, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
        return _utc_to_local(datetime(year=_to_int(abbreviated_match.group('year')),
                                      month=month[abbreviated_match.group('month')],
                                      day=_to_int(abbreviated_match.group('day')),
                                      hour=_to_int(abbreviated_match.group('hour')),
                                      minute=_to_int(abbreviated_match.group('minute')),
                                      second=_to_int(abbreviated_match.group('second'))))

    raise KodionException("Could not parse iso 8601 timestamp '%s'" % datetime_string)


def get_scheduled_start(datetime_object, localize=True):
    start_hour = '{:02d}'.format(datetime_object.hour)
    start_minute = '{:<02d}'.format(datetime_object.minute)
    start_time = ':'.join([start_hour, start_minute])
    start_date = str(datetime_object.date())
    if localize:
        now = datetime.now()
    else:
        now = datetime.utcnow()
    start_date = start_date.replace(str(now.year), '').lstrip('-')
    start_date = start_date.replace('-'.join(['{:02d}'.format(now.month), '{:02d}'.format(now.day)]), '')
    return start_date, start_time


local_timezone_offset = None


def utc_to_local(dt):
    global local_timezone_offset
    if local_timezone_offset is None:
        now = time.time()
        local_timezone_offset = datetime.fromtimestamp(now) - datetime.utcfromtimestamp(now)

    return dt + local_timezone_offset


def datetime_to_since(context, dt):
    now = datetime.now()
    diff = now - dt
    yesterday = now - timedelta(days=1)
    yyesterday = now - timedelta(days=2)
    use_yesterday = total_seconds(now - yesterday) > 10800
    today = now.date()
    tomorrow = today + timedelta(days=1)
    seconds = total_seconds(diff)

    if seconds > 0:
        if seconds < 60:
            return py2_utf8(context.localize('30676'))
        elif 60 <= seconds < 120:
            return py2_utf8(context.localize('30677'))
        elif 120 <= seconds < 3600:
            return py2_utf8(context.localize('30678'))
        elif 3600 <= seconds < 7200:
            return py2_utf8(context.localize('30679'))
        elif 7200 <= seconds < 10800:
            return py2_utf8(context.localize('30680'))
        elif 10800 <= seconds < 14400:
            return py2_utf8(context.localize('30681'))
        elif use_yesterday and dt.date() == yesterday.date():
            return ' '.join([py2_utf8(context.localize('30682')), context.format_time(dt)])
        elif dt.date() == yyesterday.date():
            return py2_utf8(context.localize('30683'))
        elif 5400 <= seconds < 86400:
            return ' '.join([py2_utf8(context.localize('30684')), context.format_time(dt)])
        elif 86400 <= seconds < 172800:
            return ' '.join([py2_utf8(context.localize('30682')), context.format_time(dt)])
    else:
        seconds *= -1
        if seconds < 60:
            return py2_utf8(context.localize('30691'))
        elif 60 <= seconds < 120:
            return py2_utf8(context.localize('30692'))
        elif 120 <= seconds < 3600:
            return py2_utf8(context.localize('30693'))
        elif 3600 <= seconds < 7200:
            return py2_utf8(context.localize('30694'))
        elif 7200 <= seconds < 10800:
            return py2_utf8(context.localize('30695'))
        elif dt.date() == today:
            return ' '.join([py2_utf8(context.localize('30696')), context.format_time(dt)])
        elif dt.date() == tomorrow:
            return ' '.join([py2_utf8(context.localize('30697')), context.format_time(dt)])

    return ' '.join([context.format_date_short(dt), context.format_time(dt)])


def strptime(s, fmt='%Y-%m-%dT%H:%M:%S.%fZ'):
    # noinspection PyUnresolvedReferences

    ms_precision = '.' in s[-5:-1]
    if fmt == '%Y-%m-%dT%H:%M:%S.%fZ' and not ms_precision:
        fmt = '%Y-%m-%dT%H:%M:%SZ'
    elif fmt == '%Y-%m-%dT%H:%M:%SZ' and ms_precision:
        fmt = '%Y-%m-%dT%H:%M:%S.%fZ'

    import _strptime
    try:
        time.strptime('01 01 2012', '%d %m %Y')  # dummy call
    except:
        pass
    return datetime(*time.strptime(s, fmt)[:6])


def total_seconds(t_delta):  # required for python 2.6 which doesn't have datetime.timedelta.total_seconds
    return 24 * 60 * 60 * t_delta.days + t_delta.seconds + (t_delta.microseconds // 1000000.)


def since_epoch(dt_object):
    return total_seconds(dt_object - datetime(1970, 1, 1))
