__author__ = 'bromix'

from ... import utils
from ...items import *


def _process_date(info_labels, param):
    if param is not None and param:
        datetime = utils.datetime_parser.parse(param)
        datetime = '%02d.%02d.%04d' % (datetime.day, datetime.month, datetime.year)
        info_labels['date'] = datetime
        pass
    pass


def _process_int_value(info_labels, name, param):
    if param is not None:
        info_labels[name] = int(param)
        pass
    pass


def _process_string_value(info_labels, name, param):
    if param is not None:
        info_labels[name] = unicode(param)
        pass
    pass


def _process_audio_rating(info_labels, param):
    if param is not None:
        rating = int(param)
        if rating > 5:
            rating = 5
            pass
        if rating < 0:
            rating = 0
            pass

        info_labels['rating'] = unicode(rating)
        pass
    pass


def _process_video_dateadded(info_labels, param):
    if param is not None and param:
        info_labels['dateadded'] = param
        pass
    pass


def _process_video_duration(context, info_labels, param):
    if param is not None:
        info_labels['duration'] = '%d' % param
        pass
    pass


def _process_video_rating(info_labels, param):
    if param is not None:
        rating = float(param)
        if rating > 10.0:
            rating = 10.0
            pass
        if rating < 0.0:
            rating = 0.0
            pass
        info_labels['rating'] = rating
        pass
    pass


def _process_date_value(info_labels, name, param):
    if param is not None:
        date = utils.datetime_parser.parse(param)
        date = '%04d-%02d-%02d' % (date.year, date.month, date.day)
        info_labels[name] = date
        pass
    pass


def _process_list_value(info_labels, name, param):
    if param is not None and isinstance(param, list):
        info_labels[name] = param
        pass
    pass


def _process_mediatype(info_labels, name, param):
    info_labels[name] = param


def create_from_item(context, base_item):
    info_labels = {}

    # 'date' = '09.03.1982'
    _process_date(info_labels, base_item.get_date())

    # Directory
    if isinstance(base_item, DirectoryItem):
        _process_string_value(info_labels, 'plot', base_item.get_plot())
        pass

    # Image
    if isinstance(base_item, ImageItem):
        # 'title' = 'Blow Your Head Off' (string)
        _process_string_value(info_labels, 'title', base_item.get_title())
        pass

    # Audio
    if isinstance(base_item, AudioItem):
        # 'duration' = 79 (int)
        _process_int_value(info_labels, 'duration', base_item.get_duration())

        # 'album' = 'Buckle Up' (string)
        _process_string_value(info_labels, 'album', base_item.get_album_name())

        # 'artist' = 'Angerfist' (string)
        _process_string_value(info_labels, 'artist', base_item.get_artist_name())

        # 'rating' = '0' - '5' (string)
        _process_audio_rating(info_labels, base_item.get_rating())
        pass

    # Video
    if isinstance(base_item, VideoItem):
        # mediatype
        _process_mediatype(info_labels, 'mediatype', base_item.get_mediatype())

        # play count
        _process_int_value(info_labels, 'playcount', base_item.get_play_count())

        # studio
        _process_string_value(info_labels, 'studio', base_item.get_studio())

        # 'artist' = [] (list)
        _process_list_value(info_labels, 'artist', base_item.get_artist())

        # 'dateadded' = '2014-08-11 13:08:56' (string) will be taken from 'date'
        _process_video_dateadded(info_labels, base_item.get_date())

        # TODO: starting with Helix this could be seconds
        # 'duration' = '3:18' (string)
        _process_video_duration(context, info_labels, base_item.get_duration())

        # 'rating' = 4.5 (float)
        _process_video_rating(info_labels, base_item.get_rating())

        # 'aired' = '2013-12-12' (string)
        _process_date_value(info_labels, 'aired', base_item.get_aired())

        # 'director' = 'Steven Spielberg' (string)
        _process_string_value(info_labels, 'director', base_item.get_director())

        # 'premiered' = '2013-12-12' (string)
        _process_date_value(info_labels, 'premiered', base_item.get_premiered())

        # 'episode' = 12 (int)
        _process_int_value(info_labels, 'episode', base_item.get_episode())

        # 'season' = 12 (int)
        _process_int_value(info_labels, 'season', base_item.get_season())

        # 'plot' = '...' (string)
        _process_string_value(info_labels, 'plot', base_item.get_plot())

        # 'code' = 'tt3458353' (string) - imdb id
        _process_string_value(info_labels, 'code', base_item.get_imdb_id())

        # 'cast' = [] (list)
        _process_list_value(info_labels, 'cast', base_item.get_cast())
        pass

    # Audio and Video
    if isinstance(base_item, AudioItem) or isinstance(base_item, VideoItem):
        # 'title' = 'Blow Your Head Off' (string)
        _process_string_value(info_labels, 'title', base_item.get_title())

        # 'tracknumber' = 12 (int)
        _process_int_value(info_labels, 'tracknumber', base_item.get_track_number())

        # 'year' = 1994 (int)
        _process_int_value(info_labels, 'year', base_item.get_year())

        # 'genre' = 'Hardcore' (string)
        _process_string_value(info_labels, 'genre', base_item.get_genre())
        pass

    return info_labels
