# -*- coding: utf-8 -*-
from base64 import b64decode
from hashlib import md5
from resources.lib.kodion import Context as __Context

DEFAULT_SWITCH = 1

__context = __Context()
__settings = __context.get_settings()

_own_key = __settings.get_string('youtube.api.key', '').strip()
_own_id = __settings.get_string('youtube.api.id', '').strip().replace('.apps.googleusercontent.com', '')
_own_secret = __settings.get_string('youtube.api.secret', '').strip()


def _has_own_keys():
    return False if not _own_key or \
                    not _own_id or \
                    not _own_secret or \
                    not __settings.get_bool('youtube.api.enable', False) else True


has_own_keys = _has_own_keys()


def __get_key_switch():
    switch = __settings.get_string('youtube.api.key.switch', str(DEFAULT_SWITCH))
    use_switch = __settings.get_string('youtube.api.key.switch.use', '')
    if not use_switch and switch:
        switch = 'own' if has_own_keys else str(DEFAULT_SWITCH)
        __settings.set_string('youtube.api.key.switch', switch)
        __settings.set_string('youtube.api.key.switch.use', switch)
        return switch
    elif use_switch != switch:
        __settings.set_string('youtube.api.key.switch.use', switch)
        return switch
    else:
        return use_switch


key_sets = {
    'youtube-tv': {
        'id': 'ODYxNTU2NzA4NDU0LWQ2ZGxtM2xoMDVpZGQ4bnBlazE4azZiZThiYTNvYzY4',
        'key': 'QUl6YVN5QWQtWUVPcVp6OW5YVnpHdG4zS1d6WUxiTGFhamhxSURB',
        'secret': 'U2JvVmhvRzlzMHJOYWZpeENTR0dLWEFU'
    },
    'own': {
        'key': _own_key,
        'id': _own_id,
        'secret': _own_secret
    },
    'provided': {
        'switch': __get_key_switch(),
        '0': {  # Bromix youtube-for-kodi-12
            'id': 'OTQ3NTk2NzA5NDE0LTA4bnJuMzE0ZDhqM2s5MWNsNGY1MXNyY3U2bTE5aHZ1',
            'key': 'QUl6YVN5Q0RuXzlFeWJUSml5bUhpcE5TM2prNVpwQ1RYZENvdFEw',
            'secret': 'SHNMVDJaQ2V4SVYtVkZ4V2VZVloyVFVj'
        },
        '1': {  # Youtube Plugin for Kodi #1
            'id': 'Mjk0ODk5MDY0NDg4LWE4a2MxazFqZDAwa2FtcXJlMHZkMm5mdHVpaWZyZjZh',
            'key': 'QUl6YVN5Q1p3UXVvc0ZKYlF6bnFucXBxcFlsYUpXVk1uMTZ3QnZz',
            'secret': 'S1RrQktJTk41dmY0T3dqMU5ZeVhMemJl',
        },
        '2': {  # Bromix youtube-for-kodi-13
            'id': 'NDQ4OTQwNjc2NzEzLW1pbjl1NWZyZnVqcHJibmI4ZjNkcmkzY3Y5anIzMnJu',
            'key': 'QUl6YVN5QW1yZjNCbmVFUVBEaVVFdVFsenkwX3JiRkdEQmctYmkw',
            'secret': 'Nzl2TXNKc05DOWp5cFNmcnlVTXUwMGpX'
        },
        '3': {  # Bromix youtube-for-kodi-14
            'id': 'MTA3NTAwNzY3NTA2LTltdmJhYWN1c2NmOGNnZTJuM2trdmo1MGE2ZG5yazhn',
            'key': 'QUl6YVN5Q0NuWkltQzdnVG5pTmZnd3FHd2l4SWRCVkd4aUNPS2xV',
            'secret': 'MmNlVmZvZ25CQ3RuOHVoMjBIbWxKTjRY'
        },
        '4': {  # Bromix youtube-for-kodi-15
            'id': 'NjEwNjk2OTE4NzA1LWJrdDZ2NTM2azdnbjJkdGN2OHZkbmdtNGIwdnQ1c2V2',
            'key': 'QUl6YVN5QVRxRGltLTU2eThIY04xTkF6UWRWWmdkTW9jNmQ5RXlz',
            'secret': 'a1Y3UmVQMWZfTGc5aTJoV1IybGlIbk82'
        },
        '5': {  # Bromix youtube-for-kodi-16
            'id': 'ODc5NzYxNzg4MTA1LXNkdWYwaHQzMzVkdmc5MjNhbmU3Y2cxam50MWQ1bDRr',
            'key': 'QUl6YVN5QlMzck55bUp0elBZYkpYNWxTR2ROQ0JTNmFqaDRWRERZ',
            'secret': 'dkJWRGEta05kQ0hEVGtwRDhiOEhPNzE4'
        }
    }
}


def get_current_switch():
    return 'own' if has_own_keys else key_sets['provided']['switch']


def get_last_switch():
    return __settings.get_string('youtube.api.last.switch', '')


def set_last_switch(value):
    __settings.set_string('youtube.api.last.switch', value)


def get_key_set_hash(value):
    m = md5()
    if value == 'own':
        m.update('%s%s%s' % (key_sets[value]['key'], key_sets[value]['id'], key_sets[value]['secret']))
    else:
        m.update('%s%s%s' % \
                 (key_sets['provided'][value]['key'], key_sets['provided'][value]['id'],
                  key_sets['provided'][value]['secret']))
    return m.hexdigest()


def set_last_hash(value):
    __settings.set_string('youtube.api.last.hash', get_key_set_hash(value))


def get_last_hash():
    return __settings.get_string('youtube.api.last.hash', '')


def _resolve_old_login():
    __context.log_debug('API key set changed: Signing out')
    __context.execute('RunPlugin(%s)' % __context.create_uri(['sign', 'out']))


# make sure we have a valid switch, if not use default
if not has_own_keys:
    if not key_sets['provided'].get(key_sets['provided']['switch'], None):
        __settings.set_string('youtube.api.key.switch', str(DEFAULT_SWITCH))
        key_sets['provided']['switch'] = __get_key_switch()


def check_for_key_changes():
    last_switch = get_last_switch()
    current_switch = get_current_switch()
    __context.log_debug('Using API key set: %s' % current_switch)
    last_set_hash = get_last_hash()
    current_set_hash = get_key_set_hash(current_switch)
    if (last_switch != current_switch) or (last_set_hash != current_set_hash):
        __context.log_warning('Switching API key set from %s to %s' % (last_switch, current_switch))
        set_last_switch(current_switch)
        set_last_hash(current_switch)
        _resolve_old_login()
        return True
    return False


api = {
    'key':
        key_sets['own']['key']
        if has_own_keys
        else
        b64decode(key_sets['provided'][key_sets['provided']['switch']]['key']),
    'id':
        '%s.apps.googleusercontent.com' %
        (key_sets['own']['id']
         if has_own_keys
         else
         b64decode(key_sets['provided'][key_sets['provided']['switch']]['id'])),
    'secret':
        key_sets['own']['secret']
        if has_own_keys
        else
        b64decode(key_sets['provided'][key_sets['provided']['switch']]['secret'])
}

youtube_tv = {
    'key': b64decode(key_sets['youtube-tv']['key']),
    'id': '%s.apps.googleusercontent.com' % b64decode(key_sets['youtube-tv']['id']),
    'secret': b64decode(key_sets['youtube-tv']['secret'])
}

keys_changed = check_for_key_changes()
