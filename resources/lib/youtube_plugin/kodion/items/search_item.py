__author__ = 'bromix'

from .directory_item import DirectoryItem
from .. import constants


class SearchItem(DirectoryItem):
    def __init__(self, context, alt_name=None, image=None, fanart=None):
        name = alt_name
        if not name:
            name = context.localize(constants.localize.SEARCH)
            pass

        if image is None:
            image = context.create_resource_path('media/search.png')
            pass

        DirectoryItem.__init__(self, name, context.create_uri([constants.paths.SEARCH, 'list']), image=image)
        if fanart:
            self.set_fanart(fanart)
            pass
        else:
            self.set_fanart(context.get_fanart())
            pass
        pass

    pass
