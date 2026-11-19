"""Stand-in for Kodi's xbmcaddon module. Settings come from SETTINGS, strings from STRINGS."""
import os
import tempfile

PROFILE = os.path.join(tempfile.gettempdir(), 'leanback-tests', 'profile')
ADDON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'plugin.video.leanback'))

SETTINGS = {}
STRINGS = {}


class Addon:
    def __init__(self, addon_id=None):
        pass

    def getAddonInfo(self, key):  # noqa: N802 (Kodi API name)
        return {'id': 'plugin.video.leanback', 'name': 'Leanback', 'version': '0.0.0',
                'profile': PROFILE, 'path': ADDON_PATH}.get(key, '')

    def getSetting(self, key):  # noqa: N802
        return str(SETTINGS.get(key, ''))

    def getSettingBool(self, key):  # noqa: N802
        return bool(SETTINGS.get(key, False))

    def getSettingInt(self, key):  # noqa: N802
        return int(SETTINGS.get(key, 0))

    def getLocalizedString(self, string_id):  # noqa: N802
        return STRINGS.get(string_id, 'str%d' % string_id)
