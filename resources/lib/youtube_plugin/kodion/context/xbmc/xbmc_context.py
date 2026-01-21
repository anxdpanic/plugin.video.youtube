# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import sys
from atexit import register as atexit_register
from timeit import default_timer
from weakref import proxy

from ..abstract_context import AbstractContext
from ... import logging
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
    BUSY_FLAG,
    CHANNEL_ID,
    CONTENT,
    FOLDER_NAME,
    PLAYLIST_ID,
    PLAY_FORCE_AUDIO,
    SERVICE_IPC,
    SERVICE_RUNNING_FLAG,
    SORT,
    URI,
    VIDEO_ID,
)
from ...json_store import APIKeyStore, AccessManager
from ...player import XbmcPlaylistPlayer
from ...settings import XbmcPluginSettings
from ...ui import XbmcContextUI
from ...utils.convert_format import to_unicode
from ...utils.file_system import make_dirs
from ...utils.methods import (
    get_kodi_setting_bool,
    get_kodi_setting_value,
    jsonrpc,
    loose_version,
    wait,
)
from ...utils.system_version import current_system_version


class IPCMonitor(xbmc.Monitor):
    EXPECTED_SENDER = '.'.join((ADDON_ID, 'service'))

    def __init__(self, target, timeout):
        super(IPCMonitor, self).__init__()
        self.target = target
        self.value = None
        self.latency = None
        self.received = False

        wait_period = 0.01
        elapsed = 0
        self._start = default_timer()
        while not self.received and not self.waitForAbort(wait_period):
            if timeout:
                elapsed += wait_period
                if elapsed >= timeout:
                    break

    def onNotification(self, sender, method, data):
        if sender != self.EXPECTED_SENDER:
            return

        group, separator, event = method.partition('.')

        if event == SERVICE_IPC:
            if not isinstance(data, dict):
                data = json.loads(data)
            if not data:
                return

            if self.target != data.get('target'):
                return

            self.value = data.get('response')
            self.latency = 1000 * (default_timer() - self._start)
            self.received = True


class XbmcContext(AbstractContext):
    log = logging.getLogger(__name__)

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
        'add.to.x': 30613,
        'added.x': 30670,
        'added.to.x': 30615,
        'after_watch.play_suggested': 30582,
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
        'bookmark.x': 30803,
        'bookmark.created': 21362,
        'bookmark.remove': 20404,
        'bookmarks': 30100,
        'bookmarks.add': 294,
        'bookmarks.clear': 30801,
        'bookmarks.clear.check': 30802,
        'bookmarks.edit.name': 30108,
        'bookmarks.edit.uri': 30109,
        'browse_channels': 30512,
        'cancel': 222,
        'channel': 19029,
        'channels': 19019,
        'client.id.incorrect': 30649,
        'client.ip.is.x': 30700,
        'client.ip.failed': 30701,
        'client.secret.incorrect': 30650,
        'completed': 19256,
        'content.clear': 30120,
        'content.clear.check.x': 30121,
        'content.delete': 30114,
        'content.delete.check.x': 30116,
        'content.remove': 30115,
        'content.remove.check.x': 30117,
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
        'edit.x': 30501,
        'error.no_streams_found': 30549,
        'error.no_videos_found': 30545,
        'error.rtmpe_not_supported': 30542,
        'failed': 30576,
        'failed.x': 30500,
        'feeds': 30518,
        'filtered': 30105,
        'go_to.x': 30502,
        'history': 30509,
        'history.clear': 30609,
        'history.clear.check': 30610,
        'history.list.unassign': 30572,
        'history.list.unassign.check': 30573,
        'history.list.assign': 30571,
        'history.list.assign.check': 30574,
        'history.mark.unwatched': 16104,
        'history.mark.watched': 16103,
        'history.remove': 15015,
        'history.reset.resume_point': 38209,
        'home': 10000,
        'httpd': 30628,
        'httpd.not.running': 30699,
        'httpd.connect.wait': 13028,
        'httpd.connect.failed': 1001,
        'inputstreamhelper.is_installed': 30625,
        'internet.connection.required': 21451,
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
        'maintenance.requests_cache': 30523,
        'maintenance.search_history': 30558,
        'maintenance.watch_later': 30782,
        'members_only': 30624,
        'my_channel': 30507,
        'my_location': 30654,
        'my_subscriptions': 30510,
        'my_subscriptions.loading': 30510,
        'my_subscriptions.filtered': 30584,
        'none': 231,
        'page.back': 30815,
        'page.choose': 30806,
        'page.empty': 30816,
        'page.next': 30106,
        'playlist': 559,
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
        'playlist.select': 524,
        'playlist.view.all': 30562,
        'playlists': 136,
        'please_wait': 30119,
        'purchases': 30622,
        'rating': 563,
        'recommendations': 30551,
        'refresh': 184,
        'refresh.settings.check': 30818,
        'remove': 15015,
        'remove.from.x': 30614,
        'removed.from.x': 30616,
        'removed.name.x': 30666,
        'removed.x': 30669,
        'rename': 118,
        'renamed.x.y': 30667,
        'reset.access_manager.check': 30581,
        'retry': 30612,
        'save': 190,
        'saved': 35259,
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
        'setup_wizard.prompt.x': 30030,
        'setup_wizard.prompt.import_playback_history': 30778,
        'setup_wizard.prompt.import_search_history': 30779,
        'setup_wizard.prompt.locale': 30527,
        'setup_wizard.prompt.migrate_watch_history': 30715,
        'setup_wizard.prompt.migrate_watch_later': 30718,
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
        'subscribe_to.x': 30517,
        'subscribed.to.channel': 30719,
        'subscriptions': 30504,
        'subtitles.download': 30705,
        'subtitles.download.pre': 30706,
        'subtitles.all': 30774,
        'subtitles.language': 21448,
        'subtitles.no_asr': 30602,
        'subtitles.translation.x': 30775,
        'subtitles.with_fallback': 30601,
        'succeeded': 30575,
        'trending': 30513,
        'unsubscribe': 30505,
        'unsubscribed.from.channel': 30720,
        'untitled': 30707,
        'upcoming': 30766,
        'updated.x': 30631,
        'uploads': 30726,
        'user.changed_to.x': 30659,
        'user.default': 571,
        'user.enter_name': 30658,
        'user.new': 30656,
        'user.remove': 30662,
        'user.rename': 30663,
        'user.switch': 30655,
        'user.switch_to.x': 30665,
        'user.unnamed': 30657,
        'video.add_to_playlist': 30520,
        'video.comments': 30732,
        'video.comments.edited': 30735,
        'video.comments.likes': 30733,
        'video.comments.replies': 30734,
        'video.description_links': 30544,
        'video.description_links.from.x': 30118,
        'video.description_links.not_found': 30545,
        'video.disliked': 30538,
        'video.liked': 30508,
        'video.more': 22082,
        'video.play': 208,
        'video.play.ask_for_quality': 30730,
        'video.play.audio_only': 30708,
        'video.play.timeshift': 30819,
        'video.play.using': 15213,
        'video.play.with_subtitles': 30702,
        'video.queue': 13347,
        'video.rate': 30528,
        'video.rate.dislike': 30530,
        'video.rate.like': 30529,
        'video.rate.none': 15015,
        'video.related': 30514,
        'video.related.to.x': 30113,
        'videos': 3,
        'watch_later': 30107,
        'watch_later.add': 30107,
        'watch_later.clear': 30769,
        'watch_later.clear.check': 30770,
        'watch_later.list.unassign': 30568,
        'watch_later.list.unassign.check': 30569,
        'watch_later.list.assign': 30567,
        'watch_later.list.assign.check': 30570,
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
        'pageToken',
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

        atexit_register(self.tear_down)

    def init(self):
        num_args = len(sys.argv)
        if num_args:
            uri = to_unicode(sys.argv[0])
            if uri.startswith('plugin://'):
                self._plugin_handle = int(sys.argv[1])
            else:
                self._plugin_handle = -1
                return
        else:
            self._plugin_handle = -1
            return

        # first the path of the uri
        self.set_path(
            urlsplit(uri).path,
            force=True,
            parser=XbmcContextUI.get_infolabel,
            update_uri=False,
        )

        # after that try to get the params
        if num_args > 2:
            params = to_unicode(sys.argv[2][1:])
            self._param_string = params
            self._params = {}
            if params:
                self.parse_params(
                    dict(parse_qsl(params, keep_blank_values=True)),
                    parser=XbmcContextUI.get_infolabel,
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
    def get_language(region=True, separator='-', code_format=xbmc.ISO_639_1):
        _code_format = xbmc.ISO_639_1
        _language = xbmc.getLanguage(format=_code_format, region=region)
        if region:
            language, _, _region = _language.partition('-')
        else:
            language = _language
            _region = None

        if not language:
            _code_format = xbmc.ISO_639_2
            _language = xbmc.getLanguage(format=_code_format, region=False)
            if region:
                language, _, _region = _language.partition('-')
                _region = _region[:2]
            else:
                language = _language
                _region = None

        if language:
            if code_format is not None and _code_format != code_format:
                _language = xbmc.convertLanguage(language, code_format)
                if _language:
                    language = _language
                elif code_format == xbmc.ISO_639_1 and language != 'fil':
                    language = language[:2]
        elif code_format == xbmc.ISO_639_2:
            language = 'eng'
        else:
            language = 'en'

        if region:
            _region = _region.upper() if _region else 'US'
            return separator.join((language, _region))

        return language

    @classmethod
    def get_language_name(cls, language=None):
        if language is None:
            language = cls.get_language(code_format=None)
        return xbmc.convertLanguage(language, xbmc.ENGLISH_NAME).split(';')[0]

    @classmethod
    def get_player_language(cls):
        language = get_kodi_setting_value('locale.audiolanguage')
        prefer_default = get_kodi_setting_bool('videoplayer.preferdefaultflag')
        if not language or language == 'default':
            language = get_kodi_setting_value('locale.language')
            if language:
                code = language.replace('resource.language.', '').split('_')[0]
            else:
                code = None
        elif language not in cls._KODI_UI_PLAYER_LANGUAGE_OPTIONS:
            code = xbmc.convertLanguage(language, xbmc.ISO_639_1)
        else:
            return language, prefer_default
        if not code:
            code = cls.get_language(
                region=False,
                code_format=xbmc.ISO_639_1,
            )
        return code, prefer_default

    @classmethod
    def get_subtitle_language(cls):
        language = get_kodi_setting_value('locale.subtitlelanguage')
        if not language or language == 'default':
            language = get_kodi_setting_value('locale.language')
            if language:
                code = language.replace('resource.language.', '').split('_')[0]
            else:
                code = None
        elif language not in cls._KODI_UI_SUBTITLE_LANGUAGE_OPTIONS:
            code = xbmc.convertLanguage(language, xbmc.ISO_639_1)
        else:
            return None
        if not code:
            code = cls.get_language(
                region=False,
                code_format=xbmc.ISO_639_1,
            )
        return code

    def reload_access_manager(self):
        access_manager = AccessManager(proxy(self))
        self._access_manager = access_manager
        return access_manager

    def reload_api_store(self):
        api_store = APIKeyStore(proxy(self))
        self._api_store = api_store
        return api_store

    def get_playlist_player(self, playlist_type=None):
        if self.get_param(PLAY_FORCE_AUDIO) or self.get_settings().audio_only():
            playlist_type = 'audio'
        playlist_player = self._playlist
        if not playlist_player or playlist_type:
            playlist_player = XbmcPlaylistPlayer(proxy(self), playlist_type)
            self._playlist = playlist_player
        return playlist_player

    def get_ui(self):
        ui = self._ui
        if not ui:
            ui = XbmcContextUI(proxy(self))
            self._ui = ui
        return ui

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

    def localize(self, text_id, args=None, default_text=None):
        if isinstance(text_id, tuple):
            _args = text_id[1:]
            _text_id = text_id[0]
            localize_args = True
        else:
            _args = args
            _text_id = text_id
            localize_args = False

        if not isinstance(_text_id, int):
            try:
                _text_id = self.LOCAL_MAP[_text_id]
            except KeyError:
                try:
                    _text_id = int(_text_id)
                except (TypeError, ValueError):
                    _text_id = -1
        if _text_id <= 0:
            msg = 'Undefined string ID: {text_id!r}'
            if default_text is None:
                default_text = msg.format(text_id=text_id)
                self.log.warning(default_text)
            else:
                self.log.warning(msg, text_id=text_id)
            return default_text

        """
        We want to use all localization strings!
        Addons should only use the range 30000 through 30999
        (see: http://kodi.wiki/view/Language_support), but we do it anyway.
        I want some of the localized strings for the views of a skin.
        """
        source = self._addon if 30000 <= _text_id < 31000 else xbmc
        result = source.getLocalizedString(_text_id)
        if not result:
            msg = 'Untranslated string ID: {text_id!r}'
            if default_text is None:
                default_text = msg.format(text_id=text_id)
                self.log.warning(default_text)
            else:
                self.log.warning(msg, text_id=text_id)
            return default_text
        result = to_unicode(result)

        if _args:
            if localize_args:
                _args = tuple(self.localize(arg, default_text=arg)
                              for arg in _args)
            try:
                return result % _args
            except TypeError:
                self.log.exception(('Localization error',
                                    'String: {result!r} ({text_id!r})',
                                    'args:   {original_args!r}'),
                                   result=result,
                                   text_id=text_id,
                                   original_args=args)
        return result

    def apply_content(self,
                      content_type=None,
                      sub_type=None,
                      category_label=None):
        # ui local variable used for ui.get_view_manager() in unofficial version
        # noinspection PyUnusedLocal
        ui = self.get_ui()

        if content_type:
            self.log.debug('Applying content-type: {type!r} for {path!r}',
                           type=(sub_type or content_type),
                           path=self.get_path())
            if content_type != 'default':
                xbmcplugin.setContent(self._plugin_handle, content_type)

        if category_label is None:
            category_label = self.get_param('category_label')
        if category_label:
            xbmcplugin.setPluginCategory(self._plugin_handle, category_label)

        detailed_labels = self.get_settings().show_detailed_labels()
        if sub_type == CONTENT.HISTORY:
            self.add_sort_method(
                SORT.HISTORY_CONTENT_DETAILED
                if detailed_labels else
                SORT.HISTORY_CONTENT_SIMPLE
            )
        elif sub_type == CONTENT.COMMENTS:
            self.add_sort_method(
                SORT.COMMENTS_CONTENT_DETAILED
                if detailed_labels else
                SORT.COMMENTS_CONTENT_SIMPLE
            )
        elif sub_type == CONTENT.PLAYLIST:
            self.add_sort_method(
                SORT.PLAYLIST_CONTENT_DETAILED
                if detailed_labels else
                SORT.PLAYLIST_CONTENT_SIMPLE
            )
        elif content_type == CONTENT.VIDEO_CONTENT:
            self.add_sort_method(
                SORT.VIDEO_CONTENT_DETAILED
                if detailed_labels else
                SORT.VIDEO_CONTENT_SIMPLE
            )
        else:
            self.add_sort_method(
                SORT.LIST_CONTENT_DETAILED
                if detailed_labels else
                SORT.LIST_CONTENT_SIMPLE
            )

    if current_system_version.compatible(19):
        def add_sort_method(self,
                            sort_methods,
                            _add_sort_method=xbmcplugin.addSortMethod):
            handle = self._plugin_handle
            for sort_method in sort_methods:
                _add_sort_method(handle, *sort_method)
    else:
        def add_sort_method(self,
                            sort_methods,
                            _add_sort_method=xbmcplugin.addSortMethod):
            handle = self._plugin_handle
            for sort_method in sort_methods:
                _add_sort_method(handle, *sort_method[:3:2])

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
        new_context._api_store = self._api_store

        new_context._bookmarks_list = self._bookmarks_list
        new_context._data_cache = self._data_cache
        new_context._feed_history = self._feed_history
        new_context._function_cache = self._function_cache
        new_context._playback_history = self._playback_history
        new_context._requests_cache = self._requests_cache
        new_context._search_history = self._search_history
        new_context._watch_later_list = self._watch_later_list

        new_context._ui = self._ui
        new_context._playlist = self._playlist

        return new_context

    def execute(self,
                command,
                wait=False,
                wait_for=None,
                wait_for_set=True,
                block_ui=None,
                _execute=xbmc.executebuiltin):
        if not wait_for:
            if block_ui is False:
                _execute('Dialog.Close(all,true)')
            _execute(command, wait)
            return

        ui = self.get_ui()
        wait_for_abort = xbmc.Monitor().waitForAbort

        if block_ui is False:
            _execute('Dialog.Close(all,true)')
        _execute(command, wait)

        if block_ui:
            _execute('ActivateWindow(busydialognocancel)')

        if isinstance(wait_for, tuple):
            wait_for, wait_for_kwargs, delay = wait_for
            while not wait_for(**wait_for_kwargs) and not wait_for_abort(delay):
                pass
        elif wait_for_set:
            ui.clear_property(wait_for)
            pop_property = ui.pop_property
            while not pop_property(wait_for) and not wait_for_abort(1):
                pass
        else:
            get_property = ui.get_property
            while get_property(wait_for) and not wait_for_abort(1):
                pass

        if block_ui:
            _execute('Dialog.Close(busydialognocancel)')

    @staticmethod
    def sleep(timeout=None):
        return wait(timeout)

    def addon_enabled(self, addon_id):
        response = jsonrpc(method='Addons.GetAddonDetails',
                           params={'addonid': addon_id,
                                   'properties': ['enabled']})
        try:
            return response['result']['addon']['enabled'] is True
        except (KeyError, TypeError):
            error = response.get('error', {})
            self.log.exception(('Error',
                                'Code:    {code}',
                                'Message: {message}'),
                               code=error.get('code', 'Unknown'),
                               message=error.get('message', 'Unknown'))
            return False

    def set_addon_enabled(self, addon_id, enabled=True):
        response = jsonrpc(method='Addons.SetAddonEnabled',
                           params={'addonid': addon_id,
                                   'enabled': enabled})
        try:
            return response['result'] == 'OK'
        except (KeyError, TypeError):
            error = response.get('error', {})
            self.log.exception(('Error',
                                'Code:    {code}',
                                'Message: {message}'),
                               code=error.get('code', 'Unknown'),
                               message=error.get('message', 'Unknown'))
            return False

    @staticmethod
    def send_notification(method, data=True, sender=ADDON_ID):
        jsonrpc(method='JSONRPC.NotifyAll',
                params={'sender': sender,
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
        # subtitles
        'vtt': loose_version('2.3.8'),
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
        return self.get_ui().get_property(
            ABORT_FLAG, stacklevel=3, as_bool=True
        )

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
            '_api_store',
            '_access_manager',
        )
        for attr in attrs:
            try:
                delattr(self, attr)
                setattr(self, attr, None)
            except AttributeError:
                pass

    def ipc_exec(self, target, timeout=None, payload=None, raise_exc=False):
        if not XbmcContextUI.get_property(SERVICE_RUNNING_FLAG, as_bool=True):
            msg = 'Service IPC - Monitor has not started'
            XbmcContextUI.set_property(SERVICE_RUNNING_FLAG, BUSY_FLAG)
            if raise_exc:
                raise RuntimeError(msg)
            self.log.warning_trace(msg)
            return None

        data = {'target': target, 'response_required': bool(timeout)}
        if payload:
            data.update(payload)
        self.send_notification(SERVICE_IPC, data)

        if not timeout:
            return None
        if timeout < 0:
            timeout = None

        response = IPCMonitor(target, timeout)
        if response.received:
            value = response.value
            if value:
                self.log.debug(('Service IPC - Responded',
                                'Procedure: {target!r}',
                                'Latency:   {latency:.2f}ms'),
                               target=target,
                               latency=response.latency)
            elif value is False:
                self.log.error_trace(('Service IPC - Failed',
                                      'Procedure: {target!r}',
                                      'Latency:   {latency:.2f}ms'),
                                     target=target,
                                     latency=response.latency)
        else:
            value = None
            self.log.error_trace(('Service IPC - Timed out',
                                  'Procedure: {target!r}',
                                  'Timeout:   {timeout:.2f}s'),
                                 target=target,
                                 timeout=timeout)
        return value

    def is_plugin_folder(self, folder_name=None):
        if folder_name is None:
            folder_name = XbmcContextUI.get_container_info(FOLDER_NAME,
                                                           container_id=None)
        return folder_name == self._plugin_name

    def refresh_requested(self, force=False, on=False, off=False, params=None):
        if params is None:
            params = self.get_params()
        refresh = params.get('refresh')
        if not force:
            return refresh and refresh > 0

        if refresh is None:
            refresh = 0
        if off:
            if refresh > 0:
                refresh = -refresh
        elif on or refresh:
            if refresh < 0:
                refresh = -refresh
            refresh += 1

        return refresh

    def parse_item_ids(self,
                       uri='',
                       from_listitem=True,
                       _ids={'video': VIDEO_ID,
                             'channel': CHANNEL_ID,
                             'playlist': PLAYLIST_ID}):
        item_ids = {}
        if not uri and from_listitem:
            uri = XbmcContextUI.get_listitem_info(URI)
        if not uri or not self.is_plugin_path(uri):
            return item_ids
        uri = urlsplit(uri)

        path = uri.path.rstrip('/')
        while path:
            id_type, _, next_part = path.partition('/')
            if not next_part:
                break

            if id_type in _ids:
                id_value = next_part.partition('/')[0]
                if id_value:
                    item_ids[_ids[id_type]] = id_value

            path = next_part

        params = dict(parse_qsl(uri.query))
        for name in _ids.values():
            id_value = params.get(name)
            if not id_value and from_listitem:
                id_value = XbmcContextUI.get_listitem_property(name)
            if id_value:
                item_ids[name] = id_value

        return item_ids
