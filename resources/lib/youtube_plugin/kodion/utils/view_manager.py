# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from .. import constants


class ViewManager(object):
    SUPPORTED_VIEWS = ['default', 'movies', 'tvshows', 'episodes', 'musicvideos', 'songs', 'albums', 'artists']
    SKIN_DATA = {
        'skin.confluence': {
            'default': [
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500}
            ],
            'movies': [
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Media info', 'id': 504},
                {'name': 'Media info 2', 'id': 503}
            ],
            'episodes': [
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Media info', 'id': 504},
                {'name': 'Media info 2', 'id': 503}
            ],
            'tvshows': [
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Poster', 'id': 500},
                {'name': 'Wide', 'id': 505},
                {'name': 'Media info', 'id': 504},
                {'name': 'Media info 2', 'id': 503},
                {'name': 'Fanart', 'id': 508}
            ],
            'musicvideos': [
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Media info', 'id': 504},
                {'name': 'Media info 2', 'id': 503}
            ],
            'songs': [
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Media info', 'id': 506}
            ],
            'albums': [
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Media info', 'id': 506}
            ],
            'artists': [
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Media info', 'id': 506}
            ]
        },
        'skin.aeon.nox.5': {
            'default': [
                {'name': 'List', 'id': 50},
                {'name': 'Episodes', 'id': 502},
                {'name': 'LowList', 'id': 501},
                {'name': 'BannerWall', 'id': 58},
                {'name': 'Shift', 'id': 57},
                {'name': 'Posters', 'id': 56},
                {'name': 'ShowCase', 'id': 53},
                {'name': 'Landscape', 'id': 52},
                {'name': 'InfoWall', 'id': 51}
            ]
        },
        'skin.xperience1080+': {
            'default': [
                {'name': 'List', 'id': 50},
                {'name': 'Thumbnail', 'id': 500},
            ],
            'episodes': [
                {'name': 'List', 'id': 50},
                {'name': 'Info list', 'id': 52},
                {'name': 'Fanart', 'id': 502},
                {'name': 'Landscape', 'id': 54},
                {'name': 'Poster', 'id': 55},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Banner', 'id': 60}
            ],
        },
        'skin.xperience1080': {
            'default': [
                {'name': 'List', 'id': 50},
                {'name': 'Thumbnail', 'id': 500},
            ],
            'episodes': [
                {'name': 'List', 'id': 50},
                {'name': 'Info list', 'id': 52},
                {'name': 'Fanart', 'id': 502},
                {'name': 'Landscape', 'id': 54},
                {'name': 'Poster', 'id': 55},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Banner', 'id': 60}
            ],
        },
        'skin.estuary': {
            'default': [
                {'name': 'Shift', 'id': 53},
                {'name': 'InfoWall', 'id': 54},
                {'name': 'Wall', 'id': 500},
                {'name': 'WideList', 'id': 55},
            ],
            'episodes': [
                {'name': 'InfoWall', 'id': 54},
                {'name': 'Wall', 'id': 500},
                {'name': 'WideList', 'id': 55},
            ]
        }
    }

    def __init__(self, context):
        self._context = context

    def has_supported_views(self):
        """
        Returns True if the View of the current skin are supported
        :return: True if the View of the current skin are supported
        """
        return self._context.get_ui().get_skin_id() in self.SKIN_DATA

    def update_view_mode(self, title, view='default'):
        view_id = -1
        settings = self._context.get_settings()

        skin_id = self._context.get_ui().get_skin_id()
        skin_data = self.SKIN_DATA.get(skin_id, {}).get(view, [])
        if skin_data:
            items = []
            for view_data in skin_data:
                items.append((view_data['name'], view_data['id']))
            view_id = self._context.get_ui().on_select(title, items)
        else:
            self._context.log_notice("ViewManager: Unknown skin id '%s'" % skin_id)

        if view_id == -1:
            old_value = settings.get_string(constants.setting.VIEW_X % view, '')
            if old_value:
                result, view_id = self._context.get_ui().on_numeric_input(title, old_value)
                if not result:
                    view_id = -1

        if view_id > -1:
            settings.set_int(constants.setting.VIEW_X % view, view_id)
            return True

        return False
