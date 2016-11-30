import re
import datetime

from .base_item import BaseItem

__RE_IMDB__ = re.compile(r'(http(s)?://)?www.imdb.(com|de)/title/(?P<imdbid>[t0-9]+)(/)?')


class VideoItem(BaseItem):
    def __init__(self, name, uri, image=u'', fanart=u''):
        BaseItem.__init__(self, name, uri, image, fanart)
        self._genre = None
        self._aired = None
        self._duration = None
        self._director = None
        self._premiered = None
        self._episode = None
        self._season = None
        self._year = None
        self._plot = None
        self._title = name
        self._imdb_id = None
        self._cast = None
        self._rating = None
        self._track_number = None
        self._studio = None
        self._artist = None
        self._play_count = None
        self._uses_dash = None
        self._mediatype = None
        self.subtitles = None
        pass

    def set_play_count(self, play_count):
        self._play_count = int(play_count)
        pass

    def get_play_count(self):
        return self._play_count

    def add_artist(self, artist):
        if self._artist is None:
            self._artist = []
            pass
        self._artist.append(unicode(artist))
        pass

    def get_artist(self):
        return self._artist

    def set_studio(self, studio):
        self._studio = unicode(studio)
        pass

    def get_studio(self):
        return self._studio

    def set_title(self, title):
        self._title = unicode(title)
        self._name = self._title
        pass

    def get_title(self):
        return self._title

    def set_track_number(self, track_number):
        self._track_number = int(track_number)
        pass

    def get_track_number(self):
        return self._track_number

    def set_year(self, year):
        self._year = int(year)
        pass

    def set_year_from_datetime(self, date_time):
        self.set_year(date_time.year)
        pass

    def get_year(self):
        return self._year

    def set_premiered(self, year, month, day):
        date = datetime.date(year, month, day)
        self._premiered = date.isoformat()
        pass

    def set_premiered_from_datetime(self, date_time):
        self.set_premiered(year=date_time.year, month=date_time.month, day=date_time.day)
        pass

    def get_premiered(self):
        return self._premiered

    def set_plot(self, plot):
        self._plot = unicode(plot)
        pass

    def get_plot(self):
        return self._plot

    def set_rating(self, rating):
        self._rating = float(rating)
        pass

    def get_rating(self):
        return self._rating

    def set_director(self, director_name):
        self._director = unicode(director_name)
        pass

    def get_director(self):
        return self._director

    def add_cast(self, cast):
        if self._cast is None:
            self._cast = []
            pass
        self._cast.append(cast)
        pass

    def get_cast(self):
        return self._cast

    def set_imdb_id(self, url_or_id):
        re_match = __RE_IMDB__.match(url_or_id)
        if re_match:
            self._imdb_id = re_match.group('imdbid')
        else:
            self._imdb_id = url_or_id
        pass

    def get_imdb_id(self):
        return self._imdb_id

    def set_episode(self, episode):
        self._episode = int(episode)
        pass

    def get_episode(self):
        return self._episode

    def set_season(self, season):
        self._season = int(season)
        pass

    def get_season(self):
        return self._season

    def set_duration(self, hours, minutes, seconds=0):
        _seconds = seconds
        _seconds += minutes * 60
        _seconds += hours * 60 * 60
        self.set_duration_from_seconds(_seconds)
        pass

    def set_duration_from_minutes(self, minutes):
        self.set_duration_from_seconds(int(minutes) * 60)
        pass

    def set_duration_from_seconds(self, seconds):
        self._duration = int(seconds)
        pass

    def get_duration(self):
        return self._duration

    def set_aired(self, year, month, day):
        date = datetime.date(year, month, day)
        self._aired = date.isoformat()
        pass

    def set_aired_from_datetime(self, date_time):
        self.set_aired(year=date_time.year, month=date_time.month, day=date_time.day)
        pass

    def get_aired(self):
        return self._aired

    def set_genre(self, genre):
        self._genre = unicode(genre)
        pass

    def get_genre(self):
        return self._genre
        
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
    
    def set_track_number(self, track_number):
        self._track_number = track_number
        pass

    def set_use_dash(self, value=True):
        self._uses_dash = value

    def use_dash(self):
        return self._uses_dash is True and 'manifest/dash' in self.get_uri()

    def set_mediatype(self, mediatype):
        self._mediatype = mediatype
        pass

    def get_mediatype(self):
        if self._mediatype not in ['video', 'movie', 'tvshow', 'season', 'episode', 'musicvideo']:
            self._mediatype = 'video'
        return self._mediatype

    def set_subtitles(self, value):
        self.subtitles = value if value and isinstance(value, list) else None
