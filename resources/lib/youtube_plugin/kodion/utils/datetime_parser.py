# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import re
import time
from datetime import date, datetime, time as dt_time, timedelta

from ..exceptions import KodionException


__RE_MATCH_TIME_ONLY__ = re.compile(r'^(?P<hour>[0-9]{2})(:?(?P<minute>[0-9]{2})(:?(?P<second>[0-9]{2}))?)?$')
__RE_MATCH_DATE_ONLY__ = re.compile(r'^(?P<year>[0-9]{4})[-/.]?(?P<month>[0-9]{2})[-/.]?(?P<day>[0-9]{2})$')
__RE_MATCH_DATETIME__ = re.compile(r'^(?P<year>[0-9]{4})[-/.]?(?P<month>[0-9]{2})[-/.]?(?P<day>[0-9]{2})["T ](?P<hour>[0-9]{2}):?(?P<minute>[0-9]{2}):?(?P<second>[0-9]{2})')
__RE_MATCH_PERIOD__ = re.compile(r'P((?P<years>\d+)Y)?((?P<months>\d+)M)?((?P<days>\d+)D)?(T((?P<hours>\d+)H)?((?P<minutes>\d+)M)?((?P<seconds>\d+)S)?)?')
__RE_MATCH_ABBREVIATED__ = re.compile(r'(\w+), (?P<day>\d+) (?P<month>\w+) (?P<year>\d+) (?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+)')

__LOCAL_OFFSET__ = datetime.now() - datetime.utcnow()

__EPOCH_DT__ = datetime.fromtimestamp(0)


def parse(datetime_string, as_utc=True):
    offset = 0 if as_utc else None

    def _to_int(value):
        if value is None:
            return 0
        return int(value)

    # match time only '00:45:10'
    time_only_match = __RE_MATCH_TIME_ONLY__.match(datetime_string)
    if time_only_match:
        return utc_to_local(
            dt=datetime.combine(
                date.today(),
                dt_time(hour=_to_int(time_only_match.group('hour')),
                        minute=_to_int(time_only_match.group('minute')),
                        second=_to_int(time_only_match.group('second')))
            ),
            offset=offset
        ).time()

    # match date only '2014-11-08'
    date_only_match = __RE_MATCH_DATE_ONLY__.match(datetime_string)
    if date_only_match:
        return utc_to_local(
            dt=datetime(_to_int(date_only_match.group('year')),
                        _to_int(date_only_match.group('month')),
                        _to_int(date_only_match.group('day'))),
            offset=offset
        )

    # full date time
    date_time_match = __RE_MATCH_DATETIME__.match(datetime_string)
    if date_time_match:
        return utc_to_local(
            dt=datetime(_to_int(date_time_match.group('year')),
                        _to_int(date_time_match.group('month')),
                        _to_int(date_time_match.group('day')),
                        _to_int(date_time_match.group('hour')),
                        _to_int(date_time_match.group('minute')),
                        _to_int(date_time_match.group('second'))),
            offset=offset
        )

    # period - at the moment we support only hours, minutes and seconds
    # e.g. videos and audio
    period_match = __RE_MATCH_PERIOD__.match(datetime_string)
    if period_match:
        return timedelta(hours=_to_int(period_match.group('hours')),
                         minutes=_to_int(period_match.group('minutes')),
                         seconds=_to_int(period_match.group('seconds')))

    # abbreviated match
    abbreviated_match = __RE_MATCH_ABBREVIATED__.match(datetime_string)
    if abbreviated_match:
        month = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'June': 6,
                 'Jun': 6, 'July': 7, 'Jul': 7, 'Aug': 8, 'Sept': 9, 'Sep': 9,
                 'Oct': 10, 'Nov': 11, 'Dec': 12}
        return utc_to_local(
            dt=datetime(year=_to_int(abbreviated_match.group('year')),
                        month=month[abbreviated_match.group('month')],
                        day=_to_int(abbreviated_match.group('day')),
                        hour=_to_int(abbreviated_match.group('hour')),
                        minute=_to_int(abbreviated_match.group('minute')),
                        second=_to_int(abbreviated_match.group('second'))),
            offset=offset
        )

    raise KodionException('Could not parse |{datetime}| as ISO 8601'
                          .format(datetime=datetime_string))


def get_scheduled_start(context, datetime_object, local=True):
    now = datetime.now() if local else datetime.utcnow()
    if datetime_object.date() == now.date():
        return '@ {start_time}'.format(
            start_time=context.format_time(datetime_object.time())
        )
    return '@ {start_date}, {start_time}'.format(
        start_time=context.format_time(datetime_object.time()),
        start_date=context.format_date_short(datetime_object.date())
    )


def utc_to_local(dt, offset=None):
    offset = __LOCAL_OFFSET__ if offset is None else timedelta(hours=offset)
    return dt + offset


def datetime_to_since(context, dt):
    now = datetime.now()
    diff = now - dt
    yesterday = now - timedelta(days=1)
    yyesterday = now - timedelta(days=2)
    use_yesterday = (now - yesterday).total_seconds() > 10800
    today = now.date()
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


def since_epoch(dt_object):
    return (dt_object - __EPOCH_DT__).total_seconds()
