# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2019 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from hashlib import md5

from .storage import Storage
from ..utils import to_utf8


class SearchHistory(Storage):
    def __init__(self, filename, max_item_count=10):
        super(SearchHistory, self).__init__(filename,
                                            max_item_count=max_item_count)

    def is_empty(self):
        return self._is_empty()

    def get_items(self):
        result = self._get_by_ids(oldest_first=False,
                                  limit=self._max_item_count)
        return [item[2] for item in result]

    def clear(self):
        self._clear()

    @staticmethod
    def _make_id(search_text):
        md5_hash = md5()
        md5_hash.update(to_utf8(search_text))
        return md5_hash.hexdigest()

    def rename(self, old_search_text, new_search_text):
        self.remove(old_search_text)
        self.update(new_search_text)

    def remove(self, search_text):
        self._remove(self._make_id(search_text))

    def update(self, search_text):
        self._set(self._make_id(search_text), search_text)
