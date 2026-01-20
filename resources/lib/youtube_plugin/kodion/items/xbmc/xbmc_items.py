# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from json import dumps

from .. import (
    AudioItem,
    DirectoryItem,
    ImageItem,
    MediaItem,
    VideoItem,
)
from ... import logging
from ...compatibility import to_str, xbmc, xbmcgui
from ...constants import (
    ACTION,
    BOOKMARK_ID,
    CHANNEL_ID,
    PATHS,
    PLAYLIST_ITEM_ID,
    PLAYLIST_ID,
    PLAY_COUNT_PROP,
    PLAY_STRM,
    PLAY_TIMESHIFT,
    PLAY_USING,
    SUBSCRIPTION_ID,
    VALUE_TO_STR,
    VIDEO_ID,
)
from ...utils.datetime import datetime_to_since, utc_to_local
from ...utils.redact import redact_ip_in_uri
from ...utils.system_version import current_system_version


def set_info(list_item, item, properties, set_play_count=True, resume=True):
    stream_details = {}
    if not current_system_version.compatible(20):
        info_labels = {}

        if isinstance(item, MediaItem):
            if isinstance(item, VideoItem):
                info_type = 'video'

                value = item.get_episode()
                if value is not None:
                    info_labels['episode'] = value

                value = item.get_season()
                if value is not None:
                    info_labels['season'] = value

                value = item.get_aspect_ratio()
                if value is not None:
                    stream_details['aspect'] = value

            elif isinstance(item, AudioItem):
                info_type = 'music'

                value = item.get_album_name()
                if value is not None:
                    info_labels['album'] = value

            else:
                return

            value = item.get_aired(as_info_label=True)
            if value is not None:
                info_labels['aired'] = value

            value = item.get_premiered(as_info_label=True)
            if value is not None:
                info_labels['premiered'] = value

            value = item.get_plot()
            if value is not None:
                info_labels['plot'] = value

            value = item.get_last_played(as_info_label=True)
            if value is not None:
                info_labels['lastplayed'] = value

            value = item.get_mediatype()
            if value is not None:
                info_labels['mediatype'] = value

            value = item.get_play_count()
            if value is not None:
                if set_play_count:
                    info_labels['playcount'] = value
                properties[PLAY_COUNT_PROP] = value

            value = item.get_rating()
            if value is not None:
                info_labels['rating'] = value

            value = item.get_name()
            if value is not None:
                info_labels['title'] = value

            value = item.get_track_number()
            if value is not None:
                info_labels['tracknumber'] = value

            value = item.get_year()
            if value is not None:
                info_labels['year'] = value

            resume_time = resume and item.get_start_time()
            if resume_time is not None:
                properties['ResumeTime'] = str(resume_time)
            duration = item.get_duration()
            if duration > 0:
                properties['TotalTime'] = str(duration)
                if info_type == 'video':
                    stream_details['duration'] = duration
                info_labels['duration'] = duration

        elif isinstance(item, DirectoryItem):
            info_type = 'video'

            value = item.get_name()
            if value is not None:
                info_labels['title'] = value

            value = item.get_plot()
            if value is not None:
                info_labels['plot'] = value

            value = item.get_track_number()
            if value is not None:
                info_labels['tracknumber'] = value

        elif isinstance(item, ImageItem):
            info_type = 'picture'

            value = item.get_name()
            if value is not None:
                info_labels['title'] = value

        else:
            return

        value = item.get_production_code()
        if value is not None:
            info_labels['code'] = value

        value = item.get_dateadded(as_info_label=True)
        if value is not None:
            info_labels['dateadded'] = value

        value = item.get_studios()
        if value is not None:
            info_labels['studio'] = value

        value = item.get_cast()
        if value is not None:
            info_labels['castandrole'] = [(member['name'], member['role'])
                                          for member in value]

        value = item.get_artists()
        if value is not None:
            info_labels['artist'] = value

        value = item.get_count()
        if value is not None:
            info_labels['count'] = value

        value = item.get_date(as_info_label=True)
        if value is not None:
            info_labels['date'] = value

        if properties:
            list_item.setProperties(properties)

        if info_type:
            if info_labels:
                list_item.setInfo(info_type, info_labels)
            if stream_details:
                list_item.addStreamInfo(info_type, stream_details)
        return

    if isinstance(item, MediaItem):
        if isinstance(item, VideoItem):
            info_tag = list_item.getVideoInfoTag()
            info_type = 'video'

            # episode: int
            value = item.get_episode()
            if value is not None:
                info_tag.setEpisode(value)

            # season: int
            value = item.get_season()
            if value is not None:
                info_tag.setSeason(value)

            value = item.get_premiered(as_info_label=True)
            if value is not None:
                info_tag.setPremiered(value)

            value = item.get_aired(as_info_label=True)
            if value is not None:
                info_tag.setFirstAired(value)

            # plot: str
            value = item.get_plot()
            if value is not None:
                info_tag.setPlot(value)

            # tracknumber: int
            # eg. 12
            value = item.get_track_number()
            if value is not None:
                info_tag.setTrackNumber(value)

            # director: list[str]
            # eg. "Steven Spielberg"
            # Currently unused
            # value = item.get_directors()
            # if value is not None:
            #     info_tag.setDirectors(value)

            # imdbnumber: str
            # eg. "tt3458353"
            # Currently unused
            # value = item.get_imdb_id()
            # if value is not None:
            #     info_tag.setIMDBNumber(value)

            # video width x height is not accurate, use aspect ratio only
            # value = item.get_stream_details()
            # if value is not None:
            #     stream_details = value

            value = item.get_aspect_ratio()
            if value is not None:
                stream_details['aspect'] = value

        elif isinstance(item, AudioItem):
            info_tag = list_item.getMusicInfoTag()
            info_type = 'music'

            # album: str
            # eg. "Buckle Up"
            value = item.get_album_name()
            if value is not None:
                info_tag.setAlbum(value)

            value = item.get_premiered(as_info_label=True)
            if value is not None:
                info_tag.setReleaseDate(value)

            # comment: str
            value = item.get_plot()
            if value is not None:
                info_tag.setComment(value)

            # artist: str
            # eg. "Artist 1, Artist 2"
            # Used as alias for channel name
            value = item.get_artists_string()
            if value is not None:
                info_tag.setArtist(value)

            # track: int
            # eg. 12
            value = item.get_track_number()
            if value is not None:
                info_tag.setTrack(value)

        else:
            return

        value = item.get_last_played(as_info_label=True)
        if value is not None:
            info_tag.setLastPlayed(value)

        # mediatype: str
        value = item.get_mediatype()
        if value is not None:
            info_tag.setMediaType(value)

        # playcount: int
        value = item.get_play_count()
        if value is not None:
            if set_play_count:
                if info_type == 'video':
                    info_tag.setPlaycount(value)
                elif info_type == 'music':
                    info_tag.setPlayCount(value)
            properties[PLAY_COUNT_PROP] = value

        # rating: float
        value = item.get_rating()
        if value is not None:
            info_tag.setRating(value)

        # title: str
        # eg. "Blow Your Head Off"
        value = item.get_name()
        if value is not None:
            info_tag.setTitle(value)

        # year: int
        # eg. 1994
        value = item.get_year()
        if value is not None:
            info_tag.setYear(value)

        # genre: list[str]
        # eg. ["Hardcore"]
        # Currently unused
        # value = item.get_genres()
        # if value is not None:
        #     info_tag.setGenres(value)

        resume_time = resume and item.get_start_time()
        duration = item.get_duration()
        if info_type == 'video':
            if resume_time is not None:
                if duration > 0:
                    info_tag.setResumePoint(resume_time, float(duration))
                else:
                    info_tag.setResumePoint(resume_time)
            if duration > 0:
                stream_details['duration'] = duration
        elif info_type == 'music':
            # These properties are deprecated but there is no other way to set
            # these details for a ListItem with a MusicInfoTag
            if resume_time is not None:
                properties['ResumeTime'] = str(resume_time)
            if duration > 0:
                properties['TotalTime'] = str(duration)

        # duration: int
        # As seconds
        if duration > 0:
            info_tag.setDuration(duration)

    elif isinstance(item, DirectoryItem):
        info_tag = list_item.getVideoInfoTag()
        info_type = 'video'

        value = item.get_name()
        if value is not None:
            info_tag.setTitle(value)

        value = item.get_plot()
        if value is not None:
            info_tag.setPlot(value)

        # tracknumber: int
        # eg. 12
        value = item.get_track_number()
        if value is not None:
            info_tag.setTrackNumber(value)

    elif isinstance(item, ImageItem):
        info_tag = list_item.getPictureInfoTag()
        info_type = 'picture'

        value = item.get_name()
        if value is not None:
            info_tag.setTitle(value)

    else:
        return

    if info_type == 'video':
        # code: str
        # eg. "466K | 3.9K | 312"
        # Production code, currently used to store misc video data for label
        # formatting
        value = item.get_production_code()
        if value is not None:
            info_tag.setProductionCode(value)

        value = item.get_dateadded(as_info_label=True)
        if value is not None:
            info_tag.setDateAdded(value)

        # studio: list[str]
        # Used as alias for channel name if enabled
        value = item.get_studios()
        if value is not None:
            info_tag.setStudios(value)

        # cast: list[xbmc.Actor]
        # From list[{member: str, role: str, order: int, thumbnail: str}]
        # Used as alias for channel name if enabled
        value = item.get_cast()
        if value is not None:
            info_tag.setCast([xbmc.Actor(**member) for member in value])

        # artist: list[str]
        # eg. ["Angerfist"]
        # Used as alias for channel name
        value = item.get_artists()
        if value is not None:
            info_tag.setArtists(value)

    # count: int
    # eg. 12
    # Can be used to store an id for later, or for sorting purposes
    # Used for Youtube video view count
    value = item.get_count()
    if value is not None:
        list_item.setInfo(info_type, {'count': value})

    value = item.get_date(as_info_label=True)
    if value is not None:
        list_item.setDateTime(value)

    if properties:
        list_item.setProperties(properties)

    if stream_details:
        info_tag.addVideoStream(xbmc.VideoStreamDetail(**stream_details))


def playback_item(context, media_item, show_fanart=None, **_kwargs):
    uri = media_item.get_uri()
    logging.debug('Converting %s for playback: %r',
                  media_item.__class__.__name__,
                  redact_ip_in_uri(uri))

    params = context.get_params()
    settings = context.get_settings()
    ui = context.get_ui()

    is_external = ui.get_property(PLAY_USING)
    is_strm = params.get(PLAY_STRM)
    mime_type = None

    if is_strm:
        kwargs = {
            'path': uri,
            'offscreen': True,
        }
        props = {}
    else:
        kwargs = {
            'label': media_item.get_name(),
            'label2': media_item.get_short_details(),
            'path': uri,
            'offscreen': True,
        }
        props = {
            'isPlayable': VALUE_TO_STR[media_item.playable],
            'ForceResolvePlugin': 'true',
            'playlist_type_hint': (
                xbmc.PLAYLIST_MUSIC
                if isinstance(media_item, AudioItem) else
                xbmc.PLAYLIST_VIDEO
            ),
        }

    if media_item.use_isa() and context.use_inputstream_adaptive():
        capabilities = context.inputstream_adaptive_capabilities()

        use_mpd = media_item.use_mpd()
        if use_mpd:
            manifest_type = 'mpd'
            mime_type = 'application/dash+xml'
        else:
            manifest_type = 'hls'
            mime_type = 'application/x-mpegURL'

        stream_select = settings.stream_select()
        if not use_mpd and 'list' in stream_select:
            props['inputstream.adaptive.stream_selection_type'] = 'manual-osd'
        elif 'auto' in stream_select:
            props['inputstream.adaptive.stream_selection_type'] = 'adaptive'
            props['inputstream.adaptive.chooser_resolution_max'] = 'auto'

        if current_system_version.compatible(19):
            props['inputstream'] = 'inputstream.adaptive'
        else:
            props['inputstreamaddon'] = 'inputstream.adaptive'

        if not current_system_version.compatible(21):
            props['inputstream.adaptive.manifest_type'] = manifest_type

        if media_item.live:
            if 'manifest_config_prop' in capabilities:
                props['inputstream.adaptive.manifest_config'] = dumps({
                    'timeshift_bufferlimit': 4 * 60 * 60,
                })
            if ui.pop_property(PLAY_TIMESHIFT) and 'timeshift' in capabilities:
                props['inputstream.adaptive.play_timeshift_buffer'] = True

        if not settings.verify_ssl() and 'config_prop' in capabilities:
            props['inputstream.adaptive.config'] = dumps({
                'ssl_verify_peer': False,
            })

        headers = media_item.get_headers(as_string=True)
        if headers:
            props['inputstream.adaptive.manifest_headers'] = headers
            props['inputstream.adaptive.stream_headers'] = headers

        license_key = media_item.get_license_key()
        if license_key:
            props['inputstream.adaptive.license_type'] = 'com.widevine.alpha'
            props['inputstream.adaptive.license_key'] = license_key

    else:
        if 'mime=' in uri:
            mime_type = uri.split('mime=', 1)[1].split('&', 1)[0]
            mime_type = mime_type.replace('%2F', '/')

        headers = media_item.get_headers(as_string=True)
        if (headers and uri.startswith('http')
                and not (is_external
                         or settings.default_player_web_urls())):
            uri = '|'.join((uri, headers))
            kwargs['path'] = uri
            media_item.set_uri(uri)

    list_item = xbmcgui.ListItem(**kwargs)

    if mime_type or is_external:
        list_item.setContentLookup(False)
        list_item.setMimeType(mime_type or '*/*')

    if is_strm:
        list_item.setProperties(props)
        return list_item

    if show_fanart is None:
        show_fanart = settings.fanart_selection()
    image = media_item.get_image()
    art = {'icon': image}
    if image:
        art['thumb'] = image
    if show_fanart:
        art['fanart'] = media_item.get_fanart()
    list_item.setArt(art)

    if media_item.subtitles:
        list_item.setSubtitles(media_item.subtitles)

    resume = params.get('resume')
    set_info(list_item, media_item, props, resume=resume)

    return list_item


def directory_listitem(context, directory_item, show_fanart=None, **_kwargs):
    uri = directory_item.get_uri()
    is_action = directory_item.is_action()
    if not is_action:
        path, params = context.parse_uri(uri)
        if path.rstrip('/') == PATHS.PLAY and params.get(ACTION) != 'list':
            is_action = True
    if is_action:
        logging.debug('Converting DirectoryItem action: %r', uri)
    else:
        logging.debug('Converting DirectoryItem: %r', uri)

    kwargs = {
        'label': directory_item.get_name(),
        'label2': directory_item.get_short_details(),
        'path': uri,
        'offscreen': True,
    }
    props = {
        'ForceResolvePlugin': 'true',
    }

    if directory_item.next_page:
        props['specialSort'] = 'bottom'
    else:
        _special_sort = directory_item.get_special_sort()
        if _special_sort is None:
            special_sort = 'top'
        elif _special_sort is False:
            special_sort = None
        else:
            special_sort = _special_sort

        prop_value = directory_item.subscription_id
        if prop_value:
            special_sort = _special_sort
            props[SUBSCRIPTION_ID] = prop_value

        prop_value = directory_item.channel_id
        if prop_value:
            special_sort = _special_sort
            props[CHANNEL_ID] = prop_value

        prop_value = directory_item.playlist_id
        if prop_value:
            special_sort = _special_sort
            props[PLAYLIST_ID] = prop_value

        prop_value = directory_item.bookmark_id
        if prop_value:
            special_sort = _special_sort
            props[BOOKMARK_ID] = prop_value

        prop_value = is_action and getattr(directory_item, VIDEO_ID, None)
        if prop_value:
            special_sort = _special_sort
            props[VIDEO_ID] = prop_value

        if special_sort:
            props['specialSort'] = special_sort

    list_item = xbmcgui.ListItem(**kwargs)

    if show_fanart is None:
        show_fanart = context.get_settings().fanart_selection()
    image = directory_item.get_image()
    art = {'icon': image}
    if image:
        art['thumb'] = image
        art['poster'] = image
    if show_fanart:
        art['fanart'] = directory_item.get_fanart()
    list_item.setArt(art)

    set_info(list_item, directory_item, props)

    context_menu = directory_item.get_context_menu()
    if context_menu is not None:
        list_item.addContextMenuItems(context_menu)

    return uri, list_item, not is_action


def image_listitem(context, image_item, show_fanart=None, **_kwargs):
    uri = image_item.get_uri()
    logging.debug('Converting ImageItem: %r', uri)

    kwargs = {
        'label': image_item.get_name(),
        'path': uri,
        'offscreen': True,
    }
    props = {
        'isPlayable': VALUE_TO_STR[image_item.playable],
        'ForceResolvePlugin': 'true',
    }

    list_item = xbmcgui.ListItem(**kwargs)

    if show_fanart is None:
        show_fanart = context.get_settings().fanart_selection()
    image = image_item.get_image()
    art = {'icon': image}
    if image:
        art['thumb'] = image
    if show_fanart:
        art['fanart'] = image_item.get_fanart()
    list_item.setArt(art)

    set_info(list_item, image_item, props)

    context_menu = image_item.get_context_menu()
    if context_menu is not None:
        list_item.addContextMenuItems(context_menu)

    return uri, list_item, False


def uri_listitem(_context, uri_item, **_kwargs):
    uri = uri_item.get_uri()
    logging.debug('Converting UriItem: %r', uri)

    kwargs = {
        'label': uri_item.get_name(),
        'path': uri,
        'offscreen': True,
    }
    props = {
        'isPlayable': VALUE_TO_STR[uri_item.playable],
        'ForceResolvePlugin': 'true',
    }

    list_item = xbmcgui.ListItem(**kwargs)
    list_item.setProperties(props)
    return list_item


def media_listitem(context,
                   media_item,
                   show_fanart=None,
                   to_sync=None,
                   **_kwargs):
    uri = media_item.get_uri()
    logging.debug('Converting %s: %r', media_item.__class__.__name__, uri)

    kwargs = {
        'label': media_item.get_name(),
        'label2': media_item.get_short_details(),
        'path': uri,
        'offscreen': True,
    }
    props = {
        'isPlayable': VALUE_TO_STR[media_item.playable],
        'ForceResolvePlugin': 'true',
        'playlist_type_hint': (
            xbmc.PLAYLIST_MUSIC
            if isinstance(media_item, AudioItem) else
            xbmc.PLAYLIST_VIDEO
        ),
    }

    published_at = media_item.get_added_utc()
    scheduled_start = media_item.get_scheduled_start_utc()
    datetime = scheduled_start or published_at
    local_datetime = None
    if datetime:
        local_datetime = utc_to_local(datetime)
        props['PublishedLocal'] = to_str(local_datetime)
    if media_item.live:
        props['PublishedSince'] = context.localize('live')
    elif local_datetime:
        props['PublishedSince'] = to_str(datetime_to_since(
            context, local_datetime
        ))

    set_play_count = True
    resume = True
    prop_value = media_item.video_id
    if prop_value:
        props[VIDEO_ID] = prop_value

        if to_sync and prop_value in to_sync:
            set_play_count = False

    # make channel_id property available for keymapping
    prop_value = media_item.channel_id
    if prop_value:
        props[CHANNEL_ID] = prop_value

    # make subscription_id property available for keymapping
    prop_value = media_item.subscription_id
    if prop_value:
        props[SUBSCRIPTION_ID] = prop_value

    # make playlist_id property available for keymapping
    prop_value = media_item.playlist_id
    if prop_value:
        props[PLAYLIST_ID] = prop_value

    # make playlist_item_id property available for keymapping
    prop_value = media_item.playlist_item_id
    if prop_value:
        props[PLAYLIST_ITEM_ID] = prop_value

    # make bookmark_id property available for keymapping
    prop_value = media_item.bookmark_id
    if prop_value:
        props[BOOKMARK_ID] = prop_value

    list_item = xbmcgui.ListItem(**kwargs)

    if show_fanart is None:
        show_fanart = context.get_settings().fanart_selection()
    image = media_item.get_image()
    art = {'icon': image}
    if image:
        art['thumb'] = image
    if show_fanart:
        art['fanart'] = media_item.get_fanart()
    list_item.setArt(art)

    if media_item.subtitles:
        list_item.setSubtitles(media_item.subtitles)

    set_info(list_item,
             media_item,
             props,
             set_play_count=set_play_count,
             resume=resume)

    context_menu = media_item.get_context_menu()
    if context_menu:
        list_item.addContextMenuItems(context_menu)

    return uri, list_item, False
