try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

import requests
import socket

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs


class DashProxyHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path.endswith('.mpd'):
            file_path = 'special://temp/temp' + self.path
            xbmc.log('[plugin.video.youtube] DashProxy: Request |{path}|'.format(path=self.path), xbmc.LOGDEBUG)
            if xbmcvfs.exists(file_path):
                f = xbmcvfs.File(file_path, 'r')
                response = f.read()
                f.close()
                self.send_response(200)
                self.send_header('Content-type', 'application/xml+dash')
                self.end_headers()
                self.wfile.write(response)
            else:
                response = 'File Not Found: {proxy_path} | {file_path}'.format(proxy_path=self.path, file_path=file_path)
                self.send_error(404, response)
        elif self.path == '/ping':
            self.send_response(204)
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
