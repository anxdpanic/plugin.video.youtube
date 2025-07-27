# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from base64 import urlsafe_b64decode
from re import compile as re_compile
from ..compatibility import parse_qs, urlencode, urlsplit, urlunsplit


def redact_ip_in_uri(
    url,
    _re=re_compile(r'([?&/]|%3F|%26|%2F)ip([=/]|%3D|%2F)[^?&/%]+'),
):
    return _re.sub(r'\g<1>ip\g<2><redacted>', url)


def redact_auth_header(headers,
                       _re=re_compile(r'"Authorization": "[^"]+"')):
    if isinstance(headers, dict):
        log_headers = headers.copy()
        if 'Authorization' in log_headers:
            log_headers['Authorization'] = '<redacted>'
        return log_headers
    return _re.sub(r'"Authorization": "<redacted>"', headers)


def redact_license_info(license_info):
    license_info = license_info.copy()
    for detail in ('url', 'token'):
        if detail in license_info:
            license_info[detail] = '<redacted>'
    return license_info


def redact_params(params):
    log_params = params.copy()
    for param, value in params.items():
        if param in {'key', 'api_key', 'api_secret', 'client_secret'}:
            log_value = (
                ['...'.join((val[:3], val[-3:]))
                 if len(val) > 9 else
                 '...'
                 for val in value]
                if isinstance(value, (list, tuple)) else
                '...'.join((value[:3], value[-3:]))
                if len(value) > 9 else
                '...'
            )
        elif param in {'api_id', 'client_id'}:
            log_value = (
                ['...'.join((val[:3], val[-5:]))
                 if len(val) > 11 else
                 '...'
                 for val in value]
                if isinstance(value, (list, tuple)) else
                '...'.join((value[:3], value[-5:]))
                if len(value) > 11 else
                '...'
            )
        elif param in {'access_token',
                       'ip',
                       'playback_stats',
                       'refresh_token',
                       'token'}:
            log_value = (
                ['<redacted>' for _ in value]
                if isinstance(value, (list, tuple)) else
                '<redacted>'
            )
        elif param in {'url',
                       'playing_file'}:
            log_value = (
                [redact_ip_in_uri(val) for val in value]
                if isinstance(value, (list, tuple)) else
                redact_ip_in_uri(value)
            )
        elif param == 'location':
            log_value = (
                ['xx.xxxx,xx.xxxx' for _ in value]
                if isinstance(value, (list, tuple)) else
                'xx.xxxx,xx.xxxx'
            )
        elif param in {'headers', '__headers'}:
            log_value = (
                [redact_auth_header(val) for val in value]
                if isinstance(value, (list, tuple)) else
                redact_auth_header(value)
            )
        elif param == 'license_info':
            log_value = (
                [redact_license_info(val) for val in value]
                if isinstance(value, (list, tuple)) else
                redact_license_info(value)
            )
        else:
            continue
        log_params[param] = log_value
    return log_params


def parse_and_redact_uri(uri, redact_only=False):
    parts = urlsplit(uri)
    if parts.query:
        params = parse_qs(parts.query, keep_blank_values=True)
        headers = params.get('__headers', [None])[0]
        if headers:
            params['__headers'] = [urlsafe_b64decode(headers).decode('utf-8')]
        log_params = redact_params(params)
        log_uri = urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(log_params, doseq=True),
            '',
        ))
    else:
        params = log_params = None
        log_uri = uri
    if redact_only:
        return log_uri
    return parts, params, log_uri, log_params
