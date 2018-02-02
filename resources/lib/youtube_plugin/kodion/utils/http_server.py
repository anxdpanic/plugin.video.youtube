from six.moves import BaseHTTPServer
from six.moves.urllib.parse import parse_qs, urlparse
from six.moves import xrange

import os
import requests
import socket

import xbmc
import xbmcaddon
import xbmcgui


class YouTubeRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        addon = xbmcaddon.Addon('plugin.video.youtube')
        whitelist_ips = addon.getSetting('kodion.http.ip.whitelist')
        whitelist_ips = ''.join(whitelist_ips.split())
        whitelist_ips = whitelist_ips.split(',')
        local_ranges = ('10.', '172.16.', '192.168.', '127.0.0.1', 'localhost', '::1')
        self.local_ranges = local_ranges
        self.whitelist_ips = whitelist_ips
        self.chunk_size = 1024 * 64
        self.base_path = 'special://temp/plugin.video.youtube'
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_GET(self):
        addon = xbmcaddon.Addon('plugin.video.youtube')
        dash_proxy_enabled = addon.getSetting('kodion.mpd.proxy') == 'true'
        api_config_enabled = addon.getSetting('youtube.api.config.page') == 'true'

        if not self.client_address[0].startswith(self.local_ranges) and not self.client_address[0] in self.whitelist_ips:
            self.send_error(403)
        else:
            if dash_proxy_enabled and self.path.endswith('.mpd'):
                file_path = xbmc.translatePath(self.base_path + self.path)
                file_chunk = True
                xbmc.log('[plugin.video.youtube] HTTPServer: Request |{proxy_path}| -> |{file_path}|'.format(proxy_path=self.path, file_path=file_path), xbmc.LOGDEBUG)
                try:
                    with open(file_path, 'rb') as f:
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/xml+dash')
                        self.send_header('Content-Length', os.path.getsize(file_path))
                        self.end_headers()
                        while file_chunk:
                            file_chunk = f.read(self.chunk_size)
                            if file_chunk:
                                self.wfile.write(file_chunk)
                    try:
                        os.remove(file_path)
                    except OSError:
                        xbmc.log('[plugin.video.youtube] HTTPServer: File removal failed |{file_path}|'.format(file_path=file_path), xbmc.LOGERROR)
                except IOError:
                    response = 'File Not Found: |{proxy_path}| -> |{file_path}|'.format(proxy_path=self.path, file_path=file_path)
                    self.send_error(404, response)
            elif api_config_enabled and self.path == '/api':
                html = self.api_config_page()
                html = html.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(html))
                self.end_headers()
                for chunk in self.get_chunks(html):
                    self.wfile.write(chunk)
            elif api_config_enabled and self.path.startswith('/api_submit'):
                addon = xbmcaddon.Addon('plugin.video.youtube')
                i18n = addon.getLocalizedString
                xbmc.executebuiltin('Dialog.Close(addonsettings,true)')
                old_api_key = addon.getSetting('youtube.api.key')
                old_api_id = addon.getSetting('youtube.api.id')
                old_api_secret = addon.getSetting('youtube.api.secret')
                params = parse_qs(urlparse(self.path).query)
                api_key = params.get('api_key', [''])[0]
                api_id = params.get('api_id', [''])[0]
                api_secret = params.get('api_secret', [''])[0]
                updated = []
                if api_key and api_key != old_api_key:
                    addon.setSetting('youtube.api.key', api_key)
                    updated.append(i18n(30201))
                if api_id and api_id != old_api_id:
                    addon.setSetting('youtube.api.id', api_id)
                    updated.append(i18n(30202))
                if api_secret and api_secret != old_api_secret:
                    updated.append(i18n(30203))
                    addon.setSetting('youtube.api.secret', api_secret)
                if addon.getSetting('youtube.api.key') and addon.getSetting('youtube.api.id') and \
                        addon.getSetting('youtube.api.secret'):
                    addon.setSetting('youtube.api.enable', 'true')
                else:
                    addon.setSetting('youtube.api.enable', 'false')
                if not updated:
                    updated = ''
                else:
                    updated = ', '.join(updated)
                html = self.api_submit_page(updated)
                html = html.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', len(html))
                self.end_headers()
                for chunk in self.get_chunks(html):
                    self.wfile.write(chunk)
            elif self.path == '/ping':
                self.send_error(204)
            else:
                self.send_error(403)

    def do_HEAD(self):
        if not self.client_address[0].startswith(self.local_ranges) and not self.client_address[0] in self.whitelist_ips:
            self.send_error(403)
        else:
            addon = xbmcaddon.Addon('plugin.video.youtube')
            dash_proxy_enabled = addon.getSetting('kodion.mpd.proxy') == 'true'
            if dash_proxy_enabled and self.path.endswith('.mpd'):
                file_path = xbmc.translatePath(self.base_path + self.path)
                if not os.path.isfile(file_path):
                    response = 'File Not Found: |{proxy_path}| -> |{file_path}|'.format(proxy_path=self.path, file_path=file_path)
                    self.send_error(404, response)
                else:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/xml+dash')
                    self.send_header('Content-Length', os.path.getsize(file_path))
                    self.end_headers()
            else:
                self.send_error(403)

    def log_message(self, format, *args):
        return

    def get_chunks(self, data):
        for i in xrange(0, len(data), self.chunk_size):
            yield data[i:i + self.chunk_size]

    @staticmethod
    def api_config_page():
        addon = xbmcaddon.Addon('plugin.video.youtube')
        i18n = addon.getLocalizedString
        api_key = addon.getSetting('youtube.api.key')
        api_id = addon.getSetting('youtube.api.id')
        api_secret = addon.getSetting('youtube.api.secret')
        html = u'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title></head>' \
               u'<body><form action="/api_submit">{api_key_head}:<br><input type="text" name="api_key" value="{api_key_value}" size="50"><br>' \
               u'{api_id_head}:<br><input type="text" name="api_id" value="{api_id_value}" size="50"><br>{api_secret_head}:<br>' \
               u'<input type="text" name="api_secret" value="{api_secret_value}" size="50"><br><br><input type="submit" value="{submit}">' \
               u'</form></body></html>'.format(title=i18n(30200), api_key_head=i18n(30201), api_id_head=i18n(30202),
                                               api_secret_head=i18n(30203), api_id_value=api_id, api_key_value=api_key, api_secret_value=api_secret,
                                               submit=i18n(30630))
        return html

    @staticmethod
    def api_submit_page(updated):
        addon = xbmcaddon.Addon('plugin.video.youtube')
        i18n = addon.getLocalizedString
        html = u'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title></head>' \
               u'<body>{updated}</body></html>'.format(title=i18n(30200), updated=i18n(30631) % updated)
        return html


def get_http_server(address=None, port=None):
    address = address if address else '0.0.0.0'
    port = int(port) if port else 50152
    try:
        server = BaseHTTPServer.HTTPServer((address, port), YouTubeRequestHandler)
        return server
    except socket.error:
        addon = xbmcaddon.Addon('plugin.video.youtube')
        xbmcgui.Dialog().notification(addon.getAddonInfo('name'), addon.getLocalizedString(30620) % str(port),
                                      xbmc.translatePath('special://home/addons/{0!s}/icon.png'.format(addon.getAddonInfo('id'))),
                                      5000, False)
        return None


def is_httpd_live(address=None, port=None):
    address = address if address else '127.0.0.1'
    port = int(port) if port else 50152
    url = 'http://{address}:{port}/ping'.format(address=address, port=port)
    try:
        response = requests.get(url)
        xbmc.log('[plugin.video.youtube] HTTPServer: Ping |{address}:{port}| |{response}|'.format(address=address, port=port, response=response.status_code), xbmc.LOGDEBUG)
        return response.status_code == 204
    except:
        xbmc.log('[plugin.video.youtube] HTTPServer: Ping |{address}:{port}| |{response}|'.format(address=address, port=port, response='failed'), xbmc.LOGDEBUG)
        return False
