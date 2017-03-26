__author__ = 'bromix'

from .base_item import BaseItem


class UriItem(BaseItem):
    def __init__(self, uri):
        BaseItem.__init__(self, name=u'', uri=uri)
        pass

    pass
