from .base_item import BaseItem


class DirectoryItem(BaseItem):
    def __init__(self, name, uri, image=u'', fanart=u''):
        BaseItem.__init__(self, name, uri, image, fanart)
        pass

    def set_name(self, name):
        self._name = unicode(name)
        pass

    pass