# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
from datetime import date, datetime

from .directory_item import DirectoryItem
from .image_item import ImageItem
from .media_item import AudioItem, VideoItem
from ..compatibility import string_type, to_str
from ..utils.datetime_parser import strptime


_ITEM_TYPES = {
    'AudioItem': AudioItem,
    'DirectoryItem': DirectoryItem,
    'ImageItem': ImageItem,
    'VideoItem': VideoItem,
}


def _decoder(obj):
    date_in_isoformat = obj.get('__isoformat__')
    if date_in_isoformat:
        if obj['__class__'] == 'date':
            return date.fromisoformat(date_in_isoformat)
        return datetime.fromisoformat(date_in_isoformat)

    format_string = obj.get('__format_string__')
    if format_string:
        value = obj['__value__']
        value = strptime(value, format_string)
        if obj['__class__'] == 'date':
            return value.date()
        return value

    return obj


def from_json(json_data, *args):
    """
    Creates an instance of the given json dump or dict.
    :param json_data:
    :return:
    """
    if isinstance(json_data, string_type):
        if json_data == to_str(None):
            # Channel bookmark that will be updated. Store timestamp for update
            if args and args[0] and len(args[0]) == 4:
                return args[0][1]
            return None
        json_data = json.loads(json_data, object_hook=_decoder)

    item_type = json_data.get('type')
    if not item_type or item_type not in _ITEM_TYPES:
        return None

    item = _ITEM_TYPES[item_type](name='', uri='')

    for key, value in json_data.get('data', {}).items():
        if hasattr(item, key):
            setattr(item, key, value)

    return item
