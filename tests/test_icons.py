import os

import pytest

from resources.lib.youtube import icons, kodi


@pytest.mark.parametrize('entry, expected', [
    ({'id': 'FEwhat_to_watch'}, 'home.png'),
    ({'id': 'FEsubscriptions'}, 'new_uploads.png'),
    ({'id': 'search'}, 'search.png'),
    ({'id': 'FEsomething', 'icon': 'TAB_TRENDING'}, 'trending.png'),
    ({'id': 'FEsomething', 'icon': 'LIVE'}, 'live.png'),
])
def test_guide_entries_use_add_on_media(entry, expected):
    assert icons.menu_entry(entry, 'DefaultFolder.png') == kodi.icon_path(expected)


def test_unknown_entries_keep_the_kodi_default():
    assert icons.menu_entry({'id': 'FEmusic', 'icon': 'MUSIC'}, 'DefaultFolder.png') == 'DefaultFolder.png'


def test_every_mapped_image_is_shipped():
    names = set(icons.BY_ID.values()) | {name for _, name in icons.BY_TYPE}
    names |= {'icon.png', 'fanart.jpg', 'user.png', 'channels.png', 'new_search.png'}
    missing = [name for name in names if not os.path.isfile(icons.media(name))]
    assert not missing
    assert os.path.isfile(icons.TV_INTERFACE)
