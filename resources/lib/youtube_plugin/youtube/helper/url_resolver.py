# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import re
from urllib.parse import parse_qsl
from urllib.parse import urlparse
from urllib.parse import parse_qs
from urllib.parse import urlunsplit
from urllib.parse import urlencode

from ...kodion.utils import FunctionCache
from ...kodion import Context as _Context
import requests


class AbstractResolver(object):
    def __init__(self):
        self._verify = _Context(plugin_id='plugin.video.youtube').get_settings().verify_ssl()

    def supports_url(self, url, url_components):
        raise NotImplementedError()

    def resolve(self, url, url_components):
        raise NotImplementedError()


class YouTubeResolver(AbstractResolver):
    RE_USER_NAME = re.compile(r'http(s)?://(www.)?youtube.com/(?P<user_name>[a-zA-Z0-9]+)$')

    def __init__(self):
        AbstractResolver.__init__(self)

    def supports_url(self, url, url_components):
        if url_components.hostname == 'www.youtube.com' or url_components.hostname == 'youtube.com':
            if url_components.path.lower() in ['/redirect', '/user']:
                return True

            if url_components.path.lower().startswith('/user'):
                return True

            re_match = self.RE_USER_NAME.match(url)
            if re_match:
                return True

        return False

    def resolve(self, url, url_components):
        def _load_page(_url):
            # we try to extract the channel id from the html content. With the channel id we can construct a url we
            # already work with.
            # https://www.youtube.com/channel/<CHANNEL_ID>
            try:
                headers = {'Cache-Control': 'max-age=0',
                           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                           'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36',
                           'DNT': '1',
                           'Accept-Encoding': 'gzip, deflate',
                           'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}
                response = requests.get(url, headers=headers, verify=self._verify)
                if response.status_code == 200:
                    match = re.search(r'<meta itemprop="channelId" content="(?P<channel_id>.+)">', response.text)
                    if match:
                        channel_id = match.group('channel_id')
                        return 'https://www.youtube.com/channel/%s' % channel_id
            except:
                # do nothing
                pass

            return _url

        if url_components.path.lower() == '/redirect':
            params = dict(parse_qsl(url_components.query))
            return params['q']

        if url_components.path.lower().startswith('/user'):
            return _load_page(url)

        re_match = self.RE_USER_NAME.match(url)
        if re_match:
            return _load_page(url)

        return url


class CommonResolver(AbstractResolver, list):
    def __init__(self):
        AbstractResolver.__init__(self)

    def supports_url(self, url, url_components):
        return True

    def resolve(self, url, url_components):
        def _loop(_url, tries=5):
            if tries == 0:
                return _url

            try:
                headers = {'Cache-Control': 'max-age=0',
                           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                           'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36',
                           'DNT': '1',
                           'Accept-Encoding': 'gzip, deflate',
                           'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}
                response = requests.head(_url, headers=headers, verify=self._verify, allow_redirects=False)
                if response.status_code == 304:
                    return url

                if response.status_code in [301, 302, 303]:
                    headers = response.headers
                    location = headers.get('location', '')

                    # validate the location - some server returned garbage
                    _url_components = urlparse(location)
                    if not _url_components.scheme and not _url_components.hostname:
                        return url

                    # some server return 301 for HEAD requests
                    # we just compare the new location - if it's equal we can return the url
                    if location == _url or ''.join([location, '/']) == _url or location == ''.join([_url, '/']):
                        return _url

                    if location:
                        return _loop(location, tries=tries - 1)

                    # just to be sure ;)
                    location = headers.get('Location', '')
                    if location:
                        return _loop(location, tries=tries - 1)

                if response.status_code == 200:
                    _url_components = urlparse(_url)
                    if _url_components.path == '/supported_browsers':
                        # "sometimes", we get a redirect through an URL of the form https://.../supported_browsers?next_url=<urlencoded_next_url>&further=paramaters&stuck=here
                        # put together query string from both what's encoded inside next_url and the remaining paramaters of this URL...
                        _query = parse_qs(_url_components.query) # top-level query string
                        _nc = urlparse(_query['next_url'][0]) # components of next_url
                        _next_query = parse_qs(_nc.query) # query string encoded inside next_url
                        del _query['next_url'] # remove next_url from top level query string
                        _next_query.update(_query) # add/overwrite all other params from top level query string
                        _next_query = dict(map(lambda kv : (kv[0], kv[1][0]), _next_query.items())) # flatten to only use first argument of each param
                        _next_url = urlunsplit((_nc.scheme, _nc.netloc, _nc.path, urlencode(_next_query), _nc.fragment)) # build new URL from these components
                        return _next_url

            except:
                # do nothing
                pass

            return _url

        resolved_url = _loop(url)

        return resolved_url


class UrlResolver(object):
    def __init__(self, context):
        self._context = context
        self._cache = {}
        self._youtube_resolver = YouTubeResolver()
        self._resolver = [
            self._youtube_resolver,
            CommonResolver()
        ]

    def clear(self):
        self._context.get_function_cache().clear()

    def _resolve(self, url):
        # try one of the resolver
        url_components = urlparse(url)
        for resolver in self._resolver:
            if resolver.supports_url(url, url_components):
                resolved_url = resolver.resolve(url, url_components)
                self._cache[url] = resolved_url

                # one last check...sometimes the resolved url is YouTube-specific and can be resolved again or
                # simplified.
                url_components = urlparse(resolved_url)
                if resolver is not self._youtube_resolver and self._youtube_resolver.supports_url(resolved_url, url_components):
                    return self._youtube_resolver.resolve(resolved_url, url_components)

                return resolved_url

    def resolve(self, url):
        function_cache = self._context.get_function_cache()
        resolved_url = function_cache.get(FunctionCache.ONE_DAY, self._resolve, url)
        if not resolved_url or resolved_url == '/':
            return url

        return resolved_url
