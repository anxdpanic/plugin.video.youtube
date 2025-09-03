# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ... import logging
from ...compatibility import xbmc
from ...constants import (
    CONTAINER_POSITION,
    CONTENT,
    SORT,
    SORT_DIR,
    SORT_METHOD,
)


class ViewManager(object):
    log = logging.getLogger(__name__)

    SETTINGS = {
        'override': 'kodion.view.override',  # (bool)
        'view_default': 'kodion.view.default',  # (int)
        'view_type': 'kodion.view.{0}',  # (int)
    }

    SUPPORTED_TYPES_MAP = {
        CONTENT.LIST_CONTENT: 'default',
        CONTENT.VIDEO_CONTENT: 'episodes',
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

    def run(self, context, step, steps, **_kwargs):
        localize = context.localize

        skin_id = xbmc.getSkinDir()
        if skin_id in self.SKIN_DATA:
            status = localize(self.STRING_MAP['supported_skin'])
        else:
            status = localize(self.STRING_MAP['unsupported_skin'])
        prompt_text = localize(self.STRING_MAP['prompt'], (skin_id, status))

        step += 1
        if context.get_ui().on_yes_no_input(
                '{youtube} - {setup_wizard} ({step}/{steps})'.format(
                    youtube=localize('youtube'),
                    setup_wizard=localize('setup_wizard'),
                    step=step,
                    steps=steps,
                ),
                localize('setup_wizard.prompt.x', prompt_text)
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
        settings = self._context.get_settings()
        ui = self._context.get_ui()

        content_type = self.SUPPORTED_TYPES_MAP[view_type]

        if content_type not in self.STRING_MAP:
            self.log.warning('Unsupported content type: %r', content_type)
            return False
        title = self._context.localize(self.STRING_MAP[content_type])

        view_setting = self.SETTINGS['view_type'].format(content_type)
        current_value = settings.get_int(view_setting)
        if current_value == -1:
            self.log.warning('No setting for content type: %r', content_type)
            return False

        skin_data = self.SKIN_DATA.get(skin_id, {})
        view_type_data = skin_data.get(view_type) or skin_data.get(content_type)
        if view_type_data:
            items = []
            preselect = -1
            for view_data in view_type_data:
                view_id = view_data['id']
                items.append((view_data['name'], view_id))
                if view_id == current_value:
                    preselect = len(items) - 1
            view_id = ui.on_select(title, items, preselect=preselect)
        else:
            self.log.warning('Unsupported view: %r', view_type)

        if view_id == -1:
            result, view_id = ui.on_numeric_input(title, current_value)
            if not result:
                return False

        if view_id > -1:
            settings.set_int(view_setting, view_id)
            settings.set_bool(self.SETTINGS['override'], True)
            return True

        return False

    def apply_view_mode(self, context):
        view_mode = self.get_view_mode()
        if view_mode is None:
            return

        self.log.debug('Applying view mode: %r', view_mode)
        context.execute('Container.SetViewMode(%s)' % view_mode)

    @classmethod
    def apply_sort_method(cls, context, **kwargs):
        execute = context.execute
        get_infobool = xbmc.getCondVisibility

        sort_method = (
                kwargs.get(SORT_METHOD)
                or CONTENT.VIDEO_CONTENT.join(('__', '__'))
        )
        sort_id = SORT.SORT_ID_MAPPING.get(sort_method)
        if sort_id is None:
            cls.log.warning('Unknown sort method: %r', sort_method)
            return

        sort_dir = kwargs.get(SORT_DIR)
        _sort_dir = SORT.SORT_DIR.get(sort_dir)
        if _sort_dir is None:
            cls.log.warning('Invalid sort direction: %r', sort_dir)
            return

        position = kwargs.get(CONTAINER_POSITION)
        if position is not None:
            context.get_ui().focus_container(position=position)

        # Workaround for Container.SetSortMethod failing for some sort methods
        num_attempts = 0
        while num_attempts < 4:
            # Workaround for Container.SetSortMethod(0) being a noop
            # https://github.com/xbmc/xbmc/blob/7e1a55cb861342cd9062745161d88aca08dcead1/xbmc/windows/GUIMediaWindow.cpp#L502
            if sort_id == 0:
                # Sort by track number to reset sort order to default order
                if not num_attempts % 2:
                    _sort_method = 'TRACKNUM'
                    _sort_id = SORT.SORT_ID_MAPPING.get(_sort_method)
                    sort_action = 'Container.SetSortMethod(%s)' % _sort_id
                # Then switch to previous sort method which is default/unsorted
                # as per the order set in XbmcContext.apply_content
                else:
                    _sort_method = 'UNSORTED'
                    _sort_id = SORT.SORT_ID_MAPPING.get(_sort_method)
                    sort_action = 'Container.PreviousSortMethod'
            else:
                _sort_method = sort_method
                _sort_id = sort_id
                sort_action = 'Container.SetSortMethod(%s)' % _sort_id

            cls.log.debug('Applying sort method: {method!r} ({id})',
                          method=_sort_method,
                          id=_sort_id)
            execute(sort_action)
            context.sleep(0.1)

            if not get_infobool('Container.SortDirection(%s)' % _sort_dir):
                cls.log.debug('Applying sort direction: %r', sort_dir)
                # This builtin should be Container.SortDirection but has been
                # broken since Kodi v16
                # https://github.com/xbmc/xbmc/commit/ac870b64b16dfd0fc2bd0496c14529cf6d563f41
                execute('Container.SetSortDirection')
                context.sleep(0.1)

            num_attempts += 1

            if get_infobool('Container.SortMethod(%s)' % sort_id):
                break
        else:
            cls.log.warning('Unable to apply sorting:'
                            ' {sort_method!r} ({sort_id}) {sort_dir!r}',
                            sort_method=sort_method,
                            sort_id=sort_id,
                            sort_dir=sort_dir)
