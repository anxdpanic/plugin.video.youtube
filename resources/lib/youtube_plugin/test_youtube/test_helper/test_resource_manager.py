__author__ = 'bromix'

from ... import kodion
from ...youtube import Provider
from ...youtube.helper import ResourceManager

import unittest


class TestResourceManager(unittest.TestCase):
    def test_get_related_playlists(self):
        provider = Provider()
        context = kodion.Context()

        resource_manager = ResourceManager(context, provider.get_client(context))
        resource_manager.clear()
        playlists = resource_manager.get_related_playlists('UCDbAn9LEzqONk__uXA6a9jQ')
        playlists = resource_manager.get_related_playlists('UCDbAn9LEzqONk__uXA6a9jQ')
        pass

    def test_get_fanarts(self):
        provider = Provider()
        context = kodion.Context()

        resource_manager = ResourceManager(context, provider.get_client(context))
        resource_manager.clear()
        fanarts = resource_manager.get_fanarts(['UCDbAn9LEzqONk__uXA6a9jQ', 'UC8i4HhaJSZhm-fu84Bl72TA'])
        fanarts = resource_manager.get_fanarts(['UCDbAn9LEzqONk__uXA6a9jQ', 'UC8i4HhaJSZhm-fu84Bl72TA'])
        pass
    pass
