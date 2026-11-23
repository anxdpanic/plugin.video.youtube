#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Package the add-on as a zip that Kodi's "Install from zip file" accepts.

The zip holds a single top-level folder named after the add-on id, and is written to
dist/<id>-<version>.zip. Caches, compiled Python and hidden files are left out.

--debug builds dist/<id>-<version>-debug.zip with reuselanguageinvoker turned off, so each plugin run starts
with fresh modules (code changes copied onto a device take effect, and no state carries over between runs).

Usage: python scripts/package.py [--output DIR] [--debug]
"""

import argparse
import fnmatch
import os
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON_DIR = os.path.join(ROOT, 'plugin.video.youtube')
EXCLUDE_DIRS = {'__pycache__', '.pytest_cache', '.ruff_cache'}
EXCLUDE_FILES = ['*.pyc', '*.pyo', '*.orig', '*.rej', '*~', 'Thumbs.db', 'desktop.ini']
REUSE_ON = '<reuselanguageinvoker>true</reuselanguageinvoker>'
REUSE_OFF = '<reuselanguageinvoker>false</reuselanguageinvoker>'


def addon_info(addon_dir):
    root = ET.parse(os.path.join(addon_dir, 'addon.xml')).getroot()
    addon_id, version = root.get('id'), root.get('version')
    if not addon_id or not version:
        raise SystemExit('addon.xml is missing the id or version attribute')
    return addon_id, version


def files_to_pack(addon_dir):
    """Yield (path on disk, path relative to the add-on folder), sorted for a stable zip."""
    for dirpath, dirnames, filenames in os.walk(addon_dir):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith('.'))
        for name in sorted(filenames):
            if name.startswith('.') or any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDE_FILES):
                continue
            path = os.path.join(dirpath, name)
            yield path, os.path.relpath(path, addon_dir).replace(os.sep, '/')


def debug_addon_xml(addon_dir):
    """addon.xml with reuselanguageinvoker turned off."""
    with open(os.path.join(addon_dir, 'addon.xml'), encoding='utf-8') as handle:
        xml = handle.read()
    if REUSE_ON not in xml:
        raise SystemExit('addon.xml has no %s to turn off' % REUSE_ON)
    return xml.replace(REUSE_ON, REUSE_OFF)


def package(addon_dir, output_dir, debug=False):
    addon_id, version = addon_info(addon_dir)
    os.makedirs(output_dir, exist_ok=True)
    target = os.path.join(output_dir, '%s-%s%s.zip' % (addon_id, version, '-debug' if debug else ''))
    count = 0
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path, rel in files_to_pack(addon_dir):
            name = '%s/%s' % (addon_id, rel)
            if debug and rel == 'addon.xml':
                archive.writestr(name, debug_addon_xml(addon_dir))
            else:
                archive.write(path, name)
            count += 1
    return target, count


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output', default=os.path.join(ROOT, 'dist'),
                        help='directory to write the zip to (default: dist/)')
    parser.add_argument('--debug', action='store_true', help='turn reuselanguageinvoker off in the zip')
    args = parser.parse_args(argv)
    target, count = package(ADDON_DIR, args.output, args.debug)
    print('Wrote %s (%d files)' % (os.path.relpath(target), count))
    return 0


if __name__ == '__main__':
    sys.exit(main())
