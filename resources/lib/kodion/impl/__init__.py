__author__ = 'bromix'

__all__ = ['Settings', 'Context']

try:
    from .xbmc.xbmc_logger import XbmcLogger as Logger
    from .xbmc.xbmc_plugin_settings import XbmcPluginSettings as Settings
    from .xbmc.xbmc_context import XbmcContext as Context
    from .xbmc.xbmc_context_ui import XbmcContextUI as ContextUI
    from .xbmc.xbmc_runner import XbmcRunner as Runner
except ImportError:
    from .mock.mock_log import MockLogger as Logger
    from .mock.mock_settings import MockSettings as Settings
    from .mock.mock_context import MockContext as Context
    from .mock.mock_context_ui import MockContextUI as ContextUI
    from .mock.mock_runner import MockRunner as Runner
    pass