# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Minimal HTTP client on urllib (no third-party modules on stock Kodi).

Every request goes through request(), which hands it to the one request broker (see broker.py):
directly inside the background service, over the service's local HTTP server from a listing, and only
when the service isn't running is it sent from here, paced through a property all processes share.
"""
import base64
import gzip
import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import xbmcgui

from . import broker, kodi

FOREGROUND, BACKGROUND = broker.FOREGROUND, broker.BACKGROUND
PORT_PROPERTY = 'youtube.port'
SERVICE_TIMEOUT = 180  # a listing's request may wait out a hold on the host, then run
PACE_PROPERTY = 'youtube.next_request'  # fallback pacing when the service isn't running

_broker = None  # set in the service process, whose own requests go straight onto the queue
_pace_lock = threading.Lock()


class HTTPError(Exception):
    def __init__(self, status, body=b'', url='', blocked=False):
        Exception.__init__(self, 'HTTP %s' % status)
        self.status = status
        self.body = body
        self.url = url
        self.blocked = blocked  # Google's automated-queries page, or held back after one

    def json(self):
        try:
            return json.loads(self.body.decode('utf-8'))
        except ValueError:
            return {}


class _ServiceUnavailable(Exception):
    pass


def install_broker(instance):
    """Called by the service: this process's requests now go to its broker."""
    global _broker
    _broker = instance


def request(url, data=None, headers=None, method=None, timeout=20, priority=FOREGROUND):
    """Returns (status, body); raises HTTPError (status 0 when there was no response at all)."""
    headers = dict(headers or {})
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode('utf-8')
        headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
    if _broker is not None:
        try:
            return _broker.request(url, data, headers, method, timeout, priority)
        except broker.Blocked as exc:
            raise HTTPError(403, b'', url, blocked=True) from exc
    port = xbmcgui.Window(10000).getProperty(PORT_PROPERTY)
    if port:
        try:
            return _via_service(port, url, data, headers, method, timeout, priority)
        except _ServiceUnavailable as exc:
            kodi.log('request broker unavailable (%s), sending directly' % exc)
    _pace(url)
    return send(url, data, headers, method, timeout)


def request_json(url, data=None, headers=None, method=None, timeout=20, priority=FOREGROUND):
    _, body = request(url, data=data, headers=headers, method=method, timeout=timeout, priority=priority)
    return json.loads(body.decode('utf-8')) if body else {}


def send(url, data=None, headers=None, method=None, timeout=20):
    """Send one request now. Only the broker (and the fallback above) call this."""
    headers = dict(headers or {})
    headers.setdefault('Accept-Encoding', 'gzip')
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
        raise HTTPError(exc.code, body, url, blocked=broker.is_block(exc.code, body)) from exc
    except (urllib.error.URLError, socket.timeout, ConnectionError) as exc:
        # No HTTP response at all (DNS, refused, timed out): status 0 so callers can tell.
        kodi.log('network error for %s: %s' % (url.split('?')[0], exc))
        raise HTTPError(0, b'', url) from exc


def _via_service(port, url, data, headers, method, timeout, priority):
    """Send the request through the service's broker, so every process shares one queue and one
    pace per host. The request travels as a JSON envelope (the body base64-encoded, since JSON can't
    carry bytes); YouTube's status and whether it was blocked come back in X-Upstream-* headers, so the
    local server's own status only ever says whether the envelope itself got through."""
    envelope = {'url': url, 'method': method, 'headers': headers, 'timeout': timeout, 'priority': priority,
                'data': base64.b64encode(data).decode('ascii') if data else None}
    req = urllib.request.Request('http://127.0.0.1:%s/fetch' % port, json.dumps(envelope).encode('utf-8'),
                                 {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=SERVICE_TIMEOUT) as resp:
            status = int(resp.headers.get('X-Upstream-Status') or 0)
            blocked = resp.headers.get('X-Upstream-Blocked') == '1'
            body = resp.read()
    except urllib.error.HTTPError as exc:  # the service refused the envelope itself
        raise _ServiceUnavailable('HTTP %s' % exc.code) from exc
    except (urllib.error.URLError, ConnectionError) as exc:
        raise _ServiceUnavailable(exc) from exc
    except socket.timeout as exc:
        raise HTTPError(0, b'', url) from exc
    if 200 <= status < 300:
        return status, body
    raise HTTPError(status, body, url, blocked=blocked)


def serve_envelope(raw, instance):
    """Service side of _via_service: run the envelope through the broker. Returns (headers, body)."""
    envelope = json.loads(raw.decode('utf-8'))
    url = envelope['url']
    if not allowed(url):
        return {'X-Upstream-Status': '0'}, b''
    data = base64.b64decode(envelope['data']) if envelope.get('data') else None
    try:
        status, body = instance.request(url, data, envelope.get('headers') or {}, envelope.get('method'),
                                        envelope.get('timeout') or 20, envelope.get('priority', FOREGROUND))
        blocked = False
    except HTTPError as exc:
        status, body, blocked = exc.status, exc.body, exc.blocked
    except broker.Blocked:
        status, body, blocked = 403, b'', True
    return {'X-Upstream-Status': str(status), 'X-Upstream-Blocked': '1' if blocked else '0'}, body or b''


def allowed(url):
    """The local server only forwards to Google's hosts, so it can't be used as an open proxy."""
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ''
    return parts.scheme == 'https' and any(host == d or host.endswith('.' + d)
                                           for d in ('youtube.com', 'googleapis.com', 'google.com', 'googlevideo.com'))


def _pace(url):
    """Without the service, space requests to a paced host through a home-window property that every
    process of the add-on reads, plus a lock for the threads of this one."""
    gap = broker.GAPS.get(urllib.parse.urlsplit(url).hostname or '', 0)
    if gap <= 0:
        return
    window = xbmcgui.Window(10000)
    with _pace_lock:
        now = time.time()
        try:
            slot = max(now, float(window.getProperty(PACE_PROPERTY) or 0))
        except ValueError:
            slot = now
        window.setProperty(PACE_PROPERTY, repr(slot + gap))
    if slot > now:
        time.sleep(slot - now)
