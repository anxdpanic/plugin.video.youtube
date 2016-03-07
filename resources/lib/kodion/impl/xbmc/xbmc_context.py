import sys
import urllib
import urlparse
import weakref
import datetime

import xbmc
import xbmcaddon

import xbmcplugin
import xbmcvfs
from ..abstract_context import AbstractContext
from .xbmc_plugin_settings import XbmcPluginSettings
from .xbmc_context_ui import XbmcContextUI
from .xbmc_system_version import XbmcSystemVersion
from .xbmc_playlist import XbmcPlaylist
from .xbmc_player import XbmcPlayer
from ... import utils


class XbmcContext(AbstractContext):
    def __init__(self, path='/', params=None, plugin_name=u'', plugin_id=u'', override=True):
        AbstractContext.__init__(self, path, params, plugin_name, plugin_id)

        if plugin_id:
            self._addon = xbmcaddon.Addon(id=plugin_id)
        else:
            self._addon = xbmcaddon.Addon()
            pass

        self._system_version = None

        """
        I don't know what xbmc/kodi is doing with a simple uri, but we have to extract the information from the
        sys parameters and re-build our clean uri.
        Also we extract the path and parameters - man, that would be so simple with the normal url-parsing routines.
        """
        # first the path of the uri
        if override:
            self._uri = sys.argv[0]
            comps = urlparse.urlparse(self._uri)
            self._path = urllib.unquote(comps.path).decode('utf-8')

            # after that try to get the params
            params = sys.argv[2][1:]
            if len(params) > 0:
                self._uri = self._uri + '?' + params

                self._params = {}
                params = dict(urlparse.parse_qsl(params))
                for _param in params:
                    item = params[_param]
                    self._params[_param] = item.decode('utf-8')
                    pass
                pass
            pass

        self._ui = None
        self._video_playlist = None
        self._audio_playlist = None
        self._video_player = None
        self._audio_player = None
        self._plugin_handle = int(sys.argv[1])
        self._plugin_id = plugin_id or self._addon.getAddonInfo('id')
        self._plugin_name = plugin_name or self._addon.getAddonInfo('name')
        self._version = self._addon.getAddonInfo('version')
        self._native_path = xbmc.translatePath(self._addon.getAddonInfo('path'))
        self._settings = XbmcPluginSettings(self._addon)

        """
        Set the data path for this addon and create the folder
        """
        self._data_path = xbmc.translatePath('special://profile/addon_data/%s' % self._plugin_id)
        if isinstance(self._data_path, str):
            self._data_path = self._data_path.decode('utf-8')
            pass
        if not xbmcvfs.exists(self._data_path):
            xbmcvfs.mkdir(self._data_path)
            pass
        pass

    def format_date_short(self, date_obj):
        date_format = xbmc.getRegion('dateshort')
        _date_obj = date_obj
        if isinstance(_date_obj, datetime.date):
            _date_obj = datetime.datetime(_date_obj.year, _date_obj.month, _date_obj.day)
            pass

        return _date_obj.strftime(date_format)

    def format_time(self, time_obj):
        time_format = xbmc.getRegion('time')
        _time_obj = time_obj
        if isinstance(_time_obj, datetime.time):
            _time_obj = datetime.time(_time_obj.hour, _time_obj.minute, _time_obj.second)
            pass

        return _time_obj.strftime(time_format)

    def get_language(self):
        """
        The xbmc.getLanguage() method is fucked up!!! We always return 'en-US' for now
        """
        return 'en-US'

        """
        if self.get_system_version().get_name() == 'Frodo':
            return 'en-US'

        try:
            language = xbmc.getLanguage(0, region=True)
            language = language.split('-')
            language = '%s-%s' % (language[0].lower(), language[1].upper())
            return language
        except Exception, ex:
            self.log_error('Failed to get system language (%s)', ex.__str__())
            return 'en-US'
        pass
        """

    def get_system_version(self):
        if not self._system_version:
            self._system_version = XbmcSystemVersion(version='', name='')
            pass

        return self._system_version

    def get_video_playlist(self):
        if not self._video_playlist:
            self._video_playlist = XbmcPlaylist('video', weakref.proxy(self))
            pass
        return self._video_playlist

    def get_audio_playlist(self):
        if not self._audio_playlist:
            self._audio_playlist = XbmcPlaylist('audio', weakref.proxy(self))
            pass
        return self._audio_playlist

    def get_video_player(self):
        if not self._video_player:
            self._video_player = XbmcPlayer('video', weakref.proxy(self))
            pass
        return self._video_player

    def get_audio_player(self):
        if not self._audio_player:
            self._audio_player = XbmcPlayer('audio', weakref.proxy(self))
            pass
        return self._audio_player

    def get_ui(self):
        if not self._ui:
            self._ui = XbmcContextUI(self._addon, weakref.proxy(self))
            pass
        return self._ui

    def get_handle(self):
        return self._plugin_handle

    def get_data_path(self):
        return self._data_path

    def get_native_path(self):
        return self._native_path

    def get_settings(self):
        return self._settings

    def localize(self, text_id, default_text=u''):
        if isinstance(text_id, int):
            """
            We want to use all localization strings!
            Addons should only use the range 30000 thru 30999 (see: http://kodi.wiki/view/Language_support) but we
            do it anyway. I want some of the localized strings for the views of a skin.
            """
            if text_id >= 0 and (text_id < 30000 or text_id > 30999):
                result = xbmc.getLocalizedString(text_id)
                if result is not None and result:
                    return utils.to_unicode(result)
                pass
            pass

        result = self._addon.getLocalizedString(int(text_id))
        if result is not None and result:
            return utils.to_unicode(result)

        return utils.to_unicode(default_text)

    def set_content_type(self, content_type):
        self.log_debug('Setting content-type: "%s" for "%s"' % (content_type, self.get_path()))
        xbmcplugin.setContent(self._plugin_handle, content_type)
        self.get_ui().set_view_mode(content_type)
        pass

    def add_sort_method(self, *sort_methods):
        for sort_method in sort_methods:
            xbmcplugin.addSortMethod(self._plugin_handle, sort_method)
            pass
        pass

    def clone(self, new_path=None, new_params=None):
        if not new_path:
            new_path = self.get_path()
            pass

        if not new_params:
            new_params = self.get_params()
            pass

        new_context = XbmcContext(path=new_path, params=new_params, plugin_name=self._plugin_name,
                                  plugin_id=self._plugin_id, override=False)
        new_context._function_cache = self._function_cache
        new_context._search_history = self._search_history
        new_context._favorite_list = self._favorite_list
        new_context._watch_later_list = self._watch_later_list
        new_context._access_manager = self._access_manager
        new_context._ui = self._ui
        new_context._video_playlist = self._video_playlist
        new_context._video_player = self._video_player

        return new_context

    def execute(self, command):
        xbmc.executebuiltin(command)
        pass

    def sleep(self, milli_seconds):
        xbmc.sleep(milli_seconds)
        pass

    pass