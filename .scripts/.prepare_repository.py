#!/usr/bin/env python3
"""
This is an:
- addons.xml generator
- addons.xml.md5 generator
- optional auto-compressor (including handling of icons, fanart and changelog)

Python 2.7 -> 3.7

Compression of addons in repositories has many benefits, including:
 - Protects addon downloads from corruption.
 - Smaller addon file size resulting in faster downloads and
   less space / bandwidth used on the repository.
 - Ability to 'roll back' addon updates in Kodi to previous versions.

To enable the auto-compressor, set the compress_addons setting to True
If you do this you must make sure the 'datadir zip' parameter in the addon.xml
of your repository file is set to 'true'.

Please bump __revision__ one decimal point and add your name to credits when making changes
"""
import sys

from lxml import etree
import hashlib
import json
import os
import shutil
import zipfile

__script__ = '.prepare_repository.py'
__revision__ = '7.0'
__homepage__ = 'https://forum.kodi.tv/showthread.php?tid=129401'
__credits__ = 'Unobtanium, anxdpanic'
__license__ = 'GPL-3.0-only'


class Generator:
    """
        Generates a new addons.xml file from each addons addon.xml file
        and a new addons.xml.md5 hash file. Must be run from the root of
        the checked-out repo. Only handles single depth folder structure.
    """

    def __init__(self):

        # paths
        self.addons_xml = os.path.join(REPOSITORY_PATH, 'addons.xml')
        self.addons_xml_md5 = os.path.join(REPOSITORY_PATH, 'addons.xml.md5')

        # call master function
        self.generate_addons_files()

    def generate_addons_files(self):
        # addon list
        addons = os.listdir(ZIPS_PATH)
        # final addons text
        addons_xml = u'<?xml version=\'1.0\' encoding=\'UTF-8\' standalone=\'yes\'?>\n<addons>\n'

        found_an_addon = False
        path = ''

        # loop through and add each addons addon.xml file
        for addon in addons:
            if addon in IGNORED_ADDONS:
                continue
            try:
                addon = os.path.join(ZIPS_PATH, addon)
                # skip any file or .svn folder
                if is_addon_dir(addon):

                    # create path
                    path = os.path.join(addon, 'addon.xml')

                    if os.path.exists(path):
                        found_an_addon = True

                    # split lines for stripping
                    xml_lines = read_file(path)
                    xml_lines = xml_lines.splitlines()

                    # new addon
                    addon_xml = ''

                    # loop through cleaning each line
                    for line in xml_lines:
                        if isinstance(line, bytes):
                            line.decode('utf-8')
                        line = str(line)
                        # skip encoding format line
                        if line.find('<?xml') >= 0:
                            continue
                        # add line
                        addon_xml += line.rstrip() + '\n'

                    # we succeeded so add to our final addons.xml text
                    addons_xml += addon_xml.rstrip() + '\n\n'

            except Exception as error:  # pylint: disable=broad-except
                # missing or poorly formatted addon.xml
                print('Excluding %s for %s' % (path, error))

        # clean and add closing tag
        addons_xml = addons_xml.strip() + u'\n</addons>\n'

        # only generate files if we found an addon.xml
        if found_an_addon:
            # save files
            save_file(self.addons_xml, addons_xml.encode('UTF-8'))
            self.generate_md5_file()

            # notify user
            print('Updated addons xml and addons.xml.md5 files')
            print(' ')
        else:
            print('Could not find any addons, so script has done nothing.')

    def generate_md5_file(self):
        try:
            # create a new md5 hash
            contents = read_file(self.addons_xml)
            md5 = hashlib.md5(contents.encode('utf-8')).hexdigest()
            # save file
            save_file(self.addons_xml_md5, md5)

        except Exception as error:  # pylint: disable=broad-except
            # oops
            print('An error occurred creating addons.xml.md5 file!\n%s' % error)


class Compressor:
    def __init__(self):
        # variables used later on
        self.addon_name = None
        self.addon_path = None
        self.addon_folder_contents = None
        self.xml_file = None
        self.addon_xml = None
        self.addon_version_number = None
        self.addon_zip_path = None
        self.addon_path_zips = None

        # run the master method of the class, when class is initialised.
        # only do so if we want addons compressed.
        if COMPRESS_ADDONS:
            self.compress_addons()

    def compress_addons(self):
        source_directory = os.listdir(SOURCE_PATH)
        for addon in source_directory:
            if addon in IGNORED_ADDONS:
                continue
            # set variables
            self.addon_name = str(addon)
            self.addon_path = os.path.join(SOURCE_PATH, addon)
            self.addon_path_zips = os.path.join(ZIPS_PATH, addon)
            # skip any file or .svn folder.
            if is_addon_dir(self.addon_path):
                # set another variable
                self.addon_folder_contents = os.listdir(self.addon_path)

                # check if addon has a current zipped release in it.
                addon_zip_exists = self._get_zipped_addon_path()

                # checking for addon.xml and try reading it.
                addon_xml_exists = self._read_addon_xml()
                if addon_xml_exists:
                    self._get_artwork()

                    # now addon.xml has been read, scrape version number from it.
                    # we need this when naming the zip (and if it exists the changelog)
                    self._read_version_number()

                    if not addon_zip_exists:
                        addon_zip_exists = self._get_zipped_addon_path()
                        if not addon_zip_exists:
                            tags = ''

                            print('Create compressed %s%s release for [%s] v%s' %
                                  (tags, self._get_release_type(), self.addon_name,
                                   self.addon_version_number))
                            self.create_compressed_addon_release()

    def _get_zip_name(self):
        if not self.addon_version_number:
            self._read_version_number()

        zip_name = self.addon_name
        zip_name += '-' + self.addon_version_number + '.zip'

        return zip_name

    def _get_zipped_addon_path(self):
        # get name of addon zip file. returns False if not found.
        addon_xml_exists = self._read_addon_xml()
        if addon_xml_exists:
            self._read_version_number()

        zip_name = self._get_zip_name()

        if not os.path.exists(self.addon_path_zips):
            if not self.addon_path_zips.endswith('zips'):
                make_path = self.addon_path_zips
                os.makedirs(make_path)

        folder_contents = os.listdir(self.addon_path_zips)

        for potential_zip in folder_contents:
            if zip_name == potential_zip:
                self.addon_zip_path = os.path.join(self.addon_path_zips, zip_name)
                return True
        # if loop is not broken by returning the addon path, zip was not found so return False
        self.addon_zip_path = None
        return False

    def _extract_addon_xml_to_release_folder(self):
        with zipfile.ZipFile(self.addon_path_zips, 'r') as zip_file:
            for filename in zip_file.namelist():
                if filename.find('addon.xml'):
                    zip_file.extract(filename, self.addon_path_zips)
                    break

    @staticmethod
    def recursive_zipper(directory, zip_file):
        # initialize zipping module
        ignored_files = IGNORED_FILES

        with zipfile.ZipFile(zip_file, 'w', compression=zipfile.ZIP_DEFLATED) as zipped_file:
            # get length of characters of what we will use as the root path
            root_len = len(os.path.dirname(os.path.abspath(directory)))

            # recursive writer
            for root, _, files in os.walk(directory):
                # subtract the source file's root from the archive root -
                # ie. make /Users/me/desktop/zip_me.txt into just /zip_me.txt
                archive_root = os.path.abspath(root)[root_len:]

                for repo_file in files:

                    if repo_file.endswith(IGNORED_FILES_END):
                        continue
                    if repo_file.startswith(IGNORED_FILES_START):
                        continue
                    if any(match for match in ignored_files if repo_file == match):
                        continue

                    full_path = str(os.path.join(root, repo_file))
                    if any(bl in full_path for bl in IGNORED_DIRECTORIES):
                        continue

                    archive_name = str(os.path.join(archive_root, repo_file))
                    zipped_file.write(full_path, archive_name, zipfile.ZIP_DEFLATED)

    def create_compressed_addon_release(self):
        # create a zip of the addon into repo root directory,
        # tagging it with '-x.x.x' release number scraped from addon.xml

        def _copy_asset(asset):
            if not asset:
                return
            if asset == 'changelog.txt':
                asset = 'changelog-' + self.addon_version_number + '.txt'

            asset_path = os.path.join(self.addon_path_zips, asset)
            try:
                try:
                    os.makedirs(os.path.dirname(asset_path))
                except(IOError, OSError) as _:
                    pass

                shutil.copyfile(os.path.join(self.addon_path, asset), asset_path)
            except (shutil.Error, IOError) as _:
                pass

        zip_name = self._get_zip_name()
        zip_path = os.path.join(ZIPS_PATH, zip_name)

        # zip full directories
        self.recursive_zipper(self.addon_path, zip_path)

        # now move the zip into the addon folder,
        # which we will now treat as the 'addon release directory'

        os.rename(zip_path, os.path.join(self.addon_path_zips, zip_name))

        art = self._get_artwork()

        _copy_asset('addon.xml')
        _copy_asset('changelog.txt')
        _copy_asset(art.get('icon', 'icon.png'))
        _copy_asset(art.get('fanart', 'fanart.jpg'))
        _copy_asset(art.get('banner', ''))
        _copy_asset(art.get('clearlogo', ''))

        for screenshot in art.get('screenshot', []):
            _copy_asset(screenshot)

    def _read_addon_xml(self):
        # check for addon.xml and try and read it.
        addon_xml_path = os.path.join(self.addon_path, 'addon.xml')
        if os.path.exists(addon_xml_path):
            # load whole text into string
            self.xml_file = read_file(addon_xml_path)
            self.addon_xml = etree.fromstring(self.xml_file.encode('utf-8'))
            # return True if we found and read the addon.xml
            return True
        # return False if we couldn't  find the addon.xml
        return False

    def _read_version_number(self):
        # find the header of the addon.
        version = self.addon_xml.get('version')
        self.addon_version_number = version

    def _get_release_type(self):

        if not self.addon_version_number:
            self._read_version_number()

        if 'alpha' in self.addon_version_number:
            tag = 'alpha'
        elif 'beta' in self.addon_version_number:
            tag = 'beta'
        else:
            tag = 'stable'

        return tag

    def _get_artwork(self):
        art = {
            'banner': '',
            'clearlogo': '',
            'fanart': 'fanart.jpg',
            'icon': 'icon.png',
            'screenshot': [],
        }

        def _set_asset(metadata, asset_type, findall=False):
            if findall:
                asset = metadata.findall('./assets/' + asset_type)
            else:
                asset = metadata.find('./assets/' + asset_type)
            if asset is not None:
                if findall:
                    if (isinstance(asset, list) and
                            len(asset) > 0 and isinstance(asset[0].text, str)):
                        art[asset_type] = [a.text for a in asset]
                else:
                    if isinstance(asset.text, str):
                        art[asset_type] = asset.text

        extensions = self.addon_xml.findall('./extension')
        for extension in extensions:
            if extension.get('point') == 'xbmc.addon.metadata':
                _set_asset(extension, 'icon')
                _set_asset(extension, 'fanart')
                _set_asset(extension, 'banner')
                _set_asset(extension, 'clearlogo')
                _set_asset(extension, 'screenshot', findall=True)

                break

        return art


def is_addon_dir(addon):
    # this function is used by both classes.
    # very simple and weak check that it is an addon dir.
    # intended to be fast, not totally accurate.
    # skip any file or .svn folder
    if not os.path.isdir(addon) or addon == '.git' or addon.endswith('zips') or addon == 'zips':
        return False

    return True


def read_file(filename, is_json=False):
    if is_json:
        with open(filename, 'r', encoding='utf-8') as open_file:
            return json.load(open_file)
    else:
        with open(filename, 'r', encoding='utf-8') as open_file:
            return open_file.read()


def save_file(filename_and_path, contents):
    if isinstance(contents, bytes):
        contents = contents.decode('utf-8')
    try:
        with open(filename_and_path, 'w', encoding='utf-8') as open_file:
            open_file.write(contents)
    except Exception as error:  # pylint: disable=broad-except
        # oops
        print('An error occurred saving %s file!\n%s' % (filename_and_path, error))


def loose_version(v):
    filled = []
    for point in v.split('.'):
        filled.append(point.zfill(8))
    return tuple(filled)


def split_version(v):
    filled = []
    for point in v.split('.'):
        if '~' in point:
            for p in point.split('~'):
                if 'alpha' in p or 'beta' in p:
                    p = '~' + p
                filled.append(p)
        else:
            filled.append(point)
    return filled


if __name__ == '__main__':
    CONFIG = read_file('.config.json', is_json=True)

    COMPRESS_ADDONS = bool(CONFIG.get('compress_addons'))

    IGNORED_ADDONS = list(set(CONFIG.get('ignored', {}).get('addons', [])))
    IGNORED_FILES = list(set(CONFIG.get('ignored', {}).get('files', [])))
    IGNORED_FILES_START = tuple(set(CONFIG.get('ignored', {}).get('file_starts_with', [])))
    IGNORED_FILES_END = tuple(set(CONFIG.get('ignored', {}).get('file_ends_with', [])))
    IGNORED_DIRECTORIES = list(set(CONFIG.get('ignored', {}).get('directories', [])))

    SOURCE_PATH = CONFIG.get('path', {}).get('source', '')
    REPOSITORY_PATH = CONFIG.get('path', {}).get('repository', '')
    ZIPS_PATH = os.path.join(REPOSITORY_PATH, 'zips')
    SOURCE_PATH_UNOFFICIAL = CONFIG.get('path', {}).get('source-unofficial', '')
    REPOSITORY_PATH_UNOFFICIAL = CONFIG.get('path', {}).get('repository-unofficial', '')
    ZIPS_PATH_UNOFFICIAL = os.path.join(REPOSITORY_PATH_UNOFFICIAL, 'zips')
    SOURCE_PATH_UNOFFICIAL_TESTING = CONFIG.get('path', {}).get('source-unofficial-testing', '')
    REPOSITORY_PATH_UNOFFICIAL_TESTING = CONFIG.get('path', {}).get('repository-unofficial-testing', '')
    ZIPS_PATH_UNOFFICIAL_TESTING = os.path.join(REPOSITORY_PATH_UNOFFICIAL_TESTING, 'zips')

    print(__script__)
    print('Version: v' + str(__revision__))
    print('License:  ' + __license__)
    print('Credits:  ' + __credits__)
    print('Homepage: ' + __homepage__)
    print(' ')

    print('Paths:')
    print('    Source:     ' + SOURCE_PATH)
    print('    Repository: ' + REPOSITORY_PATH)
    print('    Zips:       ' + ZIPS_PATH)
    print('    Unofficial Development Source:     ' + SOURCE_PATH_UNOFFICIAL)
    print('    Unofficial Development Repository: ' + REPOSITORY_PATH_UNOFFICIAL)
    print('    Unofficial Development Zips:       ' + ZIPS_PATH_UNOFFICIAL)
    print('    Unofficial Source:     ' + SOURCE_PATH_UNOFFICIAL)
    print('    Unofficial Repository: ' + REPOSITORY_PATH_UNOFFICIAL)
    print('    Unofficial Zips:       ' + ZIPS_PATH_UNOFFICIAL)
    print(' ')

    print('Compress Add-ons:       ' + str(COMPRESS_ADDONS))
    print(' ')

    print(' ')

    print('Generating official testing repository')
    Compressor()
    Generator()

    if os.path.isdir(SOURCE_PATH_UNOFFICIAL_TESTING):
        print('Generating unofficial testing repository')
        SOURCE_PATH = SOURCE_PATH_UNOFFICIAL_TESTING
        REPOSITORY_PATH = REPOSITORY_PATH_UNOFFICIAL_TESTING
        ZIPS_PATH = ZIPS_PATH_UNOFFICIAL_TESTING

        Compressor()
        Generator()

    if len(sys.argv) > 1 and sys.argv[1] == '--prerelease=false':
        if os.path.isdir(SOURCE_PATH_UNOFFICIAL):
            print('Generating unofficial repository')
            SOURCE_PATH = SOURCE_PATH_UNOFFICIAL
            REPOSITORY_PATH = REPOSITORY_PATH_UNOFFICIAL
            ZIPS_PATH = ZIPS_PATH_UNOFFICIAL

            Compressor()
            Generator()
