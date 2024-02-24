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
from ...kodion.constants import TEMP_PATH
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

    def __init__(self, context, video_id, captions, headers=None):
        self.video_id = video_id
        self._context = context

        settings = context.get_settings()
        self.lang_code = settings.get_language()
        self.pre_download = settings.subtitle_download()
        self.subtitle_languages = settings.subtitle_languages()

        if not headers and 'headers' in captions:
            headers = captions['headers']
            headers.pop('Authorization', None)
            headers.pop('Content-Length', None)
            headers.pop('Content-Type', None)
        self.headers = headers

        ui = context.get_ui()
        self.prompt_override = (ui.get_property('prompt_for_subtitles')
                                == video_id)
        ui.clear_property('prompt_for_subtitles')

        self.renderer = captions.get('playerCaptionsTracklistRenderer', {})
        self.caption_tracks = self.renderer.get('captionTracks', [])
        self.translation_langs = self.renderer.get('translationLanguages', [])

        try:
            default_audio = self.renderer.get('defaultAudioTrackIndex')
            default_audio = self.renderer.get('audioTracks')[default_audio]
        except (IndexError, TypeError):
            default_audio = None

        self.defaults = {
            'caption': {},
            'lang_code': 'und',
            'is_asr': False,
            'translation_base': None,
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

        self.defaults = {
            'caption': default_caption,
            'lang_code': default_caption.get('languageCode') or 'und',
            'is_asr': default_caption.get('kind') == 'asr',
            'translation_base': None,
        }
        if default_caption.get('isTranslatable'):
            self.defaults['translation_base'] = default_caption
        else:
            for track in self.caption_tracks:
                if track.get('isTranslatable'):
                    self.defaults['translation_base'] = track
                    break

    def _unescape(self, text):
        try:
            text = unescape(text)
        except:
            self._context.log_error('Subtitles._unescape - failed: |{text}|'
                                    .format(text=text))
        return text

    def get_default_lang(self):
        return {
            'code': self.defaults['lang_code'],
            'is_asr': self.defaults['is_asr'],
        }

    def get_subtitles(self):
        if self.prompt_override:
            languages = self.LANG_PROMPT
        else:
            languages = self.subtitle_languages

        if languages == self.LANG_NONE:
            return None

        if languages == self.LANG_ALL:
            return self.get_all(sub_format='vtt')

        if languages == self.LANG_PROMPT:
            return self._prompt()

        no_asr = languages == self.LANG_CURR_NO_ASR
        if languages == self.LANG_CURR_FALLBACK:
            lang_codes = ('en', 'en-US', 'en-GB')
        else:
            lang_codes = {self.lang_code, self.lang_code.partition('-')[0]}

        subtitles = {}
        default_lang_code = self.defaults['lang_code']
        for lang_code in lang_codes:
            track, language, kind, is_translation = self._get_track(
                lang_code, no_asr=no_asr
            )
            if not track:
                continue
            subtitles[lang_code] = {
                'default': lang_code == default_lang_code,
                'kind': kind,
                'language': language,
                'mime_type': 'text/vtt',
                'url': self._get_url(
                    caption_track=track,
                    lang_code=lang_code,
                    is_translation=is_translation,
                    sub_format='vtt',
                ),
            }
        return subtitles

    def get_all(self, sub_format='vtt'):
        if sub_format == 'vtt':
            mime_type = 'text/vtt'
        else:
            sub_format = 'ttml'
            mime_type = 'application/ttml+xml'

        subtitles = {}

        default_lang_code = self.defaults['lang_code']
        for track in self.caption_tracks:
            track_lang_code = track.get('languageCode')
            track_language = self._get_language_name(track)
            url = self._get_url(
                caption_track=track,
                lang_code=track_lang_code,
                sub_format=sub_format,
                download=False,
            )
            if url:
                subtitles[track_lang_code] = {
                    'default': track_lang_code == default_lang_code,
                    'kind': track.get('kind'),
                    'language': track_language,
                    'mime_type': mime_type,
                    'url': url,
                }

        translation_base = self.defaults['translation_base']
        if translation_base:
            for track in self.translation_langs:
                track_lang_code = track.get('languageCode')
                if track_lang_code in subtitles:
                    continue
                track_language = self._get_language_name(track)
                url = self._get_url(
                    caption_track=translation_base,
                    lang_code=track_lang_code,
                    is_translation=True,
                    sub_format=sub_format,
                    download=False,
                )
                if url:
                    subtitles[track_lang_code] = {
                        'default': track_lang_code == default_lang_code,
                        'kind': 'translation',
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
        ] if self.defaults['translation_base'] else []
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
                kind = track.get('kind')
                choice = captions[choice - num_captions]
                is_translation = False
            elif num_captions <= choice < num_total:
                track = self.defaults['translation_base']
                kind = 'translation'
                choice = translations[choice - num_captions]
                is_translation = True
            else:
                self._context.log_debug('Subtitle selection cancelled')
                return None

            url = self._get_url(
                caption_track=track,
                lang_code=choice[0],
                is_translation=is_translation,
                sub_format='vtt',
            )
            if url:
                return {
                    choice[0]: {
                        'default': True,
                        'kind': kind,
                        'language': choice[1],
                        'mime_type': 'text/vtt',
                        'url': url,
                    },
                }
            self._context.log_debug('No subtitle found for selection: |{lang}|'
                                    .format(lang=choice[0]))
        return None

    def _get_url(self,
                 caption_track,
                 lang_code,
                 is_translation=False,
                 sub_format='vtt',
                 download=None):
        if download is None:
            download = self.pre_download
        if download:
            sub_format = 'vtt'
            filename = '.'.join((self.video_id, lang_code, 'srt'))
            if not self.BASE_PATH:
                self._context.log_error('Subtitles._get_url'
                                        ' - unable to access temp directory')
                return None

            filepath = os.path.join(self.BASE_PATH, filename)
            if xbmcvfs.exists(filepath):
                self._context.log_debug('Subtitles._get_url'
                                        ' - use existing: |{lang}: {file}|'
                                        .format(lang=lang_code, file=filepath))
                return filepath

        base_url = self._normalize_url(caption_track.get('baseUrl'))
        if not base_url:
            self._context.log_error('Subtitles._get_url - no url for: |{lang}|'
                                    .format(lang=lang_code))
            return None

        subtitle_url = self._set_query_param(
            base_url,
            ('type', 'track'),
            ('fmt', sub_format),
            ('tlang', lang_code) if is_translation else (None, None),
        )
        if not is_translation:
            self._context.log_debug('Subtitles._get_url: |{lang}: {url}|'
                                    .format(lang=lang_code, url=subtitle_url))

        if not download:
            return subtitle_url

        response = BaseRequestsClass().request(
            subtitle_url,
            headers=self.headers,
            error_info=('Subtitles._get_url - GET failed for: {lang}: {{exc}}'
                        .format(lang=lang_code))
        )
        response = response and response.text
        if not response:
            return None

        output = bytearray(self._unescape(response),
                           encoding='utf8',
                           errors='ignore')
        try:
            with xbmcvfs.File(filepath, 'w') as srt_file:
                success = srt_file.write(output)
        except (IOError, OSError):
            self._context.log_error('Subtitles._get_url'
                                    ' - write failed for: {file}'
                                    .format(file=filepath))
        if success:
            return filepath
        return None

    def _get_track(self,
                   lang_code='en',
                   language=None,
                   no_asr=False):
        caption_track = caption_language = caption_kind = None
        is_translation = False

        for track in self.caption_tracks:
            track_language = self._get_language_name(track)
            track_kind = track.get('kind')
            if lang_code == track.get('languageCode'):
                if language is not None:
                    if language == track_language:
                        caption_track = track
                        caption_language = track_language
                        caption_kind = track_kind
                        break
                elif no_asr and track_kind == 'asr':
                    continue
                else:
                    caption_track = track
                    caption_language = track_language
                    caption_kind = track_kind

        if not caption_track and self.defaults['translation_base']:
            for track in self.translation_langs:
                if lang_code == track.get('languageCode'):
                    caption_track = self.defaults['translation_base']
                    caption_language = self._get_language_name(track)
                    caption_kind = 'translation'
                    is_translation = True
                    break

        if caption_track:
            return caption_track, caption_language, caption_kind, is_translation

        self._context.log_debug('Subtitles._get - no subtitle for: |{lang}|'
                                .format(lang=lang_code))
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
