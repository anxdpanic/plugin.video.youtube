# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from . import info_labels
from ...compatibility import xbmcgui
from ...items import AudioItem, UriItem, VideoItem
from ...utils import current_system_version, datetime_parser


try:
    from infotagger.listitem import set_info_tag
except ImportError:
    def set_info_tag(listitem, infolabels, tag_type, *_args, **_kwargs):
        listitem.setInfo(tag_type, infolabels)
        return ListItemInfoTag(listitem, tag_type)


    class ListItemInfoTag(object):
        __slots__ = ('__li__',)

        def __init__(self, listitem, *_args, **_kwargs):
            self.__li__ = listitem

        def add_stream_info(self, *args, **kwargs):
            return self.__li__.addStreamInfo(*args, **kwargs)

        def set_resume_point(self,
                             infoproperties,
                             resume_key='ResumeTime',
                             total_key='TotalTime'):
            if resume_key in infoproperties:
                infoproperties[resume_key] = str(infoproperties[resume_key])
            if total_key in infoproperties:
                infoproperties[total_key] = str(infoproperties[total_key])


def video_playback_item(context, video_item):
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
        'ForceResolvePlugin': 'true',
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
            video_item.set_uri('|'.join([uri, headers]))

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

    fanart = settings.show_fanart() and video_item.get_fanart() or ''
    thumb = video_item.get_image() or 'DefaultVideo.png'
    list_item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})

    if video_item.subtitles:
        list_item.setSubtitles(video_item.subtitles)

    item_info = info_labels.create_from_item(video_item)
    info_tag = set_info_tag(list_item, item_info, 'video')
    info_tag.set_resume_point(props)

    # This should work for all versions of XBMC/KODI.
    if 'duration' in item_info:
        info_tag.add_stream_info('video', {'duration': item_info['duration']})

    list_item.setProperties(props)

    return list_item


def audio_listitem(context, audio_item):
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

    fanart = (context.get_settings().show_fanart()
              and audio_item.get_fanart()
              or '')
    thumb = audio_item.get_image() or 'DefaultAudio.png'
    list_item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})

    item_info = info_labels.create_from_item(audio_item)
    set_info_tag(list_item, item_info, 'music')

    list_item.setProperties(props)

    context_menu = audio_item.get_context_menu()
    if context_menu:
        list_item.addContextMenuItems(
            context_menu, replaceItems=audio_item.replace_context_menu()
        )

    return list_item


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


def video_listitem(context, video_item):
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

    fanart = (context.get_settings().show_fanart()
              and video_item.get_fanart()
              or '')
    thumb = video_item.get_image() or 'DefaultVideo.png'
    list_item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})

    if video_item.subtitles:
        list_item.setSubtitles(video_item.subtitles)

    item_info = info_labels.create_from_item(video_item)
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

    return list_item


def to_playback_item(context, base_item):
    if isinstance(base_item, UriItem):
        return uri_listitem(context, base_item)

    if isinstance(base_item, AudioItem):
        return audio_listitem(context, base_item)

    if isinstance(base_item, VideoItem):
        return video_playback_item(context, base_item)

    return None
