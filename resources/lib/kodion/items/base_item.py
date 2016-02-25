import hashlib
import datetime


class BaseItem(object):
    VERSION = 3
    INFO_DATE = 'date'  # (string) iso 8601

    def __init__(self, name, uri, image=u'', fanart=u''):
        self._version = BaseItem.VERSION
        self._name = unicode(name)
        self._uri = str(uri)

        self._image = u''
        self.set_image(image)

        self._fanart = fanart
        self._context_menu = None
        self._replace_context_menu = False
        self._date = None
        pass

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        name = self._name
        uri = self._uri
        obj_str = "------------------------------\n'%s'\nURI: %s\nImage: %s\n------------------------------" % (
            name, uri, self._image)
        return obj_str

    def get_id(self):
        """
        Returns a unique id of the item.
        :return: unique id of the item.
        """
        m = hashlib.md5()
        m.update(self._name.encode('utf-8'))
        m.update(self._uri.encode('utf-8'))
        return m.hexdigest()

    def get_name(self):
        """
        Returns the name of the item.
        :return: name of the item.
        """
        return self._name

    def set_uri(self, uri):
        if isinstance(uri, str):
            self._uri = uri
            pass
        else:
            self._uri = ''
            pass
        pass

    def get_uri(self):
        """
        Returns the path of the item.
        :return: path of the item.
        """
        return self._uri

    def set_image(self, image):
        if image is None:
            self._image = ''
            pass
        else:
            self._image = image
            pass
        pass

    def get_image(self):
        return self._image

    def set_fanart(self, fanart):
        self._fanart = fanart
        pass

    def get_fanart(self):
        return self._fanart

    def set_context_menu(self, context_menu, replace=False):
        self._context_menu = context_menu
        self._replace_context_menu = replace
        pass

    def get_context_menu(self):
        return self._context_menu

    def replace_context_menu(self):
        return self._replace_context_menu

    def set_date(self, year, month, day, hour=0, minute=0, second=0):
        date = datetime.datetime(year, month, day, hour, minute, second)
        self._date = date.isoformat(sep=' ')
        pass

    def set_date_from_datetime(self, date_time):
        self.set_date(year=date_time.year, month=date_time.month, day=date_time.day, hour=date_time.hour,
                      minute=date_time.minute, second=date_time.second)
        pass

    def get_date(self):
        return self._date

    pass