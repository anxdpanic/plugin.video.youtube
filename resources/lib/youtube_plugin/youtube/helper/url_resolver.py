# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import re

from ...kodion.compatibility import parse_qsl, unescape, urlencode, urlsplit
from ...kodion.network import BaseRequestsClass


class AbstractResolver(BaseRequestsClass):
    _HEADERS = {
        'Cache-Control': 'max-age=0',
        'Accept': ('text/html,'
                   'application/xhtml+xml,'
                   'application/xml;q=0.9,'
                   'image/webp,'
                   '*/*;q=0.8'),
        # Desktop user agent
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                       ' AppleWebKit/537.36 (KHTML, like Gecko)'
                       ' Chrome/119.0.0.0 Safari/537.36'),
        # Mobile user agent - for testing m.youtube.com redirect
        # 'User-Agent': ('Mozilla/5.0 (Linux; Android 10; SM-G981B)'
        #                ' AppleWebKit/537.36 (KHTML, like Gecko)'
        #                ' Chrome/80.0.3987.162 Mobile Safari/537.36'),
        # Old desktop user agent - for testing /supported_browsers redirect
        # 'User-Agent': ('Mozilla/5.0 (Windows NT 6.1; WOW64)'
        #                ' AppleWebKit/537.36 (KHTML, like Gecko)'
        #                ' Chrome/41.0.2272.118 Safari/537.36'),
        'DNT': '1',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'
    }

    def __init__(self, context):
        self._context = context
        super(AbstractResolver, self).__init__()

    def supports_url(self, url, url_components):
        raise NotImplementedError()

    def resolve(self, url, url_components):
        raise NotImplementedError()


class YouTubeResolver(AbstractResolver):
    _RE_CHANNEL_URL = re.compile(r'<meta property="og:url" content="'
                                 r'(?P<channel_url>[^"]+)'
                                 r'">')
    _RE_CLIP_DETAILS = re.compile(r'(<meta property="og:video:url" content="'
                                  r'(?P<video_url>[^"]+)'
                                  r'">)'
                                  r'|("startTimeMs":"(?P<start_time>\d+)")'
                                  r'|("endTimeMs":"(?P<end_time>\d+)")')

    def __init__(self, *args, **kwargs):
        super(YouTubeResolver, self).__init__(*args, **kwargs)

    def supports_url(self, url, url_components):
        if url_components.hostname not in (
                'www.youtube.com',
                'youtube.com',
                'm.youtube.com',
        ):
            return False

        path = url_components.path.lower()
        if path.startswith((
                '/@',
                '/c/',
                '/channel/',
                '/clip',
                '/user/',
        )):
            return 'GET'

        if path.startswith((
                '/embed',
                '/live',
                '/redirect',
                '/shorts',
                '/supported_browsers',
                '/watch',
        )):
            return 'HEAD'

        # user channel in the form of youtube.com/username
        path = path.strip('/').split('/', 1)
        return 'GET' if len(path) == 1 and path[0] else False

    def resolve(self, url, url_components, method='HEAD'):
        path = url_components.path.rstrip('/').lower()
        if path == '/redirect':
            params = dict(parse_qsl(url_components.query))
            url = params['q']

        # "sometimes", we get a redirect through a URL of the form
        # https://.../supported_browsers?next_url=<urlencoded_next_url>&further=parameters&stuck=here
        # put together query string from both what's encoded inside
        # next_url and the remaining parameters of this URL...
        elif path == '/supported_browsers':
            # top-level query string
            params = dict(parse_qsl(url_components.query))
            # components of next_url
            next_components = urlsplit(params.pop('next_url', ''))
            if not next_components.scheme or not next_components.netloc:
                return url
            # query string encoded inside next_url
            next_params = dict(parse_qsl(next_components.query))
            # add/overwrite all other params from top level query string
            next_params.update(params)
            # build new URL from these components
            return next_components._replace(
                query=urlencode(next_params)
            ).geturl()

        response = self.request(url,
                                method=method,
                                headers=self._HEADERS,
                                # Manually configured cookies to avoid cookie
                                # consent redirect
                                cookies={'SOCS': 'CAISAiAD'},
                                allow_redirects=True)
        if not response or not response.ok:
            return url

        if path.startswith('/clip'):
            all_matches = self._RE_CLIP_DETAILS.finditer(response.text)
            num_matched = 0
            url_components = params = start_time = end_time = None
            for matches in all_matches:
                matches = matches.groupdict()

                if not num_matched & 1:
                    url = matches['video_url']
                    if url:
                        num_matched += 1
                        url_components = urlsplit(unescape(url))
                        params = dict(parse_qsl(url_components.query))

                if not num_matched & 2:
                    start_time = matches['start_time']
                    if start_time:
                        start_time = int(start_time) / 1000
                        num_matched += 2

                if not num_matched & 4:
                    end_time = matches['end_time']
                    if end_time:
                        end_time = int(end_time) / 1000
                        num_matched += 4

                if num_matched != 7:
                    continue

                params.update({
                    'clip': True,
                    'start': start_time,
                    'end': end_time,
                })
                return url_components._replace(query=urlencode(params)).geturl()

        # we try to extract the channel id from the html content
        # With the channel id we can construct a URL we already work with
        # https://www.youtube.com/channel/<CHANNEL_ID>
        elif method == 'GET':
            match = self._RE_CHANNEL_URL.search(response.text)
            if match:
                url = match.group('channel_url')
                if path.endswith(('/live', '/streams')):
                    url_components = urlsplit(unescape(url))
                    params = dict(parse_qsl(url_components.query))
                    params['live'] = 1
                    return url_components._replace(
                        query=urlencode(params)
                    ).geturl()
                return url

        return response.url


class CommonResolver(AbstractResolver):
    def __init__(self, *args, **kwargs):
        super(CommonResolver, self).__init__(*args, **kwargs)

    def supports_url(self, url, url_components):
        if url_components.hostname in (
                'www.youtube.com',
                'youtube.com',
                'm.youtube.com',
        ):
            return False
        return 'HEAD'

    def resolve(self, url, url_components, method='HEAD'):
        response = self.request(url,
                                method=method,
                                headers=self._HEADERS,
                                allow_redirects=True)
        if not response or not response.ok:
            return url
        return response.url


class UrlResolver(object):
    def __init__(self, context):
        self._context = context
        self._function_cache = context.get_function_cache()
        self._resolvers = (
            ('common_resolver', CommonResolver(context)),
            ('youtube_resolver', YouTubeResolver(context)),
        )

    def _resolve(self, url):
        # try one of the resolvers
        resolved_url = url
        for resolver_name, resolver in self._resolvers:
            url_components = urlsplit(resolved_url)
            method = resolver.supports_url(resolved_url, url_components)
            if not method:
                continue

            self._context.log_debug('Resolving |{uri}| using |{name} {method}|'
                                    .format(uri=resolved_url,
                                            name=resolver_name,
                                            method=method))
            resolved_url = resolver.resolve(resolved_url,
                                            url_components,
                                            method)
            self._context.log_debug('Resolved to |{0}|'.format(resolved_url))
        return resolved_url

    def resolve(self, url):
        resolved_url = self._function_cache.run(
            self._resolve,
            self._function_cache.ONE_DAY,
            _refresh=self._context.get_param('refresh'),
            url=url
        )
        if not resolved_url or resolved_url == '/':
            return url

        return resolved_url
