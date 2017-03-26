import time

__author__ = 'bromix'

import tempfile

from ..abstract_context import AbstractContext
from .mock_settings import MockSettings
from .mock_context_ui import MockContextUI
from .mock_system_version import MockSystemVersion
from ...logging import log


class MockContext(AbstractContext):
    def __init__(self, path=u'/', params=None, plugin_name='MOCK Plugin', plugin_id='mock.plugin', ):
        AbstractContext.__init__(self, path, params, plugin_name, plugin_id)

        self._data_path = tempfile.gettempdir()
        self._settings = MockSettings()
        self._dict_localization = {5000: u'Hello World',
                                   5001: u'MOCK Plugin'}

        self._ui = None
        self._system_version = MockSystemVersion(1, 3, 'Kodion Test System', 'MOCK App')
        self._language = 'en-US'
        self._version = '1.9'
        pass

    def set_localization(self, text_id, value):
        self._dict_localization[text_id] = value
        pass

    def set_language(self, language):
        self._language = language
        pass

    def get_language(self):
        return self._language

    def get_system_version(self):
        return self._system_version

    def get_ui(self):
        if not self._ui:
            self._ui = MockContextUI()
            pass
        return self._ui

    def get_handle(self):
        return 666

    def get_data_path(self):
        return self._data_path

    def get_native_path(self):
        return 'virtual_path'

    def get_settings(self):
        return self._settings

    def localize(self, text_id, default_text=u''):
        return self._dict_localization.get(text_id, default_text)

    def set_content_type(self, content_type):
        log("Set ContentType to '%s'" % content_type)
        pass

    def add_sort_method(self, *sort_methods):
        for sort_method in sort_methods:
            log("add SortMethod '%s'" % (str(sort_method)))
            pass
        pass

    def clone(self, new_path=None, new_params=None):
        if not new_path:
            new_path = self.get_path()
            pass

        if not new_params:
            new_params = self.get_params()
            pass

        new_context = MockContext(path=new_path, params=new_params, plugin_name=self._plugin_name,
                                  plugin_id=self._plugin_id)

        new_context._function_cache = self._function_cache
        new_context._search_history = self._search_history
        new_context._favorite_list = self._favorite_list
        new_context._watch_later_list = self._watch_later_list
        new_context._access_manager = self._access_manager

        return new_context

    def execute(self, command):
        log("execute '%s'" % command)
        pass

    def sleep(self, milli_seconds):
        time.sleep(milli_seconds/1000.0)
        pass

    pass