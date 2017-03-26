# -*- coding: utf-8 -*-

__author__ = 'bromix'

from .. import kodion
from ..youtube import Provider

import unittest


class TestProvider(unittest.TestCase):
    def test_description_links(self):
        provider = Provider()

        path = kodion.utils.create_path('special', 'description_links')
        context = kodion.Context(path=path, params={'video_id': 'QEwEWKbWnaQ'})
        context.set_localization(30502, 'Go to %s')
        result = provider.navigate(context)
        items = result[0]
        pass

    def test_playlist(self):
        provider = Provider()

        path = kodion.utils.create_path('playlist', 'LL9DDFrb_dGvEvcTrzNn5LpA')
        context = kodion.Context(path=path)
        context.set_localization(30502, 'Go to %s')
        result = provider.navigate(context)
        items = result[0]
        pass

    def test_channel_by_name(self):
        provider = Provider()

        path = kodion.utils.create_path('user', 'Gronkh')
        context = kodion.Context(path=path)
        context.set_localization(30502, 'Go to %s')
        result = provider.navigate(context)
        items = result[0]
        pass

    def test_play(self):
        provider = Provider()

        path = kodion.utils.create_path('play')
        context = kodion.Context(path=path, params={'video_id': 'ZCBlKMZLxZA'})
        context.set_localization(30502, 'Go to %s')
        result = provider.navigate(context)
        items = result[0]
        pass

    def test_on_channel_playlists(self):
        provider = Provider()

        path = kodion.utils.create_path('channel', 'UCDbAn9LEzqONk__uXA6a9jQ', 'playlists')
        context = kodion.Context(path=path)
        result = provider.navigate(context)
        items = result[0]
        pass

    def test_on_channel_playlist(self):
        provider = Provider()

        path = kodion.utils.create_path('channel', 'some_channel_id', 'playlist', 'UUDbAn9LEzqONk__uXA6a9jQ')
        context = kodion.Context(path=path)
        context.set_localization(30502, 'Go to %s')
        result = provider.navigate(context)
        items = result[0]
        pass

    def test_on_channel(self):
        provider = Provider()

        path = kodion.utils.create_path('channel', 'UCDbAn9LEzqONk__uXA6a9jQ')
        context = kodion.Context(path=path)
        result = provider.navigate(context)
        items = result[0]
        pass

    def test_on_search_playlist(self):
        provider = Provider()

        path = kodion.utils.create_path(kodion.constants.paths.SEARCH, 'query')
        context = kodion.Context(path=path, params={'q': 'lgr', 'search_type': 'playlist'})
        result = provider.navigate(context)
        items = result[0]
        self.assertGreater(len(items), 0)
        kodion.utils.print_items(items)

        context = context.clone(new_path=path, new_params={'q': 'lgr', 'search_type': 'playlist', 'page_token': 'CDIQAA'})
        result = provider.navigate(context)
        items = result[0]
        self.assertGreater(len(items), 0)
        kodion.utils.print_items(items)
        pass

    def test_on_search(self):
        provider = Provider()

        path = kodion.utils.create_path('search')
        context = kodion.Context(path=path, params={'q': 'The Breakfast Club é Extras'})
        context.set_localization(30502, 'Go to %s')
        result = provider.navigate(context)
        items = result[0]
        self.assertGreater(len(items), 0)
        kodion.utils.print_items(items)
        pass

    def test_on_search_video(self):
        provider = Provider()

        path = kodion.utils.create_path(kodion.constants.paths.SEARCH, 'query')
        context = kodion.Context(path=path, params={'q': 'lgr'})
        context.set_localization(30502, 'Go to %s')
        result = provider.navigate(context)
        items = result[0]
        self.assertGreater(len(items), 0)
        kodion.utils.print_items(items)
        pass

    def test_on_root(self):
        provider = Provider()

        context = kodion.Context(path='/')
        result = provider.navigate(context)

        items = result[0]
        self.assertGreater(len(items), 0)

        kodion.utils.print_items(items)
        pass

    pass
