# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import atexit
import json
import sys
from weakref import proxy

from ..abstract_context import AbstractContext
from ...compatibility import (
    parse_qsl,
    urlsplit,
    xbmc,
    xbmcaddon,
    xbmcplugin,
)
from ...constants import (
    ABORT_FLAG,
    ADDON_ID,
    CONTENT,
    CONTENT_TYPE,
    PLAY_FORCE_AUDIO,
    SORT,
    WAKEUP,
)
from ...player import XbmcPlaylistPlayer
from ...settings import XbmcPluginSettings
from ...ui import XbmcContextUI
from ...utils import (
    current_system_version,
    get_kodi_setting_bool,
    get_kodi_setting_value,
    jsonrpc,
    loose_version,
    make_dirs,
    to_unicode,
    wait,
)


class XbmcContext(AbstractContext):
    # https://github.com/xbmc/xbmc/blob/master/xbmc/LangInfo.cpp#L1230
    _KODI_UI_PLAYER_LANGUAGE_OPTIONS = {
        None,  # No setting value
        'mediadefault',
        'original',
        'default',  # UI language
    }

    # https://github.com/xbmc/xbmc/blob/master/xbmc/LangInfo.cpp#L1242
    _KODI_UI_SUBTITLE_LANGUAGE_OPTIONS = {
        None,  # No setting value
        'none',
        'forced_only',
        'original',
        'default',  # UI language
    }

    LOCAL_MAP = {
        'api.config': 30634,
        'api.config.bookmark': 30638,
        'api.config.not_updated': 30635,
        'api.config.save': 190,
        'api.config.updated': 30631,
        'api.id': 30202,
        'api.key': 30201,
        'api.key.incorrect': 30648,
        'api.personal.enabled': 30636,
        'api.personal.disabled': 30637,
        'api.personal.failed': 30599,
        'api.secret': 30203,
        'are_you_sure': 750,
        'author': 21863,
        'bookmark': 30101,
        'bookmark.channel': 30803,
        'bookmark.created': 21362,
        'bookmark.remove': 20404,
        'bookmarks': 30100,
        'bookmarks.clear': 30801,
        'bookmarks.clear.check': 30802,
        'browse_channels': 30512,
        'cancel': 222,
        'channel': 19029,
        'channels': 19019,
        'client.id.incorrect': 30649,
        'client.ip': 30700,
        'client.ip.failed': 30701,
        'client.secret.incorrect': 30650,
        'completed': 19256,
        'content.clear': 30120,
        'content.clear.check': 30121,
        'content.delete': 30114,
        'content.delete.check': 30116,
        'content.remove': 30115,
        'content.remove.check': 30117,
        'datetime.a_minute_ago': 30677,
        'datetime.airing_now': 30691,
        'datetime.airing_soon': 30693,
        'datetime.airing_today_at': 30696,
        'datetime.an_hour_ago': 30679,
        'datetime.in_a_minute': 30692,
        'datetime.in_over_an_hour': 30694,
        'datetime.in_over_two_hours': 30695,
        'datetime.just_now': 30676,
        'datetime.recently': 30678,
        'datetime.three_hours_ago': 30681,
        'datetime.today_at': 30684,
        'datetime.tomorrow_at': 30697,
        'datetime.two_days_ago': 30683,
        'datetime.two_hours_ago': 30680,
        'datetime.yesterday_at': 30682,
        'delete': 117,
        'disliked.video': 30717,
        'error.no_video_streams_found': 30549,
        'error.rtmpe_not_supported': 30542,
        'failed': 30576,
        'feeds': 30518,
        'filtered': 30105,
        'go_to_channel': 30502,
        'history': 30509,
        'history.clear': 30609,
        'history.clear.check': 30610,
        'history.list.remove': 30572,
        'history.list.remove.check': 30573,
        'history.list.set': 30571,
        'history.list.set.check': 30574,
        'history.mark.unwatched': 30669,
        'history.mark.watched': 30670,
        'history.remove': 15015,
        'history.reset.resume_point': 30674,
        'home': 10000,
        'httpd': 30628,
        'httpd.not.running': 30699,
        'httpd.connect.wait': 13028,
        'httpd.connect.failed': 1001,
        'inputstreamhelper.is_installed': 30625,
        'isa.enable.check': 30579,
        'key.requirement': 30731,
        'liked.video': 30716,
        'live': 19664,
        'live.completed': 30647,
        'live.upcoming': 30646,
        'loading': 575,
        'loading.directory': 1040,
        'loading.directory.progress': 1042,
        'maintenance.bookmarks': 30800,
        'maintenance.data_cache': 30687,
        'maintenance.feed_history': 30814,
        'maintenance.function_cache': 30557,
        'maintenance.playback_history': 30673,
        'maintenance.search_history': 30558,
        'maintenance.watch_later': 30782,
        'my_channel': 30507,
        'my_location': 30654,
        'my_subscriptions': 30510,
        'my_subscriptions.loading': 30510,
        'my_subscriptions.filter.add': 30587,
        'my_subscriptions.filter.added': 30589,
        'my_subscriptions.filter.remove': 30588,
        'my_subscriptions.filter.removed': 30590,
        'my_subscriptions.filtered': 30584,
        'none': 231,
        'page.back': 30815,
        'page.choose': 30806,
        'page.empty': 30816,
        'page.next': 30106,
        'playlist.added_to': 30714,
        'playlist.create': 525,
        'playlist.play.all': 22083,
        'playlist.play.default': 571,
        'playlist.play.from_here': 30537,
        'playlist.play.recently_added': 30539,
        'playlist.play.reverse': 30533,
        'playlist.play.select': 30535,
        'playlist.play.shuffle': 191,
        'playlist.podcast': 30820,
        'playlist.progress.updating': 30536,
        'playlist.removed_from': 30715,
        'playlist.select': 524,
        'playlist.view.all': 30562,
        'playlists': 136,
        'please_wait': 30119,
        'purchases': 30622,
        'recommendations': 30551,
        'refresh': 184,
        'refresh.settings.check': 30818,
        'related_videos': 30514,
        'remove': 15015,
        'removed': 30666,
        'rename': 118,
        'renamed': 30667,
        'reset.access_manager.check': 30581,
        'retry': 30612,
        'saved.playlists': 30611,
        'search': 137,
        'search.clear': 30556,
        'search.history': 30558,
        'search.new': 30110,
        'search.quick': 30605,
        'search.quick.incognito': 30606,
        'search.remove': 15015,
        'search.rename': 118,
        'search.sort': 550,
        'search.sort.date': 552,
        'search.sort.rating': 563,
        'search.sort.relevance': 420,
        'search.sort.title': 369,
        'search.sort.viewCount': 30767,
        'search.title': 137,
        'select': 424,
        'select.listen.ip': 30644,
        'select_video_quality': 30010,
        'settings': 10004,
        'setup_wizard': 30526,
        'setup_wizard.capabilities': 30786,
        'setup_wizard.capabilities.720p30': 30787,
        'setup_wizard.capabilities.1080p30_avc': 30797,
        'setup_wizard.capabilities.1080p30': 30788,
        'setup_wizard.capabilities.1080p60': 30796,
        'setup_wizard.capabilities.4k30': 30789,
        'setup_wizard.capabilities.4k60': 30790,
        'setup_wizard.capabilities.4k60_av1': 30791,
        'setup_wizard.capabilities.max': 30792,
        'setup_wizard.locale.language': 30524,
        'setup_wizard.locale.region': 30525,
        'setup_wizard.prompt': 30030,
        'setup_wizard.prompt.import_playback_history': 30778,
        'setup_wizard.prompt.import_search_history': 30779,
        'setup_wizard.prompt.locale': 30527,
        'setup_wizard.prompt.my_location': 30653,
        'setup_wizard.prompt.settings': 10004,
        'setup_wizard.prompt.settings.defaults': 30783,
        'setup_wizard.prompt.settings.list_details': 30784,
        'setup_wizard.prompt.settings.performance': 30785,
        'setup_wizard.prompt.settings.refresh': 30817,
        'setup_wizard.prompt.subtitles': 287,
        'shorts': 30736,
        'sign.enter_code': 30519,
        'sign.go_to': 30502,
        'sign.in': 30111,
        'sign.out': 30112,
        'sign.multi.text': 30547,
        'sign.multi.title': 30546,
        'start': 335,
        'stats.commentCount': 30732,
        # 'stats.favoriteCount': 1036,
        'stats.itemCount': 20360,
        'stats.likeCount': 30733,
        'stats.subscriberCount': 30739,
        'stats.videoCount': 3,
        'stats.viewCount': 30767,
        'stream.alt': 30747,
        'stream.automatic': 36588,
        'stream.descriptive': 30746,
        'stream.dub': 30745,
        'stream.dub.auto': 30745,
        'stream.multi_audio': 30763,
        'stream.multi_language': 30762,
        'stream.original': 30744,
        'stream.secondary': 30747,
        'subscribe': 30506,
        'subscribe_to': 30517,
        'subscribed.to.channel': 30719,
        'subscriptions': 30504,
        'subtitles.download': 30705,
        'subtitles.download.pre': 30706,
        'subtitles.all': 30774,
        'subtitles.language': 21448,
        'subtitles.no_asr': 30602,
        'subtitles.translation': 30775,
        'subtitles.with_fallback': 30601,
        'succeeded': 30575,
        'trending': 30513,
        'unrated.video': 30718,
        'unsubscribe': 30505,
        'unsubscribed.from.channel': 30720,
        'untitled': 30707,
        'upcoming': 30766,
        'updated_': 30597,
        'uploads': 30726,
        'user.changed': 30659,
        'user.default': 571,
        'user.enter_name': 30658,
        'user.new': 30656,
        'user.remove': 30662,
        'user.rename': 30663,
        'user.switch': 30655,
        'user.switch.now': 30665,
        'user.unnamed': 30657,
        'video.add_to_playlist': 30520,
        'video.comments': 30732,
        'video.comments.edited': 30735,
        'video.comments.likes': 30733,
        'video.comments.replies': 30734,
        'video.description.links': 30544,
        'video.description.links.not_found': 30545,
        'video.disliked': 30538,
        'video.liked': 30508,
        'video.more': 22082,
        'video.play': 208,
        'video.play.ask_for_quality': 30730,
        'video.play.audio_only': 30708,
        'video.play.timeshift': 30819,
        'video.play.with': 30540,
        'video.play.with_subtitles': 30702,
        'video.queue': 30511,
        'video.rate': 30528,
        'video.rate.dislike': 30530,
        'video.rate.like': 30529,
        'video.rate.none': 15015,
        'videos': 3,
        'watch_later': 30107,
        'watch_later.add': 30107,
        'watch_later.added_to': 30713,
        'watch_later.clear': 30769,
        'watch_later.clear.check': 30770,
        'watch_later.list.remove': 30568,
        'watch_later.list.remove.check': 30569,
        'watch_later.list.set': 30567,
        'watch_later.list.set.check': 30570,
        'watch_later.remove': 15015,
        'youtube': 30003,
    }

    SEARCH_PARAMS = {
        'forMine',
        'channelId',
        'channelType',
        'eventType',
        'location',
        'locationRadius',
        'maxResults',
        'order',
        'pageToken'
        'publishedAfter',
        'publishedBefore',
        'q',
        'safeSearch',
        'topicId',
        'type',
        'videoCaption',
        'videoCategoryId',
        'videoDefinition',
        'videoDimension',
        'videoDuration',
        'videoEmbeddable',
        'videoLicense',
        'videoPaidProductPlacement',
        'videoSyndicated',
        'videoType',
    }

    def __new__(cls, *args, **kwargs):
        self = super(XbmcContext, cls).__new__(cls)

        if not cls._initialized:
            addon = xbmcaddon.Addon(ADDON_ID)
            cls._addon = addon
            cls._settings = XbmcPluginSettings(addon)

            # Update default allowable params
            cls._NON_EMPTY_STRING_PARAMS.update(self.SEARCH_PARAMS)

            cls._initialized = True

        return self

    def __init__(self,
                 path='/',
                 params=None,
                 plugin_id=''):
        super(XbmcContext, self).__init__(path, params, plugin_id)

        self._plugin_id = plugin_id or ADDON_ID
        if self._plugin_id != ADDON_ID:
            addon = xbmcaddon.Addon(ADDON_ID)
            self._addon = addon
            self._settings = XbmcPluginSettings(addon)

        self._addon_path = make_dirs(self._addon.getAddonInfo('path'))
        self._data_path = make_dirs(self._addon.getAddonInfo('profile'))
        self._plugin_name = self._addon.getAddonInfo('name')
        self._plugin_icon = self._addon.getAddonInfo('icon')
        self._version = self._addon.getAddonInfo('version')

        self._ui = None
        self._playlist = None

        atexit.register(self.tear_down)

    def init(self):
        num_args = len(sys.argv)
        if num_args:
            uri = sys.argv[0]
            if uri.startswith('plugin://'):
                self._plugin_handle = int(sys.argv[1])
            else:
                self._plugin_handle = -1
                return
        else:
            self._plugin_handle = -1
            return

        # first the path of the uri
        self.set_path(urlsplit(uri).path, force=True, update_uri=False)

        # after that try to get the params
        self._params = {}
        if num_args > 2:
            params = sys.argv[2][1:]
            if params:
                self.parse_params(
                    dict(parse_qsl(params, keep_blank_values=True))
                )

        # then Kodi resume status
        if num_args > 3 and sys.argv[3].lower() == 'resume:true':
            self._params['resume'] = True

        self.update_uri()

    def get_region(self):
        pass  # implement from abstract

    def is_plugin_path(self, uri, uri_path='', partial=False):
        if isinstance(uri_path, (list, tuple)):
            if partial:
                paths = [self.create_uri(path).rstrip('/') for path in uri_path]
            else:
                paths = []
                for path in uri_path:
                    path = self.create_uri(path).rstrip('/')
                    paths.extend((
                        path + '/',
                        path + '?'
                    ))
            return uri.startswith(tuple(paths))

        uri_path = self.create_uri(uri_path).rstrip('/')
        if not partial:
            uri_path = (
                uri_path + '/',
                uri_path + '?'
            )
        return uri.startswith(uri_path)

    @staticmethod
    def format_date_short(date_obj, str_format=None):
        if str_format is None:
            str_format = xbmc.getRegion('dateshort')
        return date_obj.strftime(str_format)

    @staticmethod
    def format_time(time_obj, str_format=None):
        if str_format is None:
            str_format = (xbmc.getRegion('time')
                          .replace('%H%H', '%H')
                          .replace(':%S', ''))
        return time_obj.strftime(str_format)

    @staticmethod
    def get_language():
        language = xbmc.getLanguage(format=xbmc.ISO_639_1, region=True)
        lang_code, separator, region = language.partition('-')
        if not lang_code:
            language = xbmc.getLanguage(format=xbmc.ISO_639_2, region=False)
            lang_code, separator, region = language.partition('-')
            if lang_code != 'fil':
                lang_code = lang_code[:2]
            region = region[:2]
        if not lang_code:
            return 'en-US'
        if region:
            return separator.join((lang_code.lower(), region.upper()))
        return lang_code

    def get_language_name(self, lang_id=None):
        if lang_id is None:
            lang_id = self.get_language()
        return xbmc.convertLanguage(lang_id, xbmc.ENGLISH_NAME).split(';')[0]

    def get_player_language(self):
        language = get_kodi_setting_value('locale.audiolanguage')
        if language == 'default':
            language = get_kodi_setting_value('locale.language')
            language = language.replace('resource.language.', '').split('_')[0]
        elif language not in self._KODI_UI_PLAYER_LANGUAGE_OPTIONS:
            language = xbmc.convertLanguage(language, xbmc.ISO_639_1)
        return language, get_kodi_setting_bool('videoplayer.preferdefaultflag')

    def get_subtitle_language(self):
        language = get_kodi_setting_value('locale.subtitlelanguage')
        if language == 'default':
            language = get_kodi_setting_value('locale.language')
            language = language.replace('resource.language.', '').split('_')[0]
        elif language in self._KODI_UI_SUBTITLE_LANGUAGE_OPTIONS:
            language = None
        else:
            language = xbmc.convertLanguage(language, xbmc.ISO_639_1)
        return language

    def get_playlist_player(self, playlist_type=None):
        if self.get_param(PLAY_FORCE_AUDIO) or self.get_settings().audio_only():
            playlist_type = 'audio'
        if not self._playlist or playlist_type:
            self._playlist = XbmcPlaylistPlayer(proxy(self), playlist_type)
        return self._playlist

    def get_ui(self):
        if not self._ui:
            self._ui = XbmcContextUI(proxy(self))
        return self._ui

    def get_data_path(self):
        return self._data_path

    def get_addon_path(self):
        return self._addon_path

    def clear_settings(self):
        if self._plugin_id != ADDON_ID and self._settings:
            self._settings.flush()
        if self.__class__._settings:
            self.__class__._settings.flush()

    def get_settings(self, refresh=False):
        if refresh or not self._settings:
            if self._plugin_id != ADDON_ID:
                addon = xbmcaddon.Addon(self._plugin_id)
                self._addon = addon
                self._settings = XbmcPluginSettings(addon)
            else:
                addon = xbmcaddon.Addon(ADDON_ID)
                self.__class__._addon = addon
                self.__class__._settings = XbmcPluginSettings(addon)
        return self._settings

    def localize(self, text_id, default_text=None):
        if default_text is None:
            default_text = 'Undefined string ID: |{0}|'.format(text_id)

        if not isinstance(text_id, int):
            try:
                text_id = self.LOCAL_MAP[text_id]
            except KeyError:
                try:
                    text_id = int(text_id)
                except ValueError:
                    return default_text
        if text_id <= 0:
            return default_text

        """
        We want to use all localization strings!
        Addons should only use the range 30000 thru 30999
        (see: http://kodi.wiki/view/Language_support) but we do it anyway.
        I want some of the localized strings for the views of a skin.
        """
        source = self._addon if 30000 <= text_id < 31000 else xbmc
        result = source.getLocalizedString(text_id)
        result = to_unicode(result) if result else default_text
        return result

    def set_content(self, content_type, sub_type=None, category_label=None):
        ui = self.get_ui()
        ui.set_property(CONTENT_TYPE, json.dumps(
            (content_type, sub_type, category_label),
            ensure_ascii=False,
        ))

    def apply_content(self):
        # ui local variable used for ui.get_view_manager() in unofficial version
        ui = self.get_ui()

        content_type = ui.pop_property(CONTENT_TYPE)
        if content_type:
            content_type, sub_type, category_label = json.loads(content_type)
            self.log_debug('Applying content-type: |{type}| for |{path}|'.format(
                type=(sub_type or content_type), path=self.get_path()
            ))
            xbmcplugin.setContent(self._plugin_handle, content_type)
        else:
            content_type = None
            sub_type = None
            category_label = None

        if category_label is None:
            category_label = self.get_param('category_label')
        if category_label:
            xbmcplugin.setPluginCategory(self._plugin_handle, category_label)

        detailed_labels = self.get_settings().show_detailed_labels()
        if sub_type == 'history':
            self.add_sort_method(
                (SORT.LASTPLAYED,       '%T \u2022 %P',           '%D | %J'),
                (SORT.PLAYCOUNT,        '%T \u2022 %P',           '%D | %J'),
                (SORT.UNSORTED,         '%T \u2022 %P',           '%D | %J'),
                (SORT.LABEL,            '%T \u2022 %P',           '%D | %J'),
            ) if detailed_labels else self.add_sort_method(
                (SORT.LASTPLAYED,),
                (SORT.PLAYCOUNT,),
                (SORT.UNSORTED,),
                (SORT.LABEL,),
            )
        elif sub_type == 'comments':
            self.add_sort_method(
                (SORT.CHANNEL,          '[%A - ]%T \u2022 %P',       '%J'),
                (SORT.ARTIST,           '[%J - ]%T \u2022 %P',       '%A'),
                (SORT.PROGRAM_COUNT,    '[%A - ]%T \u2022 %P | %J',  '%C'),
                (SORT.DATE,             '[%A - ]%T \u2022 %P',       '%J'),
                (SORT.TRACKNUM,         '[%N. ][%A - ]%T \u2022 %P', '%J'),
            ) if detailed_labels else self.add_sort_method(
                (SORT.CHANNEL,          '[%A - ]%T'),
                (SORT.ARTIST,           '[%A - ]%T'),
                (SORT.PROGRAM_COUNT,    '[%A - ]%T'),
                (SORT.DATE,             '[%A - ]%T'),
                (SORT.TRACKNUM,         '[%N. ][%A - ]%T '),
            )
        else:
            self.add_sort_method(
                (SORT.UNSORTED,         '%T \u2022 %P',           '%D | %J'),
                (SORT.LABEL,            '%T \u2022 %P',           '%D | %J'),
            ) if detailed_labels else self.add_sort_method(
                (SORT.UNSORTED,),
                (SORT.LABEL,),
            )

        if content_type == CONTENT.VIDEO_CONTENT:
            self.add_sort_method(
                (SORT.CHANNEL,          '[%A - ]%T \u2022 %P',    '%D | %J'),
                (SORT.ARTIST,           '%T \u2022 %P | %D | %J', '%A'),
                (SORT.PROGRAM_COUNT,    '%T \u2022 %P | %D | %J', '%C'),
                (SORT.VIDEO_RATING,     '%T \u2022 %P | %D | %J', '%R'),
                (SORT.DATE,             '%T \u2022 %P | %D',      '%J'),
                (SORT.DATEADDED,        '%T \u2022 %P | %D',      '%a'),
                (SORT.VIDEO_RUNTIME,    '%T \u2022 %P | %J',      '%D'),
                (SORT.TRACKNUM,         '[%N. ]%T \u2022 %P',     '%D | %J'),
            ) if detailed_labels else self.add_sort_method(
                (SORT.CHANNEL,          '[%A - ]%T'),
                (SORT.ARTIST,),
                (SORT.PROGRAM_COUNT,),
                (SORT.VIDEO_RATING,),
                (SORT.DATE,),
                (SORT.DATEADDED,),
                (SORT.VIDEO_RUNTIME,),
                (SORT.TRACKNUM,         '[%N. ]%T '),
            )

    def add_sort_method(self, *sort_methods):
        args = slice(None if current_system_version.compatible(19) else 2)
        for sort_method in sort_methods:
            xbmcplugin.addSortMethod(self._plugin_handle, *sort_method[args])

    def clone(self, new_path=None, new_params=None):
        if not new_path:
            new_path = self.get_path()

        if not new_params:
            new_params = self.get_params()

        new_context = XbmcContext(path=new_path,
                                  params=new_params,
                                  plugin_id=self._plugin_id)

        new_context._access_manager = self._access_manager
        new_context._uuid = self._uuid

        new_context._bookmarks_list = self._bookmarks_list
        new_context._data_cache = self._data_cache
        new_context._feed_history = self._feed_history
        new_context._function_cache = self._function_cache
        new_context._playback_history = self._playback_history
        new_context._search_history = self._search_history
        new_context._watch_later_list = self._watch_later_list

        new_context._ui = self._ui
        new_context._playlist = self._playlist

        return new_context

    def execute(self, command, wait=False, wait_for=None):
        if not wait_for:
            xbmc.executebuiltin(command, wait)
            return

        ui = self.get_ui()
        ui.clear_property(wait_for)
        pop_property = ui.pop_property
        waitForAbort = xbmc.Monitor().waitForAbort

        xbmc.executebuiltin(command, wait)

        while not pop_property(wait_for) and not waitForAbort(1):
            pass

    @staticmethod
    def sleep(timeout=None):
        return wait(timeout)

    def addon_enabled(self, addon_id):
        response = jsonrpc(method='Addons.GetAddonDetails',
                           params={'addonid': addon_id,
                                   'properties': ['enabled']})
        try:
            return response['result']['addon']['enabled'] is True
        except (KeyError, TypeError) as exc:
            error = response.get('error', {})
            self.log_error('XbmcContext.addon_enabled - Error'
                           '\n\tException: {exc!r}'
                           '\n\tCode:      {code}'
                           '\n\tMessage:   {msg}'
                           .format(exc=exc,
                                   code=error.get('code', 'Unknown'),
                                   msg=error.get('message', 'Unknown')))
            return False

    def set_addon_enabled(self, addon_id, enabled=True):
        response = jsonrpc(method='Addons.SetAddonEnabled',
                           params={'addonid': addon_id,
                                   'enabled': enabled})
        try:
            return response['result'] == 'OK'
        except (KeyError, TypeError) as exc:
            error = response.get('error', {})
            self.log_error('XbmcContext.set_addon_enabled - Error'
                           '\n\tException: {exc!r}'
                           '\n\tCode:      {code}'
                           '\n\tMessage:   {msg}'
                           .format(exc=exc,
                                   code=error.get('code', 'Unknown'),
                                   msg=error.get('message', 'Unknown')))
            return False

    @staticmethod
    def send_notification(method, data=True):
        jsonrpc(method='JSONRPC.NotifyAll',
                params={'sender': ADDON_ID,
                        'message': method,
                        'data': data})

    def use_inputstream_adaptive(self, prompt=False):
        if not self.get_settings().use_isa():
            return None

        while 1:
            try:
                addon = xbmcaddon.Addon('inputstream.adaptive')
                return addon.getAddonInfo('version')
            except RuntimeError:
                if (prompt
                        and self.get_ui().on_yes_no_input(
                            self.get_name(),
                            self.localize('isa.enable.check'),
                        )
                        and self.set_addon_enabled('inputstream.adaptive')):
                    prompt = False
                    continue
            return None

    # Values of capability map can be any of the following:
    # - required version number, as string param to loose_version() to compare
    # against installed InputStream.Adaptive version
    # - any Falsy value to exclude capability regardless of version
    # - True to include capability regardless of version
    _ISA_CAPABILITIES = {
        # functionality
        'drm': loose_version('2.2.12'),
        'live': loose_version('2.0.12'),
        'timeshift': loose_version('2.5.2'),
        'ttml': loose_version('20.0.0'),
        # properties
        'config_prop': loose_version('21.4.11'),
        'manifest_config_prop': loose_version('21.4.5'),
        # audio codecs
        'vorbis': loose_version('2.3.14'),
        # unknown when Opus audio support was implemented
        'opus': loose_version('19.0.0'),
        'mp4a': True,
        'ac-3': loose_version('2.1.15'),
        'ec-3': loose_version('2.1.15'),
        'dts': loose_version('2.1.15'),
        # video codecs
        'avc1': True,
        'av01': loose_version('20.3.0'),
        'vp8': False,
        'vp9': loose_version('2.3.14'),
        'vp9.2': loose_version('2.4.0'),
    }

    def inputstream_adaptive_capabilities(self, capability=None):
        # Returns a frozenset of capabilities supported by installed ISA version
        # If capability param is provided, returns True if the installed version
        # of ISA supports the nominated capability, False otherwise

        inputstream_version = self.use_inputstream_adaptive()
        if not inputstream_version:
            return frozenset() if capability is None else None

        isa_loose_version = loose_version(inputstream_version)

        if capability:
            version = self._ISA_CAPABILITIES.get(capability)
            return version is True or version and isa_loose_version >= version

        return frozenset(
            capability
            for (capability, version) in self._ISA_CAPABILITIES.items()
            if version is True or version and isa_loose_version >= version
        )

    @staticmethod
    def inputstream_adaptive_auto_stream_selection():
        try:
            addon = xbmcaddon.Addon('inputstream.adaptive')
            return addon.getSetting('STREAMSELECTION') == '0'
        except RuntimeError:
            return False

    def abort_requested(self):
        return self.get_ui().get_property(ABORT_FLAG).lower() == 'true'

    @staticmethod
    def get_infobool(name):
        return xbmc.getCondVisibility(name)

    @staticmethod
    def get_infolabel(name):
        return xbmc.getInfoLabel(name)

    @staticmethod
    def get_listitem_property(detail_name):
        return xbmc.getInfoLabel('Container.ListItem(0).Property({0})'
                                 .format(detail_name))

    @staticmethod
    def get_listitem_info(detail_name):
        return xbmc.getInfoLabel('Container.ListItem(0).' + detail_name)

    def tear_down(self):
        self.clear_settings()
        attrs = (
            '_addon',
            '_settings',
        )
        for attr in attrs:
            try:
                if self._plugin_id != ADDON_ID:
                    delattr(self, attr)
                delattr(self.__class__, attr)
                setattr(self.__class__, attr, None)
            except AttributeError:
                pass

        attrs = (
            '_ui',
            '_playlist',
        )
        for attr in attrs:
            try:
                delattr(self, attr)
                setattr(self, attr, None)
            except AttributeError:
                pass

    def wakeup(self, target, timeout=None, payload=None):
        data = {'target': target, 'response_required': bool(timeout)}
        if payload:
            data.update(payload)
        self.send_notification(WAKEUP, data)
        if not timeout:
            return None

        pop_property = self.get_ui().pop_property
        no_timeout = timeout < 0
        remaining = timeout = timeout * 1000
        wait_period_ms = 100
        wait_period = wait_period_ms / 1000

        while no_timeout or remaining > 0:
            data = pop_property(WAKEUP)
            if data:
                data = json.loads(data)

            if data:
                response = data.get('response')
                response_target = data.get('target') or 'Unknown'

                if target == response_target:
                    if response:
                        self.log_debug('Wakeup |{0}| in {1}ms'
                                       .format(response_target,
                                               timeout - remaining))
                    else:
                        self.log_error('Wakeup |{0}| in {1}ms - failed'
                                       .format(response_target,
                                               timeout - remaining))
                    return response

                self.log_error('Wakeup |{0}| in {1}ms - expected |{2}|'
                               .format(response_target,
                                       timeout - remaining,
                                       target))
                break

            wait(wait_period)
            remaining -= wait_period_ms
        else:
            self.log_error('Wakeup |{0}| timed out in {1}ms'
                           .format(target, timeout))
        return False

    def is_plugin_folder(self, folder_name=None):
        if folder_name is None:
            folder_name = xbmc.getInfoLabel('Container.FolderName')
        return folder_name == self._plugin_name
