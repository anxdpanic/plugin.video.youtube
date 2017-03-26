__author__ = 'bromix'

from ..abstract_context_ui import AbstractContextUI
from ...logging import *
from .mock_progress_dialog import MockProgressDialog


class MockContextUI(AbstractContextUI):
    def __init__(self):
        AbstractContextUI.__init__(self)
        self._view_mode = None
        pass

    def set_view_mode(self, view_mode):
        self._view_mode = view_mode
        pass

    def create_progress_dialog(self, heading, text=None, background=False):
        return MockProgressDialog(heading, text)

    def get_view_mode(self):
        return self._view_mode

    def get_skin_id(self):
        return 'skin.kodion.dummy'

    def on_keyboard_input(self, title, default='', hidden=False):
        print '[' + title + ']'
        print "Returning 'Hello World'"
        # var = raw_input("Please enter something: ")
        var = u'Hello World'
        if var:
            return True, var

        return False, ''

    def show_notification(self, message, header='', image_uri='', time_milliseconds=5000):
        log('=======NOTIFICATION=======')
        log('Message  : %s' % message)
        log('header   : %s' % header)
        log('image_uri: %s' % image_uri)
        log('Time     : %d' % time_milliseconds)
        log('==========================')
        pass

    def open_settings(self):
        log("called 'open_settings'")
        pass

    def refresh_container(self):
        log("called 'refresh_container'")
        pass

    pass

