__author__ = 'bromix'

from .base_item import BaseItem


class AudioItem(BaseItem):
    def __init__(self, name, uri, image=u'', fanart=u''):
        BaseItem.__init__(self, name, uri, image, fanart)
        self._duration = None
        self._track_number = None
        self._year = None
        self._genre = None
        self._album = None
        self._artist = None
        self._title = name
        self._rating = None
        pass

    def set_rating(self, rating):
        self._rating = float(rating)
        pass

    def get_rating(self):
        return self._rating

    def set_title(self, title):
        self._title = unicode(title)
        pass

    def get_title(self):
        return self._title

    def set_artist_name(self, artist_name):
        self._artist = unicode(artist_name)
        pass

    def get_artist_name(self):
        return self._artist

    def set_album_name(self, album_name):
        self._album = unicode(album_name)
        pass

    def get_album_name(self):
        return self._album

    def set_genre(self, genre):
        self._genre = unicode(genre)
        pass

    def get_genre(self):
        return self._genre

    def set_year(self, year):
        self._year = int(year)
        pass

    def set_year_from_datetime(self, date_time):
        self.set_year(date_time.year)
        pass

    def get_year(self):
        return self._year

    def set_track_number(self, track_number):
        self._track_number = int(track_number)
        pass

    def get_track_number(self):
        return self._track_number

    def set_duration_from_milli_seconds(self, milli_seconds):
        self.set_duration_from_seconds(int(milli_seconds)/1000)
        pass

    def set_duration_from_seconds(self, seconds):
        self._duration = int(seconds)
        pass

    def set_duration_from_minutes(self, minutes):
        self.set_duration_from_seconds(int(minutes)*60)
        pass

    def get_duration(self):
        return self._duration

    pass
