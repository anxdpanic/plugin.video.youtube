import json

__author__ = 'bromix'

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
            pass

        if item is None:
            return _json_data

        data = _json_data.get('data', {})
        for key in data:
            if hasattr(item, key):
                setattr(item, key, data[key])
                pass
            pass

        return item

    if isinstance(json_data, basestring):
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
            pass

        return obj.__dict__

    return _to_json(base_item)
