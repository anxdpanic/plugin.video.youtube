import struct
import sys
import types
import zlib

import xbmcgui

from resources.lib.youtube import qr


def pixels(data):
    """(width, rows of greyscale bytes) from a PNG written by qr.png."""
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    width, height, depth, colour = struct.unpack('>IIBB', data[16:26])
    assert (width, depth, colour) == (height, 8, 0)
    idat_len = struct.unpack('>I', data[33:37])[0]
    raw = zlib.decompress(data[41:41 + idat_len])
    rows = [raw[i * (width + 1):(i + 1) * (width + 1)] for i in range(height)]
    assert all(row[0] == 0 for row in rows)  # filter type none
    return width, [row[1:] for row in rows]


def test_png_draws_each_module_in_a_quiet_zone():
    width, rows = pixels(qr.png([[1, 0], [0, 1]], scale=3, border=4))
    assert width == (2 + 8) * 3
    assert rows[0] == b'\xff' * width  # quiet zone
    assert rows[12][12] == 0 and rows[12][15] == 255  # first module row: dark, light
    assert rows[15][12] == 255 and rows[15][15] == 0


def fake_pyqrcode(monkeypatch, made):
    module = types.ModuleType('pyqrcode')

    def create(text, error='H'):
        made.append((text, error))
        return types.SimpleNamespace(code=[[1, 0], [0, 1]])
    module.create = create
    monkeypatch.setitem(sys.modules, 'pyqrcode', module)


def test_image_is_named_after_its_text_and_made_once(monkeypatch):
    made = []
    fake_pyqrcode(monkeypatch, made)
    path = qr.image('https://www.google.com/device')
    assert qr.image('https://www.google.com/device') == path
    assert qr.image('https://example.org/device') != path
    assert made == [('https://www.google.com/device', 'M'), ('https://example.org/device', 'M')]
    with open(path, 'rb') as handle:
        assert pixels(handle.read())[0] == (2 + 8) * 16


def test_no_image_without_pyqrcode(monkeypatch):
    monkeypatch.setitem(sys.modules, 'pyqrcode', None)  # import fails
    assert qr.image('https://www.google.com/device') is None


def test_no_image_when_making_it_fails(monkeypatch):
    module = types.ModuleType('pyqrcode')

    def create(text, error='H'):
        raise ValueError('too long')
    module.create = create
    monkeypatch.setitem(sys.modules, 'pyqrcode', module)
    assert qr.image('https://www.google.com/device') is None


def test_dialog_shows_the_code_and_back_cancels():
    dialog = qr.Dialog('/tmp/qr.png')
    dialog.create('Sign in', 'Go to google.com/device\nABC-DEF')
    assert dialog.shown
    assert dialog.focused is dialog.button and dialog.button.label == 'Cancel'
    assert [c.filename for c in dialog.controls if isinstance(c, xbmcgui.ControlImage)][1] == '/tmp/qr.png'
    assert [c.text for c in dialog.controls if isinstance(c, xbmcgui.ControlTextBox)] == [
        'Go to google.com/device\nABC-DEF']
    dialog.onAction(xbmcgui.Action(7))  # select: stays open
    assert not dialog.iscanceled()
    dialog.onAction(xbmcgui.Action(92))  # back
    assert dialog.iscanceled() and not dialog.shown


def test_dialog_cancel_button_cancels():
    dialog = qr.Dialog('/tmp/qr.png')
    dialog.create('Sign in', 'ABC-DEF')
    dialog.onControl(dialog.controls[0])  # not the button
    assert not dialog.iscanceled()
    dialog.onControl(dialog.button)
    assert dialog.iscanceled() and not dialog.shown
