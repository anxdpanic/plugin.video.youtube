# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
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
import xbmcaddon
import xbmcgui

from . import art, broker, history, http, kodi, playback, sponsorblock

PORT_PROPERTY = http.PORT_PROPERTY
# Default port: not 50152, the default of earlier plugin.video.youtube versions, and above Linux's ephemeral
# range (32768-60999), so outgoing connections never hold it. The service_port setting overrides it; 0 means
# any free port.
DEFAULT_PORT = 61152
FALLBACK_STEPS = 2  # also try the next ports before taking any free one
MANIFEST = re.compile(r'^/mpd/([A-Za-z0-9_-]{11})\.mpd$')
HLS_PLAYLIST = re.compile(r'^/hls/([A-Za-z0-9_-]{11})\.m3u8$')
# Files written for the player: (path pattern, file name for the video id, content type)
SERVED = ((MANIFEST, '%s.mpd', 'application/dash+xml'),
          (HLS_PLAYLIST, '%s.m3u8', 'application/vnd.apple.mpegurl'))
SUBTITLE = re.compile(r'^/sub/([A-Za-z0-9_-]{11})/(\d+)\.vtt$')
EMPTY_VTT = b'WEBVTT\n\n'
TEMP_MAX_AGE = 6 * 3600  # manifests and subtitle lists outlive any playback by far


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
        for pattern, name, content_type in SERVED:
            match = pattern.match(path)
            if match:
                self._reply_file(os.path.join(kodi.TEMP_DIR, name % match.group(1)), content_type)
                return
        self.send_error(404)

    def _reply_file(self, path, content_type):
        if not os.path.isfile(path):
            self.send_error(404)
            return
        with open(path, 'rb') as handle:
            self._reply(handle.read(), content_type)

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


def wanted_port():
    """The port the user asked for: the setting, read fresh (it can change while the service runs)."""
    try:
        port = xbmcaddon.Addon(kodi.ADDON_ID).getSettingInt('service_port')
    except (RuntimeError, TypeError):
        port = DEFAULT_PORT
    if port != 0 and not 1024 <= port <= 65535:
        # Ports below 1024 need root, which Kodi doesn't have.
        kodi.log('service port %s is not usable, using %d' % (port, DEFAULT_PORT))
        port = DEFAULT_PORT
    return port


def candidate_ports(port):
    if port == 0:
        return (0,)
    return tuple(p for p in range(port, port + FALLBACK_STEPS + 1) if p <= 65535) + (0,)


def _start_server(ports):
    for port in ports:
        try:
            return _Server(('127.0.0.1', port), _Handler)
        except OSError as exc:  # EADDRINUSE: another service instance, or another program, has it
            kodi.log('port %d unavailable: %s' % (port, exc))
    return None


class Httpd:
    """The running server, the port it was asked for, and the switch to another port."""

    def __init__(self, window):
        self.window = window
        self.server = None
        self.wanted = None

    @property
    def port(self):
        return self.server.server_address[1] if self.server else None

    def start(self, wanted):
        """Start on `wanted` (or a fallback) and publish the port. Returns False when no port worked;
        any server already running keeps serving then."""
        server = _start_server(candidate_ports(wanted))
        if server is None:
            return False
        threading.Thread(target=server.serve_forever, name='youtube-httpd', daemon=True).start()
        old, self.server, self.wanted = self.server, server, wanted
        # Publish the new port before closing the old server, so no request finds neither.
        self.window.setProperty(PORT_PROPERTY, str(self.port))
        kodi.log('manifest server on 127.0.0.1:%d' % self.port)
        if wanted and self.port != wanted:
            # Kodi loads strings at startup, so right after an update a new one can still be empty.
            message = kodi.formatted(30146, wanted, self.port)
            xbmcgui.Dialog().notification(kodi.ADDON.getAddonInfo('name'), message, xbmcgui.NOTIFICATION_WARNING, 6000)
        if old is not None:
            self._close(old)
        return True

    def follow_setting(self):
        wanted = wanted_port()
        if wanted == self.wanted:
            return
        if wanted and wanted == self.port:  # already on it (it was a fallback before)
            self.wanted = wanted
            return
        kodi.log('service port changed to %d' % wanted)
        if not self.start(wanted):
            kodi.log_error('could not move the manifest server to port %d' % wanted)

    def stop(self):
        if self.server is None:
            return
        # A service from a newer copy of the add-on (an update or re-enable) can start before this one
        # exits; it then took the next free port and published that. Only withdraw our own port.
        if self.window.getProperty(PORT_PROPERTY) == str(self.port):
            self.window.clearProperty(PORT_PROPERTY)
        self._close(self.server)
        self.server = None

    @staticmethod
    def _close(server):
        server.shutdown()
        server.server_close()  # closes the listening socket too, so the port is free straight away


class _Monitor(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.settings_changed = False

    def onSettingsChanged(self):  # noqa: N802 (Kodi API name)
        self.settings_changed = True


def _cleanup():
    kodi.prune_dir(kodi.TEMP_DIR, TEMP_MAX_AGE)


def run():
    window = xbmcgui.Window(10000)
    requests = broker.Broker(http.send)
    http.install_broker(requests)
    _Handler.broker = requests
    httpd = Httpd(window)
    if not httpd.start(wanted_port()):
        kodi.log_error('could not start manifest server')
        requests.stop()
        return
    monitor = _Monitor()
    # Older versions kept these files in the add-on profile; remove that folder.
    shutil.rmtree(kodi.LEGACY_TEMP_DIR, ignore_errors=True)
    _cleanup()
    tracker = history.Tracker()
    backfill = art.Backfill()
    start_at = playback.StartAt()  # noqa: F841 (Kodi calls it while it exists)
    skipper = sponsorblock.Skipper()  # noqa: F841 (Kodi calls it while it exists)
    last_cleanup = time.time()
    while not monitor.waitForAbort(5):
        if monitor.settings_changed:
            monitor.settings_changed = False
            kodi.refresh()
            try:
                httpd.follow_setting()
            except Exception as exc:  # a failed switch must never stop the service
                kodi.log_error('could not apply the service port setting: %s' % exc)
        tracker.tick()
        backfill.tick()
        if time.time() - last_cleanup > 1800:
            _cleanup()
            last_cleanup = time.time()
    tracker.finish()
    httpd.stop()
    requests.stop()
