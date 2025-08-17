# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json

from ..compatibility import (
    generate_hash,
    parse_qsl,
    string_type,
    urlsplit,
    xbmc,
)


__all__ = (
    'generate_hash',
    'get_kodi_setting_bool',
    'get_kodi_setting_value',
    'jsonrpc',
    'loose_version',
    'merge_dicts',
    'parse_item_ids',
    'wait',
)


def loose_version(v):
    return [point.zfill(8) for point in v.split('.')]


def parse_item_ids(uri,
                   _ids={'video': 'video_id',
                         'channel': 'channel_id',
                         'playlist': 'playlist_id'}):
    item_ids = {}
    uri = urlsplit(uri)

    path = uri.path.rstrip('/')
    while path:
        id_type, _, next_part = path.partition('/')
        if not next_part:
            break

        if id_type in _ids:
            id_value = next_part.partition('/')[0]
            if id_value:
                item_ids[_ids[id_type]] = id_value

        path = next_part

    params = dict(parse_qsl(uri.query))
    for id_type in _ids.values():
        id_value = params.get(id_type)
        if id_value:
            item_ids[id_type] = id_value

    return item_ids


def merge_dicts(item1, item2, templates=None, compare_str=False, _=Ellipsis):
    if not isinstance(item1, dict) or not isinstance(item2, dict):
        if (compare_str
                and isinstance(item1, string_type)
                and isinstance(item2, string_type)):
            return item1 if len(item1) > len(item2) else item2
        return (
            item1 if item2 is _ else
            _ if (item1 is KeyError or item2 is KeyError) else
            item2
        )
    new = {}
    keys = set(item1)
    keys.update(item2)
    for key in keys:
        value = merge_dicts(item1.get(key, _), item2.get(key, _), templates)
        if value is _:
            continue
        if (templates is not None
                and isinstance(value, string_type) and '{' in value):
            templates['{0}.{1}'.format(id(new), key)] = (new, key, value)
        new[key] = value
    return new or _


def get_kodi_setting_value(setting, process=None):
    response = jsonrpc(method='Settings.GetSettingValue',
                       params={'setting': setting})
    try:
        value = response['result']['value']
        if process:
            return process(value)
    except (KeyError, TypeError, ValueError):
        return None
    return value


def get_kodi_setting_bool(setting):
    return xbmc.getCondVisibility(setting.join(('System.GetBool(', ')')))


def jsonrpc(batch=None, **kwargs):
    """
    Perform JSONRPC calls
    """

    if not batch and not kwargs:
        return None

    do_response = False
    for request_id, kwargs in enumerate(batch or (kwargs,)):
        do_response = (not kwargs.pop('no_response', False)) or do_response
        if do_response and 'id' not in kwargs:
            kwargs['id'] = request_id
        kwargs['jsonrpc'] = '2.0'

    request = json.dumps(batch or kwargs, default=tuple, ensure_ascii=False)
    response = xbmc.executeJSONRPC(request)
    return json.loads(response) if do_response else None


def wait(timeout=None):
    if not timeout:
        timeout = 0
    elif timeout < 0:
        timeout = 0.1
    return xbmc.Monitor().waitForAbort(timeout)
