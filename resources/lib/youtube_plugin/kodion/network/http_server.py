# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import os
import re
import socket
from io import open
from textwrap import dedent

from .requests import BaseRequestsClass
from ..compatibility import (
    BaseHTTPServer,
    parse_qs,
    urlsplit,
    xbmc,
    xbmcaddon,
    xbmcgui,
    xbmcvfs,
)
from ..constants import ADDON_ID, TEMP_PATH, paths
from ..logger import log_debug, log_error
from ..settings import XbmcPluginSettings
from ..utils import validate_ip_address


_addon = xbmcaddon.Addon(ADDON_ID)
_settings = XbmcPluginSettings(_addon)
_i18n = _addon.getLocalizedString
_addon_name = _addon.getAddonInfo('name')
_addon_icon = _addon.getAddonInfo('icon')
del _addon

_server_requests = BaseRequestsClass()


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler, object):
    BASE_PATH = xbmcvfs.translatePath(TEMP_PATH)
    chunk_size = 1024 * 64
    local_ranges = (
        ((10, 0, 0, 0), (10, 255, 255, 255)),
        ((172, 16, 0, 0), (172, 31, 255, 255)),
        ((192, 168, 0, 0), (192, 168, 255, 255)),
        '127.0.0.1',
        'localhost',
        '::1',
    )

    def __init__(self, *args, **kwargs):
        self.whitelist_ips = _settings.httpd_whitelist()
        super(RequestHandler, self).__init__(*args, **kwargs)

    def connection_allowed(self):
        client_ip = self.client_address[0]
        octets = validate_ip_address(client_ip)
        log_lines = ['HTTPServer: Connection from |%s|' % client_ip]
        conn_allowed = False
        for ip_range in self.local_ranges:
            if ((any(octets)
                 and isinstance(ip_range, tuple)
                 and ip_range[0] <= octets <= ip_range[1])
                    or client_ip == ip_range):
                conn_allowed = True
                break
        log_lines.append('Local range: |%s|' % str(conn_allowed))
        if not conn_allowed:
            conn_allowed = client_ip in self.whitelist_ips
            log_lines.append('Whitelisted: |%s|' % str(conn_allowed))

        if not conn_allowed:
            log_debug('HTTPServer: Connection from |{client_ip| not allowed'
                      .format(client_ip=client_ip))
        elif self.path != paths.PING:
            log_debug(' '.join(log_lines))
        return conn_allowed

    # noinspection PyPep8Naming
    def do_GET(self):
        api_config_enabled = _settings.api_config_page()

        # Strip trailing slash if present
        stripped_path = self.path.rstrip('/')
        if stripped_path != paths.PING:
            log_debug('HTTPServer: GET |{path}|'.format(path=self.path))

        if not self.connection_allowed():
            self.send_error(403)

        elif stripped_path == paths.IP:
            client_json = json.dumps({"ip": "{ip}"
                                     .format(ip=self.client_address[0])})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(client_json)))
            self.end_headers()
            self.wfile.write(client_json.encode('utf-8'))

        elif self.path.startswith(paths.MPD):
            filepath = os.path.join(self.BASE_PATH, self.path[len(paths.MPD):])
            file_chunk = True
            try:
                with open(filepath, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/dash+xml')
                    self.send_header('Content-Length',
                                     str(os.path.getsize(filepath)))
                    self.end_headers()
                    while file_chunk:
                        file_chunk = f.read(self.chunk_size)
                        if file_chunk:
                            self.wfile.write(file_chunk)
            except IOError:
                response = ('File Not Found: |{path}| -> |{filepath}|'
                            .format(path=self.path, filepath=filepath))
                self.send_error(404, response)

        elif api_config_enabled and stripped_path == paths.API:
            html = self.api_config_page()
            html = html.encode('utf-8')

            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html)))
            self.end_headers()

            for chunk in self.get_chunks(html):
                self.wfile.write(chunk)

        elif api_config_enabled and self.path.startswith(paths.API_SUBMIT):
            xbmc.executebuiltin('Dialog.Close(addonsettings, true)')

            query = urlsplit(self.path).query
            params = parse_qs(query)
            updated = []

            api_key = params.get('api_key', [None])[0]
            api_id = params.get('api_id', [None])[0]
            api_secret = params.get('api_secret', [None])[0]
            # Bookmark this page
            footer = _i18n(30638) if api_key and api_id and api_secret else ''

            if re.search(r'api_key=(?:&|$)', query):
                api_key = ''
            if re.search(r'api_id=(?:&|$)', query):
                api_id = ''
            if re.search(r'api_secret=(?:&|$)', query):
                api_secret = ''

            if api_key is not None and api_key != _settings.api_key():
                _settings.api_key(new_key=api_key)
                updated.append(_i18n(30201))  # API Key

            if api_id is not None and api_id != _settings.api_id():
                _settings.api_id(new_id=api_id)
                updated.append(_i18n(30202))  # API ID

            if api_secret is not None and api_secret != _settings.api_secret():
                _settings.api_secret(new_secret=api_secret)
                updated.append(_i18n(30203))  # API Secret

            if api_key and api_id and api_secret:
                enabled = _i18n(30636)  # Personal keys enabled
            else:
                enabled = _i18n(30637)  # Personal keys disabled

            if updated:
                # Successfully updated
                updated = _i18n(30631) % ', '.join(updated)
            else:
                # No changes, not updated
                updated = _i18n(30635)

            html = self.api_submit_page(updated, enabled, footer)
            html = html.encode('utf-8')

            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html)))
            self.end_headers()

            for chunk in self.get_chunks(html):
                self.wfile.write(chunk)

        elif stripped_path == paths.PING:
            self.send_error(204)

        else:
            self.send_error(501)

    # noinspection PyPep8Naming
    def do_HEAD(self):
        log_debug('HTTPServer: HEAD |{path}|'.format(path=self.path))

        if not self.connection_allowed():
            self.send_error(403)

        elif self.path.startswith(paths.MPD):
            filepath = os.path.join(self.BASE_PATH, self.path[len(paths.MPD):])
            if not os.path.isfile(filepath):
                response = ('File Not Found: |{path}| -> |{filepath}|'
                            .format(path=self.path, filepath=filepath))
                self.send_error(404, response)
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/dash+xml')
                self.send_header('Content-Length',
                                 str(os.path.getsize(filepath)))
                self.end_headers()

        else:
            self.send_error(501)

    # noinspection PyPep8Naming
    def do_POST(self):
        log_debug('HTTPServer: POST |{path}|'.format(path=self.path))

        if not self.connection_allowed():
            self.send_error(403)

        elif self.path.startswith(paths.DRM):
            home = xbmcgui.Window(10000)

            lic_url = home.getProperty('-'.join((ADDON_ID, 'license_url')))
            if not lic_url:
                self.send_error(404)
                return

            lic_token = home.getProperty('-'.join((ADDON_ID, 'license_token')))
            if not lic_token:
                self.send_error(403)
                return

            size_limit = None

            length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(length)

            li_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Bearer %s' % lic_token
            }

            response = _server_requests.request(lic_url,
                                                method='POST',
                                                headers=li_headers,
                                                data=post_data,
                                                stream=True)
            if not response or not response.ok:
                self.send_error(response and response.status_code or 500)
                return

            response_length = int(response.headers.get('content-length'))
            content = response.raw.read(response_length)

            content_split = content.split('\r\n\r\n'.encode('utf-8'))
            response_header = content_split[0].decode('utf-8', 'ignore')
            response_body = content_split[1]

            match = re.search(r'^Authorized-Format-Types:\s*'
                              r'(?P<authorized_types>.+?)\r*$',
                              response_header,
                              re.MULTILINE)
            if match:
                authorized_types = match.group('authorized_types').split(',')
                log_debug('HTTPServer: Found authorized formats |{auth_fmts}|'
                          .format(auth_fmts=authorized_types))

                fmt_to_px = {
                    'SD': (1280 * 528) - 1,
                    'HD720': 1280 * 720,
                    'HD': 7680 * 4320
                }
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
                self.send_header('X-Limit-Video',
                                 'max={0}px'.format(size_limit))
            for header, value in response.headers.items():
                if re.match('^[Cc]ontent-[Ll]ength$', header):
                    self.send_header(header, str(len(response_body)))
                else:
                    self.send_header(header, value)
            self.end_headers()

            for chunk in self.get_chunks(response_body):
                self.wfile.write(chunk)

        else:
            self.send_error(501)

    # noinspection PyShadowingBuiltins
    def log_message(self, format, *args):
        return

    def get_chunks(self, data):
        for i in range(0, len(data), self.chunk_size):
            yield data[i:i + self.chunk_size]

    @staticmethod
    def api_config_page():
        api_key = _settings.api_key()
        api_id = _settings.api_id()
        api_secret = _settings.api_secret()
        html = Pages.api_configuration.get('html')
        css = Pages.api_configuration.get('css')
        html = html.format(
            css=css,
            title=_i18n(30634),  # YouTube Add-on API Configuration
            api_key_head=_i18n(30201),  # API Key
            api_id_head=_i18n(30202),  # API ID
            api_secret_head=_i18n(30203),  # API Secret
            api_id_value=api_id,
            api_key_value=api_key,
            api_secret_value=api_secret,
            submit=_i18n(30630),  # Save
            header=_i18n(30634),  # YouTube Add-on API Configuration
        )
        return html

    @staticmethod
    def api_submit_page(updated_keys, enabled, footer):
        html = Pages.api_submit.get('html')
        css = Pages.api_submit.get('css')
        html = html.format(
            css=css,
            title=_i18n(30634),  # YouTube Add-on API Configuration
            updated=updated_keys,
            enabled=enabled,
            footer=footer,
            header=_i18n(30634),  # YouTube Add-on API Configuration
        )
        return html


class Pages(object):
    api_configuration = {
        'html': dedent('''\
            <!doctype html>
            <html>
              <head>
                <link rel="icon" href="data:;base64,=">
                <meta charset="utf-8">
                <title>{{title}}</title>
                <style>{{css}}</style>
              </head>
              <body>
                <div class="center">
                  <h5>{{header}}</h5>
                  <form action="{action_url}" class="config_form">
                    <label for="api_key">
                      <span>{{api_key_head}}:</span>
                      <input type="text" name="api_key" value="{{api_key_value}}" size="50"/>
                    </label>
                    <label for="api_id">
                      <span>{{api_id_head}}:</span>
                      <input type="text" name="api_id" value="{{api_id_value}}" size="50"/>
                    </label>
                    <label for="api_secret">
                      <span>{{api_secret_head}}:</span>
                      <input type="text" name="api_secret" value="{{api_secret_value}}" size="50"/>
                    </label>
                    <input type="submit" value="{{submit}}">
                  </form>
                </div>
              </body>
            </html>
        '''.format(action_url=paths.API_SUBMIT)),
        'css': ''.join('\t\t\t'.expandtabs(2) + line for line in dedent('''
            body {
              background: #141718;
            }
            .center {
              margin: auto;
              width: 600px;
              padding: 10px;
            }
            .config_form {
              width: 575px;
              height: 145px;
              font-size: 16px;
              background: #1a2123;
              padding: 30px 30px 15px 30px;
              border: 5px solid #1a2123;
            }
            h5 {
              font-family: Arial, Helvetica, sans-serif;
              font-size: 16px;
              color: #fff;
              font-weight: 600;
              width: 575px;
              height: 20px;
              background: #0f84a5;
              padding: 5px 30px 5px 30px;
              border: 5px solid #0f84a5;
              margin: 0px;
            }
            .config_form input[type=submit],
            .config_form input[type=button],
            .config_form input[type=text],
            .config_form textarea,
            .config_form label {
              font-family: Arial, Helvetica, sans-serif;
              font-size: 16px;
              color: #fff;
            }
            .config_form label {
              display:block;
              margin-bottom: 10px;
            }
            .config_form label > span {
              display: inline-block;
              float: left;
              width: 150px;
            }
            .config_form input[type=text] {
              background: transparent;
              border: none;
              border-bottom: 1px solid #147a96;
              width: 400px;
              outline: none;
              padding: 0px 0px 0px 0px;
            }
            .config_form input[type=text]:focus {
              border-bottom: 1px dashed #0f84a5;
            }
            .config_form input[type=submit],
            .config_form input[type=button] {
              width: 150px;
              background: #141718;
              border: 1px solid #147a96;
              padding: 8px 0px 8px 10px;
              border-radius: 5px;
              color: #fff;
              margin-top: 10px
            }
            .config_form input[type=submit]:hover,
            .config_form input[type=button]:hover {
              background: #0f84a5;
            }
        ''').splitlines(True)) + '\t\t'.expandtabs(2)
    }

    api_submit = {
        'html': dedent('''\
            <!doctype html>
            <html>
              <head>
                <link rel="icon" href="data:;base64,=">
                <meta charset="utf-8">
                <title>{title}</title>
                <style>{css}</style>
              </head>
              <body>
                <div class="center">
                  <h5>{header}</h5>
                  <div class="content">
                    <p>{updated}</p>
                    <p>{enabled}</p>
                    <p class="text_center">
                      <small>{footer}</small>
                    </p>
                  </div>
                </div>
              </body>
            </html>
        '''),
        'css': ''.join('\t\t\t'.expandtabs(2) + line for line in dedent('''
            body {
              background: #141718;
            }
            .center {
              margin: auto;
              width: 600px;
              padding: 10px;
            }
            .text_center {
              margin: 2em auto auto;
              width: 600px;
              padding: 10px;
              text-align: center;
            }
            .content {
              width: 575px;
              height: 145px;
              background: #1a2123;
              padding: 30px 30px 15px 30px;
              border: 5px solid #1a2123;
            }
            h5 {
              font-family: Arial, Helvetica, sans-serif;
              font-size: 16px;
              color: #fff;
              font-weight: 600;
              width: 575px;
              height: 20px;
              background: #0f84a5;
              padding: 5px 30px 5px 30px;
              border: 5px solid #0f84a5;
              margin: 0px;
            }
            p {
              font-family: Arial, Helvetica, sans-serif;
              font-size: 16px;
              color: #fff;
              float: left;
              width: 575px;
              margin: 0.5em auto;
            }
            small {
              font-family: Arial, Helvetica, sans-serif;
              font-size: 12px;
              color: #fff;
            }
        ''').splitlines(True)) + '\t\t'.expandtabs(2)
    }


def get_http_server(address, port):
    try:
        server = BaseHTTPServer.HTTPServer((address, port), RequestHandler)
        return server
    except socket.error as exc:
        log_error('HTTPServer: Failed to start |{address}:{port}| |{response}|'
                  .format(address=address, port=port, response=str(exc)))
        xbmcgui.Dialog().notification(_addon_name,
                                      str(exc),
                                      _addon_icon,
                                      time=5000,
                                      sound=False)
        return None


def httpd_status():
    address, port = get_connect_address()
    url = 'http://{address}:{port}{path}'.format(address=address,
                                                 port=port,
                                                 path=paths.PING)
    response = _server_requests.request(url)
    result = response and response.status_code
    if result == 204:
        return True

    log_debug('HTTPServer: Ping |{address}:{port}| - |{response}|'
              .format(address=address,
                      port=port,
                      response=result or 'failed'))
    return False


def get_client_ip_address():
    ip_address = None
    address, port = get_connect_address()
    url = 'http://{address}:{port}{path}'.format(address=address,
                                                 port=port,
                                                 path=paths.IP)
    response = _server_requests.request(url)
    if response and response.status_code == 200:
        response_json = response.json()
        if response_json:
            ip_address = response_json.get('ip')
    return ip_address


def get_connect_address():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error:
        return xbmc.getIPAddress()

    address = _settings.httpd_listen()
    port = _settings.httpd_port()
    if address == '0.0.0.0':
        address = '127.0.0.1'

    sock.settimeout(0)
    try:
        sock.connect((address, 0))
        return sock.getsockname()[0], port
    except socket.error:
        return xbmc.getIPAddress(), port
    finally:
        sock.close()
