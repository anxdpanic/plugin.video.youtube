# -*- coding: utf-8 -*-
"""
    Copyright (C) 2017-2021 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import os

from ...kodion.compatibility import (
    parse_qs,
    unescape,
    urlencode,
    urljoin,
    urlsplit,
    xbmcvfs,
)
from ...kodion.constants import PLAY_PROMPT_SUBTITLES, TEMP_PATH
from ...kodion.network import BaseRequestsClass
from ...kodion.utils import make_dirs


class Subtitles(object):
    LANG_NONE = 0
    LANG_PROMPT = 1
    LANG_CURR_FALLBACK = 2
    LANG_CURR = 3
    LANG_CURR_NO_ASR = 4
    LANG_ALL = 5

    BASE_PATH = make_dirs(TEMP_PATH)

    FORMATS = {
        '_default': None,
        'vtt': {
            'mime_type': 'text/vtt',
            'extension': 'vtt',
        },
        'ttml': {
            'mime_type': 'application/ttml+xml',
            'extension': 'ttml',
        },
    }

    def __init__(self, context, video_id):
        self.video_id = video_id
        self._context = context

        self.defaults = None
        self.headers = None
        self.renderer = None
        self.caption_tracks = None
        self.translation_langs = None

        settings = context.get_settings()
        self.pre_download = settings.subtitle_download()
        self.sub_selection = settings.get_subtitle_selection()

        if (not self.pre_download
                and settings.use_mpd_videos()
                and context.inputstream_adaptive_capabilities('ttml')):
            self.FORMATS['_default'] = 'ttml'
        else:
            self.FORMATS['_default'] = 'vtt'

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

        ui = context.get_ui()
        self.prompt_override = bool(ui.pop_property(PLAY_PROMPT_SUBTITLES))

    def load(self, captions, headers=None):
        if headers:
            headers.pop('Authorization', None)
            headers.pop('Content-Length', None)
            headers.pop('Content-Type', None)
        self.headers = headers

        self.renderer = captions.get('playerCaptionsTracklistRenderer', {})
        self.caption_tracks = self.renderer.get('captionTracks', [])
        self.translation_langs = self.renderer.get('translationLanguages', [])

        try:
            default_audio = self.renderer.get('defaultAudioTrackIndex')
            default_audio = self.renderer.get('audioTracks')[default_audio]
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

        default_caption = self.renderer.get(
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

    def _unescape(self, text):
        try:
            text = unescape(text)
        except:
            self._context.log_error('Subtitles._unescape - failed: |{text}|'
                                    .format(text=text))
        return text

    def get_lang_details(self):
        return {
            'default': self.defaults['default_lang'],
            'original': self.defaults['original_lang'],
            'is_asr': self.defaults['is_asr'],
        }

    def get_subtitles(self):
        if self.prompt_override:
            selection = self.LANG_PROMPT
        else:
            selection = self.sub_selection

        if selection == self.LANG_NONE:
            return None

        if selection == self.LANG_ALL:
            return self.get_all()

        if selection == self.LANG_PROMPT:
            return self._prompt()

        preferred_lang = self.preferred_lang
        original_lang = self.defaults['original_lang']

        allowed_langs = []
        for lang in preferred_lang:
            allowed_langs.append(lang)
            if '-' in lang:
                allowed_langs.append(lang.partition('-')[0])

        use_asr = None
        if selection == self.LANG_CURR_NO_ASR:
            use_asr = False
        elif selection == self.LANG_CURR_FALLBACK:
            for lang in (original_lang, 'en', 'en-US', 'en-GB', 'ASR'):
                if lang not in preferred_lang:
                    allowed_langs.append(lang)

        subtitles = {}
        has_asr = False
        for lang in allowed_langs:
            track, track_lang, track_language, track_kind = (
                self._get_track(lang, use_asr=use_asr)
            )
            if not track:
                continue
            if track_kind:
                if track_kind == 'asr':
                    if has_asr:
                        continue
                    has_asr = True
                track_key = '_'.join((track_lang, track_kind))
            else:
                track_key = track_lang
            url, mime_type = self._get_url(track=track, lang=track_lang)
            if url:
                subtitles[track_key] = {
                    'default': track_lang in preferred_lang,
                    'original': track_lang == original_lang,
                    'kind': track_kind,
                    'lang': track_lang,
                    'language': track_language,
                    'mime_type': mime_type,
                    'url': url,
                }
        return subtitles

    def get_all(self):
        subtitles = {}

        preferred_lang = self.preferred_lang
        original_lang = self.defaults['original_lang']

        for track in self.caption_tracks:
            track_lang = track.get('languageCode')
            track_kind = track.get('kind')
            track_language = self._get_language_name(track)
            url, mime_type = self._get_url(track=track)
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
                    'mime_type': mime_type,
                    'url': url,
                }

        base_track = self.defaults['base']
        base_lang = self.defaults['base_lang']
        if not base_track:
            return subtitles

        for track in self.translation_langs:
            track_lang = track.get('languageCode')
            if not track_lang or track_lang in subtitles:
                continue
            track_language = self._get_language_name(track)
            url, mime_type = self._get_url(track=base_track, lang=track_lang)
            if url:
                track_key = '_'.join((base_lang, track_lang))
                subtitles[track_key] = {
                    'default': track_lang in preferred_lang,
                    'original': track_lang == original_lang,
                    'kind': 'translation',
                    'lang': track_lang,
                    'language': track_language,
                    'mime_type': mime_type,
                    'url': url,
                }

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
            self._context.log_debug('No subtitles found for prompt')
        else:
            translation_lang = self._context.localize('subtitles.translation')
            choice = self._context.get_ui().on_select(
                self._context.localize('subtitles.language'),
                [name for _, name in captions] +
                [translation_lang % name for _, name in translations]
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
                self._context.log_debug('Subtitle selection cancelled')
                return None

            lang, language = choice

            url, mime_type = self._get_url(track=track, lang=lang)
            if url:
                return {
                    lang: {
                        'default': True,
                        'original': lang == self.defaults['original_lang'],
                        'kind': track_kind,
                        'lang': lang,
                        'language': language,
                        'mime_type': mime_type,
                        'url': url,
                    },
                }
            self._context.log_debug('No subtitle found for selection: |{lang}|'
                                    .format(lang=lang))
        return None

    def _get_url(self, track, lang=None):
        sub_format = self.FORMATS['_default']
        tlang = None
        base_lang = track.get('languageCode')
        kind = track.get('kind')
        if lang and lang != base_lang:
            tlang = lang
            lang = '-'.join((base_lang, tlang))
        elif kind == 'asr':
            lang = '-'.join((base_lang, kind))
            sub_format = 'vtt'
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
                self._context.log_error('Subtitles._get_url'
                                        ' - unable to access temp directory')
                return None, None

            filepath = os.path.join(self.BASE_PATH, filename)
            if xbmcvfs.exists(filepath):
                self._context.log_debug('Subtitles._get_url'
                                        ' - use existing: |{lang}: {file}|'
                                        .format(lang=lang, file=filepath))
                return filepath, self.FORMATS[sub_format]['mime_type']

        base_url = self._normalize_url(track.get('baseUrl'))
        if not base_url:
            self._context.log_error('Subtitles._get_url - no url for: |{lang}|'
                                    .format(lang=lang))
            return None, None

        subtitle_url = self._set_query_param(
            base_url,
            ('type', 'track'),
            ('fmt', sub_format),
            ('tlang', tlang) if tlang else (None, None),
        )
        if not tlang:
            self._context.log_debug('Subtitles._get_url: |{lang}: {url}|'
                                    .format(lang=lang, url=subtitle_url))

        if not download:
            return subtitle_url, self.FORMATS[sub_format]['mime_type']

        response = BaseRequestsClass(context=self._context).request(
            subtitle_url,
            headers=self.headers,
            error_info=('Subtitles._get_url - GET failed for: {lang}: {{exc}}'
                        .format(lang=lang))
        )
        response = response and response.text
        if not response:
            return None, None

        output = bytearray(self._unescape(response),
                           encoding='utf8',
                           errors='ignore')
        try:
            with xbmcvfs.File(filepath, 'w') as sub_file:
                success = sub_file.write(output)
        except (IOError, OSError):
            self._context.log_error('Subtitles._get_url'
                                    ' - write failed for: {file}'
                                    .format(file=filepath))
        if success:
            return filepath, self.FORMATS[sub_format]['mime_type']
        return None, None

    def _get_track(self,
                   lang='en',
                   language=None,
                   use_asr=None):
        sel_track = sel_lang = sel_language = sel_kind = None

        if lang == 'ASR':
            if use_asr is False:
                return None, None, None, None
            if use_asr is None:
                use_asr = True
                lang = None

        for track in self.caption_tracks:
            track_lang = track.get('languageCode')
            track_language = self._get_language_name(track)
            track_kind = track.get('kind')
            is_asr = track_kind == 'asr'
            if not lang or lang == track_lang:
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
                and not use_asr
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

        self._context.log_debug('Subtitles._get - no subtitle for: |{lang}|'
                                .format(lang=lang))
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
            if name:
                query_params[name] = [value]

        return components._replace(
            query=urlencode(query_params, doseq=True)
        ).geturl()

    @staticmethod
    def _normalize_url(url):
        if not url:
            url = ''
        elif url.startswith(('http://', 'https://')):
            pass
        elif url.startswith('//'):
            url = urljoin('https:', url)
        elif url.startswith('/'):
            url = urljoin('https://www.youtube.com', url)
        return url
