# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from six.moves import range


class JsonScriptEngine(object):
    def __init__(self, json_script):
        self._json_script = json_script

    def execute(self, signature):
        _signature = signature

        _actions = self._json_script['actions']
        for action in _actions:
            func = ''.join(['_', action['func']])
            params = action['params']

            if func == '_return':
                break

            for i in range(len(params)):
                param = params[i]
                if param == '%SIG%':
                    param = _signature
                    params[i] = param
                    break

            method = getattr(self, func)
            if method:
                _signature = method(*params)
            else:
                raise Exception("Unknown method '%s'" % func)

        return _signature

    @staticmethod
    def _join(signature):
        return ''.join(signature)

    @staticmethod
    def _list(signature):
        return list(signature)

    @staticmethod
    def _slice(signature, b):
        del signature[b:]
        return signature

    @staticmethod
    def _splice(signature, a, b):
        del signature[a:b]
        return signature

    @staticmethod
    def _reverse(signature):
        return signature[::-1]

    @staticmethod
    def _swap(signature, b):
        c = signature[0]
        signature[0] = signature[b % len(signature)]
        signature[b] = c
        return signature
