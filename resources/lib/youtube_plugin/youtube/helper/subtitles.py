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

    BASE_PATH = make_dirs(TEMP_PATH)

    def __init__(self, context, video_id, captions, headers=None):
        self.video_id = video_id
        self._context = context

        settings = context.get_settings()
        self.language = settings.get_language()
        self.pre_download = settings.subtitle_download()
        self.subtitle_languages = settings.subtitle_languages()

        if not headers and 'headers' in captions:
            headers = captions['headers']
            headers.pop('Authorization', None)
            headers.pop('Content-Length', None)
            headers.pop('Content-Type', None)
        self.headers = headers

        ui = self._context.get_ui()
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
        }

    def _unescape(self, text):
        try:
            text = unescape(text)
        except:
            self._context.log_debug('Subtitle unescape: failed to unescape text')
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
        self._context.log_debug('Subtitle get_subtitles: for setting |%s|' % str(languages))
        if languages == self.LANG_NONE:
            return []
        if languages == self.LANG_CURR:
            list_of_subs = []
            list_of_subs.extend(self._get(self.language))
            list_of_subs.extend(self._get(language=self.language.split('-')[0]))
            return list(set(list_of_subs))
        if languages == self.LANG_CURR_NO_ASR:
            list_of_subs = []
            list_of_subs.extend(self._get(self.language, no_asr=True))
            list_of_subs.extend(self._get(language=self.language.split('-')[0], no_asr=True))
            return list(set(list_of_subs))
        if languages == self.LANG_PROMPT:
            return self._prompt()
        if languages == self.LANG_CURR_FALLBACK:
            list_of_subs = []
            list_of_subs.extend(self._get(language=self.language))
            list_of_subs.extend(self._get(language=self.language.split('-')[0]))
            list_of_subs.extend(self._get('en'))
            list_of_subs.extend(self._get('en-US'))
            list_of_subs.extend(self._get('en-GB'))
            return list(set(list_of_subs))
        self._context.log_debug('Unknown language_enum: %s for subtitles' % str(languages))
        return []

    def _get_all(self, download=False):
        list_of_subs = []
        for track in self.caption_tracks:
            list_of_subs.extend(self._get(track.get('languageCode'),
                                          self._get_language_name(track),
                                          download=download))
        for track in self.translation_langs:
            list_of_subs.extend(self._get(track.get('languageCode'),
                                          self._get_language_name(track),
                                          download=download))
        return list(set(list_of_subs))

    def _prompt(self):
        captions = [(track.get('languageCode'),
                     self._get_language_name(track))
                    for track in self.caption_tracks]
        translations = [(track.get('languageCode'),
                         self._get_language_name(track))
                        for track in self.translation_langs]
        num_captions = len(captions)
        num_translations = len(translations)
        num_total = num_captions + num_translations

        if num_total:
            choice = self._context.get_ui().on_select(
                self._context.localize('subtitles.language'),
                [name for _, name in captions] +
                [name + ' *' for _, name in translations]
            )
            if choice == -1:
                self._context.log_debug('Subtitle selection cancelled')
                return []

            subtitle = None
            if 0 <= choice < num_captions:
                choice = captions[choice]
                subtitle = self._get(lang_code=choice[0], language=choice[1])
            elif num_captions <= choice < num_total:
                choice = translations[choice - num_captions]
                subtitle = self._get(lang_code=choice[0], language=choice[1])

            if subtitle:
                return subtitle
        self._context.log_debug('No subtitles found for prompt')
        return []

    def _get(self, lang_code='en', language=None, no_asr=False, download=None):
        filename = '.'.join((self.video_id, lang_code, 'srt'))
        if not self.BASE_PATH:
            self._context.log_error('Subtitles._get - '
                                    'unable to access temp directory')
            return []

        filepath = os.path.join(self.BASE_PATH, filename)
        if xbmcvfs.exists(filepath):
            self._context.log_debug('Subtitle exists for |{lang}| - |{file}|'
                                    .format(lang=lang_code, file=filepath))
            return [filepath]

        if download is None:
            download = self.pre_download

        caption_track = None
        asr_track = None
        has_translation = False
        for track in self.caption_tracks:
            if lang_code == track.get('languageCode'):
                if language is not None:
                    if language == self._get_language_name(track):
                        caption_track = track
                        break
                elif no_asr and (track.get('kind') == 'asr'):
                    continue
                elif track.get('kind') == 'asr':
                    asr_track = track
                else:
                    caption_track = track

        if (caption_track is None) and (asr_track is not None):
            caption_track = asr_track

        for lang in self.translation_langs:
            if lang_code == lang.get('languageCode'):
                has_translation = True
                break

        if (lang_code != self.defaults['lang_code'] and not has_translation
                and caption_track is None):
            self._context.log_debug('No subtitles found for: %s' % lang_code)
            return []

        subtitle_url = None
        if caption_track is not None:
            base_url = self._normalize_url(caption_track.get('baseUrl'))
            has_translation = False
        elif has_translation:
            base_url = self._normalize_url(
                self.defaults['caption'].get('baseUrl')
            )
        else:
            base_url = None

        if base_url:
            subtitle_url = self._set_query_param(
                base_url,
                ('type', 'track'),
                ('fmt', 'vtt'),
                ('tlang', lang_code) if has_translation else (None, None),
            )

        if not subtitle_url:
            self._context.log_debug('No subtitles found for: %s' % lang_code)
            return []

        if not download:
            return [subtitle_url]

        response = BaseRequestsClass().request(
            subtitle_url,
            headers=self.headers,
            error_info=('Failed to retrieve subtitles for: {lang}: {{exc}}'
                        .format(lang=lang_code))
        )
        response = response and response.text
        if not response:
            return []

        output = bytearray(self._unescape(response),
                           encoding='utf8',
                           errors='ignore')
        try:
            with xbmcvfs.File(filepath, 'w') as srt_file:
                success = srt_file.write(output)
        except (IOError, OSError):
            self._context.log_error('Subtitles._get - '
                                    'file write failed for: {file}'
                                    .format(file=filepath))
        if success:
            return [filepath]
        return []

    @staticmethod
    def _get_language_name(track):
        key = 'languageName' if 'languageName' in track else 'name'
        lang_name = track.get(key, {}).get('simpleText')
        if not lang_name:
            track_name = track.get(key, {}).get('runs', [{}])
            if isinstance(track_name, (list, tuple)) and len(track_name) >= 1:
                lang_name = track_name[0].get('text')

        if lang_name:
            return lang_name
        return None

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
