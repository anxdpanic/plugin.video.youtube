# -*- coding: utf-8 -*-
import requests

from base64 import b64decode


__API_KEY = 'ZGFiODVhMzM5NTI2ZmVhNmEwZDc5ZjkzMjM2M2FjY2Q='
__API_BASE_URL = 'http://api.ipstack.com'


def locate_requester():
    access_key = b64decode(__API_KEY)
    request_url = __API_BASE_URL + '/check'
    params = {'access_key': access_key, 'fields': 'latitude,longitude', 'language': 'en', 'output': 'json'}
    response = requests.get(request_url, params)
    json_data = response.json()
    if ('success' in json_data and json_data['success'] is False) or 'error' in json_data:
        if 'error' in json_data:
            info = 'No information'
            code = '###'
            etype = 'Unknown'
            if 'info' in json_data['error']:
                info = json_data['error']['info']
            if 'code' in json_data['error']:
                code = str(json_data['error']['code'])
            if 'type' in json_data['error']:
                etype = json_data['error']['type']
            json_data = {'error': '[{code}] {error_type}: {info}'.format(code=code, error_type=etype, info=info)}
    return json_data
