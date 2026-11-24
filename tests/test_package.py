import importlib.util
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location('package', os.path.join(ROOT, 'scripts', 'package.py'))
package = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(package)


def _reuse_line(zip_path):
    with zipfile.ZipFile(zip_path) as archive:
        xml = archive.read('plugin.video.youtube/addon.xml').decode('utf-8')
    return next(line.strip() for line in xml.splitlines() if 'reuselanguageinvoker' in line)


def test_release_zip_reuses_the_language_invoker(tmp_path):
    target, _ = package.package(package.ADDON_DIR, str(tmp_path))
    assert not target.endswith('-debug.zip')
    assert _reuse_line(target) == package.REUSE_ON


def test_debug_zip_turns_reuse_off(tmp_path):
    target, _ = package.package(package.ADDON_DIR, str(tmp_path), debug=True)
    assert target.endswith('-debug.zip')
    assert _reuse_line(target) == package.REUSE_OFF
