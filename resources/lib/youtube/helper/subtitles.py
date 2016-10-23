# -*- coding: utf-8 -*-
import xbmcvfs
import re
from resources.lib.kodion import simple_requests as requests


class Subtitles(object):
    LANG_NONE = 0
    LANG_ALL = 1
    LANG_CURR = 2
    LANG_CURR_EN = 3
    LANG_EN = 4
    LANG_PROMPT = 5

    SUBTITLE_LIST_URL = 'http://www.youtube.com/api/timedtext?type=list&v=%s'
    SUBTITLE_URL = 'http://www.youtube.com/api/timedtext?fmt=vtt&v=%s&lang=%s'
    SRT_FILE = 'special://temp/%s.%s.srt'

    def __init__(self, context, video_id):
        self.context = context
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

    def get(self):
        if self._languages() != self.LANG_NONE:
            self.context.log_debug('Getting subtitles for video_id: %s, language_enum: %s' %
                                   (self.video_id, self._languages()))
            return self._get_subtitles()
        else:
            return []

    def srt_filename(self, sub_language):
        return self.SRT_FILE % (self.video_id, sub_language)

    def subtitle_url(self, sub_language):
        return self.SUBTITLE_URL % (self.video_id, sub_language)

    def _languages(self):
        return self.context.get_settings().subtitle_languages()

    def _write_file(self, _file, contents):
        self.context.log_debug('Writing subtitle file: %s' % _file)
        f = xbmcvfs.File(_file, 'w')
        f.write(contents)
        f.close()

    def _get_subtitles(self):
        languages = self._languages()
        if languages == self.LANG_NONE:
            return []

        subtitle_list_url = self.SUBTITLE_LIST_URL % self.video_id
        result = requests.get(subtitle_list_url, headers=self.headers,
                              verify=False, allow_redirects=True)
        if result.text:
            if languages == self.LANG_ALL:
                return self._get_all(result.text)
            elif languages == self.LANG_CURR:
                return self._get_current(result.text)
            elif languages == self.LANG_CURR_EN:
                list_of_subs = []
                list_of_subs.extend(self._get_current(result.text))
                list_of_subs.extend(self._get_en(result.text))
                return list(set(list_of_subs))
            elif languages == self.LANG_EN:
                return self._get_en(result.text)
            elif languages == self.LANG_PROMPT:
                return self._prompt(result.text)
            else:
                self.context.log_debug('Unknown language_enum: %s for subtitles' % str(languages))
        else:
            self.context.log_debug('Failed to retrieve subtitle list')
            return []

    def _get_all(self, xml_contents):
        return_list = []
        for match in re.finditer('lang_code="(?P<language>[^"]+?)"', xml_contents, re.IGNORECASE):
            language = match.group('language')
            fname = self.srt_filename(language)
            if xbmcvfs.exists(fname):
                self.context.log_debug('Subtitle exists for: %s, filename: %s' % (language, fname))
                return_list.append(fname)
                continue
            result = requests.get(self.subtitle_url(language), headers=self.headers,
                                  verify=False, allow_redirects=True)
            if result.text:
                self.context.log_debug('Subtitle found for: %s' % language)
                self._write_file(fname, result.text)
                return_list.append(fname)
                continue
            else:
                self.context.log_debug('Failed to retrieve subtitles for: %s' % language)
                continue

        if not return_list:
            self.context.log_debug('No subtitles found')
        return return_list

    def _get_current(self, xml_contents):
        language = self.language
        fname = self.srt_filename(language)
        if xbmcvfs.exists(fname):
            self.context.log_debug('Subtitle exists for: %s, filename: %s' % (language, fname))
            return [fname]
        if xml_contents.find('lang_code="%s"' % language) > -1:
            result = requests.get(self.subtitle_url(language), headers=self.headers,
                                  verify=False, allow_redirects=True)
            if result.text:
                self.context.log_debug('Subtitle found for: %s' % language)
                self._write_file(fname, result.text)
                return [fname]
            else:
                self.context.log_debug('Failed to retrieve subtitles for: %s' % language)
                return []
        else:
            if '-' not in self.language:
                self.context.log_debug('No subtitles found for: %s' % language)
                return []
            language = language.split('-')[0]
            fname = self.srt_filename(language)
            if xbmcvfs.exists(fname):
                self.context.log_debug('Subtitle exists for: %s, filename: %s' % (language, fname))
                return [fname]
            if xml_contents.find('lang_code="%s"' % language) > -1:
                result = requests.get(self.subtitle_url(language), headers=self.headers,
                                      verify=False, allow_redirects=True)
                if result.text:
                    self.context.log_debug('Subtitle found for: %s' % language)
                    self._write_file(fname, result.text)
                    return [fname]
                else:
                    self.context.log_debug('Failed to retrieve subtitles for: %s' % language)
                    return []
            else:
                self.context.log_debug('No subtitles found for: %s' % language)
                return []

    def _get_en(self, xml_contents):
        return self._by_regex('lang_code="(?P<language>en[^"]*)"', xml_contents)

    def _prompt(self, xml_contents):
        languages = re.findall('lang_code="(?P<language>[^"]+?)"', xml_contents, re.IGNORECASE)
        if languages:
            choice = self.context.get_ui().on_select(self.context.localize(30560), languages)
            if choice != -1:
                return self._by_regex('lang_code="(?P<language>%s[^"]*)"' % languages[choice], xml_contents)
            else:
                self.context.log_debug('Subtitle selection cancelled')
                return []
        else:
            self.context.log_debug('No subtitles found for prompt')
            return []

    def _by_regex(self, reg_exp, xml_contents):
        match = re.search(reg_exp, xml_contents, re.IGNORECASE)
        if match:
            language = match.group('language')
            fname = self.srt_filename(language)
            if xbmcvfs.exists(fname):
                self.context.log_debug('Subtitle exists for: %s, filename: %s' % (language, fname))
                return [fname]
            result = requests.get(self.subtitle_url(language), headers=self.headers,
                                  verify=False, allow_redirects=True)
            if result.text:
                self.context.log_debug('Subtitle found for: %s' % language)
                self._write_file(fname, result.text)
                return [fname]
            else:
                self.context.log_debug('Failed to retrieve subtitles for: %s' % language)
                return []
        else:
            self.context.log_debug('No subtitles found for: %s' % reg_exp)
            return []
