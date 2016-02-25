__author__ = 'bromix'

import datetime

from .storage import Storage
from .. import items


class WatchLaterList(Storage):
    def __init__(self, filename):
        Storage.__init__(self, filename)
        pass

    def clear(self):
        self._clear()
        pass

    def list(self):
        result = []

        for key in self._get_ids():
            data = self._get(key)
            item = items.from_json(data[0])
            result.append(item)
            pass

        def _sort(video_item):
            return video_item.get_date()

        self.sync()

        sorted_list = sorted(result, key=_sort, reverse=False)
        return sorted_list

    def add(self, base_item):
        now = datetime.datetime.now()
        base_item.set_date(now.year, now.month, now.day, now.hour, now.minute, now.second)

        item_json_data = items.to_json(base_item)
        self._set(base_item.get_id(), item_json_data)
        pass

    def remove(self, base_item):
        self._remove(base_item.get_id())
        pass