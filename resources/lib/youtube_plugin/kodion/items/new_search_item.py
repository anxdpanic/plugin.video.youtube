__author__ = 'bromix'

from .directory_item import DirectoryItem
from .. import constants


class NewSearchItem(DirectoryItem):
    def __init__(self, context, alt_name=None, image=None, fanart=None, incognito=False, channel_id='', addon_id=''):
        name = alt_name
        if not name:
            name = '[B]' + context.localize(constants.localize.SEARCH_NEW) + '[/B]'

        if image is None:
            image = context.create_resource_path('media/new_search.png')

        item_params = {}
        if addon_id:
            item_params.update({'addon_id': addon_id})
        if incognito:
            item_params.update({'incognito': incognito})
        if channel_id:
            item_params.update({'channel_id': channel_id})
        DirectoryItem.__init__(self, name, context.create_uri([constants.paths.SEARCH, 'input'], params=item_params), image=image)
        if fanart:
            self.set_fanart(fanart)
        else:
            self.set_fanart(context.get_fanart())
