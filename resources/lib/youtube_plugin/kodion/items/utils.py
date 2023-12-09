# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json

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


def from_json(json_data):
    """
    Creates a instance of the given json dump or dict.
    :param json_data:
    :return:
    """

    def _from_json(_json_data):
        item_type = _json_data.get('type')
        if not item_type or item_type not in _ITEM_TYPES:
            return _json_data

        item = _ITEM_TYPES[item_type]()

        data = _json_data.get('data', {})
        for key, value in data.items():
            if hasattr(item, key):
                setattr(item, key, value)

        return item

    if isinstance(json_data, str):
        json_data = json.loads(json_data)
    return _from_json(json_data)


def to_jsons(base_item):
    return json.dumps(to_json(base_item))


def to_json(base_item):
    """
    Convert the given @base_item to json
    :param base_item:
    :return: json string
    """

    def _to_json(obj):
        if isinstance(obj, dict):
            return obj.__dict__

        for name, item_type in _ITEM_TYPES.items():
            if isinstance(obj, item_type):
                return {'type': name, 'data': obj.__dict__}

        return obj.__dict__

    return _to_json(base_item)
