# -*- coding: utf-8 -*-
import xbmcvfs
import HTMLParser
import requests


class Subtitles(object):
    LANG_NONE = 0
    LANG_AUTO = 1
    LANG_CURR = 2
    LANG_PROMPT = 3

    SRT_FILE = 'special://temp/temp/%s.%s.srt'

    def __init__(self, context, video_id, captions):
        self.context = context
        self._verify = context.get_settings().get_bool('simple.requests.ssl.verify', False)
        self.video_id = video_id
        self.language = context.get_settings().get_string('youtube.language', 'en_US').replace('_', '-')
        self.headers = {'Host': 'www.youtube.com',
                        'Connection': 'keep-alive',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 '
                                      '(KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36',
                        'Accept': '*/*',
                        'DNT': '1',
                        'Referer': 'https://www.youtube.com/tv',
                        'Accept-Encoding': 'gzip, deflate',
                        'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'}

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

    def srt_filename(self, sub_language):
        return self.SRT_FILE % (self.video_id, sub_language)

    def _write_file(self, _file, contents):
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
            text = HTMLParser.HTMLParser().unescape(text)
        except:
            self.context.log_debug('Subtitle unescape: failed to unescape text')
        return text

    def get_subtitles(self):
        languages = self.context.get_settings().subtitle_languages()
        if languages == self.LANG_NONE:
            return []
        elif languages == self.LANG_CURR:
            list_of_subs = []
            list_of_subs.extend(self._get(self.language))
            list_of_subs.extend(self._get(language=self.language.split('-')[0]))
            return list(set(list_of_subs))
        elif languages == self.LANG_PROMPT:
            return self._prompt()
        elif languages == self.LANG_AUTO:
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
        tracks = [(track.get('languageCode'), track.get('name', {}).get('simpleText')) for track in self.caption_tracks]
        translations = [(track.get('languageCode'), track.get('languageName', {}).get('simpleText')) for track in self.translation_langs]
        languages = tracks + translations
        if languages:
            choice = self.context.get_ui().on_select(self.context.localize(30560), [language_name for language, language_name in languages])
            if choice != -1:
                return self._get(languages[choice][0])
            else:
                self.context.log_debug('Subtitle selection cancelled')
                return []
        else:
            self.context.log_debug('No subtitles found for prompt')
            return []

    def _get(self, language='en'):
        fname = self.srt_filename(language)
        if xbmcvfs.exists(fname):
            self.context.log_debug('Subtitle exists for: %s, filename: %s' % (language, fname))
            return [fname]

        is_caption_track = is_translation = False
        for track in self.caption_tracks:
            if language == track.get('languageCode'):
                is_caption_track = True
                break
        for lang in self.translation_langs:
            if language == lang.get('languageCode'):
                is_translation = True
                break

        if (self.caption_track.get('languageCode') != language) and (not is_translation) and (not is_caption_track):
            self.context.log_debug('No subtitles found for: %s' % language)
            return []

        subtitle_url = None
        if not is_caption_track and is_translation:
            base_url = self.caption_track.get('baseUrl')
            if base_url:
                subtitle_url = base_url + '&fmt=vtt&type=track&tlang=%s' % language
        elif is_caption_track:
            base_url = None
            for track in self.caption_tracks:
                if track.get('languageCode') == language:
                    base_url = track.get('baseUrl')
                    break
            if base_url:
                subtitle_url = base_url + '&fmt=vtt&type=track'

        if subtitle_url:
            self.context.log_debug('Subtitle url: %s' % subtitle_url)

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
