# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .base_item import BaseItem
from ..compatibility import to_str, unescape


class AudioItem(BaseItem):
    _playable = True

    def __init__(self, name, uri, image='', fanart=''):
        super(AudioItem, self).__init__(name, uri, image, fanart)
        self._start_time = None
        self._duration = -1
        self._track_number = None
        self._year = None
        self._genres = None
        self._album = None
        self._artists = None
        self._title = self.get_name()
        self._rating = None

    def set_rating(self, rating):
        rating = float(rating)
        if rating > 10:
            rating = 10.0
        elif rating < 0:
            rating = 0.0
        self._rating = rating

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

    def add_artist(self, artist):
        if self._artists is None:
            self._artists = []
        if artist:
            self._artists.append(to_str(artist))

    def get_artists(self):
        return self._artists

    def set_artists(self, artists):
        self._artists = list(artists)

    def set_album_name(self, album_name):
        self._album = album_name or ''

    def get_album_name(self):
        return self._album

    def add_genre(self, genre):
        if self._genres is None:
            self._genres = []
        if genre:
            self._genres.append(to_str(genre))

    def get_genres(self):
        return self._genres

    def set_genres(self, genres):
        self._genres = list(genres)

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

    def set_start_time(self, start_time):
        self._start_time = start_time or 0.0

    def get_start_time(self):
        return self._start_time
