# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""The sign-in dialog with a QR code of the sign-in address, so a phone can open it without typing.

The code comes from script.module.pyqrcode's module matrix, written out as a PNG with zlib. Without the
module there is no QR code and the sign-in uses Kodi's progress dialog as before."""
import hashlib
import os
import struct
import zlib

import xbmc
import xbmcgui

from . import kodi
from .tv import skin

CANCEL_ACTIONS = {9, 10, 13, 92}  # parent dir, previous menu, stop, back
# Select (OK, Enter) presses the focused Cancel button. A WindowDialog that handles onAction gets every
# action and Kodi doesn't click the focused control for it, so onControl never sees the remote's OK.
SELECT_ACTION = 7


def _chunk(kind, data):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)


def png(rows, scale=16, border=4):
    """A greyscale PNG of a module matrix (truthy is dark), in a white quiet zone of `border` modules."""
    width = (len(rows) + 2 * border) * scale
    margin = b'\xff' * (border * scale)
    quiet = b'\x00' + b'\xff' * width
    lines = [quiet] * (border * scale)
    for row in rows:
        line = b'\x00' + margin + b''.join((b'\x00' if dark else b'\xff') * scale for dark in row) + margin
        lines += [line] * scale
    lines += [quiet] * (border * scale)
    return (b'\x89PNG\r\n\x1a\n' + _chunk(b'IHDR', struct.pack('>IIBBBBB', width, width, 8, 0, 0, 0, 0))
            + _chunk(b'IDAT', zlib.compress(b''.join(lines), 9)) + _chunk(b'IEND', b''))


def image(text):
    """Path to a PNG of a QR code for text, or None when it can't be made (no script.module.pyqrcode)."""
    # Named after the text, so Kodi's texture cache never shows the code for an earlier address.
    path = os.path.join(kodi.TEMP_DIR, 'qr-%s.png' % hashlib.sha1(text.encode('utf-8')).hexdigest()[:12])
    if os.path.exists(path):
        return path
    try:
        import pyqrcode
        data = png(pyqrcode.create(text, error='M').code)
        os.makedirs(kodi.TEMP_DIR, exist_ok=True)
        with open(path + '.part', 'wb') as handle:
            handle.write(data)
        os.replace(path + '.part', path)
    except Exception as exc:  # no module, or making or writing it failed: sign in without one
        kodi.log('No QR code for the sign-in: %s' % exc)
        return None
    return path


class Dialog(xbmcgui.WindowDialog):
    """Full screen, QR code on the left, the dialog's text and a Cancel button on the right; Back cancels too.
    Used in place of xbmcgui.DialogProgress, so it has the same create/update/iscanceled/close."""

    def __init__(self, qr_png):
        super().__init__()
        self.qr_png = qr_png
        self.cancelled = False
        self.text = None
        self.button = None

    def create(self, heading, message=''):
        fonts = skin.current_fonts()
        white = os.path.join(skin.MEDIA, 'white.png')
        self.addControl(xbmcgui.ControlImage(0, 0, 1280, 720, white, colorDiffuse='0xFF0B0F1A'))
        self.addControl(xbmcgui.ControlImage(80, 140, 440, 440, self.qr_png, aspectRatio=2))
        self.addControl(xbmcgui.ControlLabel(580, 150, 640, 50, heading, font=fonts['row_title'],
                                             textColor='0xFFFFFFFF'))
        self.text = xbmcgui.ControlTextBox(580, 230, 640, 300, font=fonts['rail'], textColor='0xFFFFFFFF')
        self.addControl(self.text)
        self.text.setText(message)
        self.button = xbmcgui.ControlButton(580, 540, 240, 56, xbmc.getLocalizedString(222), focusTexture=white,
                                            noFocusTexture=white, alignment=6, font=fonts['rail'],
                                            textColor='0xFF0B0F1A', focusedColor='0xFF0B0F1A')
        self.addControl(self.button)
        self.setFocus(self.button)
        self.show()

    def update(self, percent, message=''):
        pass  # the message doesn't change while waiting, and there's no bar to move

    def iscanceled(self):
        return self.cancelled

    def onAction(self, action):  # noqa: N802 (Kodi API name)
        if action.getId() in CANCEL_ACTIONS or action.getId() == SELECT_ACTION:
            self._cancel()

    def onControl(self, control):  # noqa: N802
        if control == self.button:
            self._cancel()

    def _cancel(self):
        self.cancelled = True
        self.close()
