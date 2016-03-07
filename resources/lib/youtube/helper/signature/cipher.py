__author__ = 'bromix'

import json
import os
import re

from resources.lib.kodion import simple_requests as requests
from resources.lib.kodion.utils import FunctionCache
from .json_script_engine import JsonScriptEngine


class Cipher(object):
    def __init__(self, context, java_script_url):
        self._context = context
        self._java_script_url = java_script_url

        self._object_cache = {}
        pass

    def get_signature(self, signature):
        function_cache = self._context.get_function_cache()
        json_script = function_cache.get_cached_only(self._load_json_script, self._java_script_url)
        if not json_script:
            json_script = function_cache.get(FunctionCache.ONE_DAY, self._load_json_script, self._java_script_url)
            pass

        if json_script:
            json_script_engine = JsonScriptEngine(json_script)
            return json_script_engine.execute(signature)

        return u''

    def _cache_json_script(self, json_script, md5_hash):
        if self._cache_folder:
            if not os.path.exists(self._cache_folder):
                os.makedirs(self._cache_folder)
                pass

            filename = md5_hash + '.jsonscript'
            filename = os.path.join(self._cache_folder, filename)
            with open(filename, 'w') as outfile:
                json.dump(json_script, outfile, sort_keys=True, indent=4, ensure_ascii=False)
            pass
        pass

    def _load_json_script(self, java_script_url):
        headers = {'Connection': 'keep-alive',
                   'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                   'DNT': '1',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

        url = java_script_url
        if not url.startswith('http'):
            url = 'http://' + url
            pass

        result = requests.get(url, headers=headers, verify=False, allow_redirects=True)
        java_script = result.text

        return self._load_java_script(java_script)

    def _load_java_script(self, java_script):
        function_name = self._find_signature_function_name(java_script)
        if not function_name:
            raise Exception('Signature function not found')

        function = self._find_function_body(function_name, java_script)
        function_parameter = function[0].replace('\n', '').split(',')
        function_body = function[1].replace('\n', '').split(';')

        json_script = {'actions': []}
        for line in function_body:
            # list of characters
            split_match = re.match('%s\s?=\s?%s.split\(""\)' % (function_parameter[0], function_parameter[0]), line)
            if split_match:
                json_script['actions'].append({'func': 'list',
                                               'params': ['%SIG%']})
                pass

            # return
            return_match = re.match('return\s+%s.join\(""\)' % function_parameter[0], line)
            if return_match:
                json_script['actions'].append({'func': 'join',
                                               'params': ['%SIG%']})
                pass

            # real object functions
            cipher_match = re.match(
                r'(?P<object_name>[\$a-zA-Z0-9]+)\.(?P<function_name>[\$a-zA-Z0-9]+)\((?P<parameter>[^)]+)\)',
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
                        pass

                    parameter[i] = param
                    pass

                # get function from object
                function = self._get_object_function(object_name, function_name, java_script)

                # try to find known functions and convert them to our json_script
                slice_match = re.match('[a-zA-Z]+.slice\((?P<a>\d+),[a-zA-Z]+\)', function['body'][0])
                if slice_match:
                    a = int(slice_match.group('a'))
                    params = ['%SIG%', a, parameter[1]]
                    json_script['actions'].append({'func': 'slice',
                                                   'params': params})
                    pass

                splice_match = re.match('[a-zA-Z]+.splice\((?P<a>\d+),[a-zA-Z]+\)', function['body'][0])
                if splice_match:
                    a = int(splice_match.group('a'))
                    params = ['%SIG%', a, parameter[1]]
                    json_script['actions'].append({'func': 'splice',
                                                   'params': params})
                    pass

                swap_match = re.match('var\s?[a-zA-Z]+=\s?[a-zA-Z]+\[0\]', function['body'][0])
                if swap_match:
                    params = ['%SIG%', parameter[1]]
                    json_script['actions'].append({'func': 'swap',
                                                   'params': params})
                    pass

                reverse_match = re.match('[a-zA-Z].reverse\(\)', function['body'][0])
                if reverse_match:
                    params = ['%SIG%']
                    json_script['actions'].append({'func': 'reverse',
                                                   'params': params})
                    pass
                pass
            pass

        return json_script

    def _find_signature_function_name(self, java_script):
        # match = re.search('signature\s?=\s?(?P<name>[a-zA-Z]+)\([^)]+\)', self._java_script)
        match = re.search('set..signature..(?P<name>[$a-zA-Z]+)\([^)]\)', java_script)
        if match:
            return match.group('name')

        return ''

    def _find_function_body(self, function_name, java_script):
        # normalize function name
        function_name = function_name.replace('$', '\$')
        match = re.search(r'\s?%s=function\((?P<parameter>[^)]+)\)\s?\{\s?(?P<body>[^}]+)\s?\}' % function_name, java_script)
        if match:
            return match.group('parameter'), match.group('body')

        return '', ''

    def _find_object_body(self, object_name, java_script):
        object_name = object_name.replace('$', '\$')
        match = re.search(r'var %s={(?P<object_body>.*?})};' % object_name, java_script, re.S)
        if match:
            return match.group('object_body')
        return ''

    def _get_object_function(self, object_name, function_name, java_script):
        if not object_name in self._object_cache:
            self._object_cache[object_name] = {}
        else:
            if function_name in self._object_cache[object_name]:
                return self._object_cache[object_name][function_name]
            pass

        _object_body = self._find_object_body(object_name, java_script)
        _object_body = _object_body.split('},')
        for _function in _object_body:
            if not _function.endswith('}'):
                _function += '}'
                pass
            _function = _function.strip()

            match = re.match('(?P<name>[^:]*):function\((?P<parameter>[^)]*)\)\{(?P<body>[^}]+)\}', _function)
            if match:
                name = match.group('name')
                parameter = match.group('parameter')
                body = match.group('body').split(';')

                self._object_cache[object_name][name] = {'name': name,
                                                         'body': body,
                                                         'params': parameter}
                pass
            pass

        return self._object_cache[object_name][function_name]
