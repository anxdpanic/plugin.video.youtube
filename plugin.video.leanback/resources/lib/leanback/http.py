# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""Minimal HTTP client on urllib (no third-party modules on stock Kodi)."""
import gzip
import json
import urllib.error
import urllib.parse
import urllib.request

from . import kodi


class HTTPError(Exception):
    def __init__(self, status, body=b'', url=''):
        Exception.__init__(self, 'HTTP %s' % status)
        self.status = status
        self.body = body
        self.url = url

    def json(self):
        try:
            return json.loads(self.body.decode('utf-8'))
        except ValueError:
            return {}


def request(url, data=None, headers=None, method=None, timeout=20):
    headers = dict(headers or {})
    headers.setdefault('Accept-Encoding', 'gzip')
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode('utf-8')
        headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            if resp.headers.get('Content-Encoding') == 'gzip':
                body = gzip.decompress(body)
            return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read() or b''
        if exc.headers and exc.headers.get('Content-Encoding') == 'gzip':
            try:
                body = gzip.decompress(body)
            except OSError:
                pass
        kodi.log('HTTP %s for %s' % (exc.code, url.split('?')[0]))
        raise HTTPError(exc.code, body, url) from exc


def request_json(url, data=None, headers=None, method=None, timeout=20):
    _, body = request(url, data=data, headers=headers, method=method, timeout=timeout)
    return json.loads(body.decode('utf-8')) if body else {}
