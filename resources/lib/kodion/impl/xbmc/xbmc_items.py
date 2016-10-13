__author__ = 'bromix'

import xbmc, xbmcgui
import urllib, re

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
    if video_item.use_dash():
        item.setProperty('inputstream.mpd.license_type', '')
        item.setProperty('inputstream.mpd.license_key', '')
        item.setProperty('inputstreamaddon', 'inputstream.mpd')
    else:
        item.setProperty('inputstreamaddon', '')

    item.setProperty(u'IsPlayable', u'true')

    video_id = context.get_param('video_id')
    if video_id is not None:
        item.setSubtitles(download_subs(video_id))

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


def download_subs(video_id):
    subs = []
    sub_list = ("http://www.youtube.com/api/timedtext?type=list&v=%s" % (video_id))

    sock = urllib.urlopen(sub_list)
    xml = sock.read()
    sock.close()

    sub_langs = re.compile('lang_code=["](.*?)["]', re.IGNORECASE).findall(xml)
    for lang in sub_langs:
        sub_url = ("http://www.youtube.com/api/timedtext?fmt=vtt&v=%s&lang=%s" % (video_id, lang))
        sub_file = xbmc.translatePath('special://temp/%s.srt' % (lang))
        urllib.urlretrieve(sub_url, sub_file)
        subs.append(sub_file)
    return subs
