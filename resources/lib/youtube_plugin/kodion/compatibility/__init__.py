# -*- coding: utf-8 -*-
"""

    Copyright (C) 2023-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

__all__ = (
    'BaseHTTPRequestHandler',
    'StringIO',
    'TCPServer',
    'ThreadingMixIn',
    'available_cpu_count',
    'byte_string_type',
    'datetime_infolabel',
    'default_quote',
    'default_quote_plus',
    'entity_escape',
    'generate_hash',
    'parse_qs',
    'parse_qsl',
    'pickle',
    'quote',
    'quote_plus',
    'range_type',
    'string_type',
    'to_str',
    'unescape',
    'unquote',
    'unquote_plus',
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
    import _pickle as pickle
    from hashlib import md5
    from html import unescape
    from http.server import BaseHTTPRequestHandler
    from io import StringIO
    from socketserver import TCPServer, ThreadingMixIn
    from urllib.parse import (
        parse_qs,
        parse_qsl,
        quote,
        quote_plus,
        unquote,
        unquote_plus,
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

    range_type = (range, list)

    byte_string_type = bytes
    string_type = str
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


    def generate_hash(*args, **kwargs):
        return md5(''.join(
            map(str, args or kwargs.get('iter'))
        ).encode('utf-8')).hexdigest()


    SAFE_CHARS = frozenset(
        b'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        b'abcdefghijklmnopqrstuvwxyz'
        b'0123456789'
        b'_.-~'
        b'/'  # safe character by default
    )
    reserved = {
        chr(ordinal): '%%%x' % ordinal
        for ordinal in range(0, 128)
        if ordinal not in SAFE_CHARS
    }
    reserved_plus = reserved.copy()
    reserved_plus.update((
        ('/', '%2f'),
        (' ', '+'),
    ))
    reserved = str.maketrans(reserved)
    reserved_plus = str.maketrans(reserved_plus)
    non_ascii = str.maketrans({
        chr(ordinal): '%%%x' % ordinal
        for ordinal in range(128, 256)
    })


    def default_quote(string,
                      safe='',
                      encoding=None,
                      errors=None,
                      _encoding='utf-8',
                      _errors='strict',
                      _reserved=reserved,
                      _non_ascii=non_ascii,
                      _encode=str.encode,
                      _is_ascii=str.isascii,
                      _replace=str.replace,
                      _old='\\x',
                      _new='%',
                      _slice=slice(2, -1),
                      _str=str,
                      _translate=str.translate):
        _string = _translate(string, _reserved)
        if _is_ascii(_string):
            return _string
        _string = _str(_encode(_string, _encoding, _errors))[_slice]
        if _string == string:
            if _is_ascii(_string):
                return _string
            return _translate(_string, _non_ascii)
        if _is_ascii(_string):
            return _replace(_string, _old, _new)
        return _translate(_replace(_string, _old, _new), _non_ascii)


    def default_quote_plus(string,
                           safe='',
                           encoding=None,
                           errors=None,
                           _encoding='utf-8',
                           _errors='strict',
                           _reserved=reserved_plus,
                           _non_ascii=non_ascii,
                           _encode=str.encode,
                           _is_ascii=str.isascii,
                           _replace=str.replace,
                           _old='\\x',
                           _new='%',
                           _slice=slice(2, -1),
                           _str=str,
                           _translate=str.translate):
        if (not safe and encoding is None and errors is None
                and isinstance(string, str)):
            _string = _translate(string, _reserved)
            if _is_ascii(_string):
                return _string
            _string = _str(_encode(_string, _encoding, _errors))[_slice]
            if _string == string:
                if _is_ascii(_string):
                    return _string
                return _translate(_string, _non_ascii)
            if _is_ascii(_string):
                return _replace(_string, _old, _new)
            return _translate(_replace(_string, _old, _new), _non_ascii)
        return quote_plus(string, safe, encoding, errors)


    urlencode.__defaults__ = (False, '', None, None, default_quote_plus)

# Compatibility shims for Kodi v18 and Python v2.7
except ImportError:
    import cPickle as pickle
    from hashlib import md5
    from BaseHTTPServer import BaseHTTPRequestHandler
    from SocketServer import TCPServer, ThreadingMixIn
    from StringIO import StringIO as _StringIO
    from urllib import (
        quote as _quote,
        quote_plus as _quote_plus,
        unquote as _unquote,
        unquote_plus as _unquote_plus,
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


    default_quote = quote


    def quote_plus(data, *args, **kwargs):
        return _quote_plus(to_str(data), *args, **kwargs)


    default_quote_plus = quote_plus


    def unquote(data):
        return _unquote(to_str(data))


    def unquote_plus(data):
        return _unquote_plus(to_str(data))


    def urlencode(data, *args, **kwargs):
        if isinstance(data, dict):
            data = data.items()
        kwargs = {
            key: value
            for key, value in kwargs.viewitems()
            if key in {'query', 'doseq'}
        }
        return _urlencode({
            to_str(key): (
                [to_str(part) for part in value]
                if isinstance(value, (list, tuple)) else
                to_str(value)
            )
            for key, value in data
        }, *args, **kwargs)


    class StringIO(_StringIO):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.close()


    class File(xbmcvfs.File):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.close()


    xbmcvfs.File = File
    xbmcvfs.translatePath = xbmc.translatePath

    range_type = (xrange, list)

    byte_string_type = (bytes, str)
    string_type = basestring


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


    def generate_hash(*args, **kwargs):
        return md5(''.join(
            map(to_str, args or kwargs.get('iter'))
        )).hexdigest()


    def _loads(string, _loads=pickle.loads):
        return _loads(to_str(string))


    pickle.loads = _loads

# Kodi v20+
if hasattr(xbmcgui.ListItem, 'setDateTime'):
    def datetime_infolabel(datetime_obj, *_args, **_kwargs):
        return datetime_obj.replace(microsecond=0, tzinfo=None).isoformat()
# Compatibility shims for Kodi v18 and v19
else:
    def datetime_infolabel(datetime_obj, str_format='%Y-%m-%d %H:%M:%S'):
        return datetime_obj.strftime(str_format)

try:
    from os import sched_getaffinity as _sched_get_affinity
except ImportError:
    _sched_get_affinity = None
    try:
        from multiprocessing import cpu_count as _cpu_count
    except ImportError:
        _cpu_count = None


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
