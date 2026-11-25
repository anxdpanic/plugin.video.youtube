"""Stand-in for Kodi's xbmcgui module with just the pieces the add-on touches."""
NOTIFICATION_INFO, NOTIFICATION_WARNING, NOTIFICATION_ERROR = 'info', 'warning', 'error'

NOTIFICATIONS = []
_PROPERTIES = {}


class InfoTagVideo:
    def __init__(self):
        self.values = {}

    def __getattr__(self, name):
        if name.startswith('set'):
            def setter(*args):
                for arg in args:  # Kodi converts ints to a C long, 32 bits on the Vero
                    if isinstance(arg, int) and not -2 ** 31 <= arg < 2 ** 31:
                        raise OverflowError('Python int too large to convert to C long')
                self.values[name[3:].lower()] = args[0] if len(args) == 1 else args
            return setter
        if name.startswith('get'):
            return lambda: self.values.get(name[3:].lower(), '')
        raise AttributeError(name)


class ListItem:
    def __init__(self, label='', label2='', path='', offscreen=False):
        self.label = label
        self.path = path
        self.art = {}
        self.properties = {}
        self.context_menu = []
        self.tag = InfoTagVideo()
        self.mime = None

    def setLabel2(self, label):  # noqa: N802 (Kodi API name)
        self.label2 = label

    def setArt(self, art):  # noqa: N802
        self.art.update(art)

    def setProperty(self, key, value):  # noqa: N802
        self.properties[key] = value

    def getProperty(self, key):  # noqa: N802
        return self.properties.get(key, '')

    def addContextMenuItems(self, items):  # noqa: N802
        self.context_menu.extend(items)

    def getVideoInfoTag(self):  # noqa: N802
        return self.tag

    def setPath(self, path):  # noqa: N802
        self.path = path

    def setMimeType(self, mime):  # noqa: N802
        self.mime = mime

    def setContentLookup(self, enabled):  # noqa: N802
        pass


class Dialog:
    def notification(self, heading, message, icon=None, time=0, sound=True):
        NOTIFICATIONS.append((heading, message, icon))

    def select(self, heading, items, preselect=-1, **kwargs):
        return -1

    def multiselect(self, heading, items, preselect=None, **kwargs):
        return None

    def input(self, heading, defaultt='', **kwargs):
        return ''

    def yesno(self, heading, message, **kwargs):
        return False

    def info(self, listitem):
        return True


class DialogProgress:
    def create(self, heading, message=''):
        pass

    def update(self, percent, message=''):
        pass

    def iscanceled(self):
        return True

    def close(self):
        pass


class Window:
    def __init__(self, window_id=10000):
        pass

    def getProperty(self, key):  # noqa: N802
        return _PROPERTIES.get(key, '')

    def setProperty(self, key, value):  # noqa: N802
        _PROPERTIES[key] = value

    def clearProperty(self, key):  # noqa: N802
        _PROPERTIES.pop(key, None)


class WindowXML(Window):
    def __init__(self, xml_file='', script_path='', default_skin='Default', default_res='720p', *args):
        Window.__init__(self)


class WindowDialog(Window):
    def __init__(self):
        Window.__init__(self)
        self.controls = []
        self.shown = False

    def addControl(self, control):  # noqa: N802
        self.controls.append(control)

    def setFocus(self, control):  # noqa: N802
        self.focused = control

    def show(self):
        self.shown = True

    def close(self):
        self.shown = False


class ControlImage:
    def __init__(self, x, y, width, height, filename, aspectRatio=0, colorDiffuse=None):  # noqa: N803
        self.filename = filename


class ControlLabel:
    def __init__(self, x, y, width, height, label, font=None, textColor=None):  # noqa: N803
        self.label = label
        self.font = font


class ControlTextBox:
    def __init__(self, x, y, width, height, font=None, textColor=None):  # noqa: N803
        self.font = font
        self.text = ''

    def setText(self, text):  # noqa: N802
        self.text = text


class ControlButton:
    def __init__(self, x, y, width, height, label, focusTexture=None, noFocusTexture=None,  # noqa: N803
                 alignment=0, font=None, textColor=None, focusedColor=None):
        self.label = label


class Action:
    def __init__(self, action_id):
        self.action_id = action_id

    def getId(self):  # noqa: N802
        return self.action_id
