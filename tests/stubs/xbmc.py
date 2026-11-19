"""Minimal stand-in for Kodi's xbmc module, enough to import and exercise the add-on in tests."""
LOGDEBUG, LOGINFO, LOGWARNING, LOGERROR = 0, 1, 2, 3
ISO_639_1, ISO_639_2, ENGLISH_NAME = 0, 1, 2
PLAYLIST_VIDEO = 1

LOG = []
BUILTINS = []


def log(msg, level=LOGDEBUG):
    LOG.append((level, msg))


def getLanguage(fmt=ENGLISH_NAME, region=False):  # noqa: N802 (Kodi API name)
    return 'en-gb' if region else 'en'


def executebuiltin(command, wait=False):
    BUILTINS.append(command)


class Monitor:
    def abortRequested(self):  # noqa: N802
        return False

    def waitForAbort(self, timeout=0):  # noqa: N802
        return True


class PlayList:
    def __init__(self, playlist_id):
        self.items = []

    def clear(self):
        self.items = []

    def add(self, url, listitem=None):
        self.items.append((url, listitem))


class Player:
    def play(self, item=None):
        pass
