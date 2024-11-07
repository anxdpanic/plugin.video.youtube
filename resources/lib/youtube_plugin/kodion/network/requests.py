# -*- coding: utf-8 -*-
"""

    Copyright (C) 2023-present plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import atexit
import socket
from traceback import format_stack

from requests import Session
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import InvalidJSONError, RequestException
from requests.utils import DEFAULT_CA_BUNDLE_PATH, extract_zipped_paths
from urllib3.util.ssl_ import create_urllib3_context

from ..logger import Logger


__all__ = (
    'BaseRequestsClass',
    'InvalidJSONError'
)


class SSLHTTPAdapter(HTTPAdapter):
    _SOCKET_OPTIONS = (
        (socket.SOL_SOCKET, getattr(socket, 'SO_KEEPALIVE', None), 1),
        (socket.IPPROTO_TCP, getattr(socket, 'TCP_NODELAY', None), 1),
        (socket.IPPROTO_TCP, getattr(socket, 'TCP_KEEPIDLE', None), 300),
        # TCP_KEEPALIVE equivalent to TCP_KEEPIDLE on iOS/macOS
        (socket.IPPROTO_TCP, getattr(socket, 'TCP_KEEPALIVE', None), 300),
        # TCP_KEEPINTVL may not be implemented at app level on iOS/macOS
        (socket.IPPROTO_TCP, getattr(socket, 'TCP_KEEPINTVL', None), 60),
        # TCP_KEEPCNT may not be implemented at app level on iOS/macOS
        (socket.IPPROTO_TCP, getattr(socket, 'TCP_KEEPCNT', None), 5),
        # TCP_USER_TIMEOUT = TCP_KEEPIDLE + TCP_KEEPINTVL * TCP_KEEPCNT
        (socket.IPPROTO_TCP, getattr(socket, 'TCP_USER_TIMEOUT', None), 600),
    )

    _ssl_context = create_urllib3_context()
    _ssl_context.load_verify_locations(
        capath=extract_zipped_paths(DEFAULT_CA_BUNDLE_PATH)
    )

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self._ssl_context

        kwargs['socket_options'] = [
            socket_option for socket_option in self._SOCKET_OPTIONS
            if socket_option[1] is not None
        ]

        return super(SSLHTTPAdapter, self).init_poolmanager(*args, **kwargs)

    def cert_verify(self, conn, url, verify, cert):
        self._ssl_context.check_hostname = bool(verify)
        return super(SSLHTTPAdapter, self).cert_verify(conn, url, verify, cert)


class BaseRequestsClass(Logger):
    _session = Session()
    _session.mount('https://', SSLHTTPAdapter(
        pool_maxsize=10,
        pool_block=True,
        max_retries=Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist={500, 502, 503, 504},
            allowed_methods=None,
        )
    ))
    atexit.register(_session.close)

    def __init__(self, context, exc_type=None):
        settings = context.get_settings()
        self._verify = settings.verify_ssl()
        self._timeout = settings.requests_timeout()
        self._proxy = settings.proxy_settings()

        if isinstance(exc_type, tuple):
            self._default_exc = (RequestException,) + exc_type
        elif exc_type:
            self._default_exc = (RequestException, exc_type)
        else:
            self._default_exc = (RequestException,)

    def __enter__(self):
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self._session.close()

    def request(self, url, method='GET',
                params=None, data=None, headers=None, cookies=None, files=None,
                auth=None, timeout=None, allow_redirects=None, proxies=None,
                hooks=None, stream=None, verify=None, cert=None, json=None,
                # Custom event hook implementation
                # See _response_hook and _error_hook in login_client.py
                # for example usage
                response_hook=None,
                response_hook_kwargs=None,
                error_hook=None,
                error_hook_kwargs=None,
                error_title=None, error_info=None, raise_exc=False, **_):
        if timeout is None:
            timeout = self._timeout
        if verify is None:
            verify = self._verify
        if proxies is None:
            proxies = self._proxy
        if allow_redirects is None:
            allow_redirects = True

        response = None
        try:
            response = self._session.request(method, url,
                                             params=params,
                                             data=data,
                                             headers=headers,
                                             cookies=cookies,
                                             files=files,
                                             auth=auth,
                                             timeout=timeout,
                                             allow_redirects=allow_redirects,
                                             proxies=proxies,
                                             hooks=hooks,
                                             stream=stream,
                                             verify=verify,
                                             cert=cert,
                                             json=json)
            if not getattr(response, 'status_code', None):
                raise self._default_exc[0](response=response)

            if response_hook:
                if response_hook_kwargs is None:
                    response_hook_kwargs = {}
                response_hook_kwargs['response'] = response
                response = response_hook(**response_hook_kwargs)
            else:
                response.raise_for_status()

        except self._default_exc as exc:
            exc_response = exc.response or response
            response_text = exc_response and exc_response.text
            stack = format_stack()
            error_details = {'exc': exc}

            if error_hook:
                if error_hook_kwargs is None:
                    error_hook_kwargs = {}
                error_hook_kwargs['exc'] = exc
                error_hook_kwargs['response'] = exc_response
                error_response = error_hook(**error_hook_kwargs)
                _title, _info, _detail, _response, _trace, _exc = error_response
                if _title is not None:
                    error_title = _title
                if _info is not None:
                    error_info = _info
                if _detail is not None:
                    error_details.update(_detail)
                if _response is not None:
                    response = _response
                    response_text = repr(_response)
                if _trace is not None:
                    stack = _trace
                if _exc is not None:
                    raise_exc = _exc

            if error_title is None:
                error_title = 'Request - Failed'

            if error_info is None:
                try:
                    error_info = ('Status:    {0.status_code} - {0.reason}'
                                  .format(exc.response))
                except AttributeError:
                    error_info = ('Exception: {exc!r}'
                                  .format(exc=exc))
            elif '{' in error_info:
                try:
                    error_info = error_info.format(**error_details)
                except (AttributeError, IndexError, KeyError):
                    error_info = ('Exception: {exc!r}'
                                  .format(exc=exc))

            if response_text:
                response_text = ('Response:   {0}'
                                 .format(response_text))

            if stack:
                stack = 'Stack trace (most recent call last):\n{stack}'.format(
                    stack=''.join(stack)
                )

            self.log_error('\n\t'.join([part for part in [
                error_title, error_info, response_text, stack
            ] if part]))

            if raise_exc:
                if not isinstance(raise_exc, BaseException):
                    if not callable(raise_exc):
                        raise_exc = self._default_exc[-1]
                    raise_exc = raise_exc(error_title)

                if isinstance(raise_exc, BaseException):
                    raise_exc.__cause__ = exc
                    raise raise_exc
                raise exc

        return response
