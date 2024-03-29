# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .. import AudioItem, DirectoryItem, ImageItem, UriItem, VideoItem
from ...compatibility import xbmc, xbmcgui
from ...utils import current_system_version, datetime_parser


def set_info(list_item, item, properties):
    is_video = False
    if not current_system_version.compatible(20, 0):
        if isinstance(item, VideoItem):
            is_video = True
            info_labels = {}

            value = item.get_aired(as_info_label=True)
            if value is not None:
                info_labels['aired'] = value

            value = item.get_artists()
            if value is not None:
                info_labels['artist'] = value

            value = item.get_code()
            if value is not None:
                info_labels['code'] = value

            value = item.get_count()
            if value is not None:
                info_labels['count'] = value

            value = item.get_date(as_info_label=True)
            if value is not None:
                info_labels['date'] = value

            value = item.get_dateadded(as_info_label=True)
            if value is not None:
                info_labels['dateadded'] = value

            value = item.get_duration()
            if value is not None:
                info_labels['duration'] = value

            value = item.get_episode()
            if value is not None:
                info_labels['episode'] = value

            value = item.get_last_played(as_info_label=True)
            if value is not None:
                info_labels['lastplayed'] = value

            value = item.get_mediatype()
            if value is not None:
                info_labels['mediatype'] = value

            value = item.get_play_count()
            if value is not None:
                info_labels['playcount'] = value

            value = item.get_plot()
            if value is not None:
                info_labels['plot'] = value

            value = item.get_premiered(as_info_label=True)
            if value is not None:
                info_labels['premiered'] = value

            value = item.get_rating()
            if value is not None:
                info_labels['rating'] = value

            value = item.get_season()
            if value is not None:
                info_labels['season'] = value

            value = item.get_title()
            if value is not None:
                info_labels['title'] = value

            value = item.get_track_number()
            if value is not None:
                info_labels['tracknumber'] = value

            value = item.get_year()
            if value is not None:
                info_labels['year'] = value

            if info_labels:
                list_item.setInfo('video', info_labels)

        elif isinstance(item, DirectoryItem):
            value = item.get_plot()
            if value is not None:
                list_item.setInfo('picture', {'plot': value})

            if properties:
                list_item.setProperties(properties)
            return

        elif isinstance(item, AudioItem):
            info_labels = {}

            value = item.get_album_name()
            if value is not None:
                info_labels['album'] = value

            value = item.get_artists()
            if value is not None:
                info_labels['artist'] = value

            value = item.get_duration()
            if value is not None:
                info_labels['duration'] = value

            value = item.get_rating()
            if value is not None:
                info_labels['rating'] = value

            value = item.get_title()
            if value is not None:
                info_labels['title'] = value

            value = item.get_track_number()
            if value is not None:
                info_labels['tracknumber'] = value

            value = item.get_year()
            if value is not None:
                info_labels['year'] = value

            if info_labels:
                list_item.setInfo('music', info_labels)

        elif isinstance(item, ImageItem):
            value = item.get_title()
            if value is not None:
                list_item.setInfo('picture', {'title': value})

            if properties:
                list_item.setProperties(properties)
            return

        resume_time = item.get_start_time()
        if resume_time:
            properties['ResumeTime'] = str(resume_time)
        duration = item.get_duration()
        if duration:
            properties['TotalTime'] = str(duration)
            if is_video:
                list_item.addStreamInfo('video', {'duration': duration})
        if properties:
            list_item.setProperties(properties)
        return

    if properties:
        list_item.setProperties(properties)

    value = item.get_date(as_info_label=True)
    if value is not None:
        list_item.setDateTime(value)

    info_tag = None

    if isinstance(item, VideoItem):
        is_video = True
        info_tag = list_item.getVideoInfoTag()

        value = item.get_dateadded(as_info_label=True)
        if value is not None:
            info_tag.setDateAdded(value)

        value = item.get_last_played(as_info_label=True)
        if value is not None:
            info_tag.setLastPlayed(value)

        value = item.get_aired(as_info_label=True)
        if value is not None:
            info_tag.setFirstAired(value)

        value = item.get_premiered(as_info_label=True)
        if value is not None:
            info_tag.setPremiered(value)

        # count: int
        # eg. 12
        # Can be used to store an id for later, or for sorting purposes
        # Used for Youtube video view count
        value = item.get_count()
        if value is not None:
            list_item.setInfo('video', {'count': value})

        # cast: list[xbmc.Actor]
        # From list[{member: str, role: str, order: int, thumbnail: str}]
        # Currently unused
        # info_tag.setCast(xbmc.Actor(**member) for member in item.get_cast())

        # code: str
        # eg. "466K | 3.9K | 312"
        # Production code, currently used to store misc video data for label
        # formatting
        value = item.get_code()
        if value is not None:
            info_tag.setProductionCode(value)

        # director: list[str]
        # eg. "Steven Spielberg"
        # Currently unused
        # info_tag.setDirectors(item.get_directors())

        # episode: int
        value = item.get_episode()
        if value is not None:
            info_tag.setEpisode(value)

        # imdbnumber: str
        # eg. "tt3458353"
        # Currently unused
        # info_tag.setIMDBNumber(item.get_imdb_id())

        # mediatype: str
        value = item.get_mediatype()
        if value is not None:
            info_tag.setMediaType(value)

        # playcount: int
        value = item.get_play_count()
        if value is not None:
            info_tag.setPlaycount(value)

        # plot: str
        value = item.get_plot()
        if value is not None:
            info_tag.setPlot(value)

        # season: int
        value = item.get_season()
        if value is not None:
            info_tag.setSeason(value)

        # studio: list[str]
        # Currently unused
        # info_tag.setStudios(item.get_studios())

    elif isinstance(item, DirectoryItem):
        info_tag = list_item.getVideoInfoTag()

        value = item.get_plot()
        if value is not None:
            info_tag.setPlot(value)
        return

    elif isinstance(item, ImageItem):
        value = item.get_title()
        if value is not None:
            list_item.setInfo('picture', {'title': value})
        return

    elif isinstance(item, AudioItem):
        info_tag = list_item.getMusicInfoTag()

        # album: str
        # eg. "Buckle Up"
        value = item.get_album_name()
        if value is not None:
            info_tag.setAlbum(value)

    resume_time = item.get_start_time()
    duration = item.get_duration()
    if resume_time and duration:
        info_tag.setResumePoint(resume_time, float(duration))
    elif resume_time:
        info_tag.setResumePoint(resume_time)
    if is_video and duration:
        info_tag.addVideoStream(xbmc.VideoStreamDetail(duration=duration))

    # artist: list[str]
    # eg. ["Angerfist"]
    value = item.get_artists()
    if value is not None:
        info_tag.setArtists(value)

    # duration: int
    # As seconds
    if duration is not None:
        info_tag.setDuration(duration)

    # genre: list[str]
    # eg. ["Hardcore"]
    # Currently unused
    # info_tag.setGenres(item.get_genres())

    # rating: float
    value = item.get_rating()
    if value is not None:
        info_tag.setRating(value)

    # title: str
    # eg. "Blow Your Head Off"
    value = item.get_title()
    if value is not None:
        info_tag.setTitle(value)

    # tracknumber: int
    # eg. 12
    value = item.get_track_number()
    if value is not None:
        info_tag.setTrackNumber(value)

    # year: int
    # eg. 1994
    value = item.get_year()
    if value is not None:
        info_tag.setYear(value)


def video_playback_item(context, video_item, show_fanart=None):
    uri = video_item.get_uri()
    context.log_debug('Converting VideoItem |%s|' % uri)

    settings = context.get_settings()
    headers = video_item.get_headers()
    license_key = video_item.get_license_key()
    alternative_player = settings.support_alternative_player()
    is_strm = context.get_param('strm')
    mime_type = None

    if is_strm:
        kwargs = {
            'path': uri,
            'offscreen': True,
        }
        props = {}
    else:
        kwargs = {
            'label': video_item.get_title() or video_item.get_name(),
            'label2': video_item.get_short_details(),
            'path': uri,
            'offscreen': True,
        }
        props = {
            'isPlayable': str(video_item.playable).lower(),
        }

    if (alternative_player
            and settings.alternative_player_web_urls()
            and not license_key):
        video_item.set_uri('https://www.youtube.com/watch?v={video_id}'.format(
            video_id=video_item.video_id
        ))
    elif (video_item.use_isa_video()
            and context.addon_enabled('inputstream.adaptive')):
        if video_item.use_mpd_video():
            manifest_type = 'mpd'
            mime_type = 'application/dash+xml'
            if 'auto' in settings.stream_select():
                props['inputstream.adaptive.stream_selection_type'] = 'adaptive'
        else:
            manifest_type = 'hls'
            mime_type = 'application/x-mpegURL'

        inputstream_property = ('inputstream'
                                if current_system_version.compatible(19, 0) else
                                'inputstreamaddon')
        props[inputstream_property] = 'inputstream.adaptive'
        props['inputstream.adaptive.manifest_type'] = manifest_type

        if headers:
            props['inputstream.adaptive.manifest_headers'] = headers
            props['inputstream.adaptive.stream_headers'] = headers

        if license_key:
            props['inputstream.adaptive.license_type'] = 'com.widevine.alpha'
            props['inputstream.adaptive.license_key'] = license_key

    else:
        if 'mime=' in uri:
            mime_type = uri.split('mime=', 1)[1].split('&', 1)[0]
            mime_type = mime_type.replace('%2F', '/')

        if not alternative_player and headers and uri.startswith('http'):
            video_item.set_uri('|'.join((uri, headers)))

    list_item = xbmcgui.ListItem(**kwargs)

    if mime_type:
        list_item.setContentLookup(False)
        list_item.setMimeType(mime_type)

    if is_strm:
        list_item.setProperties(props)
        return list_item

    if show_fanart is None:
        show_fanart = settings.show_fanart()
    image = video_item.get_image()
    list_item.setArt({
        'icon': image or 'DefaultVideo.png',
        'fanart': show_fanart and video_item.get_fanart() or '',
        'thumb': image,
    })

    if video_item.subtitles:
        list_item.setSubtitles(video_item.subtitles)

    set_info(list_item, video_item, props)

    return list_item


def audio_listitem(context, audio_item, show_fanart=None):
    uri = audio_item.get_uri()
    context.log_debug('Converting AudioItem |%s|' % uri)

    kwargs = {
        'label': audio_item.get_title() or audio_item.get_name(),
        'label2': audio_item.get_short_details(),
        'path': uri,
        'offscreen': True,
    }
    props = {
        'isPlayable': str(audio_item.playable).lower(),
        'ForceResolvePlugin': 'true',
    }

    list_item = xbmcgui.ListItem(**kwargs)

    if show_fanart is None:
        show_fanart = context.get_settings().show_fanart()
    image = audio_item.get_image() or 'DefaultAudio.png'
    list_item.setArt({
        'icon': image,
        'fanart': show_fanart and audio_item.get_fanart() or '',
        'thumb': image,
    })

    set_info(list_item, audio_item, props)

    context_menu = audio_item.get_context_menu()
    if context_menu:
        list_item.addContextMenuItems(
            context_menu, replaceItems=audio_item.replace_context_menu()
        )

    return uri, list_item, False


def directory_listitem(context, directory_item, show_fanart=None):
    uri = directory_item.get_uri()
    context.log_debug('Converting DirectoryItem |%s|' % uri)

    kwargs = {
        'label': directory_item.get_name(),
        'path': uri,
        'offscreen': True,
    }
    props = {
        'specialSort': 'bottom' if directory_item.next_page else 'top',
        'ForceResolvePlugin': 'true',
    }

    list_item = xbmcgui.ListItem(**kwargs)

    # make channel_subscription_id property available for keymapping
    prop_value = directory_item.get_channel_subscription_id()
    if prop_value:
        props['channel_subscription_id'] = prop_value

    if show_fanart is None:
        show_fanart = context.get_settings().show_fanart()
    image = directory_item.get_image() or 'DefaultFolder.png'
    list_item.setArt({
        'icon': image,
        'fanart': show_fanart and directory_item.get_fanart() or '',
        'thumb': image,
    })

    set_info(list_item, directory_item, props)

    """
    # ListItems that do not open a lower level list should have the isFolder
    # parameter of the xbmcplugin.addDirectoryItem set to False, however this
    # now appears to mark the ListItem as playable, even if the IsPlayable
    # property is not set or set to "false".
    # Set isFolder to True as a workaround, regardless of whether the ListItem
    # is actually a folder.
    is_folder = not directory_item.is_action()
    """
    is_folder = True

    context_menu = directory_item.get_context_menu()
    if context_menu is not None:
        list_item.addContextMenuItems(
            context_menu, replaceItems=directory_item.replace_context_menu()
        )

    return uri, list_item, is_folder


def image_listitem(context, image_item, show_fanart=None):
    uri = image_item.get_uri()
    context.log_debug('Converting ImageItem |%s|' % uri)

    kwargs = {
        'label': image_item.get_name(),
        'path': uri,
        'offscreen': True,
    }
    props = {
        'isPlayable': str(image_item.playable).lower(),
        'ForceResolvePlugin': 'true',
    }

    list_item = xbmcgui.ListItem(**kwargs)

    if show_fanart is None:
        show_fanart = context.get_settings().show_fanart()
    image = image_item.get_image() or 'DefaultPicture.png'
    list_item.setArt({
        'icon': image,
        'fanart': show_fanart and image_item.get_fanart() or '',
        'thumb': image,
    })

    set_info(list_item, image_item, props)

    context_menu = image_item.get_context_menu()
    if context_menu is not None:
        list_item.addContextMenuItems(
            context_menu, replaceItems=image_item.replace_context_menu()
        )

    return uri, list_item, False


def uri_listitem(context, uri_item):
    uri = uri_item.get_uri()
    context.log_debug('Converting UriItem |%s|' % uri)

    kwargs = {
        'label': uri_item.get_name(),
        'path': uri,
        'offscreen': True,
    }
    props = {
        'isPlayable': str(uri_item.playable).lower(),
        'ForceResolvePlugin': 'true',
    }

    list_item = xbmcgui.ListItem(**kwargs)
    list_item.setProperties(props)
    return list_item


def video_listitem(context, video_item, show_fanart=None):
    uri = video_item.get_uri()
    context.log_debug('Converting VideoItem |%s|' % uri)

    kwargs = {
        'label': video_item.get_title() or video_item.get_name(),
        'label2': video_item.get_short_details(),
        'path': uri,
        'offscreen': True,
    }
    props = {
        'isPlayable': str(video_item.playable).lower(),
        'ForceResolvePlugin': 'true',
    }

    list_item = xbmcgui.ListItem(**kwargs)

    published_at = video_item.get_added_utc()
    scheduled_start = video_item.get_scheduled_start_utc()
    datetime = scheduled_start or published_at
    local_datetime = None
    if datetime:
        local_datetime = datetime_parser.utc_to_local(datetime)
        props['PublishedLocal'] = str(local_datetime)
    if video_item.live:
        props['PublishedSince'] = context.localize('live')
    elif local_datetime:
        props['PublishedSince'] = str(datetime_parser.datetime_to_since(
            context, local_datetime
        ))

    # make channel_id property available for keymapping
    prop_value = video_item.get_channel_id()
    if prop_value:
        props['channel_id'] = prop_value

    # make subscription_id property available for keymapping
    prop_value = video_item.get_subscription_id()
    if prop_value:
        props['subscription_id'] = prop_value

    # make playlist_id property available for keymapping
    prop_value = video_item.get_playlist_id()
    if prop_value:
        props['playlist_id'] = prop_value

    # make playlist_item_id property available for keymapping
    prop_value = video_item.get_playlist_item_id()
    if prop_value:
        props['playlist_item_id'] = prop_value

    if show_fanart is None:
        show_fanart = context.get_settings().show_fanart()
    image = video_item.get_image()
    list_item.setArt({
        'icon': image or 'DefaultVideo.png',
        'fanart': show_fanart and video_item.get_fanart() or '',
        'thumb': image,
    })

    if video_item.subtitles:
        list_item.setSubtitles(video_item.subtitles)

    set_info(list_item, video_item, props)

    context_menu = video_item.get_context_menu()
    if context_menu:
        list_item.addContextMenuItems(
            context_menu, replaceItems=video_item.replace_context_menu()
        )

    return uri, list_item, False


def playback_item(context, base_item, show_fanart=None):
    if isinstance(base_item, UriItem):
        return uri_listitem(context, base_item)

    if isinstance(base_item, AudioItem):
        _, item, _ = audio_listitem(context, base_item, show_fanart)
        return item

    if isinstance(base_item, VideoItem):
        return video_playback_item(context, base_item, show_fanart)

    return None
