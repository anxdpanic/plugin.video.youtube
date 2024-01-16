# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from ...items import AudioItem, DirectoryItem, ImageItem, VideoItem
from ...utils import current_system_version, datetime_parser


def _process_date_value(info_labels, name, param):
    if param:
        info_labels[name] = param.isoformat()


def _process_datetime_value(info_labels, name, param):
    if not param:
        return
    info_labels[name] = (param.replace(microsecond=0, tzinfo=None).isoformat()
                         if current_system_version.compatible(19, 0) else
                         param.strftime('%d.%m.%Y'))


def _process_int_value(info_labels, name, param):
    if param is not None:
        info_labels[name] = int(param)


def _process_string_value(info_labels, name, param):
    if param is not None:
        info_labels[name] = param


def _process_studios(info_labels, name, param):
    if param is not None:
        info_labels[name] = [param]


def _process_audio_rating(info_labels, param):
    if param is not None:
        rating = int(param)
        if rating > 5:
            rating = 5
        elif rating < 0:
            rating = 0
        info_labels['rating'] = rating


def _process_video_duration(info_labels, param):
    if param is not None:
        info_labels['duration'] = '%d' % param


def _process_video_rating(info_labels, param):
    if param is not None:
        rating = float(param)
        if rating > 10.0:
            rating = 10.0
        elif rating < 0.0:
            rating = 0.0
        info_labels['rating'] = rating


def _process_date_string(info_labels, name, param):
    if param:
        date = datetime_parser.parse(param)
        info_labels[name] = date.isoformat()


def _process_list_value(info_labels, name, param):
    if param is not None and isinstance(param, list):
        info_labels[name] = param


def _process_mediatype(info_labels, name, param):
    info_labels[name] = param


def create_from_item(base_item):
    info_labels = {}

    # 'date' = '1982-03-09' (string)
    _process_datetime_value(info_labels, 'date', base_item.get_date())

    # Directory
    if isinstance(base_item, DirectoryItem):
        _process_string_value(info_labels, 'plot', base_item.get_plot())

    # Image
    elif isinstance(base_item, ImageItem):
        # 'title' = 'Blow Your Head Off' (string)
        _process_string_value(info_labels, 'title', base_item.get_title())

    # Audio
    elif isinstance(base_item, AudioItem):
        # 'duration' = 79 (int)
        _process_int_value(info_labels, 'duration', base_item.get_duration())

        # 'album' = 'Buckle Up' (string)
        _process_string_value(info_labels, 'album', base_item.get_album_name())

        # 'artist' = 'Angerfist' (string)
        _process_string_value(info_labels, 'artist', base_item.get_artist_name())

        # 'rating' = '0' - '5' (string)
        _process_audio_rating(info_labels, base_item.get_rating())

    # Video
    elif isinstance(base_item, VideoItem):
        # mediatype
        _process_mediatype(info_labels, 'mediatype', base_item.get_mediatype())

        # play count
        _process_int_value(info_labels, 'playcount', base_item.get_play_count())

        # 'count' = 12 (integer)
        # Can be used to store an id for later, or for sorting purposes
        # Used for Youtube video view count
        _process_int_value(info_labels, 'count', base_item.get_count())

        # studio
        _process_studios(info_labels, 'studio', base_item.get_studio())

        # 'artist' = [] (list)
        _process_list_value(info_labels, 'artist', base_item.get_artist())

        # 'dateadded' = '2014-08-11 13:08:56' (string) will be taken from 'dateadded'
        _process_datetime_value(info_labels, 'dateadded', base_item.get_dateadded())

        # TODO: starting with Helix this could be seconds
        # 'duration' = '3:18' (string)
        _process_video_duration(info_labels, base_item.get_duration())

        _process_datetime_value(info_labels, 'lastplayed', base_item.get_last_played())

        # 'rating' = 4.5 (float)
        _process_video_rating(info_labels, base_item.get_rating())

        # 'aired' = '2013-12-12' (string)
        _process_date_value(info_labels, 'aired', base_item.get_aired(as_text=False))

        # 'director' = 'Steven Spielberg' (string)
        _process_string_value(info_labels, 'director', base_item.get_director())

        # 'premiered' = '2013-12-12' (string)
        _process_date_value(info_labels, 'premiered', base_item.get_premiered(as_text=False))

        # 'episode' = 12 (int)
        _process_int_value(info_labels, 'episode', base_item.get_episode())

        # 'season' = 12 (int)
        _process_int_value(info_labels, 'season', base_item.get_season())

        # 'plot' = '...' (string)
        _process_string_value(info_labels, 'plot', base_item.get_plot())

        # 'imdbnumber' = 'tt3458353' (string) - imdb id
        _process_string_value(info_labels, 'imdbnumber', base_item.get_imdb_id())

        # 'cast' = [] (list)
        _process_list_value(info_labels, 'cast', base_item.get_cast())

        # 'code' = '101' (string)
        # Production code, currently used to store misc video data for label
        # formatting
        _process_string_value(info_labels, 'code', base_item.get_code())

    # Audio and Video
    if isinstance(base_item, (AudioItem, VideoItem)):
        # 'title' = 'Blow Your Head Off' (string)
        _process_string_value(info_labels, 'title', base_item.get_title())

        # 'tracknumber' = 12 (int)
        _process_int_value(info_labels, 'tracknumber', base_item.get_track_number())

        # 'year' = 1994 (int)
        _process_int_value(info_labels, 'year', base_item.get_year())

        # 'genre' = 'Hardcore' (string)
        _process_string_value(info_labels, 'genre', base_item.get_genre())

    return info_labels
