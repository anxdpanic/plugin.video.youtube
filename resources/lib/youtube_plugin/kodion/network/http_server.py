# -*- coding: utf-8 -*-
"""

    Copyright (C) 2018-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os
import re
import socket
from errno import ECONNABORTED, ECONNREFUSED, ECONNRESET
from io import open
from json import dumps as json_dumps, loads as json_loads
from select import select
from textwrap import dedent

from .requests import BaseRequestsClass
from ..compatibility import (
    BaseHTTPRequestHandler,
    TCPServer,
    ThreadingMixIn,
    parse_qs,
    urlencode,
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
from ..utils import redact_auth, redact_ip, wait


class HTTPServer(ThreadingMixIn, TCPServer):
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 5
    allow_reuse_address = True
    allow_reuse_port = True

    daemon_threads = False
    block_on_close = True

    _handlers = []

    def finish_request(self, request, client_address):
        handler = self.RequestHandlerClass(request, client_address, self)
        HTTPServer._handlers.append(handler)

        try:
            handler.handle()
        finally:
            while (not handler._close_all
                   and not handler.wfile.closed
                   and not select((), (handler.wfile,), (), 0)[1]):
                pass
            if handler._close_all or handler.wfile.closed:
                return
            handler.finish()

    def server_close(self):
        request_handler = self.RequestHandlerClass
        request_handler._close_all = True
        request_handler.timeout = 0

        for handler in HTTPServer._handlers:
            handler.finish()
        HTTPServer._handlers = []

        try:
            threads = self._threads.pop_all()
        except AttributeError:
            return
        for thread in threads:
            if not thread.is_alive():
                continue
            request = thread._args[0]
            try:
                request.shutdown(socket.SHUT_RDWR)
            except (OSError, socket.error):
                pass
            request.close()
            try:
                thread.join(2)
                if not thread.is_alive():
                    continue
            except RuntimeError:
                pass


class RequestHandler(BaseHTTPRequestHandler, object):
    protocol_version = 'HTTP/1.1'
    server_version = 'plugin.video.youtube/1.0'

    _context = None
    _close_all = False

    requests = None
    BASE_PATH = xbmcvfs.translatePath(TEMP_PATH)
    chunk_size = 1024 * 64

    server_priority_list = {
        'id': None,
        'list': [],
    }

    def __init__(self, request, client_address, server):
        if not RequestHandler.requests:
            RequestHandler.requests = BaseRequestsClass(context=self._context)
        self.whitelist_ips = self._context.get_settings().httpd_whitelist()

        # Rather than calling BaseHTTPRequestHandler.__init__ we reimplement
        # the same setup so that RequestHandlerClass instance can be stored
        # after creation in HTTPServer.finish_request allowing
        # RequestHandler.finish to be called in HTTPServer.server_close to
        # ensure that all connections are properly closed.
        #
        # super(RequestHandler, self).__init__(request, client_address, server)

        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()

        # try/finally block implemented separately in HTTPServer.finish_request
        #
        # try:
        #     self.handle()
        # finally:
        #     self.finish()

    def handle_one_request(self):
        # Allow self.rfile.readline call to be interrupted by
        # HTTPServer.server_close when connection is kept open by keep-alive
        while (not self._close_all
               and not self.rfile.closed
               and not select((self.rfile,), (), (), 0)[0]):
            pass
        if self._close_all or self.rfile.closed:
            self.close_connection = True
            return

        try:
            super(RequestHandler, self).handle_one_request()
            return
        except OSError as exc:
            self.close_connection = True
            if exc.errno not in {ECONNABORTED, ECONNREFUSED, ECONNRESET}:
                raise exc

    def ip_address_status(self, ip_address):
        is_whitelisted = ip_address in self.whitelist_ips
        ip_allowed = is_whitelisted

        if not ip_allowed:
            octets = validate_ip_address(ip_address, ipv6_string=False)
            num_octets = len(octets) if any(octets) else 0
            if not num_octets:
                is_local = False
                return ip_allowed, is_local, is_whitelisted

            for ip_range in _LOCAL_RANGES:
                if isinstance(ip_range, tuple):
                    if (num_octets == len(ip_range[0])
                            and ip_range[0] < octets < ip_range[1]):
                        is_local = True
                        ip_allowed = True
                        break
                elif ip_address == ip_range:
                    is_local = True
                    ip_allowed = True
                    break
            else:
                is_local = False
        else:
            is_local = None

        return ip_allowed, is_local, is_whitelisted

    def connection_allowed(self, method):
        client_ip = self.client_address[0]
        ip_allowed, is_local, is_whitelisted = self.ip_address_status(client_ip)

        path_parts = urlsplit(self.path)
        if path_parts.query:
            params = parse_qs(path_parts.query)
            log_params = params.copy()
            for param, value in params.items():
                value = value[0]
                if param in {'key', 'api_key', 'api_secret', 'client_secret'}:
                    log_params[param] = '...'.join((value[:3], value[-3:]))
                elif param in {'api_id', 'client_id'}:
                    log_params[param] = '...'.join((value[:3], value[-5:]))
                elif param in {'access_token', 'refresh_token', 'token'}:
                    log_params[param] = '<redacted>'
                elif param == 'url':
                    log_params[param] = redact_ip(value)
                elif param == 'ip':
                    log_params[param] = '<redacted>'
                elif param == 'location':
                    log_params[param] = '|xx.xxxx,xx.xxxx|'
                elif param == '__headers':
                    log_params[param] = redact_auth(value)
            log_path = urlunsplit((
                '', '', path_parts.path, urlencode(log_params), '',
            ))
        else:
            params = log_params = None
            log_path = path_parts.path
        path = {
            'full': self.path,
            'path': path_parts.path,
            'query': path_parts.query,
            'params': params,
            'log_params': log_params,
            'log_path': log_path,
        }

        if not path['path'].startswith(PATHS.PING):
            msg = ('HTTPServer - {method}'
                   '\n\tPath:        |{path}|'
                   '\n\tParams:      |{params}|'
                   '\n\tAddress:     |{client_ip}|'
                   '\n\tWhitelisted: {is_whitelisted}'
                   '\n\tLocal range: {is_local}'
                   '\n\tStatus:      {status}'
                   .format(method=method,
                           path=path['path'],
                           params=path['log_params'],
                           client_ip=client_ip,
                           is_whitelisted=is_whitelisted,
                           is_local=('Undetermined'
                                     if is_local is None else
                                     is_local),
                           status='Allowed' if ip_allowed else 'Blocked'))
            self._context.log_debug(msg)
        return ip_allowed, path

    # noinspection PyPep8Naming
    def do_GET(self):
        allowed, path = self.connection_allowed('GET')
        if not allowed:
            self.send_error(403)
            return

        context = self._context
        localize = context.localize

        settings = context.get_settings()
        api_config_enabled = settings.api_config_page()

        empty = [None]

        if path['path'] == PATHS.IP:
            client_json = json_dumps({'ip': self.client_address[0]})
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(client_json)))
            self.end_headers()
            self.wfile.write(client_json.encode('utf-8'))

        elif path['path'].startswith(PATHS.MPD):
            try:
                file = path['params'].get('file', empty)[0]
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

                with open(file_path, 'rb', buffering=self.chunk_size) as f:
                    while 1:
                        file_chunk = f.read()
                        if not file_chunk:
                            break
                        self.wfile.write(file_chunk)
            except IOError:
                response = ('File Not Found: |{path}| -> |{file_path}|'
                            .format(path=path['log_path'], file_path=file_path))
                self.send_error(404, response)

        elif api_config_enabled and path['path'] == PATHS.API:
            html = self.api_config_page()
            html = html.encode('utf-8')

            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html)))
            self.end_headers()

            for chunk in self._get_chunks(html):
                self.wfile.write(chunk)

        elif api_config_enabled and path['path'].startswith(PATHS.API_SUBMIT):
            xbmc.executebuiltin('Dialog.Close(addonsettings,true)')

            query = path['query']
            params = path['params']
            updated = []

            api_key = params.get('api_key', empty)[0]
            api_id = params.get('api_id', empty)[0]
            api_secret = params.get('api_secret', empty)[0]
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

            for chunk in self._get_chunks(html):
                self.wfile.write(chunk)

        elif path['path'] == PATHS.PING:
            self.send_error(204)

        elif path['path'].startswith(PATHS.REDIRECT):
            url = path['params'].get('url', empty)[0]
            if url:
                wait(1)
                self.send_response(301)
                self.send_header('Location', url)
                self.send_header('Connection', 'close')
                self.end_headers()
            else:
                self.send_error(501)

        elif path['path'].startswith(PATHS.STREAM_PROXY):
            params = path['params']

            original_path = params.pop('__path', empty)[0] or '/videoplayback'

            servers = params.pop('__netloc', empty)
            stream_id = params.pop('__id', empty)[0]
            if stream_id != self.server_priority_list['id']:
                self.server_priority_list['id'] = stream_id
                _server_list = []
                self.server_priority_list['list'] = _server_list
            else:
                _server_list = self.server_priority_list['list']
                servers.sort(key=self._sort_servers, reverse=True)

            headers = params.pop('__headers', empty)[0]
            if headers:
                headers = json_loads(headers)
                if 'Range' in self.headers:
                    headers['Range'] = self.headers['Range']
            else:
                headers = self.headers

            original_query_str = urlencode(params, doseq=True)

            stream_redirect = settings.httpd_stream_redirect()

            response = None
            for server in servers:
                if not server:
                    continue

                stream_url = urlunsplit((
                    'https',
                    server,
                    original_path,
                    original_query_str,
                    '',
                ))

                if stream_redirect and server in _server_list:
                    self.send_response(301)
                    self.send_header('Location', stream_url)
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    break

                headers['Host'] = server
                with self.requests.request(stream_url,
                                           method='GET',
                                           headers=headers,
                                           stream=True) as response:
                    if not response or not response.ok:
                        continue
                    if server not in _server_list:
                        _server_list.append(server)

                    self.send_response(response.status_code)
                    for header, value in response.headers.items():
                        self.send_header(header, value)
                    self.end_headers()

                    for chunk in response.iter_content(chunk_size=None):
                        while (not self._close_all
                               and not self.wfile.closed
                               and not select((), (self.wfile,), (), 0)[1]):
                            pass
                        if self._close_all or self.wfile.closed:
                            break
                        self.wfile.write(chunk)
                break
            else:
                self.send_error(response and response.status_code or 500)

        else:
            self.send_error(501)

    # noinspection PyPep8Naming
    def do_HEAD(self):
        allowed, path = self.connection_allowed('HEAD')
        if not allowed:
            self.send_error(403)
            return

        empty = [None]

        if path['path'].startswith(PATHS.MPD):
            try:
                file = path['params'].get('file', empty)[0]
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
                            .format(path=path['log_path'], file_path=file_path))
                self.send_error(404, response)

        elif path['path'].startswith(PATHS.REDIRECT):
            self.send_error(404)

        else:
            self.send_error(501)

    # noinspection PyPep8Naming
    def do_POST(self):
        allowed, path = self.connection_allowed('POST')
        if not allowed:
            self.send_error(403)
            return

        empty = [None]

        if path['path'].startswith(PATHS.DRM):
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

            for chunk in self._get_chunks(response_body):
                self.wfile.write(chunk)

        else:
            self.send_error(501)

    # noinspection PyShadowingBuiltins
    def log_message(self, format, *args):
        return

    def _get_chunks(self, data):
        for i in range(0, len(data), self.chunk_size):
            yield data[i:i + self.chunk_size]

    def _sort_servers(self, server):
        _server_list = self.server_priority_list['list']
        try:
            index = _server_list.index(server)
        except ValueError:
            return -1
        return len(_server_list) - index

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
    RequestHandler._close_all = False
    RequestHandler.timeout = None
    if is_ipv6(address):
        HTTPServer.address_family = socket.AF_INET6
    else:
        HTTPServer.address_family = socket.AF_INET
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


def httpd_status(context, address=None):
    netloc = get_connect_address(context, as_netloc=True, address=address)
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


def get_connect_address(context, as_netloc=False, address=None):
    if address is None:
        settings = context.get_settings()
        listen_address = settings.httpd_listen()
        listen_port = settings.httpd_port()
    else:
        listen_address, listen_port = address

    if is_ipv6(listen_address):
        address_family = socket.AF_INET6
        broadcast_address = 'ff02::1'
    else:
        address_family = socket.AF_INET
        broadcast_address = '<broadcast>'

    try:
        sock = socket.socket(address_family, socket.SOCK_DGRAM)
        if listen_address in {'0.0.0.0', '::'}:
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
        if is_ipv6(connect_address):
            connect_address = connect_address.join(('[', ']'))
        return ':'.join((connect_address, str(listen_port)))
    return listen_address, listen_port


def get_listen_addresses():
    ipv4_addresses = ['127.0.0.1']
    ipv6_addresses = ['::1']
    allowed_address_families = [
        socket.AF_INET,
        getattr(socket, 'AF_INET6', None)
    ]
    for interface in (
            socket.getaddrinfo(socket.gethostname(), None)
            + socket.getaddrinfo(xbmc.getIPAddress(), None)
    ):
        ip_address = interface[4][0]
        address_family = interface[0]
        if not address_family or address_family not in allowed_address_families:
            continue
        if address_family == allowed_address_families[0]:
            addresses = ipv4_addresses
        else:
            addresses = ipv6_addresses
        if ip_address in addresses:
            continue

        octets = validate_ip_address(ip_address, ipv6_string=False)
        num_octets = len(octets) if any(octets) else 0
        if not num_octets:
            continue

        for ip_range in _LOCAL_RANGES:
            if isinstance(ip_range, tuple):
                if (num_octets == len(ip_range[0])
                        and ip_range[0] < octets < ip_range[1]):
                    addresses.append(ip_address)
                    break
            elif ip_address == ip_range:
                addresses.append(ip_address)
                break

    ipv4_addresses.append('0.0.0.0')
    ipv6_addresses.append('::')
    return ipv6_addresses + ipv4_addresses


def is_ipv6(ip_address):
    try:
        socket.inet_pton(socket.AF_INET6, ip_address)
        return True
    except (AttributeError, socket.error):
        return False


def ipv6_octets(ip_address):
    try:
        return tuple(socket.inet_pton(socket.AF_INET6, ip_address))
    except (AttributeError, socket.error):
        return ()


def validate_ip_address(ip_address, ipv6_string=True):
    if ipv6_string:
        if is_ipv6(ip_address):
            return (ip_address,)
    else:
        octets = ipv6_octets(ip_address)
        if octets:
            return octets

    try:
        socket.inet_aton(ip_address)
        try:
            octets = [octet for octet in map(int, ip_address.split('.'))
                      if 0 <= octet <= 255]
            if len(octets) != 4:
                raise ValueError
        except ValueError:
            return 0, 0, 0, 0
        return tuple(octets)
    except socket.error:
        return 0, 0, 0, 0


_LOCAL_RANGES = (
    ((127, 0, 0, 0), (127, 255, 255, 255)),
    ((10, 0, 0, 0), (10, 255, 255, 255)),
    ((172, 16, 0, 0), (172, 31, 255, 255)),
    ((192, 168, 0, 0), (192, 168, 255, 255)),
    'localhost',
    (ipv6_octets('fc00::'), ipv6_octets('fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')),
    (ipv6_octets('fe80::'), ipv6_octets('fe80::ffff:ffff:ffff:ffff')),
    '::1',
)
