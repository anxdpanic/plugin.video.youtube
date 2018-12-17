# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from six import string_types

import json

from .video_item import VideoItem
from .directory_item import DirectoryItem
from .audio_item import AudioItem
from .image_item import ImageItem


def from_json(json_data):
    """
    Creates a instance of the given json dump or dict.
    :param json_data:
    :return:
    """

    def _from_json(_json_data):
        mapping = {'VideoItem': lambda: VideoItem(u'', u''),
                   'DirectoryItem': lambda: DirectoryItem(u'', u''),
                   'AudioItem': lambda: AudioItem(u'', u''),
                   'ImageItem': lambda: ImageItem(u'', u'')}

        item = None
        item_type = _json_data.get('type', None)
        for key in mapping:
            if item_type == key:
                item = mapping[key]()
                break

        if item is None:
            return _json_data

        data = _json_data.get('data', {})
        for key in data:
            if hasattr(item, key):
                setattr(item, key, data[key])

        return item

    if isinstance(json_data, string_types):
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

        mapping = {VideoItem: 'VideoItem',
                   DirectoryItem: 'DirectoryItem',
                   AudioItem: 'AudioItem',
                   ImageItem: 'ImageItem'}

        for key in mapping:
            if isinstance(obj, key):
                return {'type': mapping[key], 'data': obj.__dict__}

        return obj.__dict__

    return _to_json(base_item)
