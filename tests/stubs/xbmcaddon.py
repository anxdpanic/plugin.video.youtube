"""Stand-in for Kodi's xbmcaddon module. Settings come from SETTINGS, strings from STRINGS."""
import ast
import os
import re
import tempfile

PROFILE = os.path.join(tempfile.gettempdir(), 'leanback-tests', 'profile')
ADDON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'plugin.video.leanback'))

SETTINGS = {}
STRINGS = {}


def english(string_id):
    """The en_GB text of a string id, from the add-on's strings.po."""
    path = os.path.join(ADDON_PATH, 'resources', 'language', 'resource.language.en_gb', 'strings.po')
    with open(path, encoding='utf-8') as po:
        found = re.search(r'msgctxt "#%d"\nmsgid "((?:[^"\\]|\\.)*)"' % string_id, po.read())
    return ast.literal_eval('"%s"' % found.group(1))


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
