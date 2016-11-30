import hashlib

from storage import Storage
from .methods import to_utf8


class SearchHistory(Storage):
    def __init__(self, filename, max_items=10):
        Storage.__init__(self, filename, max_item_count=max_items)
        pass

    def is_empty(self):
        return self._is_empty()

    def list(self):
        result = []

        keys = self._get_ids(oldest_first=False)
        for key in keys:
            item = self._get(key)
            result.append(item[0])
            pass

        return result

    def clear(self):
        self._clear()
        pass

    def _make_id(self, search_text):
        m = hashlib.md5()
        m.update(to_utf8(search_text))
        return m.hexdigest()

    def rename(self, old_search_text, new_search_text):
        self.remove(old_search_text)
        self.update(new_search_text)
        pass

    def remove(self, search_text):
        self._remove(self._make_id(search_text))
        pass

    def update(self, search_text):
        self._set(self._make_id(search_text), search_text)
        pass

    pass