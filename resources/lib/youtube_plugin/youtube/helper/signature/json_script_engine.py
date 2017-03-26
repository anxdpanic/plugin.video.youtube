__author__ = 'bromix'


class JsonScriptEngine(object):
    def __init__(self, json_script):
        self._json_script = json_script
        pass

    def execute(self, signature):
        _signature = signature

        _actions = self._json_script['actions']
        for action in _actions:
            func = '_'+action['func']
            params = action['params']

            if func == '_return':
                break

            for i in range(len(params)):
                param = params[i]
                if param == '%SIG%':
                    param = _signature
                    params[i] = param
                    break
                pass

            method = getattr(self, func)
            if method:
                _signature = method(*params)
                pass
            else:
                raise Exception("Unknown method '%s'" % func)
            pass

        return _signature

    def _join(self, signature):
        return ''.join(signature)

    def _list(self, signature):
        return list(signature)

    def _slice(self, signature, b):
        del signature[b:]
        return signature

    def _splice(self, signature, a, b):
        del signature[a:b]
        return signature

    def _reverse(self, signature):
        return signature[::-1]

    def _swap(self, signature, b):
        c = signature[0]
        signature[0] = signature[b % len(signature)]
        signature[b] = c
        return signature

    pass
