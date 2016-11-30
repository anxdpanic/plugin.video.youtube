__author__ = 'bromix'

from .storage import Storage
from .. import items


class FavoriteList(Storage):
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

        def _sort(_item):
            return _item.get_name().upper()

        return sorted(result, key=_sort, reverse=False)

    def add(self, base_item):
        item_json_data = items.to_json(base_item)
        self._set(base_item.get_id(), item_json_data)
        pass

    def remove(self, base_item):
        self._remove(base_item.get_id())
        pass