__author__ = 'bromix'

import urllib
import urllib2
from StringIO import StringIO
import gzip

import json as real_json
from ..utils import to_utf8


class ErrorHandler(urllib2.HTTPDefaultErrorHandler):
    def http_error_default(self, req, fp, code, msg, hdrs):
        infourl = urllib.addinfourl(fp, hdrs, req.get_full_url())
        infourl.status = code
        infourl.code = code
        return infourl


class NoRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        infourl = urllib.addinfourl(fp, headers, req.get_full_url())
        infourl.status = code
        infourl.code = code
        return infourl

    http_error_300 = http_error_302
    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302


class Response():
    def __init__(self):
        self.headers = {}
        self.code = -1
        self.text = u''
        self.status_code = -1
        pass

    def read(self):
        return self.text

    def json(self):
        return real_json.loads(self.text)

    pass


def _request(method, url,
             params=None,
             data=None,
             headers=None,
             cookies=None,
             files=None,
             auth=None,
             timeout=None,
             allow_redirects=True,
             proxies=None,
             hooks=None,
             stream=None,
             verify=None,
             cert=None,
             json=None):
    if not headers:
        headers = {}
        pass

    url = urllib.quote(url, safe="%/:=&?~#+!$,;'@()*[]")

    handlers = []

    import sys
    # starting with python 2.7.9 urllib verifies every https request
    if False == verify and sys.version_info >= (2, 7, 9):
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        handlers.append(urllib2.HTTPSHandler(context=ssl_context))
        pass

    # handlers.append(urllib2.HTTPCookieProcessor())
    # handlers.append(ErrorHandler)
    if not allow_redirects:
        handlers.append(NoRedirectHandler)
        pass
    opener = urllib2.build_opener(*handlers)

    query = ''
    if params:
        for key in params:
            value = params[key]
            if isinstance(value, str):
                value = value.decode('utf-8')
                pass
            params[key] = value.encode('utf-8')
            pass
        query = urllib.urlencode(params)
        pass
    if query:
        url += '?%s' % query
        pass
    request = urllib2.Request(url)
    if headers:
        for key in headers:
            request.add_header(key, str(unicode(headers[key]).encode('utf-8')))
            pass
        pass
    if data or json:
        if headers.get('Content-Type', '').startswith('application/x-www-form-urlencoded') or data:
            # transform a string into a map of values
            if isinstance(data, basestring):
                _data = data.split('&')
                data = {}
                for item in _data:
                    name, value = item.split('=')
                    data[name] = value
                    pass
                pass

            # encode each value
            for key in data:
                data[key] = to_utf8(data[key])
                pass

            # urlencode
            request.data = urllib.urlencode(data)
            pass
        elif headers.get('Content-Type', '').startswith('application/json') and data:
            request.data = real_json.dumps(data).encode('utf-8')
            pass
        elif json:
            request.data = real_json.dumps(json).encode('utf-8')
            pass
        else:
            if not isinstance(data, basestring):
                data = str(data)
                pass

            if isinstance(data, str):
                data = data.encode('utf-8')
                pass
            request.data = data
            pass
        pass
    elif method.upper() in ['POST', 'PUT']:
        request.data = "null"
        pass
    request.get_method = lambda: method
    result = Response()
    response = None
    try:
        response = opener.open(request)
    except urllib2.HTTPError, e:
        # HTTPError implements addinfourl, so we can use the exception to construct a response
        if isinstance(e, urllib2.addinfourl):
            response = e
            pass
        pass

    # process response
    result.headers.update(response.headers)
    result.status_code = response.getcode()
    if response.headers.get('Content-Encoding', '').startswith('gzip'):
        buf = StringIO(response.read())
        f = gzip.GzipFile(fileobj=buf)
        result.text = f.read()
        pass
    else:
        result.text = response.read()

    return result


def get(url, **kwargs):
    kwargs.setdefault('allow_redirects', True)
    return _request('GET', url, **kwargs)


def post(url, data=None, json=None, **kwargs):
    kwargs.setdefault('allow_redirects', True)
    return _request('POST', url, data=data, json=json, **kwargs)


def put(url, data=None, json=None, **kwargs):
    return _request('PUT', url, data=data, json=json, **kwargs)


def delete(url, **kwargs):
    return _request('DELETE', url, **kwargs)


def head(url, **kwargs):
    return _request('HEAD', url, **kwargs)