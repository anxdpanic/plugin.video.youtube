# -*- coding: utf-8 -*-
"""

    Copyright (C) 2023-present plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import atexit

from traceback import format_exc, format_stack

from requests import Session
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import RequestException


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

    def __init__(self, context, exc_type=RequestException):
        self._context = context
        self._verify = self._context.get_settings().verify_ssl()
        self._timeout = self._context.get_settings().get_timeout()
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
                cookies=None, data=None, headers=None, json=None, params=None,
                response_hook=None, error_hook=None,
                error_title=None, error_info=None, raise_exc=False, **_):
        response = None
        try:
            response = self._session.request(method, url,
                                             verify=self._verify,
                                             allow_redirects=True,
                                             timeout=self._timeout,
                                             cookies=cookies,
                                             data=data,
                                             headers=headers,
                                             json=json,
                                             params=params)
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

            self._context.log_error('\n'.join([part for part in [
                error_title, error_info, response_text, stack_trace, exc_tb
            ] if part]))

            if raise_exc:
                if isinstance(raise_exc, BaseException):
                    raise raise_exc from exc
                if not callable(raise_exc):
                    raise self._default_exc(error_title) from exc
                raise raise_exc(error_title) from exc

        return response
