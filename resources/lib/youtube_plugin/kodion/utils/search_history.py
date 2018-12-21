# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import hashlib

from .storage import Storage
from .methods import to_utf8


class SearchHistory(Storage):
    def __init__(self, filename, max_items=10):
        Storage.__init__(self, filename, max_item_count=max_items)

    def is_empty(self):
        return self._is_empty()

    def list(self):
        result = []

        keys = self._get_ids(oldest_first=False)
        for i, key in enumerate(keys):
            if i >= self._max_item_count:
                break
            item = self._get(key)
            result.append(item[0])

        return result

    def clear(self):
        self._clear()

    @staticmethod
    def _make_id(search_text):
        m = hashlib.md5()
        m.update(to_utf8(search_text))
        return m.hexdigest()

    def rename(self, old_search_text, new_search_text):
        self.remove(old_search_text)
        self.update(new_search_text)

    def remove(self, search_text):
        self._remove(self._make_id(search_text))

    def update(self, search_text):
        self._set(self._make_id(search_text), search_text)
