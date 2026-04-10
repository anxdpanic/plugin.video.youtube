# -*- coding: utf-8 -*-
"""

    Copyright (C) 2023-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""
from __future__ import absolute_import, division, unicode_literals


__all__ = (
    'BaseHTTPRequestHandler',
    'StringIO',
    'TCPServer',
    'ThreadingMixIn',
    'available_cpu_count',
    'datetime_infolabel',
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
    'to_unicode',
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

    string_type = str
    to_str = str


    def to_unicode(text):
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')
        return text


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
        parse_qs as _parse_qs,
        parse_qsl as _parse_qsl,
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


    def parse_qs(*args, **kwargs):
        num_args = len(args)
        query_dict = _parse_qs(
            to_str(args[0] if args else kwargs.get('qs')),
            keep_blank_values=(
                args[1]
                if num_args >= 2 else
                kwargs.get('keep_blank_values', 0)
            ),
            strict_parsing=(
                args[2]
                if num_args >= 3 else
                kwargs.get('strict_parsing', 0)
            ),
            # max_num_fields=(
            #     args[3]
            #     if num_args >= 4 else
            #     kwargs.get('max_num_fields', 0)
            # ),
        )
        return {
            to_unicode(key): (
                [to_unicode(part) for part in value]
                if isinstance(value, (list, tuple)) else
                to_unicode(value)
            )
            for key, value in query_dict.viewitems()
        }


    def parse_qsl(*args, **kwargs):
        num_args = len(args)
        query_list = _parse_qsl(
            to_str(args[0] if args else kwargs.get('qs')),
            keep_blank_values=(
                args[1]
                if num_args >= 2 else
                kwargs.get('keep_blank_values', 0)
            ),
            strict_parsing=(
                args[2]
                if num_args >= 3 else
                kwargs.get('strict_parsing', 0)
            ),
            # max_num_fields=(
            #     args[3]
            #     if num_args >= 4 else
            #     kwargs.get('max_num_fields', 0)
            # ),
        )
        return [
            (to_unicode(key), to_unicode(value))
            for key, value in query_list
        ]


    def quote(*args, **kwargs):
        return _quote(
            to_str(args[0] if args else kwargs.get('string')),
            safe=args[1] if len(args) >= 2 else kwargs.get('safe', '/'),
        )


    def quote_plus(*args, **kwargs):
        return _quote_plus(
            to_str(args[0] if args else kwargs.get('string')),
            safe=args[1] if len(args) >= 2 else kwargs.get('safe', '/'),
        )


    def unquote(*args, **kwargs):
        return _unquote(
            to_str(args[0] if args else kwargs.get('string'))
        )


    def unquote_plus(*args, **kwargs):
        return _unquote_plus(
            to_str(args[0] if args else kwargs.get('string'))
        )


    def urlencode(*args, **kwargs):
        query = args[0] if args else kwargs.get('query')
        if isinstance(query, dict):
            query = query.viewitems()
        return _urlencode(
            query={
                to_str(key): (
                    [to_str(part) for part in value]
                    if isinstance(value, (list, tuple)) else
                    to_str(value)
                )
                for key, value in query
            },
            doseq=args[1] if len(args) >= 2 else kwargs.get('doseq', 0),
        )


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

    string_type = basestring


    def to_str(value, _format=b'{0!s}'.format):
        if not isinstance(value, basestring):
            value = _format(value)
        elif isinstance(value, unicode):
            value = value.encode('utf-8', errors='ignore')
        return value


    def to_unicode(text):
        if isinstance(text, (bytes, str)):
            text = text.decode('utf-8', errors='ignore')
        return text


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
        return md5(b''.join(
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
