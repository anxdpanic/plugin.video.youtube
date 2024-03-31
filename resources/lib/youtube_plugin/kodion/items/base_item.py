# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
from datetime import date, datetime
from hashlib import md5

from ..compatibility import datetime_infolabel, string_type, to_str, unescape
from ..constants import MEDIA_PATH


class BaseItem(object):
    VERSION = 3

    _playable = False

    def __init__(self, name, uri, image='', fanart=''):
        self._version = BaseItem.VERSION

        self._name = None
        self.set_name(name)

        self._uri = uri

        self._image = None
        self.set_image(image)
        self._fanart = None
        self.set_fanart(fanart)

        self._context_menu = None
        self._replace_context_menu = False
        self._added_utc = None
        self._count = None
        self._date = None
        self._dateadded = None
        self._short_details = None

        self._next_page = False

    def __str__(self):
        return ('------------------------------\n'
                'Name: |{0}|\n'
                'URI: |{1}|\n'
                'Image: |{2}|\n'
                '------------------------------'.format(self._name,
                                                        self._uri,
                                                        self._image))

    def to_dict(self):
        return {'type': self.__class__.__name__, 'data': self.__dict__}

    def dumps(self):
        return json.dumps(self.to_dict(), ensure_ascii=False, cls=_Encoder)

    def get_id(self):
        """
        Returns a unique id of the item.
        :return: unique id of the item.
        """
        md5_hash = md5()
        md5_hash.update(self._name.encode('utf-8'))
        md5_hash.update(self._uri.encode('utf-8'))
        return md5_hash.hexdigest()

    def set_name(self, name):
        try:
            self._name = unescape(name)
        except:
            self._name = name
        return self._name

    def get_name(self):
        """
        Returns the name of the item.
        :return: name of the item.
        """
        return self._name

    def set_uri(self, uri):
        self._uri = uri if uri and isinstance(uri, string_type) else ''

    def get_uri(self):
        """
        Returns the path of the item.
        :return: path of the item.
        """
        return self._uri

    def set_image(self, image):
        if not image:
            self._image = ''
            return

        if '{media}/' in image:
            self._image = image.format(media=MEDIA_PATH)
        else:
            self._image = image

    def get_image(self):
        return self._image

    def set_fanart(self, fanart):
        if not fanart:
            self._fanart = '{0}/fanart.jpg'.format(MEDIA_PATH)
            return

        if '{media}/' in fanart:
            self._fanart = fanart.format(media=MEDIA_PATH)
        else:
            self._fanart = fanart

    def get_fanart(self):
        return self._fanart

    def set_context_menu(self, context_menu, replace=False):
        self._context_menu = context_menu
        self._replace_context_menu = replace

    def add_context_menu(self, context_menu, position=0, replace=None):
        if self._context_menu is None:
            self._context_menu = context_menu
        elif position == 'end':
            self._context_menu.extend(context_menu)
        else:
            self._context_menu[position:position] = context_menu
        if replace is not None:
            self._replace_context_menu = replace

    def get_context_menu(self):
        return self._context_menu

    def replace_context_menu(self):
        return self._replace_context_menu

    def set_date(self, year, month, day, hour=0, minute=0, second=0):
        self._date = datetime(year, month, day, hour, minute, second)

    def set_date_from_datetime(self, date_time):
        self._date = date_time

    def get_date(self, as_text=False, short=False, as_info_label=False):
        if not self._date:
            return ''
        if short:
            return self._date.date().strftime('%x')
        if as_text:
            return self._date.strftime('%x %X')
        if as_info_label:
            return datetime_infolabel(self._date)
        return self._date

    def set_dateadded(self, year, month, day, hour=0, minute=0, second=0):
        self._dateadded = datetime(year,
                                   month,
                                   day,
                                   hour,
                                   minute,
                                   second)

    def set_dateadded_from_datetime(self, date_time):
        self._dateadded = date_time

    def get_dateadded(self, as_text=False, as_info_label=False):
        if not self._dateadded:
            return ''
        if as_text:
            return self._dateadded.strftime('%x %X')
        if as_info_label:
            return datetime_infolabel(self._date)
        return self._dateadded

    def set_added_utc(self, date_time):
        self._added_utc = date_time

    def get_added_utc(self):
        return self._added_utc

    def get_short_details(self):
        return self._short_details

    def set_short_details(self, details):
        self._short_details = details or ''

    def get_count(self):
        return self._count

    def set_count(self, count):
        self._count = int(count or 0)

    @property
    def next_page(self):
        return self._next_page

    @next_page.setter
    def next_page(self, value):
        self._next_page = bool(value)

    @property
    def playable(self):
        return self._playable


class _Encoder(json.JSONEncoder):
    def encode(self, obj):
        if isinstance(obj, string_type):
            return to_str(obj)

        if isinstance(obj, dict):
            return {to_str(key): self.encode(value)
                    for key, value in obj.items()}

        if isinstance(obj, (list, tuple)):
            return [self.encode(item) for item in obj]

        if isinstance(obj, (date, datetime)):
            class_name = obj.__class__.__name__

            if 'fromisoformat' in dir(obj):
                return {
                    '__class__': class_name,
                    '__isoformat__': obj.isoformat(),
                }

            if class_name == 'datetime':
                if obj.tzinfo:
                    format_string = '%Y-%m-%dT%H:%M:%S%z'
                else:
                    format_string = '%Y-%m-%dT%H:%M:%S'
            else:
                format_string = '%Y-%m-%d'

            return {
                '__class__': class_name,
                '__format_string__': format_string,
                '__value__': obj.strftime(format_string)
            }

        return self.iterencode(obj)
