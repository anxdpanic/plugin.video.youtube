__author__ = 'bromix'

from .base_item import BaseItem


class ImageItem(BaseItem):
    def __init__(self, name, uri, image=u'', fanart=u''):
        BaseItem.__init__(self, name, uri, image, fanart)
        self._title = None

    def set_title(self, title):
        self._title = title

    def get_title(self):
        return self._title
