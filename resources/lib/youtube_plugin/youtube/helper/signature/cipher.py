# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from six.moves import range

import re

from ....kodion.utils import FunctionCache
from .json_script_engine import JsonScriptEngine


class Cipher(object):
    def __init__(self, context, javascript):
        self._context = context
        self._verify = context.get_settings().verify_ssl()
        self._javascript = javascript

        self._object_cache = {}

    def get_signature(self, signature):
        function_cache = self._context.get_function_cache()
        json_script = function_cache.get_cached_only(self._load_javascript, self._javascript)
        if not json_script:
            json_script = function_cache.get(FunctionCache.ONE_DAY, self._load_javascript, self._javascript)

        if json_script:
            json_script_engine = JsonScriptEngine(json_script)
            return json_script_engine.execute(signature)

        return u''

    def _load_javascript(self, javascript):
        function_name = self._find_signature_function_name(javascript)
        if not function_name:
            raise Exception('Signature function not found')

        _function = self._find_function_body(function_name, javascript)
        function_parameter = _function[0].replace('\n', '').split(',')
        function_body = _function[1].replace('\n', '').split(';')

        json_script = {'actions': []}
        for line in function_body:
            # list of characters
            split_match = re.match(r'%s\s?=\s?%s.split\(""\)' % (function_parameter[0], function_parameter[0]), line)
            if split_match:
                json_script['actions'].append({'func': 'list',
                                               'params': ['%SIG%']})

            # return
            return_match = re.match(r'return\s+%s.join\(""\)' % function_parameter[0], line)
            if return_match:
                json_script['actions'].append({'func': 'join',
                                               'params': ['%SIG%']})

            # real object functions
            cipher_match = re.match(
                r'(?P<object_name>[$a-zA-Z0-9]+)\.?\[?"?(?P<function_name>[$a-zA-Z0-9]+)"?\]?\((?P<parameter>[^)]+)\)',
                line)
            if cipher_match:
                object_name = cipher_match.group('object_name')
                function_name = cipher_match.group('function_name')
                parameter = cipher_match.group('parameter').split(',')
                for i in range(len(parameter)):
                    param = parameter[i].strip()
                    if i == 0:
                        param = '%SIG%'
                    else:
                        param = int(param)

                    parameter[i] = param

                # get function from object
                _function = self._get_object_function(object_name, function_name, javascript)

                # try to find known functions and convert them to our json_script
                slice_match = re.match(r'[a-zA-Z]+.slice\((?P<a>\d+),[a-zA-Z]+\)', _function['body'][0])
                if slice_match:
                    a = int(slice_match.group('a'))
                    params = ['%SIG%', a, parameter[1]]
                    json_script['actions'].append({'func': 'slice',
                                                   'params': params})

                splice_match = re.match(r'[a-zA-Z]+.splice\((?P<a>\d+),[a-zA-Z]+\)', _function['body'][0])
                if splice_match:
                    a = int(splice_match.group('a'))
                    params = ['%SIG%', a, parameter[1]]
                    json_script['actions'].append({'func': 'splice',
                                                   'params': params})

                swap_match = re.match(r'var\s?[a-zA-Z]+=\s?[a-zA-Z]+\[0\]', _function['body'][0])
                if swap_match:
                    params = ['%SIG%', parameter[1]]
                    json_script['actions'].append({'func': 'swap',
                                                   'params': params})

                reverse_match = re.match(r'[a-zA-Z].reverse\(\)', _function['body'][0])
                if reverse_match:
                    params = ['%SIG%']
                    json_script['actions'].append({'func': 'reverse',
                                                   'params': params})

        return json_script

    @staticmethod
    def _find_signature_function_name(javascript):
        # match_patterns source is youtube-dl
        # https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1344
        # LICENSE: The Unlicense

        match_patterns = [
            r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<name>[a-zA-Z0-9$]+)\(',
            r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<name>[a-zA-Z0-9$]+)\(',
            r'(?:\b|[^a-zA-Z0-9$])(?P<name>[a-zA-Z0-9$]{2})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)',
            r'(?P<name>[a-zA-Z0-9$]+)\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)',
            r'(["\'])signature\1\s*,\s*(?P<name>[a-zA-Z0-9$]+)\(',
            r'\.sig\|\|(?P<name>[a-zA-Z0-9$]+)\(',
            r'yt\.akamaized\.net/\)\s*\|\|\s*.*?\s*[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?:encodeURIComponent\s*\()?\s*'
            r'(?P<name>[a-zA-Z0-9$]+)\(',
            r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?P<name>[a-zA-Z0-9$]+)\(',
            r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*(?P<name>[a-zA-Z0-9$]+)\(',
            r'\bc\s*&&\s*a\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<name>[a-zA-Z0-9$]+)\(',
            r'\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<name>[a-zA-Z0-9$]+)\(',
            r'\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<name>[a-zA-Z0-9$]+)\('
        ]

        for pattern in match_patterns:
            match = re.search(pattern, javascript)
            if match:
                return re.escape(match.group('name'))

        return ''

    @staticmethod
    def _find_function_body(function_name, javascript):
        # normalize function name
        function_name = function_name.replace('$', '\\$')
        pattern = r'%s=function\((?P<parameter>\w)\){(?P<body>[a-z=\.\("\)]*;(.*);(?:.+))}' % function_name
        match = re.search(pattern, javascript)
        if match:
            return match.group('parameter'), match.group('body')

        return '', ''

    @staticmethod
    def _find_object_body(object_name, javascript):
        object_name = object_name.replace('$', '\\$')
        match = re.search(r'var %s={(?P<object_body>.*?})};' % object_name, javascript, re.S)
        if match:
            return match.group('object_body')
        return ''

    def _get_object_function(self, object_name, function_name, javascript):
        if object_name not in self._object_cache:
            self._object_cache[object_name] = {}
        else:
            if function_name in self._object_cache[object_name]:
                return self._object_cache[object_name][function_name]

        _object_body = self._find_object_body(object_name, javascript)
        _object_body = _object_body.split('},')
        for _function in _object_body:
            if not _function.endswith('}'):
                _function = ''.join([_function, '}'])
            _function = _function.strip()

            match = re.match(r'(?P<name>[^:]*):function\((?P<parameter>[^)]*)\){(?P<body>[^}]+)}', _function)
            if match:
                name = match.group('name').replace('"', '')
                parameter = match.group('parameter')
                body = match.group('body').split(';')

                self._object_cache[object_name][name] = {'name': name,
                                                         'body': body,
                                                         'params': parameter}

        return self._object_cache[object_name][function_name]
