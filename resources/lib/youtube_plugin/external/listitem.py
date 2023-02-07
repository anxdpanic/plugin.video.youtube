# -*- coding: utf-8 -*-
# Module: default
# Author: jurialmunkey
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html
from xbmc import Actor, VideoStreamDetail, AudioStreamDetail, SubtitleStreamDetail, LOGINFO
from xbmc import log as kodi_log


class ListItemInfoTag():
    INFO_TAG_ATTR = {
        'video': {
            'tag_getter': 'getVideoInfoTag',
            'tag_attr': {
                'genre': {'attr': 'setGenres', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'country': {'attr': 'setCountries', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'year': {'attr': 'setYear', 'convert': int, 'classinfo': int},
                'episode': {'attr': 'setEpisode', 'convert': int, 'classinfo': int},
                'season': {'attr': 'setSeason', 'convert': int, 'classinfo': int},
                'sortepisode': {'attr': 'setSortEpisode', 'convert': int, 'classinfo': int},
                'sortseason': {'attr': 'setSortSeason', 'convert': int, 'classinfo': int},
                'episodeguide': {'attr': 'setEpisodeGuide', 'convert': str, 'classinfo': str},
                'showlink': {'attr': 'setShowLinks', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'top250': {'attr': 'setTop250', 'convert': int, 'classinfo': int},
                'setid': {'attr': 'setSetId', 'convert': int, 'classinfo': int},
                'tracknumber': {'attr': 'setTrackNumber', 'convert': int, 'classinfo': int},
                'rating': {'attr': 'setRating', 'convert': float, 'classinfo': float},
                'userrating': {'attr': 'setUserRating', 'convert': int, 'classinfo': int},
                'watched': {'skip': True},  # Evaluated internally in Nexus based on playcount so skip
                'playcount': {'attr': 'setPlaycount', 'convert': int, 'classinfo': int},
                'overlay': {'skip': True},  # Evaluated internally in Nexus based on playcount so skip
                'cast': {'route': 'set_info_cast'},
                'castandrole': {'route': 'set_info_cast'},
                'director': {'attr': 'setDirectors', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'mpaa': {'attr': 'setMpaa', 'convert': str, 'classinfo': str},
                'plot': {'attr': 'setPlot', 'convert': str, 'classinfo': str},
                'plotoutline': {'attr': 'setPlotOutline', 'convert': str, 'classinfo': str},
                'title': {'attr': 'setTitle', 'convert': str, 'classinfo': str},
                'originaltitle': {'attr': 'setOriginalTitle', 'convert': str, 'classinfo': str},
                'sorttitle': {'attr': 'setSortTitle', 'convert': str, 'classinfo': str},
                'duration': {'attr': 'setDuration', 'convert': int, 'classinfo': int},
                'studio': {'attr': 'setStudios', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'tagline': {'attr': 'setTagLine', 'convert': str, 'classinfo': str},
                'writer': {'attr': 'setWriters', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'tvshowtitle': {'attr': 'setTvShowTitle', 'convert': str, 'classinfo': str},
                'premiered': {'attr': 'setPremiered', 'convert': str, 'classinfo': str},
                'status': {'attr': 'setTvShowStatus', 'convert': str, 'classinfo': str},
                'set': {'attr': 'setSet', 'convert': str, 'classinfo': str},
                'setoverview': {'attr': 'setSetOverview', 'convert': str, 'classinfo': str},
                'tag': {'attr': 'setTags', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'imdbnumber': {'attr': 'setIMDBNumber', 'convert': str, 'classinfo': str},
                'code': {'attr': 'setProductionCode', 'convert': str, 'classinfo': str},
                'aired': {'attr': 'setFirstAired', 'convert': str, 'classinfo': str},
                'credits': {'attr': 'setWriters', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'lastplayed': {'attr': 'setLastPlayed', 'convert': str, 'classinfo': str},
                'album': {'attr': 'setAlbum', 'convert': str, 'classinfo': str},
                'artist': {'attr': 'setArtists', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'votes': {'attr': 'setVotes', 'convert': int, 'classinfo': int},
                'path': {'attr': 'setPath', 'convert': str, 'classinfo': str},
                'trailer': {'attr': 'setTrailer', 'convert': str, 'classinfo': str},
                'dateadded': {'attr': 'setDateAdded', 'convert': str, 'classinfo': str},
                'date': {'attr': 'setDateAdded', 'convert': str, 'classinfo': str},
                'mediatype': {'attr': 'setMediaType', 'convert': str, 'classinfo': str},
                'dbid': {'attr': 'setDbId', 'convert': int, 'classinfo': int},
            }
        },
        'music': {
            'tag_getter': 'getMusicInfoTag',
            'tag_attr': {
                'tracknumber': {'attr': 'setTrack', 'convert': int, 'classinfo': int},
                'discnumber': {'attr': 'setDisc', 'convert': int, 'classinfo': int},
                'duration': {'attr': 'setDuration', 'convert': int, 'classinfo': int},
                'year': {'attr': 'setYear', 'convert': int, 'classinfo': int},
                'genre': {'attr': 'setGenres', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'album': {'attr': 'setAlbum', 'convert': str, 'classinfo': str},
                'artist': {'attr': 'setArtist', 'convert': str, 'classinfo': str},
                'title': {'attr': 'setTitle', 'convert': str, 'classinfo': str},
                'rating': {'attr': 'setRating', 'convert': float, 'classinfo': float},
                'userrating': {'attr': 'setUserRating', 'convert': int, 'classinfo': int},
                'lyrics': {'attr': 'setLyrics', 'convert': str, 'classinfo': str},
                'playcount': {'attr': 'setPlayCount', 'convert': int, 'classinfo': int},
                'lastplayed': {'attr': 'setLastPlayed', 'convert': str, 'classinfo': str},
                'mediatype': {'attr': 'setMediaType', 'convert': str, 'classinfo': str},
                'dbid': {'route': 'set_info_music_dbid'},
                'listeners': {'attr': 'setListeners', 'convert': int, 'classinfo': int},
                'musicbrainztrackid': {'attr': 'setMusicBrainzTrackID', 'convert': str, 'classinfo': str},
                'musicbrainzartistid': {'attr': 'setMusicBrainzArtistID', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'musicbrainzalbumid': {'attr': 'setMusicBrainzAlbumID', 'convert': str, 'classinfo': str},
                'musicbrainzalbumartistid': {'attr': 'setMusicBrainzAlbumArtistID', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'comment': {'attr': 'setComment', 'convert': str, 'classinfo': str},
                'albumartist': {'attr': 'setAlbumArtist', 'convert': str, 'classinfo': str},  # Not listed in setInfo docs but included for forward compatibility
            }
        },
        'game': {
            'tag_getter': 'getGameInfoTag',
            'tag_attr': {
                'title': {'attr': 'setTitle', 'convert': str, 'classinfo': str},
                'platform': {'attr': 'setPlatform', 'convert': str, 'classinfo': str},
                'genres': {'attr': 'setGenres', 'convert': lambda x: [x], 'classinfo': (list, tuple)},
                'publisher': {'attr': 'setPublisher', 'convert': str, 'classinfo': str},
                'developer': {'attr': 'setDeveloper', 'convert': str, 'classinfo': str},
                'overview': {'attr': 'setOverview', 'convert': str, 'classinfo': str},
                'year': {'attr': 'setYear', 'convert': int, 'classinfo': int},
                'gameclient': {'attr': 'setGameClient', 'convert': str, 'classinfo': str},
            }
        }
    }

    def __init__(self, listitem, tag_type: str = 'video', type_check=False):
        """
        Pass xbmcgui.ListItem() to listitem with tag_type to the library type normally in li.setInfo(type=)
        Optional set type_check=
            - False: (default)
                - Slightly increases performance by avoiding additional internal type checks
                - Relys on Kodi Python API raising a TypeError to determine when to force type conversion
                - Kodi creates EXCEPTION log spam when infolabels require type conversion
            - True:
                - Slightly descreases performance by requiring additional internal type checks
                - Uses internal isinstance type check to determine when to force type conversion
                - Prevents Kodi EXCEPTION log spam when infolabels require type conversion
        """
        self._listitem = listitem
        self._tag_type = tag_type
        self._tag_attr = self.INFO_TAG_ATTR[tag_type]['tag_attr']
        self._info_tag = getattr(self._listitem, self.INFO_TAG_ATTR[tag_type]['tag_getter'])()
        self._type_chk = type_check

    def set_info(self, infolabels: dict):
        """ Wrapper for compatibility with Matrix ListItem.setInfo() method """
        for k, v in infolabels.items():
            if v is None:
                continue
            try:
                _tag_attr = self._tag_attr[k]
                func = getattr(self._info_tag, _tag_attr['attr'])
                if self._type_chk and not isinstance(v, _tag_attr['classinfo']):
                    raise TypeError
                func(v)

            except KeyError:
                if k not in self._tag_attr:
                    log_msg = f'[script.module.infotagger] set_info:\nKeyError: {k}'
                    kodi_log(log_msg, level=LOGINFO)
                    continue

                if _tag_attr.get('skip'):
                    continue

                if 'route' in _tag_attr:
                    getattr(self, _tag_attr['route'])(v, infolabels)
                    continue

                log_msg = _tag_attr.get('log_msg') or ''
                log_msg = f'[script.module.infotagger] set_info:\nKeyError: {log_msg}'
                kodi_log(log_msg, level=LOGINFO)
                continue

            except TypeError:
                func(_tag_attr['convert'](v))  # Attempt to force conversion to correct type

    def set_info_music_dbid(self, dbid: int, infolabels: dict, *args, **kwargs):
        """ Wrapper for InfoTagMusic.setDbId to retrieve mediatype """
        try:
            mediatype = infolabels['mediatype']
            self._info_tag.setDbId(int(dbid), mediatype)
        except (KeyError, TypeError):
            return

    def set_info_cast(self, cast: list, *args, **kwargs):
        """ Wrapper to convert cast and castandrole from ListItem.setInfo() to InfoTagVideo.setCast() """
        def _set_cast_member(x, i):
            if not isinstance(i, tuple):
                i = (i, '',)
            return {'name': f'{i[0]}', 'role': f'{i[1]}', 'order': x, 'thumbnail': ''}

        self._info_tag.setCast([Actor(**_set_cast_member(x, i)) for x, i in enumerate(cast, start=1)])

    def set_cast(self, cast: list):
        """ Wrapper for compatibility with Matrix ListItem.setCast() method """
        self._info_tag.setCast([Actor(**i) for i in cast])

    def set_unique_ids(self, unique_ids: dict, default_id: str = None):
        """ Wrapper for compatibility with Matrix ListItem.setUniqueIDs() method """
        self._info_tag.setUniqueIDs({k: f'{v}' for k, v in unique_ids.items()}, default_id)

    def set_stream_details(self, stream_details: dict):
        """ Wrapper for compatibility with multiple ListItem.addStreamInfo() methods in one call """
        if not stream_details:
            return

        try:
            for i in stream_details['video']:
                try:
                    self._info_tag.addVideoStream(VideoStreamDetail(**i))
                except TypeError:
                    # TEMP BANDAID workaround for inconsistent key names prior to Nexus Beta changes
                    i['hdrType'] = i.pop('hdrtype', '')
                    i['stereoMode'] = i.pop('stereomode', '')
                    self._info_tag.addVideoStream(VideoStreamDetail(**i))
        except (KeyError, TypeError):
            pass

        try:
            for i in stream_details['audio']:
                self._info_tag.addAudioStream(AudioStreamDetail(**i))
        except (KeyError, TypeError):
            pass

        try:
            for i in stream_details['subtitle']:
                self._info_tag.addSubtitleStream(SubtitleStreamDetail(**i))
        except (KeyError, TypeError):
            pass

    def add_stream_info(self, stream_type, stream_values):
        """ Wrapper for compatibility with Matrix ListItem.addStreamInfo() method """
        stream_details = {'video': [], 'audio': [], 'subtitle': []}
        stream_details[stream_type] = [stream_values]
        self.set_stream_details(stream_details)
