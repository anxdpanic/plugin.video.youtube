import threading

from ..utils import get_http_server, is_httpd_live

import xbmc
import xbmcaddon


class YouTubeMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        _addon = xbmcaddon.Addon('plugin.video.youtube')
        self._whitelist = _addon.getSetting('kodion.http.ip.whitelist')
        self._httpd_port = int(_addon.getSetting('kodion.mpd.proxy.port'))
        self._old_httpd_port = self._httpd_port
        self._use_httpd = (_addon.getSetting('kodion.mpd.proxy') == 'true' and _addon.getSetting('kodion.video.quality.mpd') == 'true') or \
                          (_addon.getSetting('youtube.api.config.page') == 'true')
        self._use_dash = _addon.getSetting('kodion.video.support.mpd.addon') == 'true'
        self._httpd_address = _addon.getSetting('kodion.http.listen')
        self._old_httpd_address = self._httpd_address
        self.httpd = None
        self.httpd_thread = None
        if self.use_httpd():
            self.start_httpd()

    def onSettingsChanged(self):
        _addon = xbmcaddon.Addon('plugin.video.youtube')
        _use_httpd = (_addon.getSetting('kodion.mpd.proxy') == 'true' and _addon.getSetting('kodion.video.quality.mpd') == 'true') or \
                     (_addon.getSetting('youtube.api.config.page') == 'true')
        _httpd_port = int(_addon.getSetting('kodion.mpd.proxy.port'))
        _whitelist = _addon.getSetting('kodion.http.ip.whitelist')
        _use_dash = _addon.getSetting('kodion.video.support.mpd.addon') == 'true'
        _httpd_address = _addon.getSetting('kodion.http.listen')
        whitelist_changed = _whitelist != self._whitelist
        port_changed = self._httpd_port != _httpd_port
        address_changed = self._httpd_address != _httpd_address

        if not _use_dash and self._use_dash:
            _addon.setSetting('kodion.video.support.mpd.addon', 'true')

        if _whitelist != self._whitelist:
            self._whitelist = _whitelist

        if self._use_httpd != _use_httpd:
            self._use_httpd = _use_httpd

        if self._httpd_port != _httpd_port:
            self._old_httpd_port = self._httpd_port
            self._httpd_port = _httpd_port

        if self._httpd_address != _httpd_address:
            self._old_httpd_address = self._httpd_address
            self._httpd_address = _httpd_address

        if self.use_httpd() and not self.httpd:
            self.start_httpd()
        elif self.use_httpd() and (port_changed or whitelist_changed or address_changed):
            if self.httpd:
                self.restart_httpd()
            else:
                self.start_httpd()
        elif not self.use_httpd() and self.httpd:
            self.shutdown_httpd()

    def use_httpd(self):
        return self._use_httpd

    def httpd_port(self):
        return int(self._httpd_port)

    def httpd_address(self):
        return self._httpd_address

    def old_httpd_address(self):
        return self._old_httpd_address

    def old_httpd_port(self):
        return int(self._old_httpd_port)

    def httpd_port_sync(self):
        self._old_httpd_port = self._httpd_port

    def start_httpd(self):
        if not self.httpd:
            xbmc.log('[plugin.video.youtube] HTTPServer: Starting |{ip}:{port}|'.format(ip=self.httpd_address(), port=str(self.httpd_port())), xbmc.LOGDEBUG)
            self.httpd_port_sync()
            self.httpd = get_http_server(address=self.httpd_address(), port=self.httpd_port())
            if self.httpd:
                self.httpd_thread = threading.Thread(target=self.httpd.serve_forever)
                self.httpd_thread.daemon = True
                self.httpd_thread.start()
                sock_name = self.httpd.socket.getsockname()
                xbmc.log('[plugin.video.youtube] HTTPServer: Serving on |{ip}:{port}|'.format(ip=str(sock_name[0]), port=str(sock_name[1])), xbmc.LOGDEBUG)

    def shutdown_httpd(self):
        if self.httpd:
            xbmc.log('[plugin.video.youtube] HTTPServer: Shutting down |{ip}:{port}|'.format(ip=self.old_httpd_address(), port=str(self.old_httpd_port())), xbmc.LOGDEBUG)
            self.httpd_port_sync()
            self.httpd.shutdown()
            self.httpd.socket.close()
            self.httpd_thread.join()
            self.httpd_thread = None
            self.httpd = None

    def restart_httpd(self):
        xbmc.log('[plugin.video.youtube] HTTPServer: Restarting... |{old_ip}:{old_port}| -> |{ip}:{port}|'
                 .format(old_ip=self.old_httpd_address(), old_port=str(self.old_httpd_port()), ip=self.httpd_address(), port=str(self.httpd_port())), xbmc.LOGDEBUG)
        self.shutdown_httpd()
        self.start_httpd()

    def ping_httpd(self):
        return is_httpd_live(port=self.httpd_port())
