# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from xbmcgui import ListItem

try:
    from infotagger.listitem import set_info_tag
except ImportError:
    def set_info_tag(listitem, info, tag_type, *_args, **_kwargs):
        listitem.setInfo(tag_type, info)
        return ListItemInfoTag(listitem, tag_type)

    class ListItemInfoTag(object):
        __slots__ = ('__li__', )

        def __init__(self, listitem, *_args, **_kwargs):
            self.__li__ = listitem

        def add_stream_info(self, *args, **kwargs):
            return self.__li__.addStreamInfo(*args, **kwargs)

        def set_resume_point(self, *_args, **_kwargs):
            pass

from . import info_labels
from ...items import VideoItem, AudioItem, UriItem
from ...utils import datetime_parser


def to_play_item(context, play_item):
    uri = play_item.get_uri()
    context.log_debug('Converting PlayItem |%s|' % uri)

    settings = context.get_settings()
    headers = play_item.get_headers()
    license_key = play_item.get_license_key()
    alternative_player = settings.is_support_alternative_player_enabled()
    is_strm = context.get_param('strm')
    mime_type = None

    kwargs = {
        'label': (None if is_strm
                  else (play_item.get_title() or play_item.get_name())),
        'label2': None if is_strm else play_item.get_short_details(),
        'offscreen': True,
    }
    props = {
        'isPlayable': 'true',
    }

    if (alternative_player
            and settings.alternative_player_web_urls()
            and not license_key):
        play_item.set_uri('https://www.youtube.com/watch?v={video_id}'.format(
            video_id=play_item.video_id
        ))

    elif (play_item.use_isa_video()
            and context.addon_enabled('inputstream.adaptive')):
        if play_item.use_mpd_video():
            manifest_type = 'mpd'
            mime_type = 'application/xml+dash'
            # MPD manifest update is currently broken
            # Following line will force a full update but restart live stream from start
            # if play_item.live:
            #     props['inputstream.adaptive.manifest_update_parameter'] = 'full'
            if 'auto' in settings.stream_select():
                props['inputstream.adaptive.stream_selection_type'] = 'adaptive'
        else:
            manifest_type = 'hls'
            mime_type = 'application/x-mpegURL'

        props['inputstream'] = 'inputstream.adaptive'
        props['inputstream.adaptive.manifest_type'] = manifest_type

        if headers:
            props['inputstream.adaptive.manifest_headers'] = headers
            props['inputstream.adaptive.stream_headers'] = headers

        if license_key:
            props['inputstream.adaptive.license_type'] = 'com.widevine.alpha'
            props['inputstream.adaptive.license_key'] = license_key

    else:
        if 'mime=' in uri:
            mime_type = uri.partition('mime=')[2].partition('&')[0].replace('%2F', '/')

        if not alternative_player and headers and uri.startswith('http'):
            play_item.set_uri('|'.join([uri, headers]))

    list_item = ListItem(**kwargs)
    if mime_type:
        list_item.setContentLookup(False)
        list_item.setMimeType(mime_type)

    if is_strm:
        return list_item

    if not context.get_param('resume'):
        if 'ResumeTime' in props:
            del props['ResumeTime']

        prop_value = play_item.get_duration()
        if prop_value:
            props['TotalTime'] = str(prop_value)

    fanart = settings.show_fanart() and play_item.get_fanart() or ''
    thumb = play_item.get_image() or 'DefaultVideo.png'
    list_item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})

    if play_item.subtitles:
        list_item.setSubtitles(play_item.subtitles)

    info = info_labels.create_from_item(play_item)
    info_tag = set_info_tag(list_item, info, 'video')
    info_tag.set_resume_point(props)

    # This should work for all versions of XBMC/KODI.
    if 'duration' in info:
        info_tag.add_stream_info('video', {'duration': info['duration']})

    list_item.setProperties(props)

    return list_item


def to_video_item(context, video_item):
    context.log_debug('Converting VideoItem |%s|' % video_item.get_uri())

    kwargs = {
        'label': video_item.get_title() or video_item.get_name(),
        'label2': video_item.get_short_details(),
        'offscreen': True,
    }
    props = {
        'isPlayable': 'true',
    }

    list_item = ListItem(**kwargs)

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
        props['ResumeTime'] = str(prop_value)

    prop_value = video_item.get_duration()
    if prop_value:
        props['TotalTime'] = str(prop_value)

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

    fanart = (context.get_settings().show_fanart()
              and video_item.get_fanart()
              or '')
    thumb = video_item.get_image() or 'DefaultVideo.png'
    list_item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})

    if video_item.subtitles:
        list_item.setSubtitles(video_item.subtitles)

    info = info_labels.create_from_item(video_item)
    info_tag = set_info_tag(list_item, info, 'video')
    info_tag.set_resume_point(props)

    # This should work for all versions of XBMC/KODI.
    if 'duration' in info:
        info_tag.add_stream_info('video', {'duration': info['duration']})

    list_item.setProperties(props)

    context_menu = video_item.get_context_menu()
    if context_menu:
        list_item.addContextMenuItems(
            context_menu, replaceItems=video_item.replace_context_menu()
        )

    return list_item


def to_audio_item(context, audio_item):
    context.log_debug('Converting AudioItem |%s|' % audio_item.get_uri())

    kwargs = {
        'label': audio_item.get_title() or audio_item.get_name(),
        'label2': audio_item.get_short_details(),
        'offscreen': True,
    }
    props = {
        'isPlayable': 'true',
    }

    list_item = ListItem(**kwargs)

    fanart = (context.get_settings().show_fanart()
              and audio_item.get_fanart()
              or '')
    thumb = audio_item.get_image() or 'DefaultAudio.png'
    list_item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})

    info = info_labels.create_from_item(audio_item)
    set_info_tag(list_item, info, 'music')

    list_item.setProperties(props)

    context_menu = audio_item.get_context_menu()
    if context_menu:
        list_item.addContextMenuItems(
            context_menu, replaceItems=audio_item.replace_context_menu()
        )

    return list_item


def to_uri_item(context, base_item):
    context.log_debug('Converting UriItem')
    item = ListItem(path=base_item.get_uri(), offscreen=True)
    item.setProperty('IsPlayable', 'true')
    return item


def to_playback_item(context, base_item):
    if isinstance(base_item, UriItem):
        return to_uri_item(context, base_item)

    if isinstance(base_item, AudioItem):
        return to_audio_item(context, base_item)

    if isinstance(base_item, VideoItem):
        return to_play_item(context, base_item)

    return None
