__author__ = 'bromix'


class AbstractSystemVersion(object):
    def __init__(self, version, releasename, appname):
        if not isinstance(version, tuple):
            self._version = (0, 0, 0, 0)
        else:
            self._version = version
            pass

        if not releasename or not isinstance(releasename, basestring):
            self._releasename = 'UNKNOWN'
        else:
            self._releasename = releasename
            pass

        if not appname or not isinstance(appname, basestring):
            self._appname = 'UNKNOWN'
        else:
            self._appname = appname
            pass
        pass

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        obj_str = "%s (%s-%s)" % (self._releasename, self._appname, '.'.join(map(str, self._version)))
        return obj_str

    def get_release_name(self):
        return self._releasename

    def get_version(self):
        return self._version

    def get_app_name(self):
        return self._appname

    pass
