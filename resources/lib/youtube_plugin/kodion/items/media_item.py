# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import re
from datetime import date

from . import BaseItem
from ..compatibility import datetime_infolabel, to_str, unescape
from ..constants import CONTENT
from ..utils import duration_to_seconds, seconds_to_duration


class MediaItem(BaseItem):
    _ALLOWABLE_MEDIATYPES = frozenset()
    _DEFAULT_MEDIATYPE = ''

    _playable = True

    def __init__(self, name, uri, image='DefaultFile.png', fanart=None):
        super(MediaItem, self).__init__(name, uri, image, fanart)
        self._aired = None
        self._premiered = None
        self._scheduled_start_utc = None
        self._year = None

        self._artists = None
        self._cast = None
        self._genres = None
        self._studios = None

        self._duration = -1
        self._play_count = None
        self._last_played = None
        self._start_percent = None
        self._start_time = None

        self._mediatype = None
        self._plot = None
        self._production_code = None
        self._rating = None
        self._title = self.get_name()
        self._track_number = None

        self._headers = None
        self._license_key = None
        self._uses_isa = None
        self.subtitles = None

        self._completed = False
        self._live = False
        self._short = False
        self._upcoming = False
        self._vod = False

        self._video_id = None
        self._channel_id = None
        self._subscription_id = None
        self._playlist_id = None
        self._playlist_item_id = None

    def set_aired(self, year, month, day):
        self._aired = date(year, month, day)

    def set_aired_from_datetime(self, date_time):
        self._aired = date_time.date()

    def get_aired(self, as_text=True, as_info_label=False):
        if self._aired:
            if as_info_label:
                return self._aired.isoformat()
            if as_text:
                return self._aired.strftime('%x')
        return self._aired

    def set_premiered(self, year, month, day):
        self._premiered = date(year, month, day)

    def set_premiered_from_datetime(self, date_time):
        self._premiered = date_time.date()

    def get_premiered(self, as_text=True, as_info_label=False):
        if self._premiered:
            if as_info_label:
                return self._premiered.isoformat()
            if as_text:
                return self._premiered.strftime('%x')
        return self._premiered

    def set_scheduled_start_utc(self, date_time):
        self._scheduled_start_utc = date_time

    def get_scheduled_start_utc(self):
        return self._scheduled_start_utc

    def set_year(self, year):
        self._year = int(year)

    def set_year_from_datetime(self, date_time):
        self.set_year(date_time.year)

    def get_year(self):
        return self._year

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

    def add_genre(self, genre):
        if genre:
            if self._genres is None:
                self._genres = []
            self._genres.append(to_str(genre))

    def get_genres(self):
        return self._genres

    def set_genres(self, genres):
        self._genres = list(genres)

    def add_studio(self, studio):
        if studio:
            if self._studios is None:
                self._studios = []
            self._studios.append(to_str(studio))

    def get_studios(self):
        return self._studios

    def set_studios(self, studios):
        self._studios = list(studios)

    def set_duration(self, hours=0, minutes=0, seconds=0, duration=''):
        if duration:
            _seconds = duration_to_seconds(duration)
        else:
            _seconds = seconds + minutes * 60 + hours * 3600
        self._duration = _seconds or 0

    def set_duration_from_minutes(self, minutes):
        self._duration = int(minutes) * 60

    def set_duration_from_seconds(self, seconds):
        self._duration = int(seconds or 0)

    def get_duration(self, as_text=False):
        if as_text:
            return seconds_to_duration(self._duration)
        return self._duration

    def set_play_count(self, play_count):
        self._play_count = int(play_count or 0)

    def get_play_count(self):
        return self._play_count

    def set_last_played(self, last_played):
        self._last_played = last_played

    def get_last_played(self, as_info_label=False):
        if self._last_played:
            if as_info_label:
                return datetime_infolabel(self._last_played)
        return self._last_played

    def set_start_percent(self, start_percent):
        self._start_percent = start_percent or 0

    def get_start_percent(self):
        return self._start_percent

    def set_start_time(self, start_time):
        self._start_time = start_time or 0.0

    def get_start_time(self):
        return self._start_time

    def set_mediatype(self, mediatype):
        if mediatype in self._ALLOWABLE_MEDIATYPES:
            self._mediatype = mediatype
        else:
            self._mediatype = self._DEFAULT_MEDIATYPE

    def get_mediatype(self):
        return self._mediatype or self._DEFAULT_MEDIATYPE

    def set_plot(self, plot):
        try:
            plot = unescape(plot)
        except:
            pass
        self._plot = plot

    def get_plot(self):
        return self._plot

    def set_production_code(self, value):
        self._production_code = value or ''

    def get_production_code(self):
        return self._production_code

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
        self._name = self._title = title

    def get_title(self):
        return self._title

    def set_track_number(self, track_number):
        self._track_number = int(track_number)

    def get_track_number(self):
        return self._track_number

    def set_headers(self, value):
        self._headers = value

    def get_headers(self):
        return self._headers

    def set_license_key(self, url):
        self._license_key = url

    def get_license_key(self):
        return self._license_key

    def set_isa(self, value=True):
        self._uses_isa = value

    def use_isa(self):
        return self._uses_isa

    def use_hls(self):
        uri = self.get_uri()
        if 'manifest/hls' in uri or uri.endswith('.m3u8'):
            return True
        return False

    def use_mpd(self):
        uri = self.get_uri()
        if 'manifest/dash' in uri or uri.endswith('.mpd'):
            return True
        return False

    def set_subtitles(self, value):
        if value and isinstance(value, (list, tuple)):
            self.subtitles = value

    @property
    def completed(self):
        return self._completed

    @completed.setter
    def completed(self, value):
        self._completed = value

    @property
    def live(self):
        return self._live

    @live.setter
    def live(self, value):
        self._live = value

    @property
    def short(self):
        return self._short

    @short.setter
    def short(self, value):
        self._short = value

    @property
    def upcoming(self):
        return self._upcoming

    @upcoming.setter
    def upcoming(self, value):
        self._upcoming = value

    @property
    def vod(self):
        return self._vod

    @vod.setter
    def vod(self, value):
        self._vod = value

    @property
    def video_id(self):
        return self._video_id

    @video_id.setter
    def video_id(self, value):
        self._video_id = value

    @property
    def channel_id(self):
        return self._channel_id

    @channel_id.setter
    def channel_id(self, value):
        self._channel_id = value

    @property
    def subscription_id(self):
        return self._subscription_id

    @subscription_id.setter
    def subscription_id(self, value):
        self._subscription_id = value

    @property
    def playlist_id(self):
        return self._playlist_id

    @playlist_id.setter
    def playlist_id(self, value):
        self._playlist_id = value

    @property
    def playlist_item_id(self):
        return self._playlist_item_id

    @playlist_item_id.setter
    def playlist_item_id(self, value):
        self._playlist_item_id = value


class AudioItem(MediaItem):
    _ALLOWABLE_MEDIATYPES = {CONTENT.AUDIO_TYPE, 'song', 'album', 'artist'}
    _DEFAULT_MEDIATYPE = CONTENT.AUDIO_TYPE

    def __init__(self, name, uri, image='DefaultAudio.png', fanart=None):
        super(AudioItem, self).__init__(name, uri, image, fanart)
        self._album = None

    def set_album_name(self, album_name):
        self._album = album_name or ''

    def get_album_name(self):
        return self._album


class VideoItem(MediaItem):
    _ALLOWABLE_MEDIATYPES = {CONTENT.VIDEO_TYPE,
                             'movie',
                             'tvshow', 'season', 'episode',
                             'musicvideo'}
    _DEFAULT_MEDIATYPE = CONTENT.VIDEO_TYPE
    _RE_IMDB = re.compile(
        r'(http(s)?://)?www.imdb.(com|de)/title/(?P<imdbid>[t0-9]+)(/)?'
    )

    def __init__(self, name, uri, image='DefaultVideo.png', fanart=None):
        super(VideoItem, self).__init__(name, uri, image, fanart)
        self._directors = None
        self._episode = None
        self._imdb_id = None
        self._season = None

    def add_directors(self, director):
        if director:
            if self._directors is None:
                self._directors = []
            self._directors.append(to_str(director))

    def get_directors(self):
        return self._directors

    def set_directors(self, directors):
        self._directors = list(directors)

    def set_episode(self, episode):
        self._episode = int(episode)

    def get_episode(self):
        return self._episode

    def set_imdb_id(self, url_or_id):
        re_match = self._RE_IMDB.match(url_or_id)
        if re_match:
            self._imdb_id = re_match.group('imdbid')
        else:
            self._imdb_id = url_or_id

    def get_imdb_id(self):
        return self._imdb_id

    def set_season(self, season):
        self._season = int(season)

    def get_season(self):
        return self._season
