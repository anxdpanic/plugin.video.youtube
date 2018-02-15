__author__ = 'bromix'

import re

import requests
from ....kodion.utils import FunctionCache
from .jsinterp import JSInterpreter


class Cipher(object):
    def __init__(self, context, javascript_url):
        self._context = context
        self._verify = context.get_settings().verify_ssl()
        self._javascript_url = javascript_url

    def get_signature(self, signature):
        function_cache = self._context.get_function_cache()
        javascript = function_cache.get_cached_only(self._load_javascript, self._javascript_url)
        if not javascript:
            javascript = function_cache.get(FunctionCache.ONE_DAY, self._load_javascript, self._javascript_url)

        if javascript:
            func = self._parse_sig_js(javascript)
            if func:
                return func(signature)
            else:
                raise Exception('Signature function not found')

        return u''

    def _load_javascript(self, javascript_url):
        headers = {'Connection': 'keep-alive',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                   'DNT': '1',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

        url = javascript_url
        if not url.startswith('http'):
            url = 'http://' + url

        result = requests.get(url, headers=headers, verify=self._verify, allow_redirects=True)
        return result.text

    def _parse_sig_js(self, jscode):
        match = re.search(r'(["\'])signature\1\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(', jscode)
        if match:
            funcname = match.group('sig')
        else:
            match = re.search(r'\.sig\|\|(?P<sig>[a-zA-Z0-9$]+)\(', jscode)
            funcname = match.group('sig')
        if funcname:
            jsi = JSInterpreter(jscode)
            initial_function = jsi.extract_function(funcname)
            return lambda s: initial_function([s])
        return None
