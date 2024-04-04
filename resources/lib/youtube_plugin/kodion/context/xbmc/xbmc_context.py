# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import sys
import weakref

from ..abstract_context import AbstractContext
from ...compatibility import (
    parse_qsl,
    unquote,
    urlsplit,
    xbmc,
    xbmcaddon,
    xbmcplugin,
)
from ...constants import ADDON_ID, content, sort
from ...player import XbmcPlayer, XbmcPlaylist
from ...settings import XbmcPluginSettings
from ...ui import XbmcContextUI
from ...utils import (
    current_system_version,
    get_kodi_setting_value,
    jsonrpc,
    loose_version,
    make_dirs,
    to_unicode,
    wait,
)


class XbmcContext(AbstractContext):
    LOCAL_MAP = {
        'api.id': 30202,
        'api.key': 30201,
        'api.key.incorrect': 30648,
        'api.personal.enabled': 30598,
        'api.personal.failed': 30599,
        'api.secret': 30203,
        'archive': 30105,
        'are_you_sure': 30703,
        'auto_remove_watch_later': 30515,
        'browse_channels': 30512,
        'cancel': 30615,
        'channels': 30500,
        'client.id.incorrect': 30649,
        'client.ip': 30700,
        'client.ip.failed': 30701,
        'client.secret.incorrect': 30650,
        'content.clear': 30121,
        'content.clear.confirm': 30120,
        'content.delete': 30116,
        'content.delete.confirm': 30114,
        'content.remove': 30117,
        'content.remove.confirm': 30115,
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
        'delete': 30118,
        'disliked.video': 30717,
        'error.no_video_streams_found': 30549,
        'error.rtmpe_not_supported': 30542,
        'failed': 30576,
        'failed.watch_later.retry': 30614,
        'failed.watch_later.retry.2': 30709,
        'failed.watch_later.retry.3': 30710,
        'favorites': 30100,
        'favorites.add': 30101,
        'favorites.remove': 30108,
        'go_to_channel': 30502,
        'highlights': 30104,
        'history': 30509,
        'history.clear': 30609,
        'history.clear.confirm': 30610,
        'history.list.remove': 30572,
        'history.list.remove.confirm': 30573,
        'history.list.set': 30571,
        'history.list.set.confirm': 30574,
        'history.mark.unwatched': 30669,
        'history.mark.watched': 30670,
        'history.remove': 30108,
        'history.reset.resume_point': 30674,
        'httpd.not.running': 30699,
        'inputstreamhelper.is_installed': 30625,
        'isa.enable.confirm': 30579,
        'key.requirement': 30731,
        'latest_videos': 30109,
        'library': 30103,
        'liked.video': 30716,
        'live': 30539,
        'live.completed': 30647,
        'live.upcoming': 30646,
        'maintenance.data_cache': 30687,
        'maintenance.function_cache': 30557,
        'maintenance.playback_history': 30673,
        'maintenance.search_history': 30558,
        'maintenance.watch_later': 30782,
        'must_be_signed_in': 30616,
        'my_channel': 30507,
        'my_location': 30654,
        'my_subscriptions': 30510,
        'my_subscriptions.filter.add': 30587,
        'my_subscriptions.filter.added': 30589,
        'my_subscriptions.filter.remove': 30588,
        'my_subscriptions.filter.removed': 30590,
        'my_subscriptions.filtered': 30584,
        'next_page': 30106,
        'none': 30561,
        'playlist.added_to': 30714,
        'playlist.create': 30522,
        'playlist.play.all': 30531,
        'playlist.play.default': 30532,
        'playlist.play.from_here': 30537,
        'playlist.play.reverse': 30533,
        'playlist.play.select': 30535,
        'playlist.play.shuffle': 30534,
        'playlist.progress.updating': 30536,
        'playlist.removed_from': 30715,
        'playlist.select': 30521,
        'playlists': 30501,
        'please_wait': 30119,
        'prompt': 30566,
        'purchases': 30622,
        'recommendations': 30551,
        'refresh': 30543,
        'related_videos': 30514,
        'remove': 30108,
        'removed': 30666,
        'rename': 30113,
        'renamed': 30667,
        'requires.krypton': 30624,
        'reset.access_manager.confirm': 30581,
        'retry': 30612,
        'saved.playlists': 30611,
        'search': 30102,
        'search.clear': 30556,
        'search.new': 30110,
        'search.quick': 30605,
        'search.quick.incognito': 30606,
        'search.remove': 30108,
        'search.rename': 30113,
        'search.title': 30102,
        'select.listen.ip': 30644,
        'select_video_quality': 30010,
        'settings': 30577,
        'setup_wizard': 30526,
        'setup_wizard.capabilities': 30786,
        'setup_wizard.capabilities.720p30': 30787,
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
        'setup_wizard.prompt.settings': 30577,
        'setup_wizard.prompt.settings.defaults': 30783,
        'setup_wizard.prompt.settings.list_details': 30784,
        'setup_wizard.prompt.settings.performance': 30785,
        'setup_wizard.prompt.subtitles': 30600,
        'sign.enter_code': 30519,
        'sign.go_to': 30518,
        'sign.in': 30111,
        'sign.out': 30112,
        'sign.twice.text': 30547,
        'sign.twice.title': 30546,
        'stats.commentCount': 30732,
        # 'stats.favoriteCount': 30100,
        'stats.likeCount': 30733,
        'stats.viewCount': 30767,
        'stream.alternate': 30747,
        'stream.automatic': 30583,
        'stream.descriptive': 30746,
        'stream.dubbed': 30745,
        'stream.multi_audio': 30763,
        'stream.multi_language': 30762,
        'stream.original': 30744,
        'subscribe': 30506,
        'subscribe_to': 30517,
        'subscribed.to.channel': 30719,
        'subscriptions': 30504,
        'subtitles.download': 30705,
        'subtitles.download.pre': 30706,
        'subtitles.all': 30774,
        'subtitles.language': 30560,
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
        'user.default': 30532,
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
        'video.more': 30548,
        'video.play.ask_for_quality': 30730,
        'video.play.audio_only': 30708,
        'video.play.with': 30540,
        'video.play.with_subtitles': 30702,
        'video.queue': 30511,
        'video.rate': 30528,
        'video.rate.dislike': 30530,
        'video.rate.like': 30529,
        'video.rate.none': 30108,
        'watch_later': 30107,
        'watch_later.add': 30107,
        'watch_later.added_to': 30713,
        'watch_later.clear': 30769,
        'watch_later.clear.confirm': 30770,
        'watch_later.list.remove': 30568,
        'watch_later.list.remove.confirm': 30569,
        'watch_later.list.set': 30567,
        'watch_later.list.set.confirm': 30570,
        'watch_later.remove': 30108,
        'watch_later.retrieval_page': 30711,
        'youtube': 30003,
    }

    def __init__(self,
                 path='/',
                 params=None,
                 plugin_name='',
                 plugin_id='',
                 override=True):
        super(XbmcContext, self).__init__(path, params, plugin_name, plugin_id)

        self._addon = xbmcaddon.Addon(id=(plugin_id if plugin_id else ADDON_ID))

        """
        I don't know what xbmc/kodi is doing with a simple uri, but we have to extract the information from the
        sys parameters and re-build our clean uri.
        Also we extract the path and parameters - man, that would be so simple with the normal url-parsing routines.
        """
        num_args = len(sys.argv)
        if override and num_args:
            uri = sys.argv[0]
            is_plugin_invocation = uri.startswith('plugin://')
            if is_plugin_invocation:
                # first the path of the uri
                parsed_url = urlsplit(uri)
                self._path = unquote(parsed_url.path)

                # after that try to get the params
                if num_args > 2:
                    params = sys.argv[2][1:]
                    if params:
                        self.parse_params(dict(parse_qsl(params)))

                # then Kodi resume status
                if num_args > 3 and sys.argv[3].lower() == 'resume:true':
                    self._params['resume'] = True

                self._uri = self.create_uri(self._path, self._params)
        elif num_args:
            uri = sys.argv[0]
            is_plugin_invocation = uri.startswith('plugin://')
        else:
            is_plugin_invocation = False

        self._ui = None
        self._video_playlist = None
        self._audio_playlist = None
        self._video_player = None
        self._audio_player = None
        self._plugin_handle = int(sys.argv[1]) if is_plugin_invocation else -1
        self._plugin_id = plugin_id or ADDON_ID
        self._plugin_name = plugin_name or self._addon.getAddonInfo('name')
        self._version = self._addon.getAddonInfo('version')
        self._addon_path = make_dirs(self._addon.getAddonInfo('path'))
        self._data_path = make_dirs(self._addon.getAddonInfo('profile'))
        self._settings = XbmcPluginSettings(self._addon)

    def get_region(self):
        pass  # implement from abstract

    def addon(self):
        return self._addon

    def is_plugin_path(self, uri, uri_path=''):
        return uri.startswith('plugin://%s/%s' % (self.get_id(), uri_path))

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
        lang_code, seperator, region = language.partition('-')
        if not lang_code:
            language = xbmc.getLanguage(format=xbmc.ISO_639_2, region=False)
            lang_code, seperator, region = language.partition('-')
        if not lang_code:
            return 'en-US'
        if region:
            return seperator.join((lang_code.lower(), region.upper()))
        return lang_code

    def get_language_name(self, lang_id=None):
        if lang_id is None:
            lang_id = self.get_language()
        return xbmc.convertLanguage(lang_id, xbmc.ENGLISH_NAME).split(';')[0]

    def get_subtitle_language(self):
        sub_language = get_kodi_setting_value('locale.subtitlelanguage')
        # https://github.com/xbmc/xbmc/blob/master/xbmc/LangInfo.cpp#L1242
        if sub_language not in (None,  # No setting value
                                self.localize(231),  # None
                                self.localize(13207),  # Forced only
                                self.localize(308),  # Original language
                                self.localize(309)):  # UI language
            sub_language = xbmc.convertLanguage(sub_language, xbmc.ISO_639_1)
        else:
            sub_language = None
        return sub_language

    def get_video_playlist(self):
        if not self._video_playlist:
            self._video_playlist = XbmcPlaylist('video', weakref.proxy(self))
        return self._video_playlist

    def get_audio_playlist(self):
        if not self._audio_playlist:
            self._audio_playlist = XbmcPlaylist('audio', weakref.proxy(self))
        return self._audio_playlist

    def get_video_player(self):
        if not self._video_player:
            self._video_player = XbmcPlayer('video', weakref.proxy(self))
        return self._video_player

    def get_audio_player(self):
        if not self._audio_player:
            self._audio_player = XbmcPlayer('audio', weakref.proxy(self))
        return self._audio_player

    def get_ui(self):
        if not self._ui:
            self._ui = XbmcContextUI(self._addon, weakref.proxy(self))
        return self._ui

    def get_handle(self):
        return self._plugin_handle

    def get_data_path(self):
        return self._data_path

    def get_addon_path(self):
        return self._addon_path

    def get_settings(self):
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
        self.log_debug('Setting content-type: |{type}| for |{path}|'.format(
            type=(sub_type or content_type), path=self.get_path()
        ))
        xbmcplugin.setContent(self._plugin_handle, content_type)
        self.get_ui().get_view_manager().set_view_mode(content_type)
        if category_label is None:
            category_label = self.get_param('category_label')
        if category_label:
            xbmcplugin.setPluginCategory(self._plugin_handle, category_label)
        detailed_labels = self.get_settings().show_detailed_labels()
        if sub_type == 'history':
            self.add_sort_method(
                (sort.LASTPLAYED,       '%T \u2022 %P',           '%D | %J'),
                (sort.PLAYCOUNT,        '%T \u2022 %P',           '%D | %J'),
                (sort.UNSORTED,         '%T \u2022 %P',           '%D | %J'),
                (sort.LABEL,            '%T \u2022 %P',           '%D | %J'),
            ) if detailed_labels else self.add_sort_method(
                (sort.LASTPLAYED,),
                (sort.PLAYCOUNT,),
                (sort.UNSORTED,),
                (sort.LABEL,),
            )
        else:
            self.add_sort_method(
                (sort.UNSORTED,         '%T \u2022 %P',           '%D | %J'),
                (sort.LABEL,            '%T \u2022 %P',           '%D | %J'),
            ) if detailed_labels else self.add_sort_method(
                (sort.UNSORTED,),
                (sort.LABEL,),
            )
        if content_type == content.VIDEO_CONTENT:
            self.add_sort_method(
                (sort.CHANNEL,          '[%A - ]%T \u2022 %P',    '%D | %J'),
                (sort.ARTIST,           '%T \u2022 %P | %D | %J', '%A'),
                (sort.PROGRAM_COUNT,    '%T \u2022 %P | %D | %J', '%C'),
                (sort.VIDEO_RATING,     '%T \u2022 %P | %D | %J', '%R'),
                (sort.DATE,             '%T \u2022 %P | %D',      '%J'),
                (sort.DATEADDED,        '%T \u2022 %P | %D',      '%a'),
                (sort.VIDEO_RUNTIME,    '%T \u2022 %P | %J',      '%D'),
                (sort.TRACKNUM,         '[%N. ]%T \u2022 %P',     '%D | %J'),
            ) if detailed_labels else self.add_sort_method(
                (sort.CHANNEL,          '[%A - ]%T'),
                (sort.ARTIST,),
                (sort.PROGRAM_COUNT,),
                (sort.VIDEO_RATING,),
                (sort.DATE,),
                (sort.DATEADDED,),
                (sort.VIDEO_RUNTIME,),
                (sort.TRACKNUM,         '[%N. ]%T '),
            )

    def add_sort_method(self, *sort_methods):
        args = slice(None if current_system_version.compatible(19, 0) else 2)
        for sort_method in sort_methods:
            xbmcplugin.addSortMethod(self._plugin_handle, *sort_method[args])

    def clone(self, new_path=None, new_params=None):
        if not new_path:
            new_path = self.get_path()

        if not new_params:
            new_params = self.get_params()

        new_context = XbmcContext(path=new_path,
                                  params=new_params,
                                  plugin_name=self._plugin_name,
                                  plugin_id=self._plugin_id,
                                  override=False)
        new_context._function_cache = self._function_cache
        new_context._search_history = self._search_history
        new_context._favorite_list = self._favorite_list
        new_context._watch_later_list = self._watch_later_list
        new_context._access_manager = self._access_manager
        new_context._ui = self._ui
        new_context._video_playlist = self._video_playlist
        new_context._video_player = self._video_player

        return new_context

    def execute(self, command, wait=False, wait_for=None):
        xbmc.executebuiltin(command, wait)
        if wait_for:
            ui = self.get_ui()
            monitor = xbmc.Monitor()
            while not monitor.abortRequested():
                monitor.waitForAbort(1)
                if not ui.get_property(wait_for):
                    break

    @staticmethod
    def sleep(timeout=None):
        wait(timeout)

    def addon_enabled(self, addon_id):
        response = jsonrpc(method='Addons.GetAddonDetails',
                           params={'addonid': addon_id,
                                   'properties': ['enabled']})
        try:
            return response['result']['addon']['enabled'] is True
        except (KeyError, TypeError):
            error = response.get('error', {})
            self.log_error('XbmcContext.addon_enabled error - |{0}: {1}|'
                           .format(error.get('code', 'unknown'),
                                   error.get('message', 'unknown')))
            return False

    def set_addon_enabled(self, addon_id, enabled=True):
        response = jsonrpc(method='Addons.SetAddonEnabled',
                           params={'addonid': addon_id,
                                   'enabled': enabled})
        try:
            return response['result'] == 'OK'
        except (KeyError, TypeError):
            error = response.get('error', {})
            self.log_error('XbmcContext.set_addon_enabled error - |{0}: {1}|'
                           .format(error.get('code', 'unknown'),
                                   error.get('message', 'unknown')))
            return False

    def send_notification(self, method, data):
        self.log_debug('send_notification: |%s| -> |%s|' % (method, data))
        jsonrpc(method='JSONRPC.NotifyAll',
                params={'sender': ADDON_ID,
                        'message': method,
                        'data': data},
                no_response=True)

    def use_inputstream_adaptive(self):
        if self._settings.use_isa():
            if self.addon_enabled('inputstream.adaptive'):
                success = True
            elif self.get_ui().on_yes_no_input(
                self.get_name(), self.localize('isa.enable.confirm')
            ):
                success = self.set_addon_enabled('inputstream.adaptive')
            else:
                success = False
        else:
            success = False
        return success

    # Values of capability map can be any of the following:
    # - required version number, as string param to loose_version() to compare
    # against installed InputStream.Adaptive version
    # - any Falsy value to exclude capability regardless of version
    # - True to include capability regardless of version
    _ISA_CAPABILITIES = {
        'live': loose_version('2.0.12'),
        'drm': loose_version('2.2.12'),
        'ttml': loose_version('20.0.0'),
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
    }

    def inputstream_adaptive_capabilities(self, capability=None):
        # Returns a frozenset of capabilities supported by installed ISA version
        # If capability param is provided, returns True if the installed version
        # of ISA supports the nominated capability, False otherwise

        try:
            addon = xbmcaddon.Addon('inputstream.adaptive')
            inputstream_version = addon.getAddonInfo('version')
        except RuntimeError:
            inputstream_version = ''

        if not self.use_inputstream_adaptive() or not inputstream_version:
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
        return self.get_ui().get_property('abort_requested').lower() == 'true'

    @staticmethod
    def get_infolabel(name):
        return xbmc.getInfoLabel(name)

    @staticmethod
    def get_listitem_detail(detail_name, attr=False):
        return xbmc.getInfoLabel(
            'Container.ListItem(0).{0}'.format(detail_name)
            if attr else
            'Container.ListItem(0).Property({0})'.format(detail_name)
        )

    def tear_down(self):
        self._settings.flush()
        del self._addon
        self._addon = None
