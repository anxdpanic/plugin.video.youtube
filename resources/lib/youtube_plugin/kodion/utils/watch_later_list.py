# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import datetime

from .storage import Storage
from .. import items


class WatchLaterList(Storage):
    def __init__(self, filename):
        super(WatchLaterList, self).__init__(filename)

    def clear(self):
        self._clear()

    @staticmethod
    def _sort_item(_item):
        return _item[2].get_date()

    def get_items(self):
        result = self._get_by_ids(process=items.from_json)
        return sorted(result, key=self._sort_item, reverse=False)

    def add(self, base_item):
        now = datetime.datetime.now()
        base_item.set_date(now.year, now.month, now.day, now.hour, now.minute, now.second)

        item_json_data = items.to_json(base_item)
        self._set(base_item.get_id(), item_json_data)

    def remove(self, base_item):
        self._remove(base_item.get_id())
