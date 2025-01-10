# -*- coding: utf-8 -*-
"""

    Copyright (C) 2023-present plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

__all__ = (
    'BaseHTTPRequestHandler',
    'TCPServer',
    'ThreadingMixIn',
    'available_cpu_count',
    'byte_string_type',
    'datetime_infolabel',
    'entity_escape',
    'parse_qs',
    'parse_qsl',
    'quote',
    'string_type',
    'to_str',
    'unescape',
    'unquote',
    'urlencode',
    'urljoin',
    'urlsplit',
    'urlunsplit',
    'xbmc',
    'xbmcaddon',
    'xbmcgui',
    'xbmcplugin',
    'xbmcvfs',
)

# Kodi v19+ and Python v3.x
try:
    from html import unescape
    from http.server import BaseHTTPRequestHandler
    from socketserver import TCPServer, ThreadingMixIn
    from urllib.parse import (
        parse_qs,
        parse_qsl,
        quote,
        unquote,
        urlencode,
        urljoin,
        urlsplit,
        urlunsplit,
    )

    import xbmc
    import xbmcaddon
    import xbmcgui
    import xbmcplugin
    import xbmcvfs


    xbmc.LOGNOTICE = xbmc.LOGINFO
    xbmc.LOGSEVERE = xbmc.LOGFATAL

    string_type = str
    byte_string_type = bytes
    to_str = str


    def entity_escape(text,
                      entities=str.maketrans({
                          '&': '&amp;',
                          '"': '&quot;',
                          '<': '&lt;',
                          '>': '&gt;',
                          '\'': '&#x27;',
                      })):
        return text.translate(entities)

# Compatibility shims for Kodi v18 and Python v2.7
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler
    from contextlib import contextmanager as _contextmanager
    from SocketServer import TCPServer, ThreadingMixIn
    from urllib import (
        quote as _quote,
        unquote as _unquote,
        urlencode as _urlencode,
    )
    from urlparse import (
        parse_qs,
        parse_qsl,
        urljoin,
        urlsplit,
        urlunsplit,
    )
    from xml.sax.saxutils import unescape

    from kodi_six import (
        xbmc,
        xbmcaddon,
        xbmcgui,
        xbmcplugin,
        xbmcvfs,
    )


    def quote(data, *args, **kwargs):
        return _quote(to_str(data), *args, **kwargs)


    def unquote(data):
        return _unquote(to_str(data))


    def urlencode(data, *args, **kwargs):
        if isinstance(data, dict):
            data = data.items()
        return _urlencode({
            to_str(key): (
                [to_str(part) for part in value]
                if isinstance(value, (list, tuple)) else
                to_str(value)
            )
            for key, value in data
        }, *args, **kwargs)


    _File = xbmcvfs.File


    @_contextmanager
    def _file_closer(*args, **kwargs):
        file = None
        try:
            file = _File(*args, **kwargs)
            yield file
        finally:
            if file:
                file.close()


    xbmcvfs.File = _file_closer
    xbmcvfs.translatePath = xbmc.translatePath

    string_type = basestring
    byte_string_type = (bytes, str)


    def to_str(value):
        if isinstance(value, unicode):
            return value.encode('utf-8')
        return str(value)


    def entity_escape(text,
                      entities={
                          '&': '&amp;',
                          '"': '&quot;',
                          '<': '&lt;',
                          '>': '&gt;',
                          '\'': '&#x27;',
                      }):
        for key, value in entities.viewitems():
            text = text.replace(key, value)
        return text

# Kodi v20+
if hasattr(xbmcgui.ListItem, 'setDateTime'):
    def datetime_infolabel(datetime_obj, *_args, **_kwargs):
        return datetime_obj.replace(microsecond=0, tzinfo=None).isoformat()
# Compatibility shims for Kodi v18 and v19
else:
    def datetime_infolabel(datetime_obj, str_format='%Y-%m-%d %H:%M:%S'):
        return datetime_obj.strftime(str_format)


_cpu_count = _sched_get_affinity = None
try:
    from os import sched_getaffinity as _sched_getaffinity
except ImportError:
    try:
        from multiprocessing import cpu_count as _cpu_count
    except ImportError:
        pass


def available_cpu_count():
    if _sched_get_affinity:
        # Equivalent to os.process_cpu_count()
        return len(_sched_get_affinity(0)) or 1

    if _cpu_count:
        try:
            return _cpu_count() or 1
        except NotImplementedError:
            return 1

    return 1
