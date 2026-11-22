import xbmc

from resources.lib.leanback import kodi


def test_log_is_debug_only():
    del xbmc.LOG[:]
    kodi.log('hello')
    assert xbmc.LOG == [(xbmc.LOGDEBUG, '[plugin.video.leanback] hello')]


def test_log_error_keeps_error_level():
    del xbmc.LOG[:]
    kodi.log_error('boom')
    assert xbmc.LOG == [(xbmc.LOGERROR, '[plugin.video.leanback] boom')]


def test_formatted_fills_placeholders(monkeypatch):
    import xbmcaddon
    monkeypatch.setitem(xbmcaddon.STRINGS, 30112, 'Angemeldet als %s')
    assert kodi.formatted(30112, 'Signed in as %s', 'Tim') == 'Angemeldet als Tim'


def test_formatted_falls_back_when_string_is_missing_or_does_not_fit(monkeypatch):
    import xbmcaddon
    monkeypatch.setitem(xbmcaddon.STRINGS, 30112, '')  # not loaded yet: Kodi reads strings at startup
    assert kodi.formatted(30112, 'Signed in as %s', 'Tim') == 'Signed in as Tim'
    monkeypatch.setitem(xbmcaddon.STRINGS, 30112, 'Signed in')  # a translation that dropped the placeholder
    assert kodi.formatted(30112, 'Signed in as %s', 'Tim') == 'Signed in as Tim'
    monkeypatch.setitem(xbmcaddon.STRINGS, 30141, 'Watched %d%')  # a broken %
    assert kodi.formatted(30141, 'Watched %d%%', 40) == 'Watched 40%'


def test_formatted_fallbacks_match_strings_po():
    """Every English fallback handed to kodi.formatted must be the same text as strings.po."""
    import ast
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent.parent / 'plugin.video.leanback'
    po = (root / 'resources/language/resource.language.en_gb/strings.po').read_text(encoding='utf-8')
    english = {int(i): ast.literal_eval('"%s"' % t)
               for i, t in re.findall(r'msgctxt "#(\d+)"\nmsgid "((?:[^"\\]|\\.)*)"', po)}
    from resources.lib.leanback import maintenance
    checked = 0
    for path in root.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if (isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'formatted'
                    and isinstance(node.args[0], ast.Constant)):
                string_id, fallback = node.args[0].value, node.args[1]
                if isinstance(fallback, ast.Constant):
                    text = fallback.value
                elif isinstance(fallback, ast.Subscript):  # maintenance.FALLBACK[id]
                    text = maintenance.FALLBACK[string_id]
                else:
                    text = kodi_constant(path, fallback.id)
                assert english[string_id] == text, '%s: string %d' % (path.name, string_id)
                checked += 1
    assert checked >= 12


def kodi_constant(path, name):
    import ast
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and node.targets[0].id == name:
            return node.value.value
    raise AssertionError(name)
