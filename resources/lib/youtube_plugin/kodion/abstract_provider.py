# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from re import (
    UNICODE,
    compile as re_compile,
)

from . import logging
from .compatibility import string_type
from .constants import (
    CHECK_SETTINGS,
    CONTENT,
    FOLDER_URI,
    ITEMS_PER_PAGE,
    PATHS,
    REROUTE_PATH,
    WINDOW_CACHE,
    WINDOW_FALLBACK,
    WINDOW_REPLACE,
    WINDOW_RETURN,
)
from .debug import ExecTimeout
from .exceptions import KodionException
from .items import (
    DirectoryItem,
    NewSearchItem,
    NextPageItem,
    SearchHistoryItem,
    UriItem,
)
from .utils.convert_format import to_unicode


class AbstractProvider(object):
    log = logging.getLogger(__name__)

    CACHE_TO_DISC = 'provider_cache_to_disc'  # type: bool
    FALLBACK = 'provider_fallback'  # type: bool | str
    FORCE_PLAY = 'provider_force_play'  # type: bool
    FORCE_REFRESH = 'provider_force_refresh'  # type: bool
    FORCE_RESOLVE = 'provider_force_resolve'  # type: bool
    FORCE_RETURN = 'provider_force_return'  # type: bool
    POST_RUN = 'provider_post_run'  # type: bool
    UPDATE_LISTING = 'provider_update_listing'  # type: bool
    CONTENT_TYPE = 'provider_content_type'  # type: tuple[str, str, str]

    # map for regular expression (path) to method (names)
    _dict_path = {}

    def __init__(self):
        # register some default paths
        self.register_path(r''.join((
            '^',
            '(?:', PATHS.HOME, ')?/?$'
        )), self.on_root)

        self.register_path(r''.join((
            '^',
            PATHS.ROUTE,
            '(?P<path>/[^?]+?)(?:/*[?].+|/*)$'
        )), self.on_reroute)

        self.register_path(r''.join((
            '^',
            PATHS.GOTO_PAGE,
            '(?P<page>/[0-9]+)?'
            '(?P<path>/[^?]+?)(?:/*[?].+|/*)$'
        )), self.on_goto_page)

        self.register_path(r''.join((
            '^',
            PATHS.COMMAND,
            '/(?P<command>[^?]+?)(?:/*[?].+|/*)$'
        )), self.on_command)

        self.register_path(r''.join((
            '^',
            PATHS.WATCH_LATER,
            '/(?P<command>add|clear|list|play|remove)?/?$'
        )), self.on_watch_later)

        self.register_path(r''.join((
            '^',
            PATHS.BOOKMARKS,
            '/(?P<command>add|add_custom|clear|edit|list|play|remove)?/?$'
        )), self.on_bookmarks)

        self.register_path(r''.join((
            '^',
            '(', PATHS.SEARCH, '|', PATHS.EXTERNAL_SEARCH, ')',
            '/(?P<command>input|input_prompt|query|list|links|remove|clear|rename)?/?$'
        )), self.on_search)

        self.register_path(r''.join((
            '^',
            PATHS.HISTORY,
            '/(?P<command>clear|list|mark_as|mark_unwatched|mark_watched|play|remove|reset_resume)?/?$'
        )), self.on_playback_history)

        self.register_path(r'(?P<path>.*\/)extrafanart\/([\?#].+)?$',
                           self.on_extra_fanart)

    @classmethod
    def register_path(cls, re_path, command=None):
        """
        Registers a new method for the given regular expression
        :param re_path: regular expression of the path
        :param command: command or function to be registered
        :return:
        """

        def wrapper(command):
            if callable(command):
                func = command
            else:
                func = getattr(command, '__func__', None)
                if not callable(func):
                    return None

            cls._dict_path[re_compile(re_path, UNICODE)] = func
            return command

        if command:
            return wrapper(command)
        return wrapper

    def run_wizard(self, context, last_run=None):
        localize = context.localize
        # ui local variable used for ui.get_view_manager() in unofficial version
        ui = context.get_ui()

        settings_state = {'state': 'defer'}
        context.ipc_exec(CHECK_SETTINGS, timeout=5, payload=settings_state)

        if last_run and last_run > 1:
            self.pre_run_wizard_step(provider=self, context=context)
        wizard_steps = self.get_wizard_steps()

        step = 0
        steps = len(wizard_steps)

        try:
            if wizard_steps and ui.on_yes_no_input(
                    ' - '.join((localize('youtube'), localize('setup_wizard'))),
                    localize(('setup_wizard.prompt.x',
                              'setup_wizard.prompt.settings')),
            ):
                for wizard_step in wizard_steps:
                    if callable(wizard_step):
                        step = wizard_step(provider=self,
                                           context=context,
                                           step=step,
                                           steps=steps)
                    else:
                        step += 1
        finally:
            settings = context.get_settings(refresh=True)
            settings.setup_wizard_enabled(False)
            settings_state['state'] = 'process'
            context.ipc_exec(CHECK_SETTINGS, timeout=5, payload=settings_state)

    @staticmethod
    def get_wizard_steps():
        # can be overridden by the derived class
        return []

    @staticmethod
    def pre_run_wizard_step(provider, context):
        # can be overridden by the derived class
        pass

    def navigate(self, context):
        path = context.get_path()
        for re_path, handler in self._dict_path.items():
            re_match = re_path.search(path)
            if not re_match:
                continue

            exec_limit = context.get_settings().exec_limit()
            if exec_limit:
                handler = ExecTimeout(
                    seconds=exec_limit,
                    # log_only=True,
                    # trace_opcodes=True,
                    # trace_threads=True,
                    log_locals=(-15, None),
                    callback=None,
                )(handler)

            options = {
                self.CACHE_TO_DISC: True,
                self.UPDATE_LISTING: False,
            }
            result = handler(provider=self, context=context, re_match=re_match)
            if isinstance(result, tuple):
                result, new_options = result
                if new_options:
                    options.update(new_options)

            if context.refresh_requested():
                options[self.CACHE_TO_DISC] = True
                options[self.UPDATE_LISTING] = True

            return result, options

        raise KodionException('Mapping for path "%s" not found' % path)

    def on_extra_fanart_run(self, context, re_match):
        """
        The implementation of the provider can override this behavior.
        :param context:
        :param re_match:
        :return:
        """
        return

    @staticmethod
    def on_extra_fanart(provider, context, re_match):
        path = re_match.group('path')
        new_context = context.clone(new_path=path)
        return provider.on_extra_fanart_run(new_context, re_match)

    @staticmethod
    def on_playback_history(provider, context, re_match):
        raise NotImplementedError()

    @staticmethod
    def on_root(provider, context, re_match):
        raise NotImplementedError()

    @staticmethod
    def on_goto_page(provider, context, re_match):
        ui = context.get_ui()

        page = re_match.group('page')
        if page:
            page = int(page.lstrip('/'))
        else:
            result, page = ui.on_numeric_input(
                title=context.localize('page.choose'),
                default=1,
            )
            if not result:
                return False

        path = re_match.group('path')
        params = context.get_params()
        if 'page_token' in params:
            page_token = NextPageItem.create_page_token(
                page, params.get(ITEMS_PER_PAGE, 50)
            )
        else:
            page_token = ''
        for param in NextPageItem.JUMP_PAGE_PARAM_EXCLUSIONS:
            if param in params:
                del params[param]
        params = dict(params, page=page, page_token=page_token)

        if (not ui.busy_dialog_active()
                and ui.get_container_info(FOLDER_URI)):
            return provider.reroute(context=context, path=path, params=params)
        return provider.navigate(context.clone(path, params))

    @staticmethod
    def on_reroute(provider, context, re_match):
        return provider.reroute(
            context=context,
            path=re_match.group('path'),
            params=context.get_params(),
        )

    def reroute(self, context, path=None, params=None, uri=None):
        ui = context.get_ui()
        current_path, current_params = context.parse_uri(
            ui.get_container_info(FOLDER_URI, container_id=None)
        )

        if uri is None:
            if path is None:
                path = current_path
            if params is None:
                params = current_params
        else:
            uri = context.parse_uri(uri)
            if params:
                uri[1].update(params)
            path, params = uri

        if not path:
            self.log.error_trace('No route path')
            return False
        elif path.startswith(PATHS.ROUTE):
            path = path[len(PATHS.ROUTE):]

        window_cache = params.pop(WINDOW_CACHE, True)
        window_fallback = params.pop(WINDOW_FALLBACK, False)
        window_replace = params.pop(WINDOW_REPLACE, False)
        window_return = params.pop(WINDOW_RETURN, True)

        if window_fallback:
            if ui.get_container_info(FOLDER_URI):
                self.log.debug('Rerouting - Fallback route not required')
                return False, {self.FALLBACK: False}

        refresh = context.refresh_requested(params=params)
        if (refresh or (
                params == current_params
                and path.rstrip('/') == current_path.rstrip('/')
        )):
            if refresh and refresh < 0:
                del params['refresh']
            else:
                params['refresh'] = context.refresh_requested(
                    force=True,
                    on=True,
                    params=params,
                )
        else:
            params['refresh'] = 0

        result = None
        uri = context.create_uri(path, params)
        if window_cache:
            function_cache = context.get_function_cache()
            with ui.on_busy():
                result, options = function_cache.run(
                    self.navigate,
                    _refresh=True,
                    _scope=function_cache.SCOPE_NONE,
                    context=context.clone(path, params),
                )
            if not result:
                self.log.debug(('No results', 'URI: %s'), uri)
                return False

        self.log.debug(('Success',
                        'URI:      {uri}',
                        'Cache:    {window_cache!r}',
                        'Fallback: {window_fallback!r}',
                        'Replace:  {window_replace!r}',
                        'Return:   {window_return!r}'),
                       uri=uri,
                       window_cache=window_cache,
                       window_fallback=window_fallback,
                       window_replace=window_replace,
                       window_return=window_return)

        reroute_path = ui.get_property(REROUTE_PATH)
        if reroute_path:
            return True

        if window_cache:
            ui.set_property(REROUTE_PATH, path)

        action = ''.join((
            'ReplaceWindow' if window_replace else 'ActivateWindow',
            '(Videos,',
            uri,
            ',return)' if window_return else ')',
        ))

        timeout = 30
        while ui.busy_dialog_active():
            timeout -= 1
            if timeout < 0:
                self.log.warning('Multiple busy dialogs active'
                                 ' - Rerouting workaround')
                return UriItem('command://{0}'.format(action))
            context.sleep(0.1)
        else:
            context.execute(
                action,
                # wait=True,
                # wait_for=(REROUTE_PATH if window_cache else None),
                # wait_for_set=False,
                # block_ui=True,
            )
            return True

    @staticmethod
    def on_bookmarks(provider, context, re_match):
        raise NotImplementedError()

    @staticmethod
    def on_watch_later(provider, context, re_match):
        raise NotImplementedError()

    def on_search_run(self, context, query):
        raise NotImplementedError()

    @staticmethod
    def on_search(provider, context, re_match):
        params = context.get_params()
        localize = context.localize
        ui = context.get_ui()

        command = re_match.group('command')
        search_history = context.get_search_history()

        if not command or command == 'query':
            query = to_unicode(params.get('q', ''))
            if query:
                result, options = provider.on_search_run(context, query=query)
                if not options:
                    options = {provider.CACHE_TO_DISC: False}
                if result:
                    fallback = options.setdefault(
                        provider.FALLBACK, context.get_uri()
                    )
                    if fallback and isinstance(fallback, string_type):
                        ui.set_property(provider.FALLBACK, fallback)
                return result, options
            command = 'list'
            context.set_path(PATHS.SEARCH, command)

        if command == 'remove':
            query = to_unicode(params.get('q', ''))
            if not ui.on_yes_no_input(
                    localize('content.remove'),
                    localize('content.remove.check.x', query),
            ):
                return False, None

            search_history.del_item(query)
            ui.show_notification(localize('removed.name.x', query),
                                 time_ms=2500,
                                 audible=False)
            return True, {provider.FORCE_REFRESH: True}

        if command == 'rename':
            query = to_unicode(params.get('q', ''))
            result, new_query = ui.on_keyboard_input(
                localize('search.rename'), query
            )
            if not result:
                return False, None

            search_history.del_item(query)
            search_history.add_item(new_query)
            return True, {provider.FORCE_REFRESH: True}

        if command == 'clear':
            if not ui.on_yes_no_input(
                    localize('search.clear'),
                    localize(('content.clear.check.x', 'search.history'))
            ):
                return False, None

            search_history.clear()
            ui.show_notification(localize('completed'),
                                 time_ms=2500,
                                 audible=False)
            return True, {provider.FORCE_REFRESH: True}

        if command == 'links':
            return provider.on_specials_x(
                provider,
                context,
                category='description_links',
            )

        if command.startswith('input'):
            result, query = ui.on_keyboard_input(
                localize('search.title')
            )
            if result and query:
                result = []
                options = {
                    provider.FALLBACK: context.create_uri(
                        (PATHS.SEARCH, 'query'),
                        dict(params, q=query, category_label=query),
                        window={
                            'replace': False,
                            'return': True,
                        },
                    ),
                    provider.FORCE_RETURN: True,
                    provider.POST_RUN: True,
                    provider.CACHE_TO_DISC: True,
                    provider.UPDATE_LISTING: False,
                }
            else:
                result = False
                options = {
                    provider.FALLBACK: True,
                }
            return result, options

        location = context.get_param('location', False)

        result = []
        options = {
            provider.CACHE_TO_DISC: False,
            provider.CONTENT_TYPE: {
                'content_type': CONTENT.LIST_CONTENT,
                'sub_type': None,
                'category_label': localize('search'),
            },
        }

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

        return result, options

    @staticmethod
    def on_command(re_match, **_kwargs):
        command = re_match.group('command')
        return UriItem(''.join(('command://', command)))

    def handle_exception(self, context, exception_to_handle):
        return True

    def tear_down(self):
        pass
