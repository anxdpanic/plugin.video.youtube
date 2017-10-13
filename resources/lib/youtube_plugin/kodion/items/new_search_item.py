__author__ = 'bromix'

from .directory_item import DirectoryItem
from .. import constants


class NewSearchItem(DirectoryItem):
    def __init__(self, context, alt_name=None, image=None, fanart=None, use_history=True):
        name = alt_name
        if not name:
            name = '[B]' + context.localize(constants.localize.SEARCH_NEW) + '[/B]'
            pass

        if image is None:
            image = context.create_resource_path('media/new_search.png')
            pass

        use_history = str(use_history).lower()

        DirectoryItem.__init__(self, name, context.create_uri([constants.paths.SEARCH, 'input'], params={'use_history': use_history}), image=image)
        if fanart:
            self.set_fanart(fanart)
            pass
        else:
            self.set_fanart(context.get_fanart())
            pass
        pass

    pass
