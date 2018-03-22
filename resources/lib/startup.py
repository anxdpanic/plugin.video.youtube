__author__ = 'bromix'

from datetime import datetime
import time

from youtube_plugin.kodion.impl import Context
from youtube_plugin.kodion.utils import YouTubeMonitor, YouTubePlayer

context = Context(plugin_id='plugin.video.youtube')

context.log_debug('YouTube settings startup initialization...')
version = context.get_system_version().get_version()
settings = context.get_settings()


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
        total_seconds = ((time_delta.seconds + time_delta.days * 24 * 3600) * 10 ** 6) // (10 ** 6)
    return total_seconds


sleep_time = 10
ping_delay_time = 60
ping_timestamp = None
first_run = True

player = YouTubePlayer(context=context)
monitor = YouTubeMonitor()

monitor.remove_temp_dir()

while not monitor.abortRequested():

    ping_diff = get_stamp_diff(ping_timestamp)

    if (ping_timestamp is None) or (ping_diff >= ping_delay_time):
        ping_timestamp = str(datetime.now())

        if monitor.httpd and not monitor.ping_httpd():
            monitor.restart_httpd()

    if first_run:
        first_run = False

    if monitor.waitForAbort(sleep_time):
        if monitor.httpd:
            monitor.shutdown_httpd()
        break
