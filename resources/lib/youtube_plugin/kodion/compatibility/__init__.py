# -*- coding: utf-8 -*-
"""

    Copyright (C) 2023-present plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

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

    from infotagger.listitem import set_info_tag

    xbmc.LOGNOTICE = xbmc.LOGINFO
    xbmc.LOGSEVERE = xbmc.LOGFATAL

    string_type = str

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
        return _quote(data.encode('utf-8'), *args, **kwargs)


    def unquote(data):
        return _unquote(data.encode('utf-8'))


    def urlencode(data, *args, **kwargs):
        if isinstance(data, dict):
            data = data.items()
        return _urlencode({
            key.encode('utf-8'): (
                [part.encode('utf-8') if isinstance(part, unicode)
                 else str(part)
                 for part in value] if isinstance(value, (list, tuple))
                else value.encode('utf-8') if isinstance(value, unicode)
                else str(value)
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


    def set_info_tag(listitem, infolabels, tag_type, *_args, **_kwargs):
        listitem.setInfo(tag_type, infolabels)
        return ListItemInfoTag(listitem, tag_type)


    class ListItemInfoTag(object):
        __slots__ = ('__li__',)

        def __init__(self, listitem, *_args, **_kwargs):
            self.__li__ = listitem

        def add_stream_info(self, *args, **kwargs):
            return self.__li__.addStreamInfo(*args, **kwargs)

        def set_resume_point(self,
                             infoproperties,
                             resume_key='ResumeTime',
                             total_key='TotalTime'):
            if resume_key in infoproperties:
                infoproperties[resume_key] = str(infoproperties[resume_key])
            if total_key in infoproperties:
                infoproperties[total_key] = str(infoproperties[total_key])


    string_type = basestring

__all__ = (
    'BaseHTTPServer',
    'parse_qs',
    'parse_qsl',
    'quote',
    'set_info_tag',
    'string_type',
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
