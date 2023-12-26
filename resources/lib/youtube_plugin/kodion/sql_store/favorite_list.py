# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .storage import Storage
from ..items import from_json


class FavoriteList(Storage):
    _table_name = 'storage_v2'
    _table_created = False
    _table_updated = False
    _sql = {}

    def __init__(self, filepath):
        super(FavoriteList, self).__init__(filepath)

    @staticmethod
    def _sort_item(item):
        return item.get_name().upper()

    def get_items(self):
        result = self._get_by_ids(process=from_json, values_only=True)
        return sorted(result, key=self._sort_item, reverse=False)

    def add(self, item_id, item):
        self._set(item_id, item)

    def remove(self, item_id):
        self._remove(item_id)
