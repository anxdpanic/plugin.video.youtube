# -*- coding: utf-8 -*-
"""

    Copyright (C) 2023-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import socket
from atexit import register as atexit_register
from collections import OrderedDict

from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import InvalidJSONError, RequestException, URLRequired
from requests.hooks import default_hooks
from requests.models import DEFAULT_REDIRECT_LIMIT, Request
from requests.sessions import Session
from requests.utils import (
    DEFAULT_CA_BUNDLE_PATH,
    cookiejar_from_dict,
    default_headers,
    extract_zipped_paths,
)
from urllib3.util.ssl_ import create_urllib3_context

from .. import logging
from ..utils.datetime import imf_fixdate
from ..utils.methods import generate_hash


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


class CustomSession(Session):
    def __init__(self):
        #: A case-insensitive dictionary of headers to be sent on each
        #: :class:`Request <Request>` sent from this
        #: :class:`Session <Session>`.
        self.headers = default_headers()

        #: Default Authentication tuple or object to attach to
        #: :class:`Request <Request>`.
        self.auth = None

        #: Dictionary mapping protocol or protocol and host to the URL of the proxy
        #: (e.g. {'http': 'foo.bar:3128', 'http://host.name': 'foo.bar:4012'}) to
        #: be used on each :class:`Request <Request>`.
        self.proxies = {}

        #: Event-handling hooks.
        self.hooks = default_hooks()

        #: Dictionary of querystring data to attach to each
        #: :class:`Request <Request>`. The dictionary values may be lists for
        #: representing multivalued query parameters.
        self.params = {}

        #: Stream response content default.
        self.stream = False

        #: SSL Verification default.
        #: Defaults to `True`, requiring requests to verify the TLS certificate at the
        #: remote end.
        #: If verify is set to `False`, requests will accept any TLS certificate
        #: presented by the server, and will ignore hostname mismatches and/or
        #: expired certificates, which will make your application vulnerable to
        #: man-in-the-middle (MitM) attacks.
        #: Only set this to `False` for testing.
        self.verify = True

        #: SSL client certificate default, if String, path to ssl client
        #: cert file (.pem). If Tuple, ('cert', 'key') pair.
        self.cert = None

        #: Maximum number of redirects allowed. If the request exceeds this
        #: limit, a :class:`TooManyRedirects` exception is raised.
        #: This defaults to requests.models.DEFAULT_REDIRECT_LIMIT, which is
        #: 30.
        self.max_redirects = DEFAULT_REDIRECT_LIMIT

        #: Trust environment settings for proxy configuration, default
        #: authentication and similar.
        #: CustomSession.trust_env is False
        self.trust_env = False

        #: A CookieJar containing all currently outstanding cookies set on this
        #: session. By default it is a
        #: :class:`RequestsCookieJar <requests.cookies.RequestsCookieJar>`, but
        #: may be any other ``cookielib.CookieJar`` compatible object.
        self.cookies = cookiejar_from_dict({})

        # Default connection adapters.
        self.adapters = OrderedDict()
        self.mount('https://', SSLHTTPAdapter(
            pool_maxsize=20,
            pool_block=True,
            max_retries=Retry(
                total=3,
                backoff_factor=0.1,
                status_forcelist={500, 502, 503, 504},
                allowed_methods=None,
            )
        ))
        self.mount('http://', HTTPAdapter())


class BaseRequestsClass(object):
    log = logging.getLogger(__name__)

    _session = CustomSession()
    atexit_register(_session.close)

    _context = None
    _verify = True
    _timeout = (9.5, 27)
    _proxy = None
    _default_exc = (RequestException,)

    METHODS_TO_CACHE = {'GET', 'HEAD'}

    def __init__(self,
                 context=None,
                 verify_ssl=None,
                 timeout=None,
                 proxy_settings=None,
                 exc_type=None,
                 **_kwargs):
        super(BaseRequestsClass, self).__init__()
        BaseRequestsClass.init(
            context=context,
            verify_ssl=verify_ssl,
            timeout=timeout,
            proxy_settings=proxy_settings,
        )
        self._default_exc = (
            (RequestException,) + exc_type
            if isinstance(exc_type, tuple) else
            (RequestException, exc_type)
            if exc_type else
            (RequestException,)
        )

    @classmethod
    def init(cls,
             context=None,
             verify_ssl=None,
             timeout=None,
             proxy_settings=None,
             **_kwargs):
        cls._context = (cls._context
                        if context is None else
                        context)
        if cls._context:
            settings = cls._context.get_settings()
            cls._verify = (settings.verify_ssl()
                           if verify_ssl is None else
                           verify_ssl)
            cls._timeout = (settings.requests_timeout()
                            if timeout is None else
                            timeout)
            cls._proxy = (settings.proxy_settings()
                          if proxy_settings is None else
                          proxy_settings)

    def reinit(self, **kwargs):
        self.__init__(**kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self._session.close()

    @staticmethod
    def _raise_exception(new_exception, *args, **kwargs):
        if not new_exception:
            return
        if issubclass(new_exception, RequestException):
            new_exception = new_exception(*args)
            attrs = new_exception.__dict__
            for attr, value in kwargs.items():
                if attr not in attrs:
                    setattr(new_exception, attr, value)
            raise new_exception
        else:
            raise new_exception(*args, **kwargs)

    def _response_hook_json(self, **kwargs):
        response = kwargs['response']
        if response is None:
            return None, None
        with response:
            try:
                json_data = response.json()
                if 'error' in json_data:
                    kwargs.setdefault('pass_data', True)
                    kwargs.setdefault('json_data', json_data)
                    json_data.setdefault('code', response.status_code)
                    self._raise_exception(
                        kwargs.get('exception', RequestException),
                        '"error" in response JSON data',
                        **kwargs
                    )
            except ValueError as exc:
                if kwargs.get('raise_exc') is None:
                    kwargs['raise_exc'] = True
                self._raise_exception(
                    InvalidJSONError,
                    exc,
                    **kwargs
                )

            response.raise_for_status()

        return json_data.get('etag'), json_data

    def _response_hook_text(self, **kwargs):
        response = kwargs['response']
        if response is None:
            return None, None
        with response:
            response.raise_for_status()
            result = response and response.text
        if not result:
            self._raise_exception(
                kwargs.get('exception', RequestException),
                'Empty response text',
                **kwargs
            )

        return None, result

    def request(self, url=None, method='GET',
                params=None, data=None, headers=None, cookies=None, files=None,
                auth=None, timeout=None, allow_redirects=None, proxies=None,
                hooks=None, stream=None, verify=None, cert=None, json=None,
                prepared_request=None,
                # Custom event hook implementation
                # See _response_hook and _error_hook in login_client.py
                # for example usage
                response_hook=None,
                error_hook=None,
                event_hook_kwargs=None,
                error_title=None,
                error_info=None,
                raise_exc=None,
                cache=None,
                **kwargs):
        if timeout is None:
            timeout = self._timeout
        if verify is None:
            verify = self._verify
        if proxies is None:
            proxies = self._proxy
        if allow_redirects is None:
            allow_redirects = True
        stacklevel = kwargs.pop('stacklevel', 2)

        response = None
        request_id = None
        cached_response = None
        etag = None
        timestamp = None

        if url:
            prepared_request = self._session.prepare_request(Request(
                method=method,
                url=url,
                headers=headers,
                files=files,
                data=data,
                json=json,
                params=params,
                auth=auth,
                cookies=cookies,
                hooks=hooks,
            ))

        if cache is not False:
            if prepared_request:
                method = prepared_request.method
                if cache is True or method in self.METHODS_TO_CACHE:
                    headers = prepared_request.headers
                    request_id = generate_hash(
                        method,
                        prepared_request.url,
                        headers,
                        prepared_request.body,
                    )

            if request_id:
                if cache == 'refresh':
                    cache = self._context.get_requests_cache()
                    cached_request = None
                else:
                    cache = self._context.get_requests_cache()
                    cached_request = cache.get(request_id)
            else:
                cache = False
                cached_request = None

            if cached_request:
                etag, cached_response = cached_request['value']
                if cached_response is not None:
                    if etag:
                        # Etag is meant to be enclosed in double quotes, but the
                        # Google servers don't seem to support this
                        headers['If-None-Match'] = '"{0}", {0}'.format(etag)
                    timestamp = imf_fixdate(cached_request['timestamp'])
                    headers['If-Modified-Since'] = timestamp
                    self.log.debug(('Cached response',
                                    'Request ID: {request_id}',
                                    'Etag:       {etag}',
                                    'Modified:   {timestamp}'),
                                   request_id=request_id,
                                   etag=etag,
                                   timestamp=timestamp,
                                   stacklevel=stacklevel)

        if event_hook_kwargs is None:
            event_hook_kwargs = {}

        try:
            if prepared_request:
                response = self._session.send(
                    request=prepared_request,
                    stream=stream,
                    verify=verify,
                    proxies=proxies,
                    cert=cert,
                    timeout=timeout,
                    allow_redirects=allow_redirects,
                )
            else:
                raise URLRequired()

            status_code = getattr(response, 'status_code', None)
            if not status_code:
                raise self._default_exc[0](response=response)

            if cached_response is None or status_code != 304:
                timestamp = response.headers.get('Date')
                if response_hook:
                    event_hook_kwargs['exception'] = self._default_exc[-1]
                    event_hook_kwargs['raise_exc'] = raise_exc
                    event_hook_kwargs['response'] = response
                    etag, response = response_hook(**event_hook_kwargs)
                else:
                    etag = None
                    response.raise_for_status()
                # Only clear cached response if there was no error response
                cached_response = None

        except self._default_exc as exc:
            exc_response = exc.response or response
            if exc_response:
                response_text = exc_response.text
                response_status = exc_response.status_code
                response_reason = exc_response.reason
            else:
                response_text = None
                response_status = 'Error'
                response_reason = 'No response'

            log_msg = [
                '{title}',
                'URL:      {method} {url}',
                'Status:   {response_status} - {response_reason}',
                'Response: {response_text}',
            ]

            kwargs.update(event_hook_kwargs)
            kwargs['exc'] = exc
            kwargs['response'] = exc_response

            if error_hook:
                error_response = error_hook(**kwargs)
                _title, _info, _detail, _response, _exc = error_response
                if _title is not None:
                    error_title = _title
                if _info:
                    if isinstance(_info, (list, tuple)):
                        log_msg.extend(_info)
                    else:
                        log_msg.append(_info)
                if _detail is not None:
                    kwargs.update(_detail)
                if _response is not None:
                    response = _response
                    if response and not response_text:
                        response_text = repr(_response)
                if _exc is not None:
                    raise_exc = _exc

            if error_info:
                if isinstance(error_info, (list, tuple)):
                    log_msg.extend(error_info)
                else:
                    log_msg.append(error_info)

            self.log.exception(log_msg,
                               title=(error_title or 'Failed'),
                               method=method,
                               url=url,
                               response_status=response_status,
                               response_reason=response_reason,
                               response_text=response_text,
                               stacklevel=stacklevel,
                               **kwargs)

            if raise_exc:
                if not isinstance(raise_exc, BaseException):
                    if not callable(raise_exc):
                        raise_exc = self._default_exc[-1]
                    raise_exc = raise_exc(error_title)

                if isinstance(raise_exc, BaseException):
                    raise_exc.__cause__ = exc
                    raise raise_exc
                raise exc

        if not cache:
            pass
        elif cached_response is not None:
            self.log.debug(('Using cached response',
                            'Request ID: {request_id}',
                            'Etag:       {etag}',
                            'Modified:   {timestamp}'),
                           request_id=request_id,
                           etag=etag,
                           timestamp=timestamp,
                           stacklevel=stacklevel)
            cache.set(request_id)
            response = cached_response
        elif response is not None:
            self.log.debug(('Saving response to cache',
                            'Request ID: {request_id}',
                            'Etag:       {etag}',
                            'Modified:   {timestamp}'),
                           request_id=request_id,
                           etag=etag,
                           timestamp=timestamp,
                           stacklevel=stacklevel)
            cache.set(request_id, response, etag)

        return response
