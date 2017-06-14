# -*- coding: utf-8 -*-
import xbmcvfs
import re
import HTMLParser
import requests
import urllib

from .signature.cipher import Cipher


class Subtitles(object):
    LANG_NONE = 0
    LANG_ALL = 1
    LANG_CURR = 2
    LANG_CURR_EN = 3
    LANG_EN = 4
    LANG_PROMPT = 5
    LANG_AUTO = 6

    SUBTITLE_LIST_URL = 'http://www.youtube.com/api/timedtext?type=list&v=%s'
    SUBTITLE_URL = 'http://www.youtube.com/api/timedtext?fmt=vtt&v=%s&name=%s&lang=%s'
    VIDEO_URL = 'http://www.youtube.com/watch?v=%s'
    SUBTITLE_AUTO_LIST_URL = 'http://www.youtube.com/api/timedtext?key=yttt1&sparams=asr_langs%2Ccaps%2Cv%2Cexpire&caps=asr&asrs=1&type=list&tlangs=1&expire={0}&signature={1}&asr_langs={2}&v={3}'
    SUBTITLE_AUTO_URL = 'http://www.youtube.com/api/timedtext?key=yttt1&sparams=asr_langs%2Ccaps%2Cv%2Cexpire&caps=asr&name=&type=track&kind=asr&fmt=vtt&lang=en&expire={0}&signature={1}&asr_langs={2}&tlang={3}&v={4}'
    SRT_FILE = 'special://temp/temp/%s.%s.srt'

    def __init__(self, context, video_id):
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

    def get(self):
        if self._languages() != self.LANG_NONE:
            self.context.log_debug('Getting subtitles for video_id: %s, language_enum: %s' %
                                   (self.video_id, self._languages()))
            return self._get_subtitles()
        else:
            return []

    def srt_filename(self, sub_language):
        return self.SRT_FILE % (self.video_id, sub_language)

    def srt_filename_auto(self, sub_language):
        return self.SRT_FILE % (self.video_id + '_auto', sub_language)

    def subtitle_url(self, sub_name, sub_language):
        return self.SUBTITLE_URL % (self.video_id, self._unescape(sub_name).encode('utf-8'), sub_language)

    def _languages(self):
        return self.context.get_settings().subtitle_languages()

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

    def _get_subtitles(self):
        languages = self._languages()
        if languages == self.LANG_NONE:
            return []

        subtitle_list_url = self.SUBTITLE_LIST_URL % self.video_id
        result = requests.get(subtitle_list_url, headers=self.headers,
                              verify=self._verify, allow_redirects=True)
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
            elif languages == self.LANG_AUTO:
                list_of_subs = []
                list_of_subs.extend(self._get_current(result.text))
                video_url = self.VIDEO_URL % self.video_id
                list_of_subs.extend(self._get_auto(video_url, language=self.language.split('-')[0]))
                list_of_subs.extend(self._get_en(result.text))
                return list(set(list_of_subs))
            else:
                self.context.log_debug('Unknown language_enum: %s for subtitles' % str(languages))
        else:
            self.context.log_debug('Failed to retrieve subtitle list')
            return []

    def _get_all(self, xml_contents):
        return_list = []
        for match in re.finditer('name="(?P<name>[^"]*)" lang_code="(?P<language>[^"]+?)"', xml_contents, re.IGNORECASE):
            name = match.group('name')
            language = match.group('language')
            fname = self.srt_filename(language)
            if xbmcvfs.exists(fname):
                self.context.log_debug('Subtitle exists for: %s, filename: %s' % (language, fname))
                return_list.append(fname)
                continue
            result = requests.get(self.subtitle_url(name, language), headers=self.headers,
                                  verify=self._verify, allow_redirects=True)
            if result.text:
                self.context.log_debug('Subtitle found for: %s' % language)
                result = self._write_file(fname, bytearray(self._unescape(result.text), encoding='utf8', errors='ignore'))
                if result:
                    return_list.append(fname)
                continue
            else:
                self.context.log_debug('Failed to retrieve subtitles for: %s' % language)
                continue

        if not return_list:
            self.context.log_debug('No subtitles found')
        return return_list

    def _get_current(self, xml_contents):
        name = ''
        language = self.language
        fname = self.srt_filename(language)
        if xbmcvfs.exists(fname):
            self.context.log_debug('Subtitle exists for: %s, filename: %s' % (language, fname))
            return [fname]
        if xml_contents.find('name="%s" lang_code="%s"' % (name, language)) > -1:
            result = requests.get(self.subtitle_url(name, language), headers=self.headers,
                                  verify=self._verify, allow_redirects=True)
            if result.text:
                self.context.log_debug('Subtitle found for: %s' % language)
                result = self._write_file(fname, bytearray(self._unescape(result.text), encoding='utf8', errors='ignore'))
                if result:
                    return [fname]
                else:
                    return []
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
            if xml_contents.find('name="%s" lang_code="%s"' % (name, language)) > -1:
                result = requests.get(self.subtitle_url(name, language), headers=self.headers,
                                      verify=self._verify, allow_redirects=True)
                if result.text:
                    self.context.log_debug('Subtitle found for: %s' % language)
                    result = self._write_file(fname, bytearray(self._unescape(result.text), encoding='utf8', errors='ignore'))
                    if result:
                        return [fname]
                    else:
                        return []
                else:
                    self.context.log_debug('Failed to retrieve subtitles for: %s' % language)
                    return []
            else:
                self.context.log_debug('No subtitles found for: %s' % language)
                return []

    def _get_en(self, xml_contents):
        return self._by_regex('name="(?P<name>[^"]*)" lang_code="(?P<language>en[^"]*)"', xml_contents)

    def _prompt(self, xml_contents):
        languages = re.findall('lang_code="(?P<language>[^"]+?)"', xml_contents, re.IGNORECASE)
        if languages:
            choice = self.context.get_ui().on_select(self.context.localize(30560), languages)
            if choice != -1:
                return self._by_regex('name="(?P<name>[^"]*)" lang_code="(?P<language>%s[^"]*)"' % languages[choice], xml_contents)
            else:
                self.context.log_debug('Subtitle selection cancelled')
                return []
        else:
            self.context.log_debug('No subtitles found for prompt')
            return []

    def _by_regex(self, reg_exp, xml_contents):
        match = re.search(reg_exp, xml_contents, re.IGNORECASE)
        if match:
            name = match.group('name')
            language = match.group('language')
            fname = self.srt_filename(language)
            if xbmcvfs.exists(fname):
                self.context.log_debug('Subtitle exists for: %s, filename: %s' % (language, fname))
                return [fname]
            result = requests.get(self.subtitle_url(name, language), headers=self.headers,
                                  verify=self._verify, allow_redirects=True)
            if result.text:
                self.context.log_debug('Subtitle found for: %s' % language)
                result = self._write_file(fname, bytearray(self._unescape(result.text), encoding='utf8', errors='ignore'))
                if result:
                    return [fname]
                else:
                    return []
            else:
                self.context.log_debug('Failed to retrieve subtitles for: %s' % language)
                return []
        else:
            self.context.log_debug('No subtitles found for: %s' % reg_exp)
            return []

    def _get_auto(self, video_url, language='en'):
        fname = self.srt_filename_auto(language)
        if xbmcvfs.exists(fname):
            self.context.log_debug('Automatic subtitle exists for: %s, filename: %s' % (language, fname))
            return [fname]

        result = requests.get(video_url, headers=self.headers,
                              verify=self._verify, allow_redirects=True)

        if result.text:
            tts_result = result.text
            if tts_result.find("'TTS_URL': \"") > -1:
                tts_result = tts_result.split("'TTS_URL': \"")
                tts_result = tts_result[1].split("\"")[0]
                if len(tts_result) < 250:
                    return []
            else:
                return []

            tts_result = tts_result.replace("\\/", "/")
            tts_result = tts_result.replace("\\u0026", "&")
            tts_result = tts_result.replace("%2C", ",")
            tts_result = tts_result.split("?")[1]
            tts_result += '&'
            self.context.log_debug('Auto Subtitle debug: %s' % tts_result)

            asr_langs = re.compile('asr_langs=(.*?)[&]').findall(tts_result)
            if asr_langs and (language in asr_langs[0]):
                asr_langs = asr_langs[0]
                signature = re.compile('signature=(.*?)[&]').findall(tts_result)
                if not signature:
                    signature = re.compile('s=(.*?)[&]').findall(tts_result)
                    if signature:
                        re_match_js = re.search(r'\"js\"[^:]*:[^"]*\"(?P<js>.+?)\"', tts_result)
                        cipher = None
                        if re_match_js:
                            js = re_match_js.group('js').replace('\\', '').strip('//')
                            if not js.startswith('http'):
                                js = 'http://www.youtube.com/%s' % js
                            cipher = Cipher(self.context, java_script_url=js)
                        signature = cipher.get_signature(signature[0])
                else:
                    signature = signature[0]
                expire = re.compile('expire=(.*?)[&]').findall(tts_result)
                if expire:
                    expire = expire[0]

                if expire and signature and asr_langs:
                    subtitle_auto_url = self.SUBTITLE_AUTO_URL.format(expire, signature, urllib.quote(asr_langs), language, self.video_id)
                    self.context.log_debug('Auto subtitle url: %s' % subtitle_auto_url)

                    result_auto = requests.get(subtitle_auto_url, headers=self.headers,
                                               verify=self._verify, allow_redirects=True)

                    if result_auto.text:
                        self.context.log_debug('Auto subtitle found for: %s' % language)
                        self._write_file(fname, bytearray(self._unescape(result_auto.text), encoding='utf8', errors='ignore'))
                        return [fname]
                    else:
                        self.context.log_debug('Failed to retrieve subtitles for: %s' % language)

        self.context.log_debug('No automatic subtitles found for: %s' % language)
        return []
