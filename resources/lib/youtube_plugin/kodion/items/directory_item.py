from .base_item import BaseItem


class DirectoryItem(BaseItem):
    def __init__(self, name, uri, image=u'', fanart=u''):
        BaseItem.__init__(self, name, uri, image, fanart)
        self._plot = unicode(name)

    def set_name(self, name):
        self._name = unicode(name)

    def set_plot(self, plot):
        self._plot = unicode(plot)

    def get_plot(self):
        return self._plot
