__author__ = 'bromix'

from datetime import datetime
import time
import threading

from youtube_plugin.kodion.impl import Context
from youtube_plugin.kodion.constants import setting
from youtube_plugin.kodion.utils import get_proxy_server, is_proxy_live, Monitor

context = Context(plugin_id='plugin.video.youtube')

context.log_debug('YouTube settings startup initialization...')
version = context.get_system_version().get_version()
application = context.get_system_version().get_app_name()
settings = context.get_settings()

mpd_addon = False
mpd_builtin = False

if version >= (17, 0):
    mpd_addon = True
elif version >= (16, 5) and application == 'SPMC':
    mpd_builtin = True
else:
    settings.set_bool(setting.USE_DASH, False)

settings.set_bool(setting.DASH_SUPPORT_BUILTIN, mpd_builtin)
settings.set_bool(setting.DASH_SUPPORT_ADDON, mpd_addon)
context.log_notice('Startup: detected {0}, setting DASH_SUPPORT_BUILTIN = {1}, DASH_SUPPORT_ADDON = {2}'
                   .format(context.get_system_version(), mpd_builtin, mpd_addon))


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


sleep_time = 1
proxy_delay_time = 30
ping_delay_time = 60
proxy_timestamp = None
ping_timestamp = None
first_run = True
dash_proxy = None
proxy_thread = None

if mpd_addon or mpd_builtin:
    monitor = Monitor()
    while not monitor.abortRequested():

        proxy_diff = get_stamp_diff(proxy_timestamp)
        ping_diff = get_stamp_diff(ping_timestamp)

        if (proxy_timestamp is None) or (proxy_diff >= proxy_delay_time):
            proxy_timestamp = str(datetime.now())

            use_proxy = monitor.use_proxy()
            proxy_port = monitor.proxy_port()

            if use_proxy:
                if dash_proxy is None:
                    context.log_debug('DashProxy: Starting |{port}|'.format(port=str(proxy_port)))
                    monitor.proxy_port_sync()
                    dash_proxy = get_proxy_server(port=proxy_port)
                    if dash_proxy:
                        proxy_thread = threading.Thread(target=dash_proxy.serve_forever)
                        proxy_thread.daemon = True
                        proxy_thread.start()
                elif dash_proxy and monitor.proxy_port_changed():
                    context.log_debug('DashProxy: Port changed, restarting... |{old_port}| -> |{port}|'
                                      .format(old_port=str(monitor.old_proxy_port()), port=str(proxy_port)))
                    dash_proxy.shutdown()
                    proxy_thread.join()
                    proxy_thread = None
                    monitor.proxy_port_sync()
                    dash_proxy = get_proxy_server(port=proxy_port)
                    if dash_proxy:
                        proxy_thread = threading.Thread(target=dash_proxy.serve_forever)
                        proxy_thread.daemon = True
                        proxy_thread.start()
            else:
                if dash_proxy is not None:
                    context.log_debug('DashProxy: Shutting down |{port}|'.format(port=str(monitor.old_proxy_port())))
                    monitor.proxy_port_sync()
                    dash_proxy.shutdown()
                    proxy_thread.join()
                    proxy_thread = None
                    dash_proxy = None

        if (ping_timestamp is None) or (ping_diff >= ping_delay_time):
            ping_timestamp = str(datetime.now())

            use_proxy = monitor.use_proxy()
            proxy_port = monitor.proxy_port()

            if dash_proxy:
                if not is_proxy_live(port=proxy_port):
                    context.log_debug('DashProxy: Port changed, restarting... |{old_port}| -> |{port}|'
                                      .format(old_port=str(monitor.old_proxy_port()), port=str(proxy_port)))
                    dash_proxy.shutdown()
                    proxy_thread.join()
                    proxy_thread = None
                    monitor.proxy_port_sync()
                    dash_proxy = get_proxy_server(port=proxy_port)
                    if dash_proxy:
                        proxy_thread = threading.Thread(target=dash_proxy.serve_forever)
                        proxy_thread.daemon = True
                        proxy_thread.start()

        if first_run:
            first_run = False

        if monitor.waitForAbort(sleep_time):
            if dash_proxy is not None:
                dash_proxy.shutdown()
            if proxy_thread is not None:
                proxy_thread.join()
            break
