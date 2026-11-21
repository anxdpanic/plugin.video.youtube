"""Stand-in for Kodi's xbmcplugin module; records what a listing call produced."""
SORT_METHOD_UNSORTED, SORT_METHOD_LABEL, SORT_METHOD_DURATION = 0, 1, 2

ITEMS = []
ENDED = []
RESOLVED = []
CONTENT = []


def reset():
    del ITEMS[:]
    del ENDED[:]
    del RESOLVED[:]
    del CONTENT[:]


def addDirectoryItem(handle, url, listitem, isFolder=False, totalItems=0):  # noqa: N802,N803 (Kodi API)
    ITEMS.append((url, listitem, isFolder))
    return True


def endOfDirectory(handle, succeeded=True, updateListing=False, cacheToDisc=True):  # noqa: N802,N803
    ENDED.append(succeeded)


def setResolvedUrl(handle, succeeded, listitem):  # noqa: N802
    RESOLVED.append((succeeded, listitem))


def setContent(handle, content):  # noqa: N802
    CONTENT.append(content)


def addSortMethod(handle, sortMethod, labelMask='', label2Mask=''):  # noqa: N802,N803
    pass
