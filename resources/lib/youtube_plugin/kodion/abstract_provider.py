# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import json
import re
from urllib.parse import quote
from urllib.parse import unquote

from .exceptions import KodionException
from . import items
from . import constants
from . import utils


class AbstractProvider(object):
    RESULT_CACHE_TO_DISC = 'cache_to_disc'  # (bool)
    RESULT_UPDATE_LISTING = 'update_listing'

    def __init__(self):
        self._local_map = {
            'kodion.wizard.view.default': 30027,
            'kodion.wizard.view.episodes': 30028,
            'kodion.wizard.view.movies': 30029,
            'kodion.wizard.view.tvshows': 30032,
            'kodion.wizard.view.songs': 30033,
            'kodion.wizard.view.artists': 30034,
            'kodion.wizard.view.albums': 30035
        }

        # map for regular expression (path) to method (names)
        self._dict_path = {}

        self._data_cache = None

        # register some default paths
        self.register_path(r'^/$', '_internal_root')
        self.register_path(r''.join(['^/', constants.paths.WATCH_LATER, '/(?P<command>add|remove|list)/?$']),
                           '_internal_watch_later')
        self.register_path(r''.join(['^/', constants.paths.FAVORITES, '/(?P<command>add|remove|list)/?$']), '_internal_favorite')
        self.register_path(r''.join(['^/', constants.paths.SEARCH, '/(?P<command>input|query|list|remove|clear|rename)/?$']),
                           '_internal_search')
        self.register_path(r'(?P<path>.*\/)extrafanart\/([\?#].+)?$', '_internal_on_extra_fanart')

        """
        Test each method of this class for the appended attribute '_re_match' by the
        decorator (RegisterProviderPath).
        The '_re_match' attributes describes the path which must match for the decorated method.
        """

        for method_name in dir(self):
            method = getattr(self, method_name)
            if hasattr(method, 'kodion_re_path'):
                self.register_path(method.kodion_re_path, method_name)

    def get_alternative_fanart(self, context):
        return context.get_fanart()

    def register_path(self, re_path, method_name):
        """
        Registers a new method by name (string) for the given regular expression
        :param re_path: regular expression of the path
        :param method_name: name of the method
        :return:
        """
        self._dict_path[re_path] = method_name

    def _process_wizard(self, context):
        # start the setup wizard
        wizard_steps = []
        if context.get_settings().is_setup_wizard_enabled():
            context.get_settings().set_bool(constants.setting.SETUP_WIZARD, False)
            wizard_steps.extend(self.get_wizard_steps(context))

        if wizard_steps and context.get_ui().on_yes_no_input(context.get_name(),
                                                             context.localize(constants.localize.SETUP_WIZARD_EXECUTE)):
            for wizard_step in wizard_steps:
                wizard_step[0](*wizard_step[1])

    def get_wizard_supported_views(self):
        return ['default']

    def get_wizard_steps(self, context):
        # can be overridden by the derived class
        return []

    def navigate(self, context):
        self._process_wizard(context)

        path = context.get_path()

        for key in self._dict_path:
            re_match = re.search(key, path, re.UNICODE)
            if re_match is not None:
                method_name = self._dict_path.get(key, '')
                method = getattr(self, method_name)
                if method is not None:
                    result = method(context, re_match)
                    if not isinstance(result, tuple):
                        result = result, {}
                    return result

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
        return None

    def _internal_on_extra_fanart(self, context, re_match):
        path = re_match.group('path')
        new_context = context.clone(new_path=path)
        return self.on_extra_fanart(new_context, re_match)

    def on_search(self, search_text, context, re_match):
        raise NotImplementedError()

    def on_root(self, context, re_match):
        raise NotImplementedError()

    def on_watch_later(self, context, re_match):
        pass

    def _internal_root(self, context, re_match):
        return self.on_root(context, re_match)

    @staticmethod
    def _internal_favorite(context, re_match):
        context.add_sort_method(constants.sort_method.LABEL_IGNORE_THE)

        params = context.get_params()

        command = re_match.group('command')
        if command == 'add':
            fav_item = items.from_json(params['item'])
            context.get_favorite_list().add(fav_item)
        elif command == 'remove':
            fav_item = items.from_json(params['item'])
            context.get_favorite_list().remove(fav_item)
            context.get_ui().refresh_container()
        elif command == 'list':

            directory_items = context.get_favorite_list().list()

            for directory_item in directory_items:
                context_menu = [(context.localize(constants.localize.WATCH_LATER_REMOVE),
                                 'RunPlugin(%s)' % context.create_uri([constants.paths.FAVORITES, 'remove'],
                                                                      params={'item': items.to_jsons(directory_item)}))]
                directory_item.set_context_menu(context_menu)

            return directory_items
        else:
            pass

    def _internal_watch_later(self, context, re_match):
        self.on_watch_later(context, re_match)

        params = context.get_params()

        command = re_match.group('command')
        if command == 'add':
            item = items.from_json(params['item'])
            context.get_watch_later_list().add(item)
        elif command == 'remove':
            item = items.from_json(params['item'])
            context.get_watch_later_list().remove(item)
            context.get_ui().refresh_container()
        elif command == 'list':
            video_items = context.get_watch_later_list().list()

            for video_item in video_items:
                context_menu = [(context.localize(constants.localize.WATCH_LATER_REMOVE),
                                 'RunPlugin(%s)' % context.create_uri([constants.paths.WATCH_LATER, 'remove'],
                                                                      params={'item': items.to_jsons(video_item)}))]
                video_item.set_context_menu(context_menu)

            return video_items
        else:
            # do something
            pass

    @property
    def data_cache(self):
        return self._data_cache

    @data_cache.setter
    def data_cache(self, context):
        if not self._data_cache:
            self._data_cache = context.get_data_cache()

    def _internal_search(self, context, re_match):
        params = context.get_params()

        command = re_match.group('command')
        search_history = context.get_search_history()
        if command == 'remove':
            query = params['q']
            search_history.remove(query)
            context.get_ui().refresh_container()
            return True
        elif command == 'rename':
            query = params['q']
            result, new_query = context.get_ui().on_keyboard_input(context.localize(constants.localize.SEARCH_RENAME),
                                                                   query)
            if result:
                search_history.rename(query, new_query)
                context.get_ui().refresh_container()
            return True
        elif command == 'clear':
            search_history.clear()
            context.get_ui().refresh_container()
            return True
        elif command == 'input':
            self.data_cache = context

            folder_path = context.get_ui().get_info_label('Container.FolderPath')
            query = None
            if (folder_path.startswith('plugin://%s' % context.get_id()) and
                    re.match('.+/(?:query|input)/.*', folder_path)):
                cached_query = self.data_cache.get_item(self.data_cache.ONE_DAY, 'search_query')
                #  came from page 1 of search query by '..'/back, user doesn't want to input on this path
                if cached_query and cached_query.get('search_query', {}).get('query'):
                    query = cached_query.get('search_query', {}).get('query')
                    query = utils.to_unicode(query)
                    query = unquote(query)
            else:
                result, input_query = context.get_ui().on_keyboard_input(context.localize(constants.localize.SEARCH_TITLE))
                if result:
                    query = input_query

            if not query:
                return False

            incognito = str(context.get_param('incognito', False)).lower() == 'true'
            channel_id = context.get_param('channel_id', '')

            query = utils.to_utf8(query)
            try:
                self._data_cache.set('search_query', json.dumps({'query': quote(query)}))
            except KeyError:
                encoded = json.dumps({'query': quote(query.encode('utf8'))})
                self._data_cache.set('search_query', encoded)

            if not incognito and not channel_id:
                try:
                    search_history.update(query)
                except:
                    pass
            context.set_path('/kodion/search/query/')
            if isinstance(query, bytes):
                query = query.decode('utf-8')
            return self.on_search(query, context, re_match)

        elif command == 'query':
            incognito = str(context.get_param('incognito', False)).lower() == 'true'
            channel_id = context.get_param('channel_id', '')
            query = params['q']
            query = utils.to_unicode(query)

            if not incognito and not channel_id:
                try:
                    search_history.update(query)
                except:
                    pass
            if isinstance(query, bytes):
                query = query.decode('utf-8')
            return self.on_search(query, context, re_match)
        else:
            context.set_content_type(constants.content_type.FILES)
            result = []

            location = str(context.get_param('location', False)).lower() == 'true'

            # 'New Search...'
            new_search_item = items.NewSearchItem(context, fanart=self.get_alternative_fanart(context), location=location)
            result.append(new_search_item)

            for search in search_history.list():
                # little fallback for old history entries
                if isinstance(search, items.DirectoryItem):
                    search = search.get_name()

                # we create a new instance of the SearchItem
                search_history_item = items.SearchHistoryItem(context, search, fanart=self.get_alternative_fanart(context), location=location)
                result.append(search_history_item)

            if search_history.is_empty():
                #  context.execute('RunPlugin(%s)' % context.create_uri([constants.paths.SEARCH, 'input']))
                pass

            return result, {self.RESULT_CACHE_TO_DISC: False}

    def handle_exception(self, context, exception_to_handle):
        return True

    def tear_down(self, context):
        pass
