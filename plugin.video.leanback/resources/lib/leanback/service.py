# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""Background service: a localhost HTTP server that hands generated DASH manifests to
InputStream Adaptive (ISA only downloads manifests over HTTP, not from local paths), and the home of
the request broker every request to Google goes through (listings reach it via POST /fetch)."""
import json
import os
import re
import shutil
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

import xbmc
import xbmcgui

from . import broker, history, http, kodi

PORT_PROPERTY = http.PORT_PROPERTY
PREFERRED_PORTS = (50152, 50153, 50154, 0)
MANIFEST = re.compile(r'^/mpd/([A-Za-z0-9_-]{11})\.mpd$')
SUBTITLE = re.compile(r'^/sub/([A-Za-z0-9_-]{11})/(\d+)\.vtt$')
EMPTY_VTT = b'WEBVTT\n\n'


class _Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class _Handler(BaseHTTPRequestHandler):
    broker = None

    def do_POST(self):  # noqa: N802 (http.server API)
        if self.path != '/fetch' or self.broker is None:
            self.send_error(404)
            return
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        headers, body = http.serve_envelope(raw, self.broker)
        self.send_response(200)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 (http.server API)
        path = self.path.split('?')[0]
        sub = SUBTITLE.match(path)
        if sub:
            self._reply(_subtitle(sub.group(1), int(sub.group(2))), 'text/vtt; charset=utf-8')
            return
        match = MANIFEST.match(path)
        path = os.path.join(kodi.TEMP_DIR, '%s.mpd' % match.group(1)) if match else None
        if not path or not os.path.isfile(path):
            self.send_error(404)
            return
        with open(path, 'rb') as handle:
            self._reply(handle.read(), 'application/dash+xml')

    def _reply(self, body, content_type):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        kodi.log('httpd: ' + fmt % args)


def _subtitle(video_id, index):
    """Fetch one caption track from YouTube; retry a rate limit once, else return an empty track."""
    try:
        with open(os.path.join(kodi.TEMP_DIR, '%s.subs.json' % video_id), encoding='utf-8') as handle:
            info = json.load(handle)
    except (OSError, ValueError):
        info = {}
    urls = info.get('urls', [])
    if index >= len(urls):
        return EMPTY_VTT
    for attempt in range(2):
        try:
            _, body = http.request(urls[index], headers={'User-Agent': info.get('ua', '')}, timeout=15)
            return body if body.startswith(b'WEBVTT') else EMPTY_VTT
        except http.HTTPError as exc:
            kodi.log('subtitle %s/%d: HTTP %s' % (video_id, index, exc.status))
            if exc.status != 429 or attempt:
                break
            time.sleep(1.5)
        except (OSError, ValueError) as exc:
            kodi.log('subtitle %s/%d: %s' % (video_id, index, exc))
            break
    return EMPTY_VTT


def _start_server():
    for port in PREFERRED_PORTS:
        try:
            return _Server(('127.0.0.1', port), _Handler)
        except OSError:
            continue
    return None


def _cleanup(max_age=6 * 3600):
    if not os.path.isdir(kodi.TEMP_DIR):
        return
    now = time.time()
    for name in os.listdir(kodi.TEMP_DIR):
        path = os.path.join(kodi.TEMP_DIR, name)
        try:
            if now - os.path.getmtime(path) > max_age:
                os.remove(path)
        except OSError:
            pass


def run():
    window = xbmcgui.Window(10000)
    requests = broker.Broker(http.send)
    http.install_broker(requests)
    _Handler.broker = requests
    server = _start_server()
    if server is None:
        kodi.log_error('could not start manifest server')
        return
    port = server.server_address[1]
    window.setProperty(PORT_PROPERTY, str(port))
    thread = threading.Thread(target=server.serve_forever, name='leanback-httpd')
    thread.daemon = True
    thread.start()
    kodi.log('manifest server on 127.0.0.1:%d' % port)
    monitor = xbmc.Monitor()
    # Older versions kept these files in the add-on profile; remove that folder.
    shutil.rmtree(kodi.LEGACY_TEMP_DIR, ignore_errors=True)
    _cleanup()
    tracker = history.Tracker()
    last_cleanup = time.time()
    while not monitor.waitForAbort(5):
        tracker.tick()
        if time.time() - last_cleanup > 1800:
            _cleanup()
            last_cleanup = time.time()
    tracker.finish()
    window.clearProperty(PORT_PROPERTY)
    server.shutdown()
    server.server_close()
    requests.stop()
