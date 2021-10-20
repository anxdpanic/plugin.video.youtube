# -*- coding: utf-8 -*-
"""
    Copyright (C) 2017-2021 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

import xbmcvfs
import requests
from ...kodion.utils import make_dirs

from six.moves.urllib_parse import parse_qs
from six.moves.urllib_parse import urlencode
from six.moves.urllib_parse import urlsplit
from six.moves.urllib_parse import urlunsplit

from six import PY2

try:
    from six.moves import html_parser

    unescape = html_parser.HTMLParser().unescape
except AttributeError:
    import html

    unescape = html.unescape


class Subtitles(object):
    LANG_NONE = 0
    LANG_PROMPT = 1
    LANG_CURR_FALLBACK = 2
    LANG_CURR = 3
    LANG_CURR_NO_ASR = 4

    BASE_PATH = 'special://temp/plugin.video.youtube/'
    SRT_FILE = ''.join([BASE_PATH, '%s.%s.srt'])

    def __init__(self, context, headers, video_id, captions):
        self.context = context
        self._verify = context.get_settings().verify_ssl()
        self.video_id = video_id
        self.language = context.get_settings().get_string('youtube.language', 'en_US').replace('_', '-')
        self.headers = headers.copy()

        self.caption_track = {}
        self.renderer = captions.get('playerCaptionsTracklistRenderer', {})
        self.caption_tracks = self.renderer.get('captionTracks', [])
        self.translation_langs = self.renderer.get('translationLanguages', [])

        default_audio = self.renderer.get('defaultAudioTrackIndex')
        if default_audio is not None:
            audio_tracks = self.renderer.get('audioTracks', [])
            try:
                audio_track = audio_tracks[default_audio]
            except:
                audio_track = None
            if audio_track:
                default_caption = audio_track.get('defaultCaptionTrackIndex')
                if default_caption is None:
                    default_caption = audio_track.get('captionTrackIndices')
                    if (default_caption is not None) and (isinstance(default_caption, list)):
                        default_caption = default_caption[0]
                if default_caption is not None:
                    try:
                        self.caption_track = self.caption_tracks[default_caption]
                    except:
                        pass

        ui = self.context.get_ui()
        self.prompt_override = ui.get_home_window_property('prompt_for_subtitles') == video_id
        ui.clear_home_window_property('prompt_for_subtitles')

    def srt_filename(self, sub_language):
        return self.SRT_FILE % (self.video_id, sub_language)

    def _write_file(self, _file, contents):
        if not make_dirs(self.BASE_PATH):
            self.context.log_debug('Failed to create directories: %s' % self.BASE_PATH)
            return False
        self.context.log_debug('Writing subtitle file: %s' % _file)
        try:
            f = xbmcvfs.File(_file, 'w')
            f.write(contents)
            f.close()
            return True
        except:
            self.context.log_debug('File write failed for: %s' % _file)
            return False

    def _unescape(self, text):
        try:
            text = text.decode('utf8', 'ignore')
        except:
            self.context.log_debug('Subtitle unescape: failed to decode utf-8')
        try:
            text = unescape(text)
        except:
            self.context.log_debug('Subtitle unescape: failed to unescape text')
        return text

    def get_subtitles(self):
        if self.prompt_override:
            languages = self.LANG_PROMPT
        else:
            languages = self.context.get_settings().subtitle_languages()
        self.context.log_debug('Subtitle get_subtitles: for setting |%s|' % str(languages))
        if languages == self.LANG_NONE:
            return []
        elif languages == self.LANG_CURR:
            list_of_subs = []
            list_of_subs.extend(self._get(self.language))
            list_of_subs.extend(self._get(language=self.language.split('-')[0]))
            return list(set(list_of_subs))
        elif languages == self.LANG_CURR_NO_ASR:
            list_of_subs = []
            list_of_subs.extend(self._get(self.language, no_asr=True))
            list_of_subs.extend(self._get(language=self.language.split('-')[0], no_asr=True))
            return list(set(list_of_subs))
        elif languages == self.LANG_PROMPT:
            return self._prompt()
        elif languages == self.LANG_CURR_FALLBACK:
            list_of_subs = []
            list_of_subs.extend(self._get(language=self.language))
            list_of_subs.extend(self._get(language=self.language.split('-')[0]))
            list_of_subs.extend(self._get('en'))
            list_of_subs.extend(self._get('en-US'))
            list_of_subs.extend(self._get('en-GB'))
            return list(set(list_of_subs))
        else:
            self.context.log_debug('Unknown language_enum: %s for subtitles' % str(languages))

    def _get_all(self):
        list_of_subs = []
        for language in self.translation_langs:
            list_of_subs.extend(self._get(language=language.get('languageCode')))
        return list(set(list_of_subs))

    def _prompt(self):
        tracks = [(track.get('languageCode'), self._get_language_name(track)) for track in self.caption_tracks]
        translations = [(track.get('languageCode'), self._get_language_name(track)) for track in self.translation_langs]
        languages = tracks + translations
        if languages:
            choice = self.context.get_ui().on_select(self.context.localize(30560), [language_name for language, language_name in languages])
            if choice != -1:
                return self._get(language=languages[choice][0], language_name=languages[choice][1])
            else:
                self.context.log_debug('Subtitle selection cancelled')
                return []
        else:
            self.context.log_debug('No subtitles found for prompt')
            return []

    def _get(self, language='en', language_name=None, no_asr=False):
        fname = self.srt_filename(language)
        if xbmcvfs.exists(fname):
            self.context.log_debug('Subtitle exists for: %s, filename: %s' % (language, fname))
            return [fname]

        caption_track = None
        asr_track = None
        has_translation = False
        for track in self.caption_tracks:
            if language == track.get('languageCode'):
                if language_name is not None:
                    if language_name == self._get_language_name(track):
                        caption_track = track
                        break
                else:
                    if no_asr and (track.get('kind') == 'asr'):
                        continue
                    elif track.get('kind') == 'asr':
                        asr_track = track
                    else:
                        caption_track = track

        if (caption_track is None) and (asr_track is not None):
            caption_track = asr_track

        for lang in self.translation_langs:
            if language == lang.get('languageCode'):
                has_translation = True
                break

        if (self.caption_track.get('languageCode') != language) and (not has_translation) and (caption_track is None):
            self.context.log_debug('No subtitles found for: %s' % language)
            return []

        subtitle_url = None
        if (caption_track is None) and has_translation:
            base_url = self.caption_track.get('baseUrl')
            if base_url:
                subtitle_url = self.set_query_param(base_url, 'type', 'track')
                subtitle_url = self.set_query_param(base_url, 'tlang', language)
        elif caption_track is not None:
            base_url = caption_track.get('baseUrl')
            if base_url:
                subtitle_url = self.set_query_param(base_url, 'type', 'track')

        if subtitle_url:
            subtitle_url = self.set_query_param(subtitle_url, 'fmt', 'vtt')
            self.context.log_debug('Subtitle url: %s' % subtitle_url)
            if not self.context.get_settings().subtitle_download():
                return [subtitle_url]
            else:
                result_auto = requests.get(subtitle_url, headers=self.headers,
                                           verify=self._verify, allow_redirects=True)

                if result_auto.text:
                    self.context.log_debug('Subtitle found for: %s' % language)
                    self._write_file(fname, bytearray(self._unescape(result_auto.text), encoding='utf8', errors='ignore'))
                    return [fname]
                else:
                    self.context.log_debug('Failed to retrieve subtitles for: %s' % language)
                    return []
        else:
            self.context.log_debug('No subtitles found for: %s' % language)
            return []

    def _get_language_name(self, track):
        key = 'languageName' if 'languageName' in track else 'name'
        lang_name = track.get(key, {}).get('simpleText')
        if not lang_name:
            track_name = track.get(key, {}).get('runs', [{}])
            if isinstance(track_name, list) and len(track_name) >= 1:
                lang_name = track_name[0].get('text')

        if lang_name:
            return self._decode_language_name(lang_name)

        return None

    @staticmethod
    def _decode_language_name(language_name):
        language_name = language_name.encode('raw_unicode_escape')

        if PY2:
            language_name = language_name.decode('utf-8')

        else:
            language_name = language_name.decode('raw_unicode_escape')

        return language_name

    @staticmethod
    def set_query_param(url, name, value):
        scheme, netloc, path, query_string, fragment = urlsplit(url)
        query_params = parse_qs(query_string)

        query_params[name] = [value]
        new_query_string = urlencode(query_params, doseq=True)
        if isinstance(scheme, bytes):
            new_query_string = new_query_string.encode('utf-8')

        return urlunsplit((scheme, netloc, path, new_query_string, fragment))
