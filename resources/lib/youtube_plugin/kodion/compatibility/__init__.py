# -*- coding: utf-8 -*-
"""

    Copyright (C) 2023-present plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

__all__ = (
    'BaseHTTPServer',
    'byte_string_type',
    'datetime_infolabel',
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
    'xbmc',
    'xbmcaddon',
    'xbmcgui',
    'xbmcplugin',
    'xbmcvfs',
)

# Kodi v19+ and Python v3.x
try:
    from html import unescape
    from http import server as BaseHTTPServer
    from urllib.parse import (
        parse_qs,
        parse_qsl,
        quote,
        unquote,
        urlencode,
        urljoin,
        urlsplit,
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
# Compatibility shims for Kodi v18 and Python v2.7
except ImportError:
    import BaseHTTPServer
    from contextlib import contextmanager as _contextmanager
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

# Kodi v20+
if hasattr(xbmcgui.ListItem, 'setDateTime'):
    def datetime_infolabel(datetime_obj):
        if datetime_obj:
            return datetime_obj.replace(microsecond=0, tzinfo=None).isoformat()
        return ''
# Compatibility shims for Kodi v18 and v19
else:
    def datetime_infolabel(datetime_obj):
        if datetime_obj:
            return datetime_obj.strftime('%d.%m.%Y')
        return ''
