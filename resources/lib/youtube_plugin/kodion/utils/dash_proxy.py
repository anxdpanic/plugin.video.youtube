try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

import os
import requests
import socket

import xbmc
import xbmcaddon
import xbmcgui


class DashProxyHandler(BaseHTTPRequestHandler):
    local_ranges = ('10.', '172.16.', '192.168.', '127.0.0.1', 'localhost', '::1')
    chunk_size = 1024 * 64
    base_path = 'special://temp/temp'

    def do_GET(self):
        if not self.client_address[0].startswith(self.local_ranges):
            self.send_error(403)
        else:
            if self.path.endswith('.mpd'):
                file_path = xbmc.translatePath(self.base_path + self.path)
                file_chunk = True
                xbmc.log('[plugin.video.youtube] DashProxy: Request |{proxy_path}| -> |{file_path}|'.format(proxy_path=self.path, file_path=file_path), xbmc.LOGDEBUG)
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
                        xbmc.log('[plugin.video.youtube] DashProxy: File removal failed |{file_path}|'.format(file_path=file_path), xbmc.LOGERROR)
                except IOError:
                    response = 'File Not Found: |{proxy_path}| -> |{file_path}|'.format(proxy_path=self.path, file_path=file_path)
                    self.send_error(404, response)
            elif self.path == '/ping':
                self.send_error(204)
            else:
                self.send_error(403)

    def do_HEAD(self):
        if not self.client_address[0].startswith(self.local_ranges):
            self.send_error(403)
        else:
            if self.path.endswith('.mpd'):
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


def get_proxy_server(address=None, port=None):
    address = address if address else '127.0.0.1'
    port = int(port) if port else 50152
    try:
        server = HTTPServer((address, port), DashProxyHandler)
        return server
    except socket.error:
        addon = xbmcaddon.Addon('plugin.video.youtube')
        xbmcgui.Dialog().notification(addon.getAddonInfo('name'), addon.getLocalizedString(30620) % str(port),
                                      xbmc.translatePath('special://home/addons/{0!s}/icon.png'.format(addon.getAddonInfo('id'))),
                                      5000, False)
        return None


def is_proxy_live(address=None, port=None):
    address = address if address else '127.0.0.1'
    port = int(port) if port else 50152
    url = 'http://{address}:{port}/ping'.format(address=address, port=port)
    try:
        response = requests.get(url)
        xbmc.log('[plugin.video.youtube] DashProxy: Ping |{address}:{port}| |{response}|'.format(address=address, port=port, response=response.status_code), xbmc.LOGDEBUG)
        return response.status_code == 204
    except:
        xbmc.log('[plugin.video.youtube] DashProxy: Ping |{address}:{port}| |{response}|'.format(address=address, port=port, response='failed'), xbmc.LOGDEBUG)
        return False
