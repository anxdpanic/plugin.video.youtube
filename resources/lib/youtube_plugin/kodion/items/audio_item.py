# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from .base_item import BaseItem

from html import unescape


class AudioItem(BaseItem):
    def __init__(self, name, uri, image=u'', fanart=u''):
        BaseItem.__init__(self, name, uri, image, fanart)
        self._duration = None
        self._track_number = None
        self._year = None
        self._genre = None
        self._album = None
        self._artist = None
        self._title = self.get_name()
        self._rating = None

    def set_rating(self, rating):
        self._rating = float(rating)

    def get_rating(self):
        return self._rating

    def set_title(self, title):
        try:
            title = unescape(title)
        except:
            pass
        self._title = title

    def get_title(self):
        return self._title

    def set_artist_name(self, artist_name):
        self._artist = artist_name

    def get_artist_name(self):
        return self._artist

    def set_album_name(self, album_name):
        self._album = album_name

    def get_album_name(self):
        return self._album

    def set_genre(self, genre):
        self._genre = genre

    def get_genre(self):
        return self._genre

    def set_year(self, year):
        self._year = int(year)

    def set_year_from_datetime(self, date_time):
        self.set_year(date_time.year)

    def get_year(self):
        return self._year

    def set_track_number(self, track_number):
        self._track_number = int(track_number)

    def get_track_number(self):
        return self._track_number

    def set_duration_from_milli_seconds(self, milli_seconds):
        self.set_duration_from_seconds(int(milli_seconds) // 1000)

    def set_duration_from_seconds(self, seconds):
        self._duration = int(seconds)

    def set_duration_from_minutes(self, minutes):
        self.set_duration_from_seconds(int(minutes) * 60)

    def get_duration(self):
        return self._duration
