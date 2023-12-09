# -*- coding: utf-8 -*-
"""

    Copyright (C) 2023-present plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import atexit
from traceback import format_exc, format_stack

from requests import Session
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import RequestException

from ..compatibility import xbmcaddon
from ..logger import log_error
from ..settings import Settings


_settings = Settings(xbmcaddon.Addon(id='plugin.video.youtube'))


class BaseRequestsClass(object):
    http_adapter = HTTPAdapter(
        pool_maxsize=10,
        pool_block=True,
        max_retries=Retry(
            total=3,
            backoff_factor=1,
            status_forcelist={500, 502, 503, 504},
            allowed_methods=None,
        )
    )

    def __init__(self, exc_type=RequestException):
        self._verify = _settings.verify_ssl()
        self._timeout = _settings.get_timeout()
        self._default_exc = exc_type

        self._session = Session()
        self._session.verify = self._verify
        self._session.mount('https://', self.http_adapter)
        atexit.register(self._session.close)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._session.close()

    def request(self, url, method='GET',
                params=None, data=None, headers=None, cookies=None, files=None,
                auth=None, timeout=None, allow_redirects=None, proxies=None,
                hooks=None, stream=None, verify=None, cert=None, json=None,
                # Custom event hook implementation
                # See _login_json_hook and _login_error_hook in login_client.py
                # for example usage
                response_hook=None, error_hook=None,
                error_title=None, error_info=None, raise_exc=False, **_):
        if timeout is None:
            timeout = self._timeout
        if verify is None:
            verify = self._verify
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
                                             json=json,)
            if response_hook:
                response = response_hook(response)
            else:
                response.raise_for_status()

        except (RequestException, self._default_exc) as exc:
            response_text = exc.response and exc.response.text
            stack_trace = format_stack()
            exc_tb = format_exc()

            if error_hook:
                error_response = error_hook(exc, response)
                _title, _info, _response, _trace, _exc = error_response
                if _title is not None:
                    error_title = _title
                if _info is not None:
                    error_info = _info
                if _response is not None:
                    response = _response
                    response_text = str(_response)
                if _trace is not None:
                    stack_trace = _trace
                if _exc is not None:
                    raise_exc = _exc

            if error_title is None:
                error_title = 'Request failed'

            if error_info is None:
                error_info = str(exc)
            elif '{' in error_info:
                try:
                    error_info = error_info.format(exc=exc)
                except (AttributeError, IndexError, KeyError):
                    error_info = str(exc)

            if response_text:
                response_text = 'Request response:\n{0}'.format(response_text)

            if stack_trace:
                stack_trace = (
                    'Stack trace (most recent call last):\n{0}'.format(
                        ''.join(stack_trace)
                    )
                )

            log_error('\n'.join([part for part in [
                error_title, error_info, response_text, stack_trace, exc_tb
            ] if part]))

            if raise_exc:
                if isinstance(raise_exc, BaseException):
                    raise raise_exc(exc)
                if callable(raise_exc):
                    raise raise_exc(error_title)(exc)
                raise self._default_exc(error_title)(exc)

        return response
