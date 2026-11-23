# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""The TV interface: YouTube's TV layout in a window of its own, built on the plugin's pages and playback."""


def open_window():
    from . import skin
    from .window import TVWindow

    window = TVWindow(skin.XML_NAME, skin.prepare(), 'Default', '1080i')
    window.doModal()
    del window
