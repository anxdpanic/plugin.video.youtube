"""Stand-in for Kodi's xbmcvfs module: special:// paths map into a temporary folder."""
import os
import tempfile

ROOT = os.path.join(tempfile.gettempdir(), 'youtube-tests')


def translatePath(path):  # noqa: N802 (Kodi API name)
    if path.startswith('special://'):
        return os.path.join(ROOT, path[len('special://'):])
    return path
