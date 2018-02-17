# -*- coding: utf-8 -*-

from base64 import b64decode
from ...kodion.json_store import APIKeyStore
from ...kodion import Context as __Context
from ... import key_sets

DEFAULT_SWITCH = 1

__context = __Context(plugin_id='plugin.video.youtube')
__settings = __context.get_settings()

_api_jstore = APIKeyStore()
_json_api = _api_jstore.load()

_own_key = __settings.get_string('youtube.api.key', '')
_own_id = __settings.get_string('youtube.api.id', '')
_own_secret = __settings.get_string('youtube.api.secret', '')


def _has_own_keys():
    return False if not _own_key or \
                    not _own_id or \
                    not _own_secret or \
                    not __settings.get_bool('youtube.api.enable', False) else True


has_own_keys = _has_own_keys()

key_sets['own'] = {'key': _own_key, 'id': _own_id, 'secret': _own_secret}
key_sets['provided']['switch'] = __settings.get_string('youtube.api.key.switch', str(DEFAULT_SWITCH))

developer_keys = _json_api['keys']['developer']

api = dict()
if has_own_keys:
    api['key'] = key_sets['own']['key']
    api['id'] = key_sets['own']['id'] + '.apps.googleusercontent.com'
    api['secret'] = key_sets['own']['secret']
    __context.log_debug('Using API key set: own')
else:
    api['key'] = b64decode(key_sets['provided'][key_sets['provided']['switch']]['key']).decode('utf-8')
    api['id'] = b64decode(key_sets['provided'][key_sets['provided']['switch']]['id']).decode('utf-8') + '.apps.googleusercontent.com'
    api['secret'] = b64decode(key_sets['provided'][key_sets['provided']['switch']]['secret']).decode('utf-8')
    __context.log_debug('Using API key set: ' + key_sets['provided']['switch'])

youtube_tv = {
    'key': b64decode(key_sets['youtube-tv']['key']).decode('utf-8'),
    'id': '%s.apps.googleusercontent.com' % b64decode(key_sets['youtube-tv']['id']).decode('utf-8'),
    'secret': b64decode(key_sets['youtube-tv']['secret']).decode('utf-8')
}
