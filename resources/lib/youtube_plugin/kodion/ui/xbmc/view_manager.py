# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ...compatibility import xbmc
from ...constants import content


class ViewManager(object):
    SETTINGS = {
        'override': 'kodion.view.override',  # (bool)
        'view_default': 'kodion.view.default',  # (int)
        'view_type': 'kodion.view.{0}',  # (int)
    }

    SUPPORTED_TYPES_MAP = {
        content.LIST_CONTENT: 'default',
        content.VIDEO_CONTENT: 'episodes',
    }

    STRING_MAP = {
        'prompt': 30777,
        'unsupported_skin': 10109,
        'supported_skin': 14240,
        'albums': 30035,
        'artists': 30034,
        'default': 30027,
        'episodes': 30028,
        'movies': 30029,
        'songs': 30033,
        'tvshows': 30032,
    }

    SKIN_DATA = {
        'skin.confluence': {
            'default': (
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500}
            ),
            'movies': (
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Media info', 'id': 504},
                {'name': 'Media info 2', 'id': 503}
            ),
            'episodes': (
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Media info', 'id': 504},
                {'name': 'Media info 2', 'id': 503}
            ),
            'tvshows': (
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Poster', 'id': 500},
                {'name': 'Wide', 'id': 505},
                {'name': 'Media info', 'id': 504},
                {'name': 'Media info 2', 'id': 503},
                {'name': 'Fanart', 'id': 508}
            ),
            'musicvideos': (
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Media info', 'id': 504},
                {'name': 'Media info 2', 'id': 503}
            ),
            'songs': (
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Media info', 'id': 506}
            ),
            'albums': (
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Media info', 'id': 506}
            ),
            'artists': (
                {'name': 'List', 'id': 50},
                {'name': 'Big List', 'id': 51},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Media info', 'id': 506}
            )
        },
        'skin.aeon.nox.5': {
            'default': (
                {'name': 'List', 'id': 50},
                {'name': 'Episodes', 'id': 502},
                {'name': 'LowList', 'id': 501},
                {'name': 'BannerWall', 'id': 58},
                {'name': 'Shift', 'id': 57},
                {'name': 'Posters', 'id': 56},
                {'name': 'ShowCase', 'id': 53},
                {'name': 'Landscape', 'id': 52},
                {'name': 'InfoWall', 'id': 51}
            )
        },
        'skin.xperience1080+': {
            'default': (
                {'name': 'List', 'id': 50},
                {'name': 'Thumbnail', 'id': 500},
            ),
            'episodes': (
                {'name': 'List', 'id': 50},
                {'name': 'Info list', 'id': 52},
                {'name': 'Fanart', 'id': 502},
                {'name': 'Landscape', 'id': 54},
                {'name': 'Poster', 'id': 55},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Banner', 'id': 60}
            ),
        },
        'skin.xperience1080': {
            'default': (
                {'name': 'List', 'id': 50},
                {'name': 'Thumbnail', 'id': 500},
            ),
            'episodes': (
                {'name': 'List', 'id': 50},
                {'name': 'Info list', 'id': 52},
                {'name': 'Fanart', 'id': 502},
                {'name': 'Landscape', 'id': 54},
                {'name': 'Poster', 'id': 55},
                {'name': 'Thumbnail', 'id': 500},
                {'name': 'Banner', 'id': 60}
            ),
        },
        'skin.estuary': {
            'default': (
                {'name': 'IconWall', 'id': 52},
                {'name': 'WideList', 'id': 55},
            ),
            'videos': (
                {'name': 'Shift', 'id': 53},
                {'name': 'InfoWall', 'id': 54},
                {'name': 'WideList', 'id': 55},
                {'name': 'Wall', 'id': 500},
            ),
            'episodes': (
                {'name': 'InfoWall', 'id': 54},
                {'name': 'Wall', 'id': 500},
                {'name': 'WideList', 'id': 55},
            )
        }
    }

    def __init__(self, context):
        self._context = context
        self._view_mode = None

    def is_override_view_enabled(self):
        return self._context.get_settings().get_bool(self.SETTINGS['override'])

    def get_wizard_steps(self):
        return (self.run,)

    def run(self, _provider, context, step, steps):
        localize = context.localize

        skin_id = xbmc.getSkinDir()
        if skin_id in self.SKIN_DATA:
            status = localize(self.STRING_MAP['supported_skin'])
        else:
            status = localize(self.STRING_MAP['unsupported_skin'])
        prompt_text = localize(self.STRING_MAP['prompt']) % (skin_id, status)

        step += 1
        if context.get_ui().on_yes_no_input(
            localize('setup_wizard') + ' ({0}/{1})'.format(step, steps),
            localize('setup_wizard.prompt') % prompt_text,
        ):
            for view_type in self.SUPPORTED_TYPES_MAP:
                self.update_view_mode(skin_id, view_type)
        return step

    def get_view_mode(self):
        if self._view_mode is None:
            self.set_view_mode()
        return self._view_mode

    def set_view_mode(self, view_type='default'):
        settings = self._context.get_settings()
        default = settings.get_int(self.SETTINGS['view_default'], 50)
        if view_type == 'default':
            view_mode = default
        else:
            view_type = self.SUPPORTED_TYPES_MAP.get(view_type, 'default')
            view_mode = settings.get_int(
                self.SETTINGS['view_type'].format(view_type), default
            )
        self._view_mode = view_mode

    def update_view_mode(self, skin_id, view_type='default'):
        view_id = -1
        log_info = self._context.log_info
        settings = self._context.get_settings()
        ui = self._context.get_ui()

        content_type = self.SUPPORTED_TYPES_MAP[view_type]

        if content_type not in self.STRING_MAP:
            log_info('ViewManager: Unsupported content type |{content_type}|'
                     .format(content_type=content_type))
            return
        title = self._context.localize(self.STRING_MAP[content_type])

        view_setting = self.SETTINGS['view_type'].format(content_type)
        current_value = settings.get_int(view_setting)
        if current_value == -1:
            log_info('ViewManager: No setting for content type |{content_type}|'
                     .format(content_type=content_type))
            return False

        skin_data = self.SKIN_DATA.get(skin_id, {})
        view_type_data = skin_data.get(view_type) or skin_data.get(content_type)
        if view_type_data:
            items = []
            preselect = None
            for view_data in view_type_data:
                view_id = view_data['id']
                items.append((view_data['name'], view_id))
                if view_id == current_value:
                    preselect = len(items) - 1
            view_id = ui.on_select(title, items, preselect=preselect)
        else:
            log_info('ViewManager: Unsupported view |{view_type}|'
                     .format(view_type=view_type))

        if view_id == -1:
            result, view_id = ui.on_numeric_input(title, current_value)
            if not result:
                return False

        if view_id > -1:
            settings.set_int(view_setting, view_id)
            settings.set_bool(self.SETTINGS['override'], True)
            return True

        return False
