__author__ = 'bromix'

import xbmcgui

from ...items import VideoItem, AudioItem, UriItem
from . import info_labels


def to_video_item(context, video_item):
    context.log_debug('Converting VideoItem')
    item = xbmcgui.ListItem(label=video_item.get_name(),
                            iconImage=u'DefaultVideo.png',
                            thumbnailImage=video_item.get_image())

    # only set fanart is enabled
    settings = context.get_settings()
    if video_item.get_fanart() and settings.show_fanart():
        item.setProperty(u'fanart_image', video_item.get_fanart())
        pass
    if video_item.get_context_menu() is not None:
        item.addContextMenuItems(video_item.get_context_menu(), replaceItems=video_item.replace_context_menu())
        pass

    item.setProperty(u'IsPlayable', u'true')

    _info_labels = info_labels.create_from_item(context, video_item)

    # This should work for all versions of XBMC/KODI.
    if 'duration' in _info_labels:
        duration = _info_labels['duration']
        del _info_labels['duration']
        item.addStreamInfo('video', {'duration': duration})
        pass

    item.setInfo(type=u'video', infoLabels=_info_labels)
    return item


def to_audio_item(context, audio_item):
    context.log_debug('Converting AudioItem')
    item = xbmcgui.ListItem(label=audio_item.get_name(),
                            iconImage=u'DefaultAudio.png',
                            thumbnailImage=audio_item.get_image())

    # only set fanart is enabled
    settings = context.get_settings()
    if audio_item.get_fanart() and settings.show_fanart():
        item.setProperty(u'fanart_image', audio_item.get_fanart())
        pass
    if audio_item.get_context_menu() is not None:
        item.addContextMenuItems(audio_item.get_context_menu(), replaceItems=audio_item.replace_context_menu())
        pass

    item.setProperty(u'IsPlayable', u'true')

    item.setInfo(type=u'music', infoLabels=info_labels.create_from_item(context, audio_item))
    return item


def to_uri_item(context, base_item):
    context.log_debug('Converting UriItem')
    item = xbmcgui.ListItem(path=base_item.get_uri())
    item.setProperty(u'IsPlayable', u'true')
    return item


def to_item(context, base_item):
    if isinstance(base_item, UriItem):
        return to_uri_item(context, base_item)

    if isinstance(base_item, VideoItem):
        return to_video_item(context, base_item)

    if isinstance(base_item, AudioItem):
        return to_audio_item(context, base_item)

    return None