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

from .audio_item import AudioItem
from .directory_item import DirectoryItem
from .image_item import ImageItem
from .video_item import VideoItem


_ITEM_TYPES = {
    'AudioItem': AudioItem,
    'DirectoryItem': DirectoryItem,
    'ImageItem': ImageItem,
    'VideoItem': VideoItem,
}


def _decoder(obj):
    date_in_isoformat = obj.get('__isoformat__')
    if not date_in_isoformat:
        return obj

    if obj['__class__'] == 'date':
        return date.fromisoformat(date_in_isoformat)
    return datetime.fromisoformat(date_in_isoformat)


def from_json(json_data, *_args):
    """
    Creates an instance of the given json dump or dict.
    :param json_data:
    :return:
    """
    if isinstance(json_data, str):
        json_data = json.loads(json_data, object_hook=_decoder)

    item_type = json_data.get('type')
    if not item_type or item_type not in _ITEM_TYPES:
        return json_data

    item = _ITEM_TYPES[item_type](name='', uri='')

    for key, value in json_data.get('data', {}).items():
        if hasattr(item, key):
            setattr(item, key, value)

    return item
