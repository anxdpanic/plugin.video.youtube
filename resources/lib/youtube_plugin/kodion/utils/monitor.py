import threading

from ..utils import get_proxy_server, is_proxy_live

import xbmc
import xbmcaddon

_addon = xbmcaddon.Addon('plugin.video.youtube')


class YouTubeMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        self._proxy_port = int(_addon.getSetting('kodion.mpd.proxy.port'))
        self._old_proxy_port = self._proxy_port
        self._use_proxy = _addon.getSetting('kodion.mpd.proxy') == 'true'
        self.dash_proxy = None
        self.proxy_thread = None
        if self.use_proxy():
            self.start_proxy()
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        _use_proxy = _addon.getSetting('kodion.mpd.proxy') == 'true'
        _proxy_port = int(_addon.getSetting('kodion.mpd.proxy.port'))

        if self._use_proxy != _use_proxy:
            self._use_proxy = _use_proxy

        if self._proxy_port != _proxy_port:
            self._old_proxy_port = self._proxy_port
            self._proxy_port = _proxy_port

        if self.use_proxy() and not self.dash_proxy:
            self.start_proxy()
        elif self.use_proxy() and (self.old_proxy_port() != self.proxy_port()):
            if self.dash_proxy:
                self.restart_proxy()
            elif not self.dash_proxy:
                self.start_proxy()
        elif not self.use_proxy() and self.dash_proxy:
            self.shutdown_proxy()

    def use_proxy(self):
        return self._use_proxy

    def proxy_port(self):
        return int(self._proxy_port)

    def old_proxy_port(self):
        return int(self._old_proxy_port)

    def proxy_port_sync(self):
        self._old_proxy_port = self._proxy_port

    def start_proxy(self):
        if not self.dash_proxy:
            xbmc.log('[plugin.video.youtube] DashProxy: Starting |{port}|'.format(port=str(self.proxy_port())), xbmc.LOGDEBUG)
            self.proxy_port_sync()
            self.dash_proxy = get_proxy_server(port=self.proxy_port())
            if self.dash_proxy:
                self.proxy_thread = threading.Thread(target=self.dash_proxy.serve_forever)
                self.proxy_thread.daemon = True
                self.proxy_thread.start()

    def shutdown_proxy(self):
        if self.dash_proxy:
            xbmc.log('[plugin.video.youtube] DashProxy: Shutting down |{port}|'.format(port=str(self.old_proxy_port())), xbmc.LOGDEBUG)
            self.proxy_port_sync()
            self.dash_proxy.shutdown()
            self.dash_proxy.socket.close()
            self.proxy_thread.join()
            self.proxy_thread = None
            self.dash_proxy = None

    def restart_proxy(self):
        xbmc.log('[plugin.video.youtube] DashProxy: Restarting... |{old_port}| -> |{port}|'
                 .format(old_port=str(self.old_proxy_port()), port=str(self.proxy_port())), xbmc.LOGDEBUG)
        self.shutdown_proxy()
        self.start_proxy()

    def ping_proxy(self):
        return is_proxy_live(port=self.proxy_port())
