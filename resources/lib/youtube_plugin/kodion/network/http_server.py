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
    BaseHTTPRequestHandler,
    TCPServer,
    parse_qsl,
    urlsplit,
    urlunsplit,
    xbmc,
    xbmcgui,
    xbmcvfs,
)
from ..constants import (
    ADDON_ID,
    LICENSE_TOKEN,
    LICENSE_URL,
    PATHS,
    TEMP_PATH,
)
from ..utils import redact_ip, validate_ip_address, wait


class HTTPServer(TCPServer):
    allow_reuse_address = True
    allow_reuse_port = True

    def server_close(self):
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except (OSError, socket.error):
            pass
        self.socket.close()


class RequestHandler(BaseHTTPRequestHandler, object):
    protocol_version = 'HTTP/1.1'
    server_version = 'plugin.video.youtube/1.0'

    _context = None
    requests = None
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
        if not RequestHandler.requests:
            RequestHandler.requests = BaseRequestsClass(context=self._context)
        self.whitelist_ips = self._context.get_settings().httpd_whitelist()
        super(RequestHandler, self).__init__(*args, **kwargs)

    def connection_allowed(self, method):
        client_ip = self.client_address[0]
        is_whitelisted = client_ip in self.whitelist_ips
        conn_allowed = is_whitelisted

        if not conn_allowed:
            octets = validate_ip_address(client_ip)
            for ip_range in self.local_ranges:
                if ((any(octets)
                     and isinstance(ip_range, tuple)
                     and ip_range[0] <= octets <= ip_range[1])
                        or client_ip == ip_range):
                    in_local_range = True
                    conn_allowed = True
                    break
            else:
                in_local_range = False
        else:
            in_local_range = 'Undetermined'

        if self.path != PATHS.PING:
            msg = ('HTTPServer - {method}'
                   '\n\tPath:        |{path}|'
                   '\n\tAddress:     |{client_ip}|'
                   '\n\tWhitelisted: {is_whitelisted}'
                   '\n\tLocal range: {in_local_range}'
                   '\n\tStatus:      {status}'
                   .format(method=method,
                           path=redact_ip(self.path),
                           client_ip=client_ip,
                           is_whitelisted=is_whitelisted,
                           in_local_range=in_local_range,
                           status='Allowed' if conn_allowed else 'Blocked'))
            self._context.log_debug(msg)
        return conn_allowed

    # noinspection PyPep8Naming
    def do_GET(self):
        if not self.connection_allowed('GET'):
            self.send_error(403)
            return

        context = self._context
        localize = context.localize

        settings = context.get_settings()
        api_config_enabled = settings.api_config_page()

        # Strip trailing slash if present
        stripped_path = self.path.rstrip('/')

        if stripped_path == PATHS.IP:
            client_json = json.dumps({'ip': self.client_address[0]})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(client_json)))
            self.end_headers()
            self.wfile.write(client_json.encode('utf-8'))

        elif stripped_path.startswith(PATHS.MPD):
            try:
                file = dict(parse_qsl(urlsplit(self.path).query)).get('file')
                if file:
                    filepath = os.path.join(self.BASE_PATH, file)
                else:
                    filepath = None
                    raise IOError

                with open(filepath, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/dash+xml')
                    self.send_header('Content-Length',
                                     str(os.path.getsize(filepath)))
                    self.end_headers()

                    file_chunk = True
                    while file_chunk:
                        file_chunk = f.read(self.chunk_size)
                        if file_chunk:
                            self.wfile.write(file_chunk)
            except IOError:
                response = ('File Not Found: |{path}| -> |{filepath}|'
                            .format(path=self.path, filepath=filepath))
                self.send_error(404, response)

        elif api_config_enabled and stripped_path == PATHS.API:
            html = self.api_config_page()
            html = html.encode('utf-8')

            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html)))
            self.end_headers()

            for chunk in self.get_chunks(html):
                self.wfile.write(chunk)

        elif api_config_enabled and stripped_path.startswith(PATHS.API_SUBMIT):
            xbmc.executebuiltin('Dialog.Close(addonsettings,true)')

            query = urlsplit(self.path).query
            params = dict(parse_qsl(query))
            updated = []

            api_key = params.get('api_key')
            api_id = params.get('api_id')
            api_secret = params.get('api_secret')
            # Bookmark this page
            if api_key and api_id and api_secret:
                footer = localize('api.config.bookmark')
            else:
                footer = ''

            if re.search(r'api_key=(?:&|$)', query):
                api_key = ''
            if re.search(r'api_id=(?:&|$)', query):
                api_id = ''
            if re.search(r'api_secret=(?:&|$)', query):
                api_secret = ''

            if api_key is not None and api_key != settings.api_key():
                settings.api_key(new_key=api_key)
                updated.append(localize('api.key'))

            if api_id is not None and api_id != settings.api_id():
                settings.api_id(new_id=api_id)
                updated.append(localize('api.id'))

            if api_secret is not None and api_secret != settings.api_secret():
                settings.api_secret(new_secret=api_secret)
                updated.append(localize('api.secret'))

            if api_key and api_id and api_secret:
                enabled = localize('api.personal.enabled')
            else:
                enabled = localize('api.personal.disabled')

            if updated:
                # Successfully updated
                updated = localize('api.config.updated') % ', '.join(updated)
            else:
                # No changes, not updated
                updated = localize('api.config.not_updated')

            html = self.api_submit_page(updated, enabled, footer)
            html = html.encode('utf-8')

            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html)))
            self.end_headers()

            for chunk in self.get_chunks(html):
                self.wfile.write(chunk)

        elif stripped_path == PATHS.PING:
            self.send_error(204)

        elif stripped_path.startswith(PATHS.REDIRECT):
            url = dict(parse_qsl(urlsplit(self.path).query)).get('url')
            if url:
                wait(1)
                self.send_response(301)
                self.send_header('Location', url)
                self.send_header('Connection', 'close')
                self.end_headers()
            else:
                self.send_error(501)

        else:
            self.send_error(501)

    # noinspection PyPep8Naming
    def do_HEAD(self):
        if not self.connection_allowed('HEAD'):
            self.send_error(403)
            return

        if self.path.startswith(PATHS.MPD):
            try:
                file = dict(parse_qsl(urlsplit(self.path).query)).get('file')
                if file:
                    file_path = os.path.join(self.BASE_PATH, file)
                else:
                    file_path = None
                    raise IOError

                file_size = os.path.getsize(file_path)
                self.send_response(200)
                self.send_header('Content-Type', 'application/dash+xml')
                self.send_header('Content-Length', str(file_size))
                self.end_headers()
            except IOError:
                response = ('File Not Found: |{path}| -> |{file_path}|'
                            .format(path=self.path, file_path=file_path))
                self.send_error(404, response)

        elif self.path.startswith(PATHS.REDIRECT):
            self.send_error(404)

        else:
            self.send_error(501)

    # noinspection PyPep8Naming
    def do_POST(self):
        if not self.connection_allowed('POST'):
            self.send_error(403)
            return

        if self.path.startswith(PATHS.DRM):
            home = xbmcgui.Window(10000)

            lic_url = home.getProperty('-'.join((ADDON_ID, LICENSE_URL)))
            if not lic_url:
                self.send_error(404)
                return

            lic_token = home.getProperty('-'.join((ADDON_ID, LICENSE_TOKEN)))
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

            response = self.requests.request(lic_url,
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
                self._context.log_debug('HTTPServer - Found authorized formats'
                                        '\n\tFormats: {auth_fmts}'
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

    @classmethod
    def api_config_page(cls):
        settings = cls._context.get_settings()
        localize = cls._context.localize
        api_key = settings.api_key()
        api_id = settings.api_id()
        api_secret = settings.api_secret()
        html = Pages.api_configuration.get('html')
        css = Pages.api_configuration.get('css')
        html = html.format(
            css=css,
            title=localize('api.config'),
            api_key_head=localize('api.key'),
            api_id_head=localize('api.id'),
            api_secret_head=localize('api.secret'),
            api_id_value=api_id,
            api_key_value=api_key,
            api_secret_value=api_secret,
            submit=localize('api.config.save'),
            header=localize('api.config'),
        )
        return html

    @classmethod
    def api_submit_page(cls, updated_keys, enabled, footer):
        localize = cls._context.localize
        html = Pages.api_submit.get('html')
        css = Pages.api_submit.get('css')
        html = html.format(
            css=css,
            title=localize('api.config'),
            updated=updated_keys,
            enabled=enabled,
            footer=footer,
            header=localize('api.config'),
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
        '''.format(action_url=PATHS.API_SUBMIT)),
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


def get_http_server(address, port, context):
    RequestHandler._context = context
    try:
        server = HTTPServer((address, port), RequestHandler)
        return server
    except socket.error as exc:
        context.log_error('HTTPServer - Failed to start'
                          '\n\tAddress:  |{address}:{port}|'
                          '\n\tResponse: {response}'
                          .format(address=address, port=port, response=exc))
        xbmcgui.Dialog().notification(context.get_name(),
                                      str(exc),
                                      context.get_icon(),
                                      time=5000,
                                      sound=False)
        return None


def httpd_status(context):
    netloc = get_connect_address(context, as_netloc=True)
    url = urlunsplit((
        'http',
        netloc,
        PATHS.PING,
        '',
        '',
    ))
    if not RequestHandler.requests:
        RequestHandler.requests = BaseRequestsClass(context=context)
    response = RequestHandler.requests.request(url)
    result = response and response.status_code
    if result == 204:
        return True

    context.log_debug('HTTPServer - Ping'
                      '\n\tAddress:  |{netloc}|'
                      '\n\tResponse: {response}'
                      .format(netloc=netloc,
                              response=result or 'failed'))
    return False


def get_client_ip_address(context):
    ip_address = None
    url = urlunsplit((
        'http',
        get_connect_address(context, as_netloc=True),
        PATHS.IP,
        '',
        '',
    ))
    if not RequestHandler.requests:
        RequestHandler.requests = BaseRequestsClass(context=context)
    response = RequestHandler.requests.request(url)
    if response and response.status_code == 200:
        response_json = response.json()
        if response_json:
            ip_address = response_json.get('ip')
    return ip_address


def get_connect_address(context, as_netloc=False):
    settings = context.get_settings()
    listen_address = settings.httpd_listen()
    listen_port = settings.httpd_port()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if listen_address == '0.0.0.0':
            broadcast_address = '<broadcast>'
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        else:
            broadcast_address = listen_address
            if hasattr(socket, 'SO_REUSEADDR'):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, 'SO_REUSEPORT'):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except socket.error as exc:
        context.log_error('HTTPServer'
                          ' - get_connect_address failed to create socket'
                          '\n\tException: {exc!r}'
                          .format(exc=exc))
        connect_address = xbmc.getIPAddress()
    else:
        sock.settimeout(0)
        try:
            sock.connect((broadcast_address, 0))
        except socket.error as exc:
            context.log_error('HTTPServer'
                              ' - get_connect_address failed connect'
                              '\n\tException: {exc!r}'
                              .format(exc=exc))
            connect_address = xbmc.getIPAddress()
        else:
            try:
                connect_address = sock.getsockname()[0]
            except socket.error as exc:
                context.log_error('HTTPServer'
                                  ' - get_connect_address failed to get address'
                                  '\n\tException: {exc!r}'
                                  .format(exc=exc))
                connect_address = xbmc.getIPAddress()
        finally:
            sock.close()

    if as_netloc:
        return ':'.join((connect_address, str(listen_port)))
    return listen_address, listen_port
