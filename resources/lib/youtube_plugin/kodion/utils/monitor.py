import xbmc
import xbmcaddon

_addon = xbmcaddon.Addon('plugin.video.youtube')


class YouTubeMonitor(xbmc.Monitor):

    def __init__(self, *args, **kwargs):
        self._proxy_port = int(_addon.getSetting('kodion.mpd.proxy.port'))
        self._old_proxy_port = self._proxy_port
        self._use_proxy = _addon.getSetting('kodion.mpd.proxy') == 'true'
        xbmc.Monitor.__init__(self)

    def onSettingsChanged(self):
        _use_proxy = _addon.getSetting('kodion.mpd.proxy') == 'true'
        _proxy_port = int(_addon.getSetting('kodion.mpd.proxy.port'))

        if self._proxy_port != _proxy_port:
            self._old_proxy_port = self._proxy_port
            self._proxy_port = _proxy_port

        self._use_proxy = _use_proxy

    def use_proxy(self):
        return self._use_proxy

    def proxy_port(self):
        return int(self._proxy_port)

    def proxy_port_changed(self):
        changed = self._old_proxy_port != self._proxy_port
        self._old_proxy_port = self._proxy_port
        return changed
