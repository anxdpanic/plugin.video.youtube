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

from .menu_items import separator
from ..compatibility import (
    datetime_infolabel,
    parse_qsl,
    string_type,
    to_str,
    unescape,
    urlsplit,
)
from ..constants import MEDIA_PATH


class BaseItem(object):
    _version = 3
    _playable = False

    def __init__(self, name, uri, image=None, fanart=None):
        self._name = None
        self.set_name(name)

        self._uri = uri
        self._available = True
        self._callback = None

        self._image = ''
        if image:
            self.set_image(image)
        self._fanart = ''
        if fanart:
            self.set_fanart(fanart)

        self._bookmark_id = None
        self._bookmark_timestamp = None
        self._context_menu = None
        self._added_utc = None
        self._count = None
        self._date = None
        self._dateadded = None
        self._short_details = None
        self._production_code = None
        self._track_number = None

        self._cast = None
        self._artists = None
        self._studios = None

    def __str__(self):
        return ('{type}'
                '\n\tName:  |{name}|'
                '\n\tURI:   |{uri}|'
                '\n\tImage: |image}|'
                .format(type=self.__class__.__name__,
                        name=self._name,
                        uri=self._uri,
                        image=self._image))

    def __repr__(self):
        return json.dumps(
            {'type': self.__class__.__name__, 'data': self.__dict__},
            ensure_ascii=False,
            cls=_Encoder
        )

    def get_id(self):
        """
        Returns a unique id of the item.
        :return: unique id of the item.
        """
        return md5(''.join((self._name, self._uri)).encode('utf-8')).hexdigest()

    def parse_item_ids_from_uri(self):
        if not self._uri:
            return None

        item_ids = {}

        uri = urlsplit(self._uri)
        path = uri.path.rstrip('/')
        params = dict(parse_qsl(uri.query))

        video_id = params.get('video_id')
        if video_id:
            item_ids['video_id'] = video_id

        channel_id = None
        playlist_id = None

        while path:
            part, _, next_part = path.partition('/')
            if not next_part:
                break

            if part == 'channel':
                channel_id = next_part.partition('/')[0]
            elif part == 'playlist':
                playlist_id = next_part.partition('/')[0]
            path = next_part

        if channel_id:
            item_ids['channel_id'] = channel_id
        if playlist_id:
            item_ids['playlist_id'] = playlist_id

        for item_id, value in item_ids.items():
            try:
                setattr(self, item_id, value)
            except AttributeError:
                pass

        return item_ids

    def set_name(self, name):
        try:
            name = unescape(name)
        except Exception:
            pass
        self._name = name
        return name

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

    @property
    def available(self):
        return self._available

    @available.setter
    def available(self, value):
        self._available = value

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, value):
        self._callback = value

    def set_image(self, image):
        if not image:
            return

        if '{media}/' in image:
            self._image = image.format(media=MEDIA_PATH)
        else:
            self._image = image

    def get_image(self):
        return self._image

    def set_fanart(self, fanart):
        if not fanart:
            return

        if '{media}/' in fanart:
            self._fanart = fanart.format(media=MEDIA_PATH)
        else:
            self._fanart = fanart

    def get_fanart(self, default=True):
        if self._fanart or not default:
            return self._fanart
        return '/'.join((
            MEDIA_PATH,
            'fanart.jpg',
        ))

    def add_context_menu(self,
                         context_menu,
                         position='end',
                         replace=False,
                         end_separator=separator()):
        context_menu = [item for item in context_menu if item]
        if context_menu and end_separator and context_menu[-1] != end_separator:
            context_menu.append(end_separator)
        if replace or not self._context_menu:
            self._context_menu = context_menu
        elif position == 'end':
            self._context_menu.extend(context_menu)
        else:
            self._context_menu[position:position] = context_menu

    def get_context_menu(self):
        return self._context_menu

    def set_date(self, year, month, day, hour=0, minute=0, second=0):
        self._date = datetime(year, month, day, hour, minute, second)

    def set_date_from_datetime(self, date_time):
        self._date = date_time

    def get_date(self, as_text=False, short=False, as_info_label=False):
        if self._date:
            if as_info_label:
                return datetime_infolabel(self._date, '%d.%m.%Y')
            if short:
                return self._date.date().strftime('%x')
            if as_text:
                return self._date.strftime('%x %X')
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
        if self._dateadded:
            if as_info_label:
                return datetime_infolabel(self._dateadded)
            if as_text:
                return self._dateadded.strftime('%x %X')
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
    def bookmark_id(self):
        return self._bookmark_id

    @bookmark_id.setter
    def bookmark_id(self, value):
        self._bookmark_id = value

    def set_bookmark_timestamp(self, timestamp):
        self._bookmark_timestamp = timestamp

    def get_bookmark_timestamp(self):
        return self._bookmark_timestamp

    @property
    def playable(self):
        return self._playable

    @playable.setter
    def playable(self, value):
        self._playable = value

    def add_artist(self, artist):
        if artist:
            if self._artists is None:
                self._artists = []
            self._artists.append(to_str(artist))

    def get_artists(self):
        return self._artists

    def get_artists_string(self):
        if self._artists:
            return ', '.join(self._artists)
        return None

    def set_artists(self, artists):
        self._artists = list(artists)

    def set_cast(self, members):
        self._cast = list(members)

    def add_cast(self, name, role=None, order=None, thumbnail=None):
        if name:
            if self._cast is None:
                self._cast = []
            self._cast.append({
                'name': to_str(name),
                'role': to_str(role) if role else '',
                'order': int(order) if order else len(self._cast) + 1,
                'thumbnail': to_str(thumbnail) if thumbnail else '',
            })

    def get_cast(self):
        return self._cast

    def add_studio(self, studio):
        if studio:
            if self._studios is None:
                self._studios = []
            self._studios.append(to_str(studio))

    def get_studios(self):
        return self._studios

    def set_studios(self, studios):
        self._studios = list(studios)

    def set_production_code(self, value):
        self._production_code = value or ''

    def get_production_code(self):
        return self._production_code

    def set_track_number(self, track_number):
        self._track_number = int(track_number)

    def get_track_number(self):
        return self._track_number


class _Encoder(json.JSONEncoder):
    def encode(self, obj, nested=False):
        if isinstance(obj, (date, datetime)):
            class_name = obj.__class__.__name__
            if 'fromisoformat' in dir(obj):
                obj = {
                    '__class__': class_name,
                    '__isoformat__': obj.isoformat(),
                }
            else:
                if class_name == 'datetime':
                    if obj.tzinfo:
                        format_string = '%Y-%m-%dT%H:%M:%S%z'
                    else:
                        format_string = '%Y-%m-%dT%H:%M:%S'
                else:
                    format_string = '%Y-%m-%d'
                obj = {
                    '__class__': class_name,
                    '__format_string__': format_string,
                    '__value__': obj.strftime(format_string)
                }

        if isinstance(obj, string_type):
            output = to_str(obj)
        elif isinstance(obj, dict):
            output = {to_str(key): self.encode(value, nested=True)
                      for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            output = [self.encode(item, nested=True) for item in obj]
        else:
            output = obj

        if nested:
            return output
        return super(_Encoder, self).encode(output)

    def default(self, obj):
        pass
