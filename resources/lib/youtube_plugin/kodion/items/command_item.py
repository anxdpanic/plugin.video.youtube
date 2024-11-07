# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from . import menu_items
from .directory_item import DirectoryItem
from ..constants import PATHS


class CommandItem(DirectoryItem):
    def __init__(self,
                 name,
                 command,
                 context,
                 image=None,
                 fanart=None,
                 plot=None):
        super(CommandItem, self).__init__(
            name,
            context.create_uri((PATHS.COMMAND, command)),
            image=image,
            fanart=fanart,
            plot=plot,
            action=True,
            category_label='__inherit__',
        )

        context_menu = [
            menu_items.refresh(context),
            menu_items.goto_home(context),
            menu_items.goto_quick_search(context),
        ]
        self.add_context_menu(context_menu)
