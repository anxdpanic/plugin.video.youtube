import xbmc

from resources.lib.youtube import kodi


def test_log_is_debug_only():
    del xbmc.LOG[:]
    kodi.log('hello')
    assert xbmc.LOG == [(xbmc.LOGDEBUG, '[plugin.video.youtube] hello')]


def test_log_error_keeps_error_level():
    del xbmc.LOG[:]
    kodi.log_error('boom')
    assert xbmc.LOG == [(xbmc.LOGERROR, '[plugin.video.youtube] boom')]


def test_formatted_fills_placeholders(monkeypatch):
    import xbmcaddon
    monkeypatch.setitem(xbmcaddon.STRINGS, 30112, 'Angemeldet als %s')
    assert kodi.formatted(30112, 'Tim') == 'Angemeldet als Tim'


def test_formatted_shows_a_string_that_does_not_fit_as_it_is(monkeypatch):
    import xbmcaddon
    monkeypatch.setitem(xbmcaddon.STRINGS, 30112, 'Signed in')  # a translation that dropped the placeholder
    assert kodi.formatted(30112, 'Tim') == 'Signed in'
    monkeypatch.setitem(xbmcaddon.STRINGS, 30141, 'Watched %d%')  # a broken %
    assert kodi.formatted(30141, 40) == 'Watched %d%'


def test_used_string_ids_are_in_strings_po():
    """Every add-on string id the code asks for exists in strings.po."""
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent.parent / 'plugin.video.youtube'
    po = (root / 'resources/language/resource.language.en_gb/strings.po').read_text(encoding='utf-8')
    defined = {int(i) for i in re.findall(r'msgctxt "#(\d+)"', po)}
    used = set()
    for path in root.rglob('*.py'):
        used.update(int(i) for i in re.findall(r'\b(?:string|formatted)\((3\d{4})\b',path.read_text(encoding='utf-8')))
    assert len(used) > 50
    assert used <= defined, sorted(used - defined)
