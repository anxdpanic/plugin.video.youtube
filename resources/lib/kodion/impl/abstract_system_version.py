__author__ = 'bromix'


class AbstractSystemVersion(object):
    def __init__(self, version, name):
        if not isinstance(version, tuple):
            self._version = (0, 0, 0, 0)
        else:
            self._version = version
            pass

        if not name or not isinstance(name, basestring):
            self._name = 'UNKNOWN'
        else:
            self._name = name
            pass
        pass

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        obj_str = "%s (%s)" % (self._name, '.'.join(map(str, self._version)))
        return obj_str

    def get_name(self):
        return self._name

    def get_version(self):
        return self._version

    pass
