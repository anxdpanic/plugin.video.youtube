# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import re
import datetime

from .base_item import BaseItem

from html import unescape

__RE_IMDB__ = re.compile(r'(http(s)?://)?www.imdb.(com|de)/title/(?P<imdbid>[t0-9]+)(/)?')


class VideoItem(BaseItem):
    def __init__(self, name, uri, image=u'', fanart=u''):
        BaseItem.__init__(self, name, uri, image, fanart)
        self._genre = None
        self._aired = None
        self._aired_utc = None
        self._scheduled_start_utc = None
        self._duration = None
        self._director = None
        self._premiered = None
        self._episode = None
        self._season = None
        self._year = None
        self._plot = None
        self._title = self.get_name()
        self._imdb_id = None
        self._cast = None
        self._rating = None
        self._track_number = None
        self._studio = None
        self._artist = None
        self._play_count = None
        self._uses_dash = None
        self._mediatype = None
        self._last_played = None
        self._start_percent = None
        self._start_time = None
        self._live = False
        self.subtitles = None
        self._headers = None
        self.license_key = None
        self._video_id = None
        self._channel_id = None
        self._subscription_id = None
        self._playlist_id = None
        self._playlist_item_id = None

    def set_play_count(self, play_count):
        self._play_count = int(play_count)

    def get_play_count(self):
        return self._play_count

    def add_artist(self, artist):
        if self._artist is None:
            self._artist = []
        # noinspection PyUnresolvedReferences
        self._artist.append(artist)

    def get_artist(self):
        return self._artist

    def set_studio(self, studio):
        self._studio = studio

    def get_studio(self):
        return self._studio

    def set_title(self, title):
        try:
            title = unescape(title)
        except:
            pass
        self._title = title
        self._name = self._title

    def get_title(self):
        return self._title

    def set_track_number(self, track_number):
        self._track_number = int(track_number)

    def get_track_number(self):
        return self._track_number

    def set_year(self, year):
        self._year = int(year)

    def set_year_from_datetime(self, date_time):
        self.set_year(date_time.year)

    def get_year(self):
        return self._year

    def set_premiered(self, year, month, day):
        date = datetime.date(year, month, day)
        self._premiered = date.isoformat()

    def set_premiered_from_datetime(self, date_time):
        self.set_premiered(year=date_time.year, month=date_time.month, day=date_time.day)

    def get_premiered(self):
        return self._premiered

    def set_plot(self, plot):
        try:
            plot = unescape(plot)
        except:
            pass
        self._plot = plot

    def get_plot(self):
        return self._plot

    def set_rating(self, rating):
        self._rating = float(rating)

    def get_rating(self):
        return self._rating

    def set_director(self, director_name):
        self._director = director_name

    def get_director(self):
        return self._director

    def add_cast(self, cast):
        if self._cast is None:
            self._cast = []
        # noinspection PyUnresolvedReferences
        self._cast.append(cast)

    def get_cast(self):
        return self._cast

    def set_imdb_id(self, url_or_id):
        re_match = __RE_IMDB__.match(url_or_id)
        if re_match:
            self._imdb_id = re_match.group('imdbid')
        else:
            self._imdb_id = url_or_id

    def get_imdb_id(self):
        return self._imdb_id

    def set_episode(self, episode):
        self._episode = int(episode)

    def get_episode(self):
        return self._episode

    def set_season(self, season):
        self._season = int(season)

    def get_season(self):
        return self._season

    def set_duration(self, hours, minutes, seconds=0):
        _seconds = seconds
        _seconds += minutes * 60
        _seconds += hours * 60 * 60
        self.set_duration_from_seconds(_seconds)

    def set_duration_from_minutes(self, minutes):
        self.set_duration_from_seconds(int(minutes) * 60)

    def set_duration_from_seconds(self, seconds):
        self._duration = int(seconds)

    def get_duration(self):
        return self._duration

    def set_aired(self, year, month, day):
        date = datetime.date(year, month, day)
        self._aired = date.isoformat()

    def set_aired_utc(self, dt):
        self._aired_utc = dt

    def get_aired_utc(self):
        return self._aired_utc

    def set_aired_from_datetime(self, date_time):
        self.set_aired(year=date_time.year, month=date_time.month, day=date_time.day)

    def set_scheduled_start_utc(self, dt):
        self._scheduled_start_utc = dt

    def get_scheduled_start_utc(self):
        return self._scheduled_start_utc

    @property
    def live(self):
        return self._live

    @live.setter
    def live(self, value):
        self._live = value

    def get_aired(self):
        return self._aired

    def set_genre(self, genre):
        self._genre = genre

    def get_genre(self):
        return self._genre

    def set_date(self, year, month, day, hour=0, minute=0, second=0):
        date = datetime.datetime(year, month, day, hour, minute, second)
        self._date = date.isoformat(sep=' ')

    def set_date_from_datetime(self, date_time):
        self.set_date(year=date_time.year, month=date_time.month, day=date_time.day, hour=date_time.hour,
                      minute=date_time.minute, second=date_time.second)

    def get_date(self):
        return self._date

    def set_use_dash(self, value=True):
        self._uses_dash = value

    def use_dash(self):
        return self._uses_dash is True and ('manifest/dash' in self.get_uri() or self.get_uri().endswith('.mpd'))

    def set_mediatype(self, mediatype):
        self._mediatype = mediatype

    def get_mediatype(self):
        if self._mediatype not in ['video', 'movie', 'tvshow', 'season', 'episode', 'musicvideo']:
            self._mediatype = 'video'
        return self._mediatype

    def set_subtitles(self, value):
        self.subtitles = value if value and isinstance(value, list) else None

    def set_headers(self, value):
        self._headers = value

    def get_headers(self):
        return self._headers

    def set_license_key(self, url):
        self.license_key = url

    def get_license_key(self):
        return self.license_key

    def set_last_played(self, last_played):
        self._last_played = last_played

    def get_last_played(self):
        return self._last_played

    def set_start_percent(self, start_percent):
        self._start_percent = start_percent

    def get_start_percent(self):
        return self._start_percent

    def set_start_time(self, start_time):
        self._start_time = start_time

    def get_start_time(self):
        return self._start_time

    @property
    def video_id(self):
        return self._video_id

    @video_id.setter
    def video_id(self, value):
        self._video_id = value

    def get_channel_id(self):
        return self._channel_id

    def set_channel_id(self, value):
        self._channel_id = value

    def get_subscription_id(self):
        return self._subscription_id

    def set_subscription_id(self, value):
        self._subscription_id = value

    def get_playlist_id(self):
        return self._playlist_id

    def set_playlist_id(self, value):
        self._playlist_id = value

    def get_playlist_item_id(self):
        return self._playlist_item_id

    def set_playlist_item_id(self, value):
        self._playlist_item_id = value
