# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 anxdpanic
"""Builds a static DASH manifest (SegmentBase / byte ranges) from InnerTube adaptiveFormats."""
import re
from xml.sax.saxutils import escape, quoteattr

from .parser import text

SUPPORTED_VIDEO = ('avc1', 'vp9', 'vp09', 'av01')
SUPPORTED_AUDIO = ('mp4a', 'opus', 'ec-3', 'ac-3')
TRANSFER_SCHEME = 'urn:mpeg:mpegB:cicp:TransferCharacteristics'
CHANNEL_SCHEME = 'urn:mpeg:dash:23003:3:audio_channel_configuration:2011'
HDR_TRANSFER = ('COLOR_TRANSFER_CHARACTERISTICS_SMPTEST2084', 'COLOR_TRANSFER_CHARACTERISTICS_ARIB_STD_B67')


def _mime_codec(fmt):
    match = re.match(r'([^;]+);\s*codecs="([^"]+)"', fmt.get('mimeType', ''))
    if not match:
        return None, None
    return match.group(1), match.group(2)


def codec_family(codec):
    codec = codec.lower()
    if codec.startswith(('vp9', 'vp09')):
        return 'vp9'
    return codec.split('.')[0]


def is_hdr(fmt):
    return fmt.get('colorInfo', {}).get('transferCharacteristics') in HDR_TRANSFER


def select_video(formats, max_height=0, codec='any', allow_hdr=True):
    videos = []
    for fmt in formats:
        mime, codecs = _mime_codec(fmt)
        if not mime or not mime.startswith('video/') or not fmt.get('url'):
            continue
        if 'initRange' not in fmt or 'indexRange' not in fmt or fmt.get('drmFamilies'):
            continue
        if codec_family(codecs) not in ('avc1', 'vp9', 'av01'):
            continue
        if not allow_hdr and is_hdr(fmt):
            continue
        videos.append(fmt)
    if max_height:
        capped = [f for f in videos if min(f.get('height', 0), f.get('width', 0)) <= max_height]
        videos = capped or sorted(videos, key=lambda f: f.get('height', 0))[:1]
    if codec and codec != 'any':
        preferred = [f for f in videos if codec_family(_mime_codec(f)[1]) == codec]
        if preferred:
            videos = preferred
    return videos


def select_audio(formats):
    audios = []
    for fmt in formats:
        mime, codecs = _mime_codec(fmt)
        if not mime or not mime.startswith('audio/') or not fmt.get('url'):
            continue
        if 'initRange' not in fmt or 'indexRange' not in fmt or fmt.get('drmFamilies'):
            continue
        if codec_family(codecs) not in ('mp4a', 'opus', 'ec-3', 'ac-3'):
            continue
        audios.append(fmt)
    return audios


def _duration(formats, fallback):
    for fmt in formats:
        if fmt.get('approxDurationMs'):
            return int(fmt['approxDurationMs']) / 1000.0
    return float(fallback or 0)


def _representation(fmt, codecs, extra=''):
    attrs = ['id="%s"' % fmt['itag'], 'codecs=%s' % quoteattr(codecs),
             'bandwidth="%d"' % (fmt.get('bitrate') or fmt.get('averageBitrate') or 0)]
    if fmt.get('width'):
        attrs.append('width="%d" height="%d"' % (fmt['width'], fmt['height']))
    if fmt.get('fps'):
        attrs.append('frameRate="%d"' % fmt['fps'])
    if fmt.get('audioSampleRate'):
        attrs.append('audioSamplingRate="%s"' % fmt['audioSampleRate'])
    out = ['      <Representation %s>' % ' '.join(attrs)]
    if extra:
        out.append(extra)
    out.append('        <BaseURL>%s</BaseURL>' % escape(fmt['url']))
    out.append('        <SegmentBase indexRange="%s-%s">' % (fmt['indexRange']['start'], fmt['indexRange']['end']))
    out.append('          <Initialization range="%s-%s"/>' % (fmt['initRange']['start'], fmt['initRange']['end']))
    out.append('        </SegmentBase>')
    out.append('      </Representation>')
    return out


def _audio_language(fmt):
    track = fmt.get('audioTrack') or {}
    track_id = track.get('id', '')
    lang = track_id.split('.')[0] if track_id else 'und'
    return lang or 'und', track.get('displayName', ''), bool(track.get('audioIsDefault', not track))


def build(player_resp, max_height=0, codec='any', allow_hdr=True, audio_pref='original', ui_lang='en',
          subtitles=None):
    """Returns the MPD as a string, or None when there is nothing usable."""
    data = player_resp.get('streamingData', {})
    formats = data.get('adaptiveFormats', [])
    videos = select_video(formats, max_height, codec, allow_hdr)
    audios = select_audio(formats)
    if not videos or not audios:
        return None
    duration = _duration(videos + audios, player_resp.get('videoDetails', {}).get('lengthSeconds'))

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" '
           'type="static" minBufferTime="PT1.5S" mediaPresentationDuration="PT%.3fS">' % duration,
           '  <Period>']
    set_id = 0

    # Video: one AdaptationSet per container + codec family (+ HDR) so ISA can switch within it.
    groups = {}
    for fmt in videos:
        mime, codecs = _mime_codec(fmt)
        groups.setdefault((mime, codec_family(codecs), is_hdr(fmt)), []).append(fmt)
    for (mime, _family, hdr), group in sorted(groups.items(), key=lambda kv: -max(f.get('height', 0) for f in kv[1])):
        out.append('    <AdaptationSet id="%d" contentType="video" mimeType="%s" subsegmentAlignment="true" '
                   'startWithSAP="1" scanType="progressive">' % (set_id, mime))
        if hdr:
            # CICP transfer characteristics: 16 = PQ (HDR10), 18 = HLG
            pq = 'SMPTEST2084' in group[0]['colorInfo']['transferCharacteristics']
            out.append('      <SupplementalProperty schemeIdUri="%s" value="%s"/>'
                       % (TRANSFER_SCHEME, '16' if pq else '18'))
        for fmt in sorted(group, key=lambda f: (f.get('height', 0), f.get('bitrate', 0))):
            out.extend(_representation(fmt, _mime_codec(fmt)[1]))
        out.append('    </AdaptationSet>')
        set_id += 1

    # Audio: one AdaptationSet per language/track + codec; mark the preferred one as default/main.
    groups = {}
    for fmt in audios:
        mime, codecs = _mime_codec(fmt)
        lang, name, default = _audio_language(fmt)
        groups.setdefault((lang, name, default, mime, codec_family(codecs)), []).append(fmt)
    langs = {key[0] for key in groups}
    if audio_pref == 'kodi' and any(lang.split('-')[0] == ui_lang for lang in langs):
        is_main = lambda key: key[0].split('-')[0] == ui_lang  # noqa: E731
    else:
        is_main = lambda key: key[2]  # noqa: E731
    for key, group in sorted(groups.items(), key=lambda kv: (not is_main(kv[0]), kv[0][4] != 'opus')):
        lang, name, default, mime, family = key
        label = name or lang
        title = '%s (%s)' % (label, family.upper()) if name else family.upper()
        out.append('    <AdaptationSet id="%d" contentType="audio" mimeType="%s" lang="%s" name=%s%s%s '
                   'subsegmentAlignment="true" startWithSAP="1">'
                   % (set_id, mime, escape(lang), quoteattr(title),
                      ' default="true"' if is_main(key) else '',
                      ' original="true"' if default else ''))
        out.append('      <Label>%s</Label>' % escape(title))
        out.append('      <Role schemeIdUri="urn:mpeg:dash:role:2011" value="%s"/>'
                   % ('main' if is_main(key) else 'alternate'))
        for fmt in sorted(group, key=lambda f: f.get('bitrate', 0)):
            channels = fmt.get('audioChannels', 2)
            extra = '        <AudioChannelConfiguration schemeIdUri="%s" value="%d"/>' % (CHANNEL_SCHEME, channels)
            out.extend(_representation(fmt, _mime_codec(fmt)[1], extra))
        out.append('    </AdaptationSet>')
        set_id += 1

    # Subtitles: WebVTT side files, one AdaptationSet each.
    for index, sub in enumerate(subtitles or []):
        out.append('    <AdaptationSet id="%d" contentType="text" mimeType="text/vtt" lang="%s" name=%s%s%s>'
                   % (set_id, escape(sub['lang']), quoteattr(sub['label']),
                      ' forced="true"' if sub.get('forced') else '',
                      ' impaired="true"' if sub.get('kind') == 'asr' else ''))
        out.append('      <Label>%s</Label>' % escape(sub['label']))
        out.append('      <Role schemeIdUri="urn:mpeg:dash:role:2011" value="%s"/>'
                   % ('subtitle' if sub.get('kind') != 'asr' else 'caption'))
        out.append('      <Representation id="sub%d" bandwidth="0">' % index)
        out.append('        <BaseURL>%s</BaseURL>' % escape(sub['url']))
        out.append('      </Representation>')
        out.append('    </AdaptationSet>')
        set_id += 1

    out.append('  </Period>')
    out.append('</MPD>')
    return '\n'.join(out)


def subtitle_tracks(player_resp, include_asr=True, translate_to=None):
    """Caption tracks to offer: native tracks, auto-generated (optional) and machine translations
    into the requested languages when no native track exists."""
    renderer = player_resp.get('captions', {}).get('playerCaptionsTracklistRenderer', {})
    tracks = renderer.get('captionTracks', [])
    if not tracks:
        return []
    translatable = {t.get('languageCode') for t in renderer.get('translationLanguages', [])}
    names = {t.get('languageCode'): text(t.get('languageName')) for t in renderer.get('translationLanguages', [])}
    subs = []
    native = set()
    for track in tracks:
        kind = track.get('kind', '')
        if kind == 'asr' and not include_asr:
            continue
        lang = track.get('languageCode', 'und')
        label = text(track.get('name')) or lang
        if kind != 'asr':
            native.add(lang.split('-')[0])
        subs.append({'lang': lang, 'label': label, 'kind': kind, 'url': track['baseUrl'] + '&fmt=vtt'})
    source = next((t for t in tracks if t.get('kind') != 'asr' and t.get('isTranslatable', True)), None) or \
        next((t for t in tracks if t.get('isTranslatable', True)), None)
    for lang in translate_to or []:
        if not lang or lang.split('-')[0] in native or source is None:
            continue
        if translatable and lang not in translatable:
            match = [code for code in translatable if code.split('-')[0] == lang.split('-')[0]]
            if not match:
                continue
            lang = match[0]
        label = '%s (%s)' % (names.get(lang) or lang, 'auto-translated')
        subs.append({'lang': lang, 'label': label, 'kind': 'translated',
                     'url': source['baseUrl'] + '&fmt=vtt&tlang=' + lang})
    return subs

