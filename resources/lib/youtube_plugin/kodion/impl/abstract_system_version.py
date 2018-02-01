__author__ = 'bromix'

from six.moves import map
from six import string_types
from six import python_2_unicode_compatible


@python_2_unicode_compatible
class AbstractSystemVersion(object):
    def __init__(self, version, releasename, appname):
        if not isinstance(version, tuple):
            self._version = (0, 0, 0, 0)
        else:
            self._version = version

        if not releasename or not isinstance(releasename, string_types):
            self._releasename = 'UNKNOWN'
        else:
            self._releasename = releasename

        if not appname or not isinstance(appname, string_types):
            self._appname = 'UNKNOWN'
        else:
            self._appname = appname

    def __str__(self):
        obj_str = "%s (%s-%s)" % (self._releasename, self._appname, '.'.join(map(str, self._version)))
        return obj_str

    def get_release_name(self):
        return self._releasename

    def get_version(self):
        return self._version

    def get_app_name(self):
        return self._appname
