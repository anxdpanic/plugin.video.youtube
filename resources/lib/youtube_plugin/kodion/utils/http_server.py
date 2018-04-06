from six.moves import BaseHTTPServer
from six.moves.urllib.parse import parse_qs, urlparse
from six.moves import xrange

import os
import re
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
        local_ranges = ('10.', '172.16.', '192.168.')
        local_ips = ['127.0.0.1', 'localhost', '::1']
        self.local_ranges = local_ranges
        self.whitelist_ips = whitelist_ips + local_ips
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
                query = urlparse(self.path).query
                params = parse_qs(query)
                api_key = params.get('api_key', [None])[0]
                api_id = params.get('api_id', [None])[0]
                api_secret = params.get('api_secret', [None])[0]
                if api_key and api_id and api_secret:
                    footer = i18n(30638)
                else:
                    footer = u''
                if re.search(r'api_key=(?:&|$)', query):
                    api_key = ''
                if re.search(r'api_id=(?:&|$)', query):
                    api_id = ''
                if re.search(r'api_secret=(?:&|$)', query):
                    api_secret = ''
                updated = []
                if api_key is not None and api_key != old_api_key:
                    addon.setSetting('youtube.api.key', api_key)
                    updated.append(i18n(30201))
                if api_id is not None and api_id != old_api_id:
                    addon.setSetting('youtube.api.id', api_id)
                    updated.append(i18n(30202))
                if api_secret is not None and api_secret != old_api_secret:
                    updated.append(i18n(30203))
                    addon.setSetting('youtube.api.secret', api_secret)
                if addon.getSetting('youtube.api.key') and addon.getSetting('youtube.api.id') and \
                        addon.getSetting('youtube.api.secret'):
                    enabled = i18n(30636)
                    addon.setSetting('youtube.api.enable', 'true')
                else:
                    enabled = i18n(30637)
                    addon.setSetting('youtube.api.enable', 'false')
                if not updated:
                    updated = i18n(30635)
                else:
                    updated = i18n(30631) % u', '.join(updated)
                html = self.api_submit_page(updated, enabled, footer)
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

    def do_POST(self):
        if not self.client_address[0].startswith(self.local_ranges) and not self.client_address[0] in self.whitelist_ips:
            self.send_error(403)
        elif self.path.startswith('/widevine'):
            xbmc.log('[plugin.video.youtube] HTTPServer: Request |{proxy_path}|'.format(proxy_path=self.path), xbmc.LOGDEBUG)

            license_url = xbmcgui.Window(10000).getProperty('plugin.video.youtube-license_url')
            license_token = xbmcgui.Window(10000).getProperty('plugin.video.youtube-license_token')

            if not license_url:
                self.send_error(404)
                return
            if not license_token:
                self.send_error(403)
                return

            size_limit = None

            length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(length)

            li_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Bearer %s' % license_token
            }

            result = requests.post(url=license_url, headers=li_headers, data=post_data, stream=True)

            response_length = int(result.headers.get('content-length'))
            content = result.raw.read(response_length)

            content_split = content.split('\r\n\r\n'.encode('utf-8'))
            response_header = content_split[0].decode('utf-8', 'ignore')
            response_body = content_split[1]
            response_length = len(response_body)

            match = re.search('^Authorized-Format-Types:\s*(?P<authorized_types>.+?)\r*$', response_header, re.MULTILINE)
            if match:
                authorized_types = match.group('authorized_types').split(',')
                xbmc.log('[plugin.video.youtube] HTTPServer: Found authorized formats |{authorized_fmts}|'.format(authorized_fmts=authorized_types), xbmc.LOGDEBUG)

                fmt_to_px = {'SD': (1280 * 528) - 1, 'HD720': 1280 * 720, 'HD': 7680 * 4320}
                if 'HD' in authorized_types:
                    size_limit = fmt_to_px['HD']
                elif 'HD720' in authorized_types:
                    if xbmc.getCondVisibility('system.platform.android') == 1:
                        size_limit = fmt_to_px['HD720']
                    else:
                        size_limit = fmt_to_px['SD']
                elif 'SD' in authorized_types:
                    size_limit = fmt_to_px['SD']

            self.send_response(200)

            if size_limit:
                self.send_header('X-Limit-Video', 'max={size_limit}px'.format(size_limit=str(size_limit)))
            for d in list(result.headers.items()):
                if re.match('^[Cc]ontent-[Ll]ength$', d[0]):
                    self.send_header(d[0], response_length)
                else:
                    self.send_header(d[0], d[1])
            self.end_headers()

            for chunk in self.get_chunks(response_body):
                self.wfile.write(chunk)
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
        html = Pages().api_configuration.get('html')
        css = Pages().api_configuration.get('css')
        html = html.format(css=css, title=i18n(30634), api_key_head=i18n(30201), api_id_head=i18n(30202),
                           api_secret_head=i18n(30203), api_id_value=api_id, api_key_value=api_key,
                           api_secret_value=api_secret, submit=i18n(30630), header=i18n(30634))
        return html

    @staticmethod
    def api_submit_page(updated_keys, enabled, footer):
        addon = xbmcaddon.Addon('plugin.video.youtube')
        i18n = addon.getLocalizedString
        html = Pages().api_submit.get('html')
        css = Pages().api_submit.get('css')
        html = html.format(css=css, title=i18n(30634), updated=updated_keys, enabled=enabled, footer=footer, header=i18n(30634))
        return html


class Pages(object):
    api_configuration = {
        'html':
            u'<!doctype html>\n<html>\n'
            u'<head>\n\t<meta charset="utf-8">\n'
            u'\t<title>{title}</title>\n'
            u'\t<style>\n{css}\t</style>\n'
            u'</head>\n<body>\n'
            u'\t<div class="center">\n'
            u'\t<h5>{header}</h5>\n'
            u'\t<form action="/api_submit" class="config_form">\n'
            u'\t\t<label for="api_key">\n'
            u'\t\t<span>{api_key_head}</span><input type="text" name="api_key" value="{api_key_value}" size="50"/>\n'
            u'\t\t</label>\n'
            u'\t\t<label for="api_id">\n'
            u'\t\t<span>{api_id_head}</span><input type="text" name="api_id" value="{api_id_value}" size="50"/>\n'
            u'\t\t</label>\n'
            u'\t\t<label for="api_secret">\n'
            u'\t\t<span>{api_secret_head}</span><input type="text" name="api_secret" value="{api_secret_value}" size="50"/>\n'
            u'\t\t</label>\n'
            u'\t\t<input type="submit" value="{submit}">\n'
            u'\t</form>\n'
            u'\t</div>\n'
            u'</body>\n</html>',

        'css':
            u'body {\n'
            u'  background: #141718;\n'
            u'}\n'
            u'.center {\n'
            u'  margin: auto;\n'
            u'  width: 600px;\n'
            u'  padding: 10px;\n'
            u'}\n'
            u'.config_form {\n'
            u'  width: 575px;\n'
            u'  height: 145px;\n'
            u'  font-size: 16px;\n'
            u'  background: #1a2123;\n'
            u'  padding: 30px 30px 15px 30px;\n'
            u'  border: 5px solid #1a2123;\n'
            u'}\n'
            u'h5 {\n'
            u'  font-family: Arial, Helvetica, sans-serif;\n'
            u'  font-size: 16px;\n'
            u'  color: #fff;\n'
            u'  font-weight: 600;\n'
            u'  width: 575px;\n'
            u'  height: 20px;\n'
            u'  background: #0f84a5;\n'
            u'  padding: 5px 30px 5px 30px;\n'
            u'  border: 5px solid #0f84a5;\n'
            u'  margin: 0px;\n'
            u'}\n'
            u'.config_form input[type=submit],\n'
            u'.config_form input[type=button],\n'
            u'.config_form input[type=text],\n'
            u'.config_form textarea,\n'
            u'.config_form label {\n'
            u'  font-family: Arial, Helvetica, sans-serif;\n'
            u'  font-size: 16px;\n'
            u'  color: #fff;\n'
            u'}\n'
            u'.config_form label {\n'
            u'  display:block;\n'
            u'  margin-bottom: 10px;\n'
            u'}\n'
            u'.config_form label > span {\n'
            u'  display: inline-block;\n'
            u'  float: left;\n'
            u'  width: 150px;\n'
            u'}\n'
            u'.config_form input[type=text] {\n'
            u'  background: transparent;\n'
            u'  border: none;\n'
            u'  border-bottom: 1px solid #147a96;\n'
            u'  width: 400px;\n'
            u'  outline: none;\n'
            u'  padding: 0px 0px 0px 0px;\n'
            u'}\n'
            u'.config_form input[type=text]:focus {\n'
            u'  border-bottom: 1px dashed #0f84a5;\n'
            u'}\n'
            u'.config_form input[type=submit],\n'
            u'.config_form input[type=button] {\n'
            u'  width: 150px;\n'
            u'  background: #141718;\n'
            u'  border: none;\n'
            u'  padding: 8px 0px 8px 10px;\n'
            u'  border-radius: 5px;\n'
            u'  color: #fff;\n'
            u'  margin-top: 10px\n'
            u'}\n'
            u'.config_form input[type=submit]:hover,\n'
            u'.config_form input[type=button]:hover {\n'
            u'  background: #0f84a5;\n'
            u'}\n'
    }

    api_submit = {
        'html':
            u'<!doctype html>\n<html>\n'
            u'<head>\n\t<meta charset="utf-8">\n'
            u'\t<title>{title}</title>\n'
            u'\t<style>\n{css}\t</style>\n'
            u'</head>\n<body>\n'
            u'\t<div class="center">\n'
            u'\t<h5>{header}</h5>\n'
            u'\t<div class="content">\n'
            u'\t\t<span>{updated}</span>\n'
            u'\t\t<span>{enabled}</span>\n'
            u'\t\t<span>&nbsp;</span>\n'
            u'\t\t<span>&nbsp;</span>\n'
            u'\t\t<span>&nbsp;</span>\n'
            u'\t\t<span>&nbsp;</span>\n'
            u'\t\t<div class="textcenter">\n'
            u'\t\t\t<span><small>{footer}</small></span>\n'
            u'\t\t</div>\n'
            u'\t</div>\n'
            u'\t</div>\n'
            u'</body>\n</html>',

        'css':
            u'body {\n'
            u'  background: #141718;\n'
            u'}\n'
            u'.center {\n'
            u'  margin: auto;\n'
            u'  width: 600px;\n'
            u'  padding: 10px;\n'
            u'}\n'
            u'.textcenter {\n'
            u'  margin: auto;\n'
            u'  width: 600px;\n'
            u'  padding: 10px;\n'
            u'  text-align: center;\n'
            u'}\n'
            u'.content {\n'
            u'  width: 575px;\n'
            u'  height: 145px;\n'
            u'  background: #1a2123;\n'
            u'  padding: 30px 30px 15px 30px;\n'
            u'  border: 5px solid #1a2123;\n'
            u'}\n'
            u'h5 {\n'
            u'  font-family: Arial, Helvetica, sans-serif;\n'
            u'  font-size: 16px;\n'
            u'  color: #fff;\n'
            u'  font-weight: 600;\n'
            u'  width: 575px;\n'
            u'  height: 20px;\n'
            u'  background: #0f84a5;\n'
            u'  padding: 5px 30px 5px 30px;\n'
            u'  border: 5px solid #0f84a5;\n'
            u'  margin: 0px;\n'
            u'}\n'
            u'span {\n'
            u'  font-family: Arial, Helvetica, sans-serif;\n'
            u'  font-size: 16px;\n'
            u'  color: #fff;\n'
            u'  display: block;\n'
            u'  float: left;\n'
            u'  width: 575px;\n'
            u'}\n'
            u'small {\n'
            u'  font-family: Arial, Helvetica, sans-serif;\n'
            u'  font-size: 12px;\n'
            u'  color: #fff;\n'
            u'}\n'
    }


def get_http_server(address=None, port=None):
    addon = xbmcaddon.Addon('plugin.video.youtube')
    address = address if address else addon.getSetting('kodion.http.listen')
    address = address if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', address) else '0.0.0.0'
    port = int(port) if port else 50152
    try:
        server = BaseHTTPServer.HTTPServer((address, port), YouTubeRequestHandler)
        return server
    except socket.error as e:
        xbmc.log('[plugin.video.youtube] HTTPServer: Failed to start |{address}:{port}| |{response}|'.format(address=address, port=port, response=str(e)), xbmc.LOGDEBUG)
        xbmcgui.Dialog().notification(addon.getAddonInfo('name'), str(e),
                                      xbmc.translatePath('special://home/addons/{0!s}/icon.png'.format(addon.getAddonInfo('id'))),
                                      5000, False)
        return None


def is_httpd_live(address=None, port=None):
    addon = xbmcaddon.Addon('plugin.video.youtube')
    address = address if address else addon.getSetting('kodion.http.listen')
    address = '127.0.0.1' if address == '0.0.0.0' else address
    address = address if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', address) else '127.0.0.1'
    port = int(port) if port else 50152
    url = 'http://{address}:{port}/ping'.format(address=address, port=port)
    try:
        response = requests.get(url)
        xbmc.log('[plugin.video.youtube] HTTPServer: Ping |{address}:{port}| |{response}|'.format(address=address, port=port, response=response.status_code), xbmc.LOGDEBUG)
        return response.status_code == 204
    except:
        xbmc.log('[plugin.video.youtube] HTTPServer: Ping |{address}:{port}| |{response}|'.format(address=address, port=port, response='failed'), xbmc.LOGDEBUG)
        return False
