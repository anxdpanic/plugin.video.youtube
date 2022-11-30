# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import xbmcgui

from ...items import VideoItem, AudioItem, UriItem
from ... import utils
from . import info_labels


def to_play_item(context, play_item):
    context.log_debug('Converting PlayItem |%s|' % play_item.get_uri())

    major_version = context.get_system_version().get_version()[0]

    is_strm = str(context.get_param('strm', False)).lower() == 'true' and major_version >= 18

    thumb = play_item.get_image() if play_item.get_image() else u'DefaultVideo.png'
    title = play_item.get_title() if play_item.get_title() else play_item.get_name()
    fanart = ''
    settings = context.get_settings()
    if is_strm:
        list_item = xbmcgui.ListItem(offscreen=True)
    elif major_version > 17:
        list_item = xbmcgui.ListItem(label=utils.to_unicode(title), offscreen=True)
    else:
        list_item = xbmcgui.ListItem(label=utils.to_unicode(title))

    if not is_strm:
        list_item.setProperty('IsPlayable', 'true')

        if play_item.get_fanart() and settings.show_fanart():
            fanart = play_item.get_fanart()
        if major_version <= 15:
            list_item.setArt({'thumb': thumb, 'fanart': fanart})
            list_item.setIconImage(thumb)
        else:
            list_item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})

    if not play_item.use_dash() and not settings.is_support_alternative_player_enabled() and \
            play_item.get_headers() and play_item.get_uri().startswith('http'):
        play_item.set_uri('|'.join([play_item.get_uri(), play_item.get_headers()]))

    if settings.is_support_alternative_player_enabled() and \
            settings.alternative_player_web_urls() and \
            not play_item.get_license_key():
        play_item.set_uri('https://www.youtube.com/watch?v={video_id}'.format(video_id=play_item.video_id))

    if play_item.use_dash() and context.addon_enabled('inputstream.adaptive'):
        inputstream_property = 'inputstream'
        if major_version < 19:
            inputstream_property += 'addon'
       
        list_item.setContentLookup(False)
        list_item.setMimeType('application/xml+dash')
        list_item.setProperty(inputstream_property, 'inputstream.adaptive')
        list_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        if play_item.get_headers():
            list_item.setProperty('inputstream.adaptive.stream_headers', play_item.get_headers())

        if play_item.get_license_key():
            list_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
            list_item.setProperty('inputstream.adaptive.license_key', play_item.get_license_key())
    else:
        uri = play_item.get_uri()
        if 'mime=' in uri:
            try:
                mime_type = uri.split('mime=', 1)[-1].split('&', 1)[0].replace('%2F', '/', 1)
                list_item.setMimeType(mime_type)
                list_item.setContentLookup(False)
            except:
                pass

    if not is_strm:
        if play_item.get_play_count() == 0:
            if play_item.get_start_percent():
                list_item.setProperty('StartPercent', play_item.get_start_percent())

            if play_item.get_start_time():
                list_item.setProperty('StartOffset', play_item.get_start_time())

        if play_item.subtitles:
            list_item.setSubtitles(play_item.subtitles)

        _info_labels = info_labels.create_from_item(play_item)

        # This should work for all versions of XBMC/KODI.
        if 'duration' in _info_labels:
            duration = _info_labels['duration']
            del _info_labels['duration']
            list_item.addStreamInfo('video', {'duration': duration})

        list_item.setInfo(type='video', infoLabels=_info_labels)
    return list_item


def to_video_item(context, video_item):
    context.log_debug('Converting VideoItem |%s|' % video_item.get_uri())
    major_version = context.get_system_version().get_version()[0]
    thumb = video_item.get_image() if video_item.get_image() else u'DefaultVideo.png'
    title = video_item.get_title() if video_item.get_title() else video_item.get_name()
    fanart = ''
    settings = context.get_settings()
    if major_version > 17:
        item = xbmcgui.ListItem(label=utils.to_unicode(title), offscreen=True)
    else:
        item = xbmcgui.ListItem(label=utils.to_unicode(title))
    if video_item.get_fanart() and settings.show_fanart():
        fanart = video_item.get_fanart()
    if major_version <= 15:
        item.setArt({'thumb': thumb, 'fanart': fanart})
        item.setIconImage(thumb)
    else:
        item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})

    if video_item.get_context_menu() is not None:
        item.addContextMenuItems(video_item.get_context_menu(), replaceItems=video_item.replace_context_menu())

    item.setProperty('IsPlayable', 'true')

    if not video_item.live:
        published_at = video_item.get_aired_utc()
        scheduled_start = video_item.get_scheduled_start_utc()
        use_dt = scheduled_start or published_at
        if use_dt:
            local_dt = utils.datetime_parser.utc_to_local(use_dt)
            item.setProperty('PublishedSince',
                             utils.to_unicode(utils.datetime_parser.datetime_to_since(context, local_dt)))
            item.setProperty('PublishedLocal', str(local_dt))
    else:
        item.setProperty('PublishedSince', context.localize('30539'))

    _info_labels = info_labels.create_from_item(video_item)

    if video_item.get_play_count() == 0:
        if video_item.get_start_percent():
            item.setProperty('StartPercent', video_item.get_start_percent())

        if video_item.get_start_time():
            item.setProperty('StartOffset', video_item.get_start_time())

    # This should work for all versions of XBMC/KODI.
    if 'duration' in _info_labels:
        duration = _info_labels['duration']
        del _info_labels['duration']
        item.addStreamInfo('video', {'duration': duration})

    item.setInfo(type='video', infoLabels=_info_labels)

    if video_item.get_channel_id():  # make channel_id property available for keymapping
        item.setProperty('channel_id', video_item.get_channel_id())

    if video_item.get_subscription_id():  # make subscription_id property available for keymapping
        item.setProperty('subscription_id', video_item.get_subscription_id())

    if video_item.get_playlist_id():  # make playlist_id property available for keymapping
        item.setProperty('playlist_id', video_item.get_playlist_id())

    if video_item.get_playlist_item_id():  # make playlist_item_id property available for keymapping
        item.setProperty('playlist_item_id', video_item.get_playlist_item_id())

    return item


def to_audio_item(context, audio_item):
    context.log_debug('Converting AudioItem |%s|' % audio_item.get_uri())
    major_version = context.get_system_version().get_version()[0]
    thumb = audio_item.get_image() if audio_item.get_image() else u'DefaultAudio.png'
    title = audio_item.get_name()
    fanart = ''
    settings = context.get_settings()
    if major_version > 17:
        item = xbmcgui.ListItem(label=utils.to_unicode(title), offscreen=True)
    else:
        item = xbmcgui.ListItem(label=utils.to_unicode(title))
    if audio_item.get_fanart() and settings.show_fanart():
        fanart = audio_item.get_fanart()
    if major_version <= 15:
        item.setArt({'thumb': thumb, 'fanart': fanart})
        item.setIconImage(thumb)
    else:
        item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})

    if audio_item.get_context_menu() is not None:
        item.addContextMenuItems(audio_item.get_context_menu(), replaceItems=audio_item.replace_context_menu())

    item.setProperty('IsPlayable', 'true')

    item.setInfo(type='music', infoLabels=info_labels.create_from_item(audio_item))
    return item


def to_uri_item(context, base_item):
    context.log_debug('Converting UriItem')
    major_version = context.get_system_version().get_version()[0]
    if major_version > 17:
        item = xbmcgui.ListItem(path=base_item.get_uri(), offscreen=True)
    else:
        item = xbmcgui.ListItem(path=base_item.get_uri())
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
