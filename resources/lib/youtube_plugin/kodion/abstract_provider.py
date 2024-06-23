# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import re

from .constants import CHECK_SETTINGS, REROUTE, content, paths
from .exceptions import KodionException
from .items import (
    DirectoryItem,
    NewSearchItem,
    NextPageItem,
    SearchHistoryItem,
    UriItem,
)
from .utils import to_unicode


class AbstractProvider(object):
    RESULT_CACHE_TO_DISC = 'cache_to_disc'  # (bool)
    RESULT_FORCE_RESOLVE = 'force_resolve'  # (bool)
    RESULT_UPDATE_LISTING = 'update_listing'  # (bool)

    def __init__(self):
        # map for regular expression (path) to method (names)
        self._dict_path = {}

        # register some default paths
        self.register_path(r''.join((
            '^',
            '(?:', paths.HOME, ')?/?$'
        )), self._internal_root)

        self.register_path(r''.join((
            '^',
            paths.ROUTE,
            '(?P<path>/[^?]+?)(?:/*[?].+|/*)$'
        )), self.reroute)

        self.register_path(r''.join((
            '^',
            paths.GOTO_PAGE,
            '(?P<page>/[0-9]+)?'
            '(?P<path>/[^?]+?)(?:/*[?].+|/*)$'
        )), self._internal_goto_page)

        self.register_path(r''.join((
            '^',
            paths.COMMAND,
            '/(?P<command>[^?]+?)(?:/*[?].+|/*)$'
        )), self._on_command)

        self.register_path(r''.join((
            '^',
            paths.WATCH_LATER,
            '/(?P<command>add|clear|list|remove)/?$'
        )), self.on_watch_later)

        self.register_path(r''.join((
            '^',
            paths.BOOKMARKS,
            '/(?P<command>add|clear|list|remove)/?$'
        )), self.on_bookmarks)

        self.register_path(r''.join((
            '^',
            '(', paths.SEARCH, '|', paths.EXTERNAL_SEARCH, ')',
            '/(?P<command>input|query|list|remove|clear|rename)?/?$'
        )), self._internal_search)

        self.register_path(r''.join((
            '^',
            paths.HISTORY,
            '/?$'
        )), self.on_playback_history)

        self.register_path(r'(?P<path>.*\/)extrafanart\/([\?#].+)?$',
                           self._internal_on_extra_fanart)

        """
        Test each method of this class for the attribute 'kodion_re_path' added
        by the decorator @RegisterProviderPath.
        The 'kodion_re_path' attribute is a regular expression that must match
        the current path in order for the decorated method to run.
        """
        for attribute_name in dir(self):
            if attribute_name.startswith('__'):
                continue
            attribute = getattr(self, attribute_name, None)
            if not attribute or not callable(attribute):
                continue
            re_path = getattr(attribute, 'kodion_re_path', None)
            if re_path:
                self.register_path(re_path, attribute)

    def register_path(self, re_path, method):
        """
        Registers a new method for the given regular expression
        :param re_path: regular expression of the path
        :param method: method to be registered
        :return:
        """
        self._dict_path[re.compile(re_path, re.UNICODE)] = method

    def run_wizard(self, context):
        settings = context.get_settings()
        ui = context.get_ui()

        context.send_notification(CHECK_SETTINGS, 'defer')

        wizard_steps = self.get_wizard_steps(context)
        wizard_steps.extend(ui.get_view_manager().get_wizard_steps())

        step = 0
        steps = len(wizard_steps)

        try:
            if wizard_steps and ui.on_yes_no_input(
                    context.localize('setup_wizard'),
                    (context.localize('setup_wizard.prompt')
                     % context.localize('setup_wizard.prompt.settings'))
            ):
                for wizard_step in wizard_steps:
                    if callable(wizard_step):
                        step = wizard_step(self, context, step, steps)
                    else:
                        step += 1
        finally:
            settings.setup_wizard_enabled(False)
            context.send_notification(CHECK_SETTINGS, 'process')

    def get_wizard_steps(self, context):
        # can be overridden by the derived class
        return []

    def navigate(self, context):
        path = context.get_path()
        for re_path, method in self._dict_path.items():
            re_match = re_path.search(path)
            if not re_match:
                continue

            options = {
                self.RESULT_CACHE_TO_DISC: True,
                self.RESULT_UPDATE_LISTING: False,
            }
            result = method(context, re_match)
            if isinstance(result, tuple):
                result, new_options = result
                options.update(new_options)

            refresh = context.get_param('refresh')
            if refresh is not None:
                options[self.RESULT_UPDATE_LISTING] = bool(refresh)

            return result, options

        raise KodionException("Mapping for path '%s' not found" % path)

    # noinspection PyUnusedLocal
    @staticmethod
    def on_extra_fanart(context, re_match):
        """
        The implementation of the provider can override this behavior.
        :param context:
        :param re_match:
        :return:
        """
        return

    def _internal_on_extra_fanart(self, context, re_match):
        path = re_match.group('path')
        new_context = context.clone(new_path=path)
        return self.on_extra_fanart(new_context, re_match)

    def on_playback_history(self, context, re_match):
        raise NotImplementedError()

    def on_search(self, search_text, context, re_match):
        raise NotImplementedError()

    def on_root(self, context, re_match):
        raise NotImplementedError()

    def _internal_root(self, context, re_match):
        return self.on_root(context, re_match)

    def _internal_goto_page(self, context, re_match):
        page = re_match.group('page')
        if page:
            page = int(page.lstrip('/'))
        else:
            result, page = context.get_ui().on_numeric_input(
                context.localize('page.choose'), 1
            )
            if not result:
                return False

        path = re_match.group('path')
        params = context.get_params()
        if 'page_token' in params:
            page_token = NextPageItem.create_page_token(
                page, params.get('items_per_page', 50)
            )
        else:
            page_token = ''
        params = dict(params, page=page, page_token=page_token)
        return self.reroute(context, path=path, params=params)

    def reroute(self, context, re_match=None, path=None, params=None):
        current_path = context.get_path()
        current_params = context.get_params()
        if re_match:
            path = re_match.group('path')
        if params is None:
            params = current_params
        if (path and path != current_path
                or 'refresh' in params
                or params != current_params):
            result = None
            function_cache = context.get_function_cache()
            window_return = params.pop('window_return', True)
            try:
                result, options = function_cache.run(
                    self.navigate,
                    _refresh=True,
                    _scope=function_cache.SCOPE_NONE,
                    context=context.clone(path, params),
                )
            finally:
                if not result:
                    return False
                context.get_ui().set_property(REROUTE, path)
                context.execute('ActivateWindow(Videos, {0}{1})'.format(
                    context.create_uri(path, params),
                    ', return' if window_return else '',
                ))
        return False

    def on_bookmarks(self, context, re_match):
        raise NotImplementedError()

    def on_watch_later(self, context, re_match):
        raise NotImplementedError()

    def _internal_search(self, context, re_match):
        params = context.get_params()
        ui = context.get_ui()

        command = re_match.group('command')
        search_history = context.get_search_history()

        if not command or command == 'query':
            query = to_unicode(params.get('q', ''))
            if not params.get('incognito') and not params.get('channel_id'):
                search_history.update(query)
            return self.on_search(query, context, re_match)

        if command == 'remove':
            query = to_unicode(params.get('q', ''))
            search_history.remove(query)
            ui.refresh_container()
            return True

        if command == 'rename':
            query = to_unicode(params.get('q', ''))
            result, new_query = ui.on_keyboard_input(
                context.localize('search.rename'), query
            )
            if result:
                search_history.rename(query, new_query)
                ui.refresh_container()
            return True

        if command == 'clear':
            search_history.clear()
            ui.refresh_container()
            return True

        if command == 'input':
            data_cache = context.get_data_cache()

            query = None
            #  came from page 1 of search query by '..'/back
            #  user doesn't want to input on this path
            if (not params.get('refresh')
                    and context.is_plugin_path(
                        context.get_infolabel('Container.FolderPath'),
                        ('query', 'input')
                    )):
                cached = data_cache.get_item('search_query', data_cache.ONE_DAY)
                if cached:
                    query = to_unicode(cached)
            else:
                result, input_query = ui.on_keyboard_input(
                    context.localize('search.title')
                )
                if result:
                    query = input_query

            if not query:
                return False

            data_cache.set_item('search_query', query)

            if not params.get('incognito') and not params.get('channel_id'):
                search_history.update(query)
            context.set_path(paths.SEARCH, 'query')
            return self.on_search(query, context, re_match)

        context.set_content(content.LIST_CONTENT)
        result = []

        location = context.get_param('location', False)

        # 'New Search...'
        new_search_item = NewSearchItem(
            context, location=location
        )
        result.append(new_search_item)

        for search in search_history.get_items():
            # little fallback for old history entries
            if isinstance(search, DirectoryItem):
                search = search.get_name()

            # we create a new instance of the SearchItem
            search_history_item = SearchHistoryItem(
                context, search, location=location
            )
            result.append(search_history_item)

        return result, {self.RESULT_CACHE_TO_DISC: False}

    def _on_command(self, _context, re_match):
        command = re_match.group('command')
        return UriItem('command://{0}'.format(command))

    def handle_exception(self, context, exception_to_handle):
        return True

    def tear_down(self):
        pass


class RegisterProviderPath(object):
    def __init__(self, re_path):
        self._kodion_re_path = re_path

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # only use a wrapper if you need extra code to be run here
            return func(*args, **kwargs)

        wrapper.kodion_re_path = self._kodion_re_path
        return wrapper
