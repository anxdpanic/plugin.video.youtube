__author__ = 'bromix'

from datetime import datetime
import time

from youtube_plugin.kodion.impl import Context
from youtube_plugin.kodion.constants import setting
from youtube_plugin.kodion.utils import Monitor

context = Context(plugin_id='plugin.video.youtube')

context.log_debug('YouTube settings startup initialization...')
version = context.get_system_version().get_version()
settings = context.get_settings()

mpd_addon = False

if version >= (17, 0):
    mpd_addon = True
else:
    settings.set_bool(setting.USE_DASH, False)

settings.set_bool(setting.DASH_SUPPORT_ADDON, mpd_addon)
context.log_notice('Startup: detected {0}, DASH_SUPPORT_ADDON = {1}'
                   .format(context.get_system_version(), mpd_addon))


def strptime(stamp, stamp_fmt):
    import _strptime
    try:
        time.strptime('01 01 2012', '%d %m %Y')  # dummy call
    except:
        pass
    return time.strptime(stamp, stamp_fmt)


def get_stamp_diff(current_stamp):
    stamp_format = '%Y-%m-%d %H:%M:%S.%f'
    current_datetime = datetime.now()
    if not current_stamp: return 86400  # 24 hrs
    try:
        stamp_datetime = datetime(*(strptime(current_stamp, stamp_format)[0:6]))
    except ValueError:  # current_stamp has no microseconds
        stamp_format = '%Y-%m-%d %H:%M:%S'
        stamp_datetime = datetime(*(strptime(current_stamp, stamp_format)[0:6]))

    time_delta = current_datetime - stamp_datetime
    total_seconds = 0
    if time_delta:
        total_seconds = ((time_delta.seconds + time_delta.days * 24 * 3600) * 10 ** 6) / 10 ** 6
    return total_seconds


sleep_time = 10
ping_delay_time = 60
ping_timestamp = None
first_run = True

if mpd_addon:
    monitor = Monitor()
    while not monitor.abortRequested():

        ping_diff = get_stamp_diff(ping_timestamp)

        if (ping_timestamp is None) or (ping_diff >= ping_delay_time):
            ping_timestamp = str(datetime.now())

            if monitor.dash_proxy and not monitor.ping_proxy():
                monitor.restart_proxy()

        if first_run:
            first_run = False

        if monitor.waitForAbort(sleep_time):
            if monitor.dash_proxy:
                monitor.shutdown_proxy()
            break
