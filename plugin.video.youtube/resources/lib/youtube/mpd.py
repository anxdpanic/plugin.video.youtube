# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 plugin.video.youtube
"""Builds a static DASH manifest (SegmentBase / byte ranges) from InnerTube adaptiveFormats."""
import re
from functools import partial
from xml.sax.saxutils import escape, quoteattr

from .parser import text

# Codec families (see codec_family) a manifest offers.
SUPPORTED_VIDEO = ('avc1', 'vp9', 'av01')
SUPPORTED_AUDIO = ('mp4a', 'opus', 'ec-3', 'ac-3')
TRANSFER_SCHEME = 'urn:mpeg:mpegB:cicp:TransferCharacteristics'
CHANNEL_SCHEME = 'urn:mpeg:dash:23003:3:audio_channel_configuration:2011'
HDR_TRANSFER = ('COLOR_TRANSFER_CHARACTERISTICS_SMPTEST2084', 'COLOR_TRANSFER_CHARACTERISTICS_ARIB_STD_B67')
# YouTube reports 23.976, 29.97 and 59.94 fps as 24, 30 and 60.
FRACTIONAL_FPS = {24: '24000/1001', 30: '30000/1001', 60: '60000/1001'}


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


def _usable(fmt, media, families):
    """A stream of this media type ('video'/'audio') in a supported codec that a manifest can address
    by byte ranges: a direct URL, init and index ranges, and no DRM."""
    mime, codecs = _mime_codec(fmt)
    return bool(mime and mime.startswith(media + '/') and fmt.get('url') and 'initRange' in fmt
                and 'indexRange' in fmt and not fmt.get('drmFamilies') and codec_family(codecs) in families)


def quality_of(fmt):
    """(height, fps, hdr, codec family) of a video format. Height is the short side, so a vertical
    1080x1920 is 1080. The codec is part of it because not every device decodes every codec: a low-end
    one may only manage H.264, or play VP9 or AV1 only at lower resolutions."""
    height = min(fmt.get('height', 0), fmt.get('width', 0)) or fmt.get('height', 0)
    return height, fmt.get('fps', 0), is_hdr(fmt), codec_family(_mime_codec(fmt)[1])


def qualities(formats, codec='any', allow_hdr=True):
    """The qualities a manifest can offer, as quality_of() tuples: tallest first, then highest frame rate,
    HDR before SDR, and at each of those the `codec` preference first, then AV1, VP9 and H.264."""
    order = [codec] + [c for c in reversed(SUPPORTED_VIDEO) if c != codec]
    found = {quality_of(f) for f in select_video(formats, 0, 'any', allow_hdr)}
    return sorted(found, key=lambda q: (-q[0], -q[1], not q[2], order.index(q[3]) if q[3] in order else len(order)))


def bitrate_of(formats, quality):
    """Bits per second of a quality's video, for telling a slow connection what it needs: the average
    rate where YouTube gives one (the peak rate otherwise), the highest when several formats share it."""
    rates = [f.get('averageBitrate') or f.get('bitrate') or 0
             for f in select_video(formats, quality=quality)]
    return int(max(rates, default=0))


def select_video(formats, max_height=0, codec='any', allow_hdr=True, quality=None):
    """The video formats to offer. `quality` (a quality_of() tuple) keeps only that one quality."""
    videos = [f for f in formats if _usable(f, 'video', SUPPORTED_VIDEO) and (allow_hdr or not is_hdr(f))]
    if quality:
        videos = [f for f in videos if quality_of(f) == tuple(quality)]
    if max_height:
        capped = [f for f in videos if min(f.get('height', 0), f.get('width', 0)) <= max_height]
        videos = capped or sorted(videos, key=lambda f: f.get('height', 0))[:1]
    if codec and codec != 'any':
        preferred = [f for f in videos if codec_family(_mime_codec(f)[1]) == codec]
        if preferred:
            videos = preferred
    return videos


def _is_drc(fmt):
    """YouTube's stable volume copy of an audio stream, which shares the original's itag."""
    return bool(fmt.get('isDrc')) or 'drc%3D1' in fmt.get('url', '')


def _audio_key(fmt):
    return fmt['itag'], (fmt.get('audioTrack') or {}).get('id')


def select_audio(formats):
    """Usable audio, leaving out stable volume copies of streams that are also offered as they are."""
    audios = [f for f in formats if _usable(f, 'audio', SUPPORTED_AUDIO)]
    plain = {_audio_key(f) for f in audios if not _is_drc(f)}
    return [f for f in audios if not (_is_drc(f) and _audio_key(f) in plain)]


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
        attrs.append('frameRate="%s"' % FRACTIONAL_FPS.get(fmt['fps'], fmt['fps']))
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


def _group_videos(videos):
    """One group per container + codec family (+ HDR) so ISA can switch within it; tallest first."""
    groups = {}
    for fmt in videos:
        mime, codecs = _mime_codec(fmt)
        groups.setdefault((mime, codec_family(codecs), is_hdr(fmt)), []).append(fmt)
    return sorted(groups.items(), key=lambda kv: -max(f.get('height', 0) for f in kv[1]))


def _video_set(set_id, mime, hdr, group):
    out = ['    <AdaptationSet id="%d" contentType="video" mimeType="%s" subsegmentAlignment="true" '
           'startWithSAP="1" scanType="progressive">' % (set_id, mime)]
    if hdr:
        # CICP transfer characteristics: 16 = PQ (HDR10), 18 = HLG
        pq = 'SMPTEST2084' in group[0]['colorInfo']['transferCharacteristics']
        out.append('      <SupplementalProperty schemeIdUri="%s" value="%s"/>'
                   % (TRANSFER_SCHEME, '16' if pq else '18'))
    for fmt in sorted(group, key=lambda f: (f.get('height', 0), f.get('bitrate', 0))):
        out.extend(_representation(fmt, _mime_codec(fmt)[1]))
    out.append('    </AdaptationSet>')
    return out


def _group_audios(audios):
    """One group per language/track + codec: {(lang, name, original, mime, family): [formats]}."""
    groups = {}
    for fmt in audios:
        mime, codecs = _mime_codec(fmt)
        lang, name, default = _audio_language(fmt)
        groups.setdefault((lang, name, default, mime, codec_family(codecs)), []).append(fmt)
    return groups


def _main_audio_test(groups, audio_pref, ui_lang):
    """A predicate for the audio group to play by default: Kodi's language when asked and offered, else original."""
    langs = {key[0] for key in groups}
    if audio_pref == 'kodi' and any(lang.split('-')[0] == ui_lang for lang in langs):
        return lambda key: key[0].split('-')[0] == ui_lang
    return lambda key: key[2]


def _audio_set(set_id, key, group, main):
    lang, name, default, mime, family = key
    title = '%s (%s)' % (name, family.upper()) if name else family.upper()
    out = ['    <AdaptationSet id="%d" contentType="audio" mimeType="%s" lang="%s" name=%s%s%s '
           'subsegmentAlignment="true" startWithSAP="1">'
           % (set_id, mime, escape(lang), quoteattr(title),
              ' default="true"' if main else '', ' original="true"' if default else ''),
           '      <Label>%s</Label>' % escape(title),
           '      <Role schemeIdUri="urn:mpeg:dash:role:2011" value="%s"/>' % ('main' if main else 'alternate')]
    for fmt in sorted(group, key=lambda f: f.get('bitrate', 0)):
        channels = fmt.get('audioChannels', 2)
        extra = '        <AudioChannelConfiguration schemeIdUri="%s" value="%d"/>' % (CHANNEL_SCHEME, channels)
        out.extend(_representation(fmt, _mime_codec(fmt)[1], extra))
    out.append('    </AdaptationSet>')
    return out


def _subtitle_set(set_id, index, sub):
    """A WebVTT side file as an AdaptationSet of its own."""
    asr = sub.get('kind') == 'asr'
    return ['    <AdaptationSet id="%d" contentType="text" mimeType="text/vtt" lang="%s" name=%s%s%s>'
            % (set_id, escape(sub['lang']), quoteattr(sub['label']),
               ' forced="true"' if sub.get('forced') else '', ' impaired="true"' if asr else ''),
            '      <Label>%s</Label>' % escape(sub['label']),
            '      <Role schemeIdUri="urn:mpeg:dash:role:2011" value="%s"/>' % ('caption' if asr else 'subtitle'),
            '      <Representation id="sub%d" bandwidth="0">' % index,
            '        <BaseURL>%s</BaseURL>' % escape(sub['url']),
            '      </Representation>',
            '    </AdaptationSet>']


def _adaptation_sets(videos, audios, audio_pref, ui_lang, subtitles):
    """A maker per AdaptationSet in manifest order (video, audio with the default first, subtitles);
    each takes the set's id and returns its lines."""
    for (mime, _family, hdr), group in _group_videos(videos):
        yield partial(_video_set, mime=mime, hdr=hdr, group=group)
    groups = _group_audios(audios)
    is_main = _main_audio_test(groups, audio_pref, ui_lang)
    for key, group in sorted(groups.items(), key=lambda kv: (not is_main(kv[0]), kv[0][4] != 'opus')):
        yield partial(_audio_set, key=key, group=group, main=is_main(key))
    for index, sub in enumerate(subtitles or []):
        yield partial(_subtitle_set, index=index, sub=sub)


def _mpd_open(duration):
    return ['<?xml version="1.0" encoding="UTF-8"?>',
            '<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" '
            'type="static" minBufferTime="PT1.5S" mediaPresentationDuration="PT%.3fS">' % duration,
            '  <Period>']


def build(player_resp, max_height=0, codec='any', allow_hdr=True, audio_pref='original', ui_lang='en',
          subtitles=None, quality=None):
    """Returns the MPD as a string, or None when there is nothing usable."""
    formats = player_resp.get('streamingData', {}).get('adaptiveFormats', [])
    videos = select_video(formats, max_height, codec, allow_hdr, quality)
    audios = select_audio(formats)
    if not videos or not audios:
        return None
    out = _mpd_open(_duration(videos + audios, player_resp.get('videoDetails', {}).get('lengthSeconds')))
    for set_id, make in enumerate(_adaptation_sets(videos, audios, audio_pref, ui_lang, subtitles)):
        out.extend(make(set_id))
    out.extend(['  </Period>', '</MPD>'])
    return '\n'.join(out)


def _translation_source(tracks):
    """The track to machine-translate from: a translatable native track, else any translatable one."""
    return next((t for t in tracks if t.get('kind') != 'asr' and t.get('isTranslatable', True)), None) or \
        next((t for t in tracks if t.get('isTranslatable', True)), None)


def _translatable_code(lang, translatable):
    """YouTube's code for a wanted language ('pt' may only be offered as 'pt-PT'), or None."""
    if not translatable or lang in translatable:
        return lang
    return next((code for code in translatable if code.split('-')[0] == lang.split('-')[0]), None)


def _native_subtitles(tracks, include_asr):
    for track in tracks:
        kind = track.get('kind', '')
        if kind == 'asr' and not include_asr:
            continue
        lang = track.get('languageCode', 'und')
        yield {'lang': lang, 'label': text(track.get('name')) or lang, 'kind': kind,
               'url': track['baseUrl'] + '&fmt=vtt'}


def _translated_subtitles(renderer, source, native, translate_to):
    languages = renderer.get('translationLanguages', [])
    translatable = {t.get('languageCode') for t in languages}
    names = {t.get('languageCode'): text(t.get('languageName')) for t in languages}
    for wanted in translate_to or []:
        if not wanted or wanted.split('-')[0] in native:
            continue
        lang = _translatable_code(wanted, translatable)
        if lang:
            yield {'lang': lang, 'label': '%s (%s)' % (names.get(lang) or lang, 'auto-translated'),
                   'kind': 'translated', 'url': source['baseUrl'] + '&fmt=vtt&tlang=' + lang}


def subtitle_tracks(player_resp, include_asr=True, translate_to=None):
    """Caption tracks to offer: native tracks, auto-generated (optional) and machine translations
    into the requested languages when no native track exists."""
    renderer = player_resp.get('captions', {}).get('playerCaptionsTracklistRenderer', {})
    tracks = renderer.get('captionTracks', [])
    if not tracks:
        return []
    subs = list(_native_subtitles(tracks, include_asr))
    native = {sub['lang'].split('-')[0] for sub in subs if sub['kind'] != 'asr'}
    source = _translation_source(tracks)
    if source is not None:
        subs.extend(_translated_subtitles(renderer, source, native, translate_to))
    return subs
