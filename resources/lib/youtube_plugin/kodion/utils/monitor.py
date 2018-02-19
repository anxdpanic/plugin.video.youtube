import threading

from hashlib import md5

from ..utils import get_http_server, is_httpd_live
from ...kodion.json_store import APIKeyStore
from ... import key_sets

import xbmc
import xbmcaddon
import xbmcgui


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
        self.api_keys_update()

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

        current_switch = 'own' if self.has_own_api_keys(_addon) else _addon.getSetting('youtube.api.key.switch')
        updated_hash = self.api_keys_changed(_addon, current_switch)
        if updated_hash:
            self.api_keys_update()

    def onNotification(self, sender, method, data):
        if sender == 'plugin.video.youtube':
            if method.endswith('check_api_keys'):
                xbmc.log('[plugin.video.youtube] onNotification: Checking API keys', xbmc.LOGDEBUG)
                self.api_keys_update()

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

    def api_keys_update(self):
        _addon = xbmcaddon.Addon('plugin.video.youtube')
        api_jstore = APIKeyStore()
        json_api = api_jstore.load()

        j_key = json_api['keys']['personal'].get('api_key', '')
        j_id = json_api['keys']['personal'].get('client_id', '')
        j_secret = json_api['keys']['personal'].get('client_secret', '')

        own_key = _addon.getSetting('youtube.api.key')
        own_id = _addon.getSetting('youtube.api.id')
        own_secret = _addon.getSetting('youtube.api.secret')

        stripped_key = ''.join(own_key.split())
        stripped_id = ''.join(own_id.replace('.apps.googleusercontent.com', '').split())
        stripped_secret = ''.join(own_secret.split())

        if own_key != stripped_key:
            if stripped_key not in own_key:
                xbmc.log('[plugin.video.youtube] Personal API setting: |Key| Skipped: potentially mangled by stripping', xbmc.LOGDEBUG)
            else:
                xbmc.log('[plugin.video.youtube] Personal API setting: |Key| had whitespace removed', xbmc.LOGDEBUG)
                own_key = stripped_key
                _addon.setSetting('youtube.api.key', own_key)

        if own_id != stripped_id:
            if stripped_id not in own_id:
                xbmc.log('[plugin.video.youtube] Personal API setting: |Id| Skipped: potentially mangled by stripping', xbmc.LOGDEBUG)
            else:
                googleusercontent = ''
                if '.apps.googleusercontent.com' in own_id:
                    googleusercontent = ' and .apps.googleusercontent.com'
                xbmc.log('[plugin.video.youtube] Personal API setting: |Id| had whitespace%s removed' % googleusercontent, xbmc.LOGDEBUG)
                own_id = stripped_id
                _addon.setSetting('youtube.api.id', own_id)

        if own_secret != stripped_secret:
            if stripped_secret not in own_secret:
                xbmc.log('[plugin.video.youtube] Personal API setting: |Secret| Skipped: potentially mangled by stripping', xbmc.LOGDEBUG)
            else:
                xbmc.log('[plugin.video.youtube] Personal API setting: |Secret| had whitespace removed', xbmc.LOGDEBUG)
                own_secret = stripped_secret
                _addon.setSetting('youtube.api.secret', own_secret)

        key_sets['own'] = {'key': own_key, 'id': own_id, 'secret': own_secret}

        if (j_key and j_id and j_secret) and (not own_id or not own_key or not own_secret):
            do_key_load = xbmcgui.Dialog().yesno(heading=_addon.getAddonInfo('name'), line1=_addon.getLocalizedString(30639))
            if do_key_load:
                own_key = j_key
                _addon.setSetting('youtube.api.key', own_key)
                own_id = j_id
                _addon.setSetting('youtube.api.id', own_id)
                own_secret = j_secret
                _addon.setSetting('youtube.api.secret', own_secret)
                _addon.setSetting('youtube.api.enable', 'true')
                key_sets.update({'own': {'key': own_key, 'id': own_id, 'secret': own_secret}})
                _addon.setSetting('youtube.api.last.hash', self.get_key_set_hash('own'))
                json_api['keys']['personal'] = {'api_key': own_key, 'client_id': own_id, 'client_secret': own_secret}
                api_jstore.save(json_api)

        if (j_key != own_key) or (j_id != own_id) or (j_secret != own_secret):
            json_api['keys']['personal'] = {'api_key': own_key, 'client_id': own_id, 'client_secret': own_secret}
            api_jstore.save(json_api)

        current_switch = 'own' if self.has_own_api_keys(_addon) else _addon.getSetting('youtube.api.key.switch')
        updated_hash = self.api_keys_changed(_addon, current_switch)
        if updated_hash:
            xbmc.log('[plugin.video.youtube] Switching API key set to %s' % current_switch, xbmc.LOGWARNING)
            _addon.setSetting('youtube.api.last.hash', updated_hash)
            xbmc.log('[plugin.video.youtube] API key set changed: Signing out', xbmc.LOGDEBUG)
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.youtube/sign/out/?confirmed=true)')
        else:
            xbmc.log('[plugin.video.youtube] Using API key set: %s' % current_switch, xbmc.LOGDEBUG)

    def api_keys_changed(self, addon, switch):
        if not switch or (switch == 'own' and not self.has_own_api_keys(addon)):
            switch = '1'
        last_set_hash = addon.getSetting('youtube.api.last.hash')
        current_set_hash = self.get_key_set_hash(switch)
        if last_set_hash != current_set_hash:
            return current_set_hash
        else:
            return None

    @staticmethod
    def has_own_api_keys(addon):
        own_key = addon.getSetting('youtube.api.key')
        own_id = addon.getSetting('youtube.api.id')
        own_secret = addon.getSetting('youtube.api.secret')
        return False if not own_key or \
                        not own_id or \
                        not own_secret or \
                        not addon.getSetting('youtube.api.enable') == 'true' else True

    @staticmethod
    def get_key_set_hash(value):
        if value == 'own':
            api_key = key_sets[value]['key'].encode('utf-8')
            client_id = key_sets[value]['id'].encode('utf-8')
            client_secret = key_sets[value]['secret'].encode('utf-8')
        else:
            api_key = key_sets['provided'][value]['key'].encode('utf-8')
            client_id = key_sets['provided'][value]['id'].encode('utf-8')
            client_secret = key_sets['provided'][value]['secret'].encode('utf-8')

        m = md5()
        m.update(api_key)
        m.update(client_id)
        m.update(client_secret)

        return m.hexdigest()
