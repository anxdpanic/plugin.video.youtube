__author__ = 'bromix'

import re
import time as _time
from datetime import date, datetime, timedelta, time

from ..exceptions import KodionException

__RE_MATCH_TIME_ONLY__ = re.compile(r'^(?P<hour>[0-9]{2})([:]?(?P<minute>[0-9]{2})([:]?(?P<second>[0-9]{2}))?)?$')
__RE_MATCH_DATE_ONLY__ = re.compile(r'^(?P<year>[0-9]{4})[-]?(?P<month>[0-9]{2})[-]?(?P<day>[0-9]{2})$')
__RE_MATCH_DATETIME__ = re.compile(r'^(?P<year>[0-9]{4})[-]?(?P<month>[0-9]{2})[-]?(?P<day>[0-9]{2})[" ""T"](?P<hour>[0-9]{2})[:]?(?P<minute>[0-9]{2})[:]?(?P<second>[0-9]{2})')
__RE_MATCH_PERIOD__ = re.compile(r'P((?P<years>\d+)Y)?((?P<months>\d+)M)?((?P<days>\d+)D)?(T((?P<hours>\d+)H)?((?P<minutes>\d+)M)?((?P<seconds>\d+)S)?)?')
__RE_MATCH_ABBREVIATED__ = re.compile(r'(\w+), (?P<day>\d+) (?P<month>\w+) (?P<year>\d+) (?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+)')


def parse(datetime_string):
    def _to_int(value):
        if value is None:
            return 0
        return int(value)

    # match time only '00:45:10'
    time_only_match = __RE_MATCH_TIME_ONLY__.match(datetime_string)
    if time_only_match:
        return time(hour=_to_int(time_only_match.group('hour')),
                    minute=_to_int(time_only_match.group('minute')),
                    second=_to_int(time_only_match.group('second')))

    # match date only '2014-11-08'
    date_only_match = __RE_MATCH_DATE_ONLY__.match(datetime_string)
    if date_only_match:
        return date(_to_int(date_only_match.group('year')),
                    _to_int(date_only_match.group('month')),
                    _to_int(date_only_match.group('day')))

    # full date time
    date_time_match = __RE_MATCH_DATETIME__.match(datetime_string)
    if date_time_match:
        return datetime(_to_int(date_time_match.group('year')),
                        _to_int(date_time_match.group('month')),
                        _to_int(date_time_match.group('day')),
                        _to_int(date_time_match.group('hour')),
                        _to_int(date_time_match.group('minute')),
                        _to_int(date_time_match.group('second')))

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
        return datetime(year=_to_int(abbreviated_match.group('year')),
                        month=month[abbreviated_match.group('month')],
                        day=_to_int(abbreviated_match.group('day')),
                        hour=_to_int(abbreviated_match.group('hour')),
                        minute=_to_int(abbreviated_match.group('minute')),
                        second=_to_int(abbreviated_match.group('second')))

    raise KodionException("Could not parse iso 8601 timestamp '%s'" % datetime_string)


def get_scheduled_start(datetime_object):
    start_hour = '{:02d}'.format(datetime_object.hour)
    start_minute = '{:<02d}'.format(datetime_object.minute)
    start_time = start_hour + ':' + start_minute
    start_date = str(datetime_object.date())
    now = datetime.now()
    start_date = start_date.replace(str(now.year), '').lstrip('-')
    start_date = start_date.replace('{:02d}'.format(now.month) + '-' + '{:02d}'.format(now.day), '')
    return start_date, start_time


local_timezone_offset = None


def utc_to_local(dt):
    global local_timezone_offset
    if local_timezone_offset is None:
        now = _time.time()
        local_timezone_offset = datetime.fromtimestamp(now) - datetime.utcfromtimestamp(now)

    return dt + local_timezone_offset


def datetime_to_since(dt, context):
    now = datetime.now()
    diff = now - dt
    yesterday = now - timedelta(days=1)
    yyesterday = now - timedelta(days=2)
    use_yesterday = (now - yesterday).total_seconds() > 10800
    seconds = diff.total_seconds()

    if seconds > 0:
        if seconds < 60:
            return context.localize('30676')
        elif 60 <= seconds < 120:
            return context.localize('30677')
        elif 120 <= seconds < 3600:
            return context.localize('30678')
        elif 3600 <= seconds < 7200:
            return context.localize('30679')
        elif 7200 <= seconds < 10800:
            return context.localize('30680')
        elif 10800 <= seconds < 14400:
            return context.localize('30681')
        elif use_yesterday and dt.date() == yesterday.date():
            return u' '.join([context.localize('30682'), context.format_time(dt)])
        elif dt.date() == yyesterday.date():
            return context.localize('30683')
        elif 5400 <= seconds < 86400:
            return u' '.join([context.localize('30684'), context.format_time(dt)])
        elif 86400 <= seconds < 172800:
            return u' '.join([context.localize('30682'), context.format_time(dt)])
    return u' '.join([context.format_date_short(dt), context.format_time(dt)])


def strptime(s, fmt="%Y-%m-%dT%H:%M:%S.%fZ"):
    try:
        return datetime.strptime(s, fmt)
    except TypeError:
        # see https://forum.kodi.tv/showthread.php?tid=112916
        return datetime(*_time.strptime(s, fmt)[:6])
