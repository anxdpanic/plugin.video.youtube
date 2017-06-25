from .base_item import BaseItem


class DirectoryItem(BaseItem):
    def __init__(self, name, uri, image=u'', fanart=u''):
        BaseItem.__init__(self, name, uri, image, fanart)
        self._plot = unicode(name)
        pass

    def set_name(self, name):
        self._name = unicode(name)
        pass

    def set_plot(self, plot):
        self._plot = unicode(plot)
        pass

    def get_plot(self):
        return self._plot
