# -*- coding: utf-8 -*-
"""
    Copyright (C) 2017-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import os

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen

from .request_client import YouTubeRequestClient
from ...kodion import logging
from ...kodion.compatibility import parse_qs, urlencode, urlsplit, xbmcvfs
from ...kodion.constants import (
    PLAY_PROMPT_SUBTITLES,
    TEMP_PATH,
    TRANSLATION_LANGUAGES,
)
from ...kodion.utils.file_system import make_dirs


SUBTITLE_OPTIONS = {
    'none': 0,
    'prompt': 1,
    'preferred': 2,
    'fallback': 4,
    'no_asr': 8,
    'all': 16,
}

SUBTITLE_SELECTIONS = {
    0: SUBTITLE_OPTIONS['none'],
    1: SUBTITLE_OPTIONS['all']
       + SUBTITLE_OPTIONS['prompt'],
    2: SUBTITLE_OPTIONS['preferred']
       + SUBTITLE_OPTIONS['fallback'],
    3: SUBTITLE_OPTIONS['preferred']
       + SUBTITLE_OPTIONS['fallback']
       + SUBTITLE_OPTIONS['no_asr'],
    4: SUBTITLE_OPTIONS['preferred']
       + SUBTITLE_OPTIONS['no_asr'],
    5: SUBTITLE_OPTIONS['all'],
    'none': 0,
    'prompt': 1,
    'preferred_fallback_asr': 2,
    'preferred_fallback': 3,
    'preferred': 4,
    'all': 5,
}


class Subtitles(YouTubeRequestClient):
    log = logging.getLogger(__name__)

    BASE_PATH = make_dirs(TEMP_PATH)

    FORMATS = {
        # '_default': None,
        # '_fallback': None,
        'srt': {
            # 'mime_type': 'application/x-subrip',
            # Fake mimetype to allow ISA to decode as WebVTT
            'mime_type': 'text/vtt',
            'extension': 'srt',
            # Fake @codecs to allow ISA to decode as WebVTT
            'codec': 'wvtt',
        },
        'vtt': {
            'mime_type': 'text/vtt',
            'extension': 'vtt',
            'codec': 'wvtt',
        },
        'ttml': {
            'mime_type': 'application/ttml+xml',
            'extension': 'ttml',
            'codec': 'ttml',
        },
    }

    def __init__(self, context, video_id, use_mpd=None):
        settings = context.get_settings()
        super(Subtitles, self).__init__(
            context=context,
            language=settings.get_language(),
            region=settings.get_region(),
        )

        self.video_id = video_id

        self.defaults = None
        self.headers = None
        self.caption_tracks = None
        self.translation_langs = None

        self.pre_download = settings.subtitle_download()
        self.translate_locally = (self.pre_download
                                  and settings.subtitle_translate_locally())
        self.sub_selection = settings.get_subtitle_selection()
        stream_features = settings.stream_features()
        if use_mpd is None:
            use_mpd = settings.use_mpd_videos()

        use_isa = not self.pre_download and use_mpd
        self.use_isa = use_isa
        default_format = None
        fallback_format = None
        if use_isa:
            if ('ttml' in stream_features
                    and context.inputstream_adaptive_capabilities('ttml')):
                default_format = 'ttml'
                fallback_format = 'ttml'

            if context.inputstream_adaptive_capabilities('vtt'):
                if 'vtt' in stream_features:
                    default_format = default_format or 'vtt'
                    fallback_format = 'vtt'
                else:
                    default_format = default_format or 'srt'
                    fallback_format = 'srt'

        if not default_format or not use_isa:
            if ('vtt' in stream_features
                    and context.get_system_version().compatible(20)):
                default_format = 'vtt'
                fallback_format = 'vtt'
            else:
                default_format = 'srt'
                fallback_format = 'srt'

        self.FORMATS['_default'] = default_format
        self.FORMATS['_fallback'] = fallback_format

        kodi_sub_lang = context.get_subtitle_language()
        plugin_lang = settings.get_language()
        if not kodi_sub_lang and plugin_lang:
            self.preferred_lang = (plugin_lang,)
        elif kodi_sub_lang:
            if not plugin_lang:
                self.preferred_lang = (kodi_sub_lang,)
            elif (plugin_lang.partition('-')[0]
                  != kodi_sub_lang.partition('-')[0]):
                self.preferred_lang = (kodi_sub_lang, plugin_lang)
            else:
                self.preferred_lang = (kodi_sub_lang,)
        else:
            self.preferred_lang = ('en',)

        self.prompt_override = context.get_ui().pop_property(
            PLAY_PROMPT_SUBTITLES,
            as_bool=True,
        )

    def load(self, captions, headers=None):
        if headers:
            headers.pop('Authorization', None)
            headers.pop('Content-Length', None)
            headers.pop('Content-Type', None)
        self.headers = headers

        renderer = captions.get('playerCaptionsTracklistRenderer', {})
        self.caption_tracks = renderer.get('captionTracks', [])
        self.translation_langs = renderer.get('translationLanguages', [])
        self.translation_langs.extend(TRANSLATION_LANGUAGES)

        try:
            default_audio = renderer.get('defaultAudioTrackIndex')
            default_audio = renderer.get('audioTracks')[default_audio]
        except (IndexError, TypeError):
            default_audio = None

        self.defaults = {
            'default_lang': 'und',
            'original_lang': 'und',
            'is_asr': False,
            'base': None,
            'base_lang': None
        }
        if default_audio is None:
            return

        default_caption = renderer.get(
            'defaultTranslationSourceTrackIndices', [None]
        )[0]

        if default_caption is None and default_audio.get('hasDefaultTrack'):
            default_caption = default_audio.get('defaultCaptionTrackIndex')

        if default_caption is None:
            try:
                default_caption = default_audio.get('captionTrackIndices')[0]
            except (IndexError, TypeError):
                default_caption = 0

        try:
            default_caption = self.caption_tracks[default_caption] or {}
        except IndexError:
            return

        asr_caption = [
            track
            for track in self.caption_tracks
            if track.get('kind') == 'asr'
        ]
        original_caption = asr_caption and asr_caption[0] or {}

        self.defaults = {
            'default_lang': default_caption.get('languageCode') or 'und',
            'original_lang': original_caption.get('languageCode') or 'und',
            'is_asr': default_caption.get('kind') == 'asr',
            'base': None,
            'base_lang': None,
        }
        if original_caption.get('isTranslatable'):
            self.defaults['base'] = original_caption
            self.defaults['base_lang'] = self.defaults['original_lang']
        elif default_caption.get('isTranslatable'):
            self.defaults['base'] = default_caption
            self.defaults['base_lang'] = self.defaults['default_lang']
        else:
            for track in self.caption_tracks:
                if track.get('isTranslatable'):
                    base_lang = track.get('languageCode')
                    if base_lang:
                        self.defaults['base'] = track
                        self.defaults['base_lang'] = base_lang
                        break

    _MT_URL = 'https://translate.googleapis.com/translate_a/single'
    _MT_BATCH_CHARS = 4000

    def _get_local_translation(self, track, base_lang, tlang):
        if not self.BASE_PATH or not base_lang or not tlang:
            return None
        # Prefer subtitles in the language of the default caption track (the
        # original audio). Videos with auto-dubbed audio also have ASR tracks
        # in the dubbed languages and the first ASR track may be one of them.
        source = None
        source_langs = []
        for lang in (self.defaults.get('default_lang'), base_lang):
            if lang and lang != 'und' and lang not in source_langs:
                source_langs.append(lang)
        for lang in source_langs:
            candidates = [
                caption_track
                for caption_track in self.caption_tracks
                if caption_track.get('languageCode') == lang
                and caption_track.get('baseUrl')
                and caption_track.get('isTranslatable', True)
            ]
            candidates.sort(key=lambda t: t.get('kind') == 'asr')
            if candidates:
                source = candidates[0]
                break
        if not source:
            source = track
        base_lang = source.get('languageCode') or base_lang
        is_asr = source.get('kind') == 'asr'

        file_path = os.path.join(self.BASE_PATH, '.'.join((
            self.video_id,
            '-'.join(('mt', base_lang, tlang)),
            'vtt',
        )))
        if xbmcvfs.exists(file_path):
            try:
                with xbmcvfs.File(file_path) as sub_file:
                    if sub_file.read().startswith('WEBVTT'):
                        return file_path
            except (IOError, OSError):
                pass

        url = self._set_query_param(
            self._normalize_url(source.get('baseUrl')),
            ('fmt', 'json3'),
            ('tlang', None),
            ('xosf', None),
        )
        if not url:
            return None
        response = self.request(
            url,
            headers=self.headers,
            error_title='Local translation: source subtitle download failed',
        )
        if response is None:
            return None
        with response:
            try:
                events = (response.json() or {}).get('events') or []
            except ValueError:
                events = []
        cues = self._json3_cues(events, is_asr)
        if not cues:
            self.log.warning('Local translation: no cues in source subtitle')
            return None

        texts = self._mt_translate([cue[2] for cue in cues],
                                   base_lang,
                                   tlang)
        if not texts:
            return None

        output = ['WEBVTT', '']
        for (start, end, _), text in zip(cues, texts):
            output.append('{0} --> {1}'.format(self._vtt_time(start),
                                               self._vtt_time(end)))
            output.append(text)
            output.append('')
        try:
            with xbmcvfs.File(file_path, 'w') as sub_file:
                success = sub_file.write(bytearray('\n'.join(output),
                                                   encoding='utf8'))
        except (IOError, OSError):
            self.log.exception('Local translation: write failed')
            return None
        if not success:
            return None
        self.log.info(('Local translation created',
                       'Source: {lang!r} ({kind}), cues: {num}',
                       'File: {file}'),
                      lang=base_lang,
                      kind='asr' if is_asr else 'manual',
                      num=len(cues),
                      file=file_path)
        return file_path

    @staticmethod
    def _vtt_time(ms):
        ms = max(0, int(ms))
        return '{0:02d}:{1:02d}:{2:02d}.{3:03d}'.format(
            ms // 3600000, (ms // 60000) % 60, (ms // 1000) % 60, ms % 1000
        )

    @staticmethod
    def _json3_cues(events, is_asr):
        raw = []
        for event in events:
            segs = event.get('segs')
            if not segs or event.get('aAppend'):
                continue
            text = ''.join(seg.get('utf8', '') for seg in segs)
            text = ' '.join(text.split())
            if not text:
                continue
            start = int(event.get('tStartMs', 0))
            end = start + int(event.get('dDurationMs', 0))
            raw.append([start, end, text])
        raw.sort(key=lambda cue: cue[0])
        if not is_asr:
            return raw

        # Auto-generated lines roll and overlap: end each line when the next
        # one starts, then join lines into sentence-like cues for translation
        for idx in range(len(raw) - 1):
            next_start = raw[idx + 1][0]
            if raw[idx][1] > next_start > raw[idx][0]:
                raw[idx][1] = next_start
        merged = []
        current = None
        for start, end, text in raw:
            if current is None:
                current = [start, end, text]
                continue
            ends_sentence = current[2].rstrip('"\')]').endswith(
                ('.', '!', '?', '\u2026')
            )
            if (ends_sentence
                    or len(current[2]) + len(text) > 90
                    or end - current[0] > 7000
                    or start - current[1] > 1500):
                merged.append(current)
                current = [start, end, text]
            else:
                current[1] = end
                current[2] = ' '.join((current[2], text))
        if current:
            merged.append(current)
        return merged

    # YouTube and Google Translate use different codes for some languages
    _MT_LANG_MAP = {
        'iw': 'he',
        'jw': 'jv',
        'fil': 'tl',
        'zh-Hans': 'zh-CN',
        'zh-Hant': 'zh-TW',
        'zh-HK': 'zh-TW',
    }

    @classmethod
    def _mt_lang(cls, lang, source=False):
        if not lang:
            return 'auto'
        if lang in cls._MT_LANG_MAP:
            return cls._MT_LANG_MAP[lang]
        base_lang = lang.partition('-')[0]
        if source or base_lang not in ('pt', 'zh'):
            return cls._MT_LANG_MAP.get(base_lang, base_lang)
        return lang

    def _mt_request(self, text, source_lang, target_lang):
        # Plain urllib on purpose: Google answers requests made through the
        # addon requests session with HTTP 429, while plain requests succeed
        url = '?'.join((self._MT_URL, urlencode({
            'client': 'gtx',
            'sl': self._mt_lang(source_lang, source=True),
            'tl': self._mt_lang(target_lang),
            'dt': 't',
        })))
        request = Request(
            url,
            data=urlencode({'q': text}).encode('utf-8'),
            headers={'User-Agent': ('Mozilla/5.0 (X11; Linux aarch64) '
                                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                                    'Chrome/131.0.0.0 Safari/537.36')},
        )
        try:
            response = urlopen(request, timeout=15)
            data = json.loads(response.read().decode('utf-8'))
        except Exception as exc:
            self.log.warning('Local translation: request failed: %r', exc)
            return None
        try:
            return ''.join(part[0] for part in data[0] if part and part[0])
        except (IndexError, TypeError):
            return None

    def _mt_translate(self, texts, source_lang, target_lang):
        batches = []
        batch = []
        size = 0
        for text in texts:
            if batch and size + len(text) + 1 > self._MT_BATCH_CHARS:
                batches.append(batch)
                batch = []
                size = 0
            batch.append(text)
            size += len(text) + 1
        if batch:
            batches.append(batch)

        result = []
        for batch in batches:
            translated = self._mt_request('\n'.join(batch),
                                          source_lang,
                                          target_lang)
            if not translated:
                # Network error or blocked: give up, do not hammer the service
                return None
            lines = translated.split('\n')
            if len(lines) == len(batch):
                result.extend(line.strip() for line in lines)
                continue
            self.log.debug('Local translation: line mismatch, per cue')
            for text in batch:
                single = self._mt_request(text, source_lang, target_lang)
                if not single:
                    return None
                result.append(single.strip())
        return result

    def get_lang_details(self):
        return {
            'default': self.defaults['default_lang'],
            'original': self.defaults['original_lang'],
            'is_asr': self.defaults['is_asr'],
        }

    def get_subtitles(self):
        selection = self.sub_selection

        if self.prompt_override or selection == SUBTITLE_SELECTIONS['prompt']:
            return self._prompt()

        if selection == SUBTITLE_SELECTIONS['none']:
            return None

        if selection == SUBTITLE_SELECTIONS['all']:
            return self.get_all()

        selected_options = SUBTITLE_SELECTIONS[selection]

        allowed_langs = []

        preferred_lang = self.preferred_lang
        for lang in preferred_lang:
            allowed_langs.append(lang)
            if '-' in lang:
                allowed_langs.append(lang.partition('-')[0])

        use_asr = None
        if selected_options & SUBTITLE_OPTIONS['no_asr']:
            use_asr = False

        original_lang = self.defaults['original_lang']
        if selected_options & SUBTITLE_OPTIONS['fallback']:
            fallback_langs = (original_lang, 'en', 'en-US', 'en-GB')
            for lang in fallback_langs:
                if lang not in allowed_langs:
                    allowed_langs.append(lang)
            allowed_langs.append('ASR')
        else:
            fallback_langs = None

        subtitles = {}
        for lang in allowed_langs:
            if lang != 'ASR':
                track_details = self._get_track(lang, use_asr=use_asr)
            elif subtitles:
                continue
            else:
                track_details = self._get_track(
                    lang=None,
                    use_asr=(use_asr is None or None),
                    fallbacks=fallback_langs,
                )

            track, track_lang, track_language, track_kind = track_details
            if not track:
                continue
            if track_kind:
                track_key = '_'.join((track_lang, track_kind))
            else:
                track_key = track_lang
            url, sub_format = self._get_url(track=track, lang=track_lang)
            if url:
                subtitles[track_key] = {
                    'default': track_lang in preferred_lang,
                    'original': track_lang == original_lang,
                    'kind': track_kind,
                    'lang': track_lang,
                    'language': track_language,
                    'mime_type': sub_format['mime_type'],
                    'codec': sub_format['codec'],
                    'url': url,
                }
        if subtitles and self.use_isa:
            subtitles['_headers'] = self.headers
        return subtitles

    def get_all(self):
        subtitles = {}

        preferred_lang = self.preferred_lang
        original_lang = self.defaults['original_lang']

        for track in self.caption_tracks:
            track_lang = track.get('languageCode')
            track_kind = track.get('kind')
            track_language = self._get_language_name(track)
            url, sub_format = self._get_url(track=track)
            if url:
                if track_kind:
                    track_key = '_'.join((track_lang, track_kind))
                else:
                    track_key = track_lang
                subtitles[track_key] = {
                    'default': track_lang in preferred_lang,
                    'original': track_lang == original_lang,
                    'kind': track_kind,
                    'lang': track_lang,
                    'language': track_language,
                    'mime_type': sub_format['mime_type'],
                    'codec': sub_format['codec'],
                    'url': url,
                }

        base = self.defaults['base']
        base_lang = self.defaults['base_lang']
        if base:
            for track in self.translation_langs:
                track_lang = track.get('languageCode')
                if not track_lang or track_lang in subtitles:
                    continue
                track_language = self._get_language_name(track)
                url, sub_format = self._get_url(track=base, lang=track_lang)
                if url:
                    track_key = '_'.join((base_lang, track_lang))
                    subtitles[track_key] = {
                        'default': track_lang in preferred_lang,
                        'original': track_lang == original_lang,
                        'kind': 'translation',
                        'lang': track_lang,
                        'language': track_language,
                        'mime_type': sub_format['mime_type'],
                        'codec': sub_format['codec'],
                        'url': url,
                    }

        if subtitles and self.use_isa:
            subtitles['_headers'] = self.headers
        return subtitles

    def _prompt(self):
        captions = [
            (track.get('languageCode'), self._get_language_name(track))
            for track in self.caption_tracks
        ]
        translations = [
            (track.get('languageCode'), self._get_language_name(track))
            for track in self.translation_langs
        ] if self.defaults['base'] else []
        num_captions = len(captions)
        num_translations = len(translations)
        num_total = num_captions + num_translations

        if not num_total:
            self.log.debug('No subtitles found for prompt')
        else:
            localize = self._context.localize
            choice = self._context.get_ui().on_select(
                localize('subtitles.language'),
                [name for _, name in captions] +
                [localize('subtitles.translation.x', name)
                 for _, name in translations]
            )

            if 0 <= choice < num_captions:
                track = self.caption_tracks[choice]
                track_kind = track.get('kind')
                choice = captions[choice - num_captions]
            elif num_captions <= choice < num_total:
                track = self.defaults['base']
                track_kind = 'translation'
                choice = translations[choice - num_captions]
            else:
                self.log.debug('Subtitle selection cancelled')
                return False

            lang, language = choice
            self.log.debug('Selected: %r', lang)
            url, sub_format = self._get_url(track=track, lang=lang)
            if url:
                subtitle = {
                    lang: {
                        'default': True,
                        'original': lang == self.defaults['original_lang'],
                        'kind': track_kind,
                        'lang': lang,
                        'language': language,
                        'mime_type': sub_format['mime_type'],
                        'codec': sub_format['codec'],
                        'url': url,
                    },
                }
                if self.use_isa:
                    subtitle['_headers'] = self.headers
                return subtitle
        return None

    def _get_url(self, track, lang=None):
        sub_format = self.FORMATS.get('_default')
        if not sub_format:
            self.log.error_trace('Invalid subtitle options selected')
            return None, None

        tlang = None
        base_lang = track.get('languageCode')
        kind = track.get('kind')
        if lang and lang != base_lang:
            tlang = lang
            lang = '-'.join((base_lang, tlang))
            # YouTube may refuse requests for auto-translated subtitles
            # (HTTP 429, see #1250). If enabled, download the source track and
            # translate it with Google Translate instead.
            if self.translate_locally:
                local_path = self._get_local_translation(track,
                                                         base_lang,
                                                         tlang)
                if local_path:
                    return local_path, self.FORMATS['vtt']
        elif kind == 'asr':
            lang = '-'.join((base_lang, kind))
            sub_format = self.FORMATS['_fallback']
        else:
            lang = base_lang

        download = self.pre_download
        if download:
            filename = '.'.join((
                self.video_id,
                lang,
                self.FORMATS[sub_format]['extension']
            ))
            if not self.BASE_PATH:
                self.log.error_trace('Unable to access temp directory')
                return None, None

            file_path = os.path.join(self.BASE_PATH, filename)
            if xbmcvfs.exists(file_path):
                self.log.debug(('Use existing subtitle for: {lang!r}',
                                'File: {file}'),
                               lang=lang,
                               file=file_path)
                return file_path, self.FORMATS[sub_format]

        base_url = self._normalize_url(track.get('baseUrl'))
        if not base_url:
            self.log.error_trace('No URL for: %r', lang)
            return None, None

        subtitle_url = self._set_query_param(
            base_url,
            ('fmt', sub_format),
            ('tlang', tlang),
            ('xosf', None),
        )
        self.log.debug(('Found new subtitle for: {lang!r}',
                        'URL: {url!u}'),
                       lang=lang,
                       url=subtitle_url)

        if not download:
            return subtitle_url, self.FORMATS[sub_format]

        response = self.request(
            subtitle_url,
            headers=self.headers,
            error_title='Failed to download subtitle for: {sub_lang!r}',
            sub_lang=lang,
        )
        if response is None:
            return None, None
        with response:
            response_text = response.text
            if not response_text:
                return None, None
            # Do not save an HTML error page (e.g. HTTP 429) as subtitles
            if response_text.lstrip()[:1] == '<' and sub_format != 'ttml':
                self.log.warning('Subtitle response is not a subtitle file'
                                 ' for: %r', lang)
                return None, None

        output = bytearray(self._unescape(response_text),
                           encoding='utf8',
                           errors='ignore')
        try:
            with xbmcvfs.File(file_path, 'w') as sub_file:
                success = sub_file.write(output)
        except (IOError, OSError):
            self.log.exception(('Write failed for: {lang!r}',
                                'File: {file}'),
                               lang=lang,
                               file=file_path)
        if success:
            return file_path, self.FORMATS[sub_format]
        return None, None

    def _get_track(self,
                   lang='en',
                   language=None,
                   use_asr=None,
                   fallbacks=None):
        sel_track = sel_lang = sel_language = sel_kind = None

        for track in self.caption_tracks:
            track_lang = track.get('languageCode')
            track_language = self._get_language_name(track)
            track_kind = track.get('kind')
            is_asr = track_kind == 'asr'
            if lang and lang != track_lang:
                continue
            if not lang and fallbacks and track_lang not in fallbacks:
                continue
            if language is not None:
                if language == track_language:
                    sel_track = track
                    sel_lang = track_lang
                    sel_language = track_language
                    sel_kind = track_kind
                    break
            elif (use_asr is False and is_asr) or (use_asr and not is_asr):
                continue
            elif (not sel_track
                  or (use_asr is None and sel_kind == 'asr')
                  or (use_asr and is_asr)):
                sel_track = track
                sel_lang = track_lang
                sel_language = track_language
                sel_kind = track_kind

        if (not sel_track
                and lang
                and use_asr is None
                and self.defaults['base']
                and lang != self.defaults['base_lang']):
            for track in self.translation_langs:
                if lang == track.get('languageCode'):
                    sel_track = self.defaults['base']
                    sel_lang = lang
                    sel_language = self._get_language_name(track)
                    sel_kind = 'translation'
                    break

        if sel_track:
            return sel_track, sel_lang, sel_language, sel_kind

        self.log.debug('No subtitle for: %r', lang)
        return None, None, None, None

    @staticmethod
    def _get_language_name(track):
        lang_obj = None
        if 'languageName' in track:
            lang_obj = track['languageName']
        elif 'name' in track:
            lang_obj = track['name']

        if not lang_obj:
            return None

        lang_name = lang_obj.get('simpleText')
        if lang_name:
            return lang_name

        track_name = lang_obj.get('runs')
        if isinstance(track_name, (list, tuple)) and len(track_name) >= 1:
            lang_name = track_name[0].get('text')

        return lang_name

    @staticmethod
    def _set_query_param(url, *pairs):
        if not url or not pairs:
            return url

        num_params = len(pairs)
        if not num_params:
            return url
        if not isinstance(pairs[0], (list, tuple)):
            if num_params >= 2:
                pairs = zip(*[iter(pairs)] * 2)
            else:
                return url

        components = urlsplit(url)
        query_params = parse_qs(components.query)

        for name, value in pairs:
            if not name:
                continue
            if isinstance(value, (list, tuple)):
                query_params[name] = value
            elif value is not None:
                query_params[name] = [value]
            elif name in query_params:
                del query_params[name]

        return components._replace(
            query=urlencode(query_params, doseq=True)
        ).geturl()
