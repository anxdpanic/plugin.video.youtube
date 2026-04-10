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

from ..compatibility import (
    parse_qs,
    string_type,
    urlencode,
    urlsplit,
    urlunsplit,
)
from ..constants.const_settings import API_ID, API_KEY, API_SECRET, LOCATION


def redact_ip(url,
              _re=re_compile(r'([?&/]|%3F|%26|%2F)ip([=/]|%3D|%2F)[^?&/%]+')):
    return _re.sub(r'\g<1>ip\g<2>REDACTED', url)


def redact_auth_header(headers,
                       _re=re_compile(r'"Authorization": "[^"]+"')):
    if not headers:
        return headers

    if isinstance(headers, dict):
        log_headers = headers.copy()
        if 'Authorization' in log_headers:
            log_headers['Authorization'] = 'REDACTED'
        return log_headers
    return _re.sub(r'"Authorization": "REDACTED"', headers)


def redact_license_info(license_info):
    license_info = license_info.copy()
    for detail in ('url', 'token'):
        if detail in license_info:
            license_info[detail] = 'REDACTED'
    return license_info


def redact_params(params,
                  _seq_types=(list, tuple),
                  _partially_redacted_secret_params=frozenset((
                          'key',
                          'api_key',
                          API_KEY,
                          'api_secret',
                          API_SECRET,
                          'client_secret',
                          'secret',
                  )),
                  _partially_redacted_id_params=frozenset((
                          'api_id',
                          API_ID,
                          'client_id',
                  )),
                  _fully_redacted_params=frozenset((
                          'access_token',
                          'code',
                          'ip',
                          'playback_stats',
                          'refresh_token',
                          'token',
                  )),
                  _path_params=frozenset((
                          'conn',
                  )),
                  _query_params=frozenset((
                          'stream',
                  )),
                  _url_params=frozenset((
                          'playing_file',
                          'url',
                  )),
                  _location_params=frozenset((
                          'location',
                          LOCATION,
                  )),
                  _header_params=frozenset((
                          'headers',
                          '__headers',
                  ))):
    if not params:
        return params

    log_params = params.copy()
    for param, value in params.items():
        if not value:
            continue

        if isinstance(value, dict):
            log_params[param] = redact_params(value)
            continue

        if isinstance(value, _seq_types):
            doseq = True
        else:
            doseq = False
            value = (value,)

        if param in _partially_redacted_secret_params:
            log_value = [
                '...'.join((val[:3], val[-3:]))
                if len(val) > 9 else
                '...'
                for val in value
            ]
        elif param in _partially_redacted_id_params:
            log_value = []
            for val in value:
                val = val.replace('.apps.googleusercontent.com', '')
                if len(val) > 11:
                    log_value.append('...'.join((val[:3], val[-5:])))
                else:
                    log_value.append('...')
        elif param in _fully_redacted_params:
            log_value = [
                'REDACTED'
                for _ in value
            ]
        elif param in _path_params:
            log_value = [
                redact_ip(val)
                for val in value
            ]
        elif param in _query_params:
            log_value = [
                parse_and_redact_uri(
                    val if val.startswith('?') else '?' + val,
                    redact_only=True,
                )
                for val in value
            ]
        elif param in _url_params:
            log_value = [
                parse_and_redact_uri(val, redact_only=True)
                for val in value
            ]
        elif param in _location_params:
            log_value = [
                'xx.xxxx,xx.xxxx'
                for _ in value
            ]
        elif param in _header_params:
            log_value = [
                redact_auth_header(val)
                for val in value
            ]
        elif param == 'license_info':
            log_value = [
                redact_license_info(val)
                for val in value
            ]
        else:
            continue
        log_params[param] = log_value if doseq else log_value[0]
    return log_params


def parse_and_redact_uri(uri, redact_only=False):
    if not isinstance(uri, string_type):
        uri = getattr(uri, 'group', str)()
        redact_only = True

    parts = urlsplit(uri or '')

    log_path = redact_ip(parts.path)

    if parts.query:
        params = parse_qs(parts.query, keep_blank_values=True)
        headers = params.get('__headers', [None])[0]
        if headers:
            params['__headers'] = [
                urlsafe_b64decode(headers.encode('utf-8')).decode('utf-8')
            ]
        log_params = redact_params(params)
        log_query = urlencode(log_params, doseq=True)
    else:
        params = log_params = None
        log_query = ''

    log_uri = urlunsplit((
        parts.scheme,
        parts.netloc,
        log_path,
        log_query,
        '',
    ))

    if redact_only:
        return log_uri
    return parts, params, log_uri, log_params, log_path
