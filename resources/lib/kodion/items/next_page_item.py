__author__ = 'bromix'

from .directory_item import DirectoryItem
from .. import constants


class NextPageItem(DirectoryItem):
    def __init__(self, context, current_page=1, image=None, fanart=None):
        new_params = {}
        new_params.update(context.get_params())
        new_params['page'] = unicode(current_page + 1)
        name = context.localize(constants.localize.NEXT_PAGE, 'Next Page')
        if name.find('%d') != -1:
            name %= current_page + 1
            pass

        DirectoryItem.__init__(self, name, context.create_uri(context.get_path(), new_params), image=image)
        if fanart:
            self.set_fanart(fanart)
            pass
        else:
            self.set_fanart(context.get_fanart())
            pass

        pass

    pass
