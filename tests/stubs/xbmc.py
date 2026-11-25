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


CONDITIONS = {'Window.IsMedia': True}  # browsed in the Videos window unless a test says otherwise


def getCondVisibility(condition):  # noqa: N802
    return CONDITIONS.get(condition, False)


# Kodi's own strings, worded as Kodi 21 ships them.
LOCALIZED = {222: 'Cancel', 12021: 'Play from beginning', 12022: 'Resume from {0:s}'}


def getLocalizedString(string_id):  # noqa: N802
    return LOCALIZED.get(string_id, '')


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
    PLAYING = ''  # file the stub reports as playing
    TIME = 0.0
    SEEKS = []
    PLAYED = []
    START_POSITIONS = []

    def play(self, item=None, listitem=None, windowed=False, startpos=-1):
        Player.PLAYED.append(item)
        Player.START_POSITIONS.append(startpos)

    def isPlayingVideo(self):  # noqa: N802
        return bool(Player.PLAYING)

    def isPlaying(self):  # noqa: N802
        return bool(Player.PLAYING)

    def getPlayingFile(self):  # noqa: N802
        return Player.PLAYING

    def getTime(self):  # noqa: N802
        return Player.TIME

    def seekTime(self, seconds):  # noqa: N802
        Player.SEEKS.append(seconds)
