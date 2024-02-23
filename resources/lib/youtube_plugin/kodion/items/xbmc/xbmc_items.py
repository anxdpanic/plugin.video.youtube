# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from .. import AudioItem, DirectoryItem, ImageItem, UriItem, VideoItem
from ...compatibility import set_info_tag, xbmcgui
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


def create_info_labels(base_item):
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


def video_playback_item(context, video_item, show_fanart=None):
    uri = video_item.get_uri()
    context.log_debug('Converting VideoItem |%s|' % uri)

    settings = context.get_settings()
    headers = video_item.get_headers()
    license_key = video_item.get_license_key()
    alternative_player = settings.is_support_alternative_player_enabled()
    is_strm = context.get_param('strm')
    mime_type = None

    if is_strm:
        kwargs = {
            'path': uri,
            'offscreen': True,
        }
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

    manifest_type = None
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
            """
            # MPD manifest update is currently broken
            # Following line will force a full update but restart live stream
            if video_item.live:
                props['inputstream.adaptive.manifest_update_parameter'] = 'full'
            """
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
        return list_item

    if not context.get_param('resume'):
        if context.get_param('start'):
            prop_value = video_item.get_start_time()
            if prop_value:
                props['ResumeTime'] = prop_value
        elif 'ResumeTime' in props:
            del props['ResumeTime']

        prop_value = video_item.get_duration()
        if prop_value:
            props['TotalTime'] = prop_value

    if show_fanart is None:
        show_fanart = settings.show_fanart()
    image = video_item.get_image()
    list_item.setArt({
        'icon': image or 'DefaultVideo.png',
        'fanart': show_fanart and video_item.get_fanart() or '',
        'thumb': image,
    })

    if video_item.subtitles and manifest_type != 'mpd':
        list_item.setSubtitles(video_item.subtitles)

    item_info = create_info_labels(video_item)
    info_tag = set_info_tag(list_item, item_info, 'video')
    info_tag.set_resume_point(props)

    # This should work for all versions of XBMC/KODI.
    if 'duration' in item_info:
        info_tag.add_stream_info('video', {'duration': item_info['duration']})

    list_item.setProperties(props)

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

    item_info = create_info_labels(audio_item)
    set_info_tag(list_item, item_info, 'music')

    list_item.setProperties(props)

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

    item_info = create_info_labels(directory_item)
    set_info_tag(list_item, item_info, 'video')

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

    list_item.setProperties(props)

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

    item_info = create_info_labels(image_item)
    set_info_tag(list_item, item_info, 'picture')

    list_item.setProperties(props)

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

    prop_value = video_item.get_start_time()
    if prop_value:
        props['ResumeTime'] = prop_value

    prop_value = video_item.get_duration()
    if prop_value:
        props['TotalTime'] = prop_value

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

    item_info = create_info_labels(video_item)
    info_tag = set_info_tag(list_item, item_info, 'video')
    info_tag.set_resume_point(props)

    # This should work for all versions of XBMC/KODI.
    if 'duration' in item_info:
        info_tag.add_stream_info('video', {'duration': item_info['duration']})

    list_item.setProperties(props)

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
