# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import os
import re
import shutil
import socket
from base64 import b64decode

from .client import YouTube
from .helper import (
    ResourceManager,
    UrlResolver,
    UrlToItemConverter,
    v3,
    yt_context_menu,
    yt_login,
    yt_old_actions,
    yt_play,
    yt_playlist,
    yt_setup_wizard,
    yt_specials,
    yt_subscriptions,
    yt_video,
)
from .youtube_exceptions import InvalidGrant, LoginException
from ..kodion import (AbstractProvider, RegisterProviderPath, constants)
from ..kodion.compatibility import xbmcaddon, xbmcvfs
from ..kodion.items import DirectoryItem, NewSearchItem, SearchItem
from ..kodion.network import get_client_ip_address, is_httpd_live
from ..kodion.utils import find_video_id, strip_html_from_text


class Provider(AbstractProvider):
    def __init__(self):
        super(Provider, self).__init__()
        self._resource_manager = None

        self._client = None
        self._is_logged_in = False

        self.yt_video = yt_video

    def get_wizard_supported_views(self):
        return ['default', 'episodes']

    def get_wizard_steps(self, context):
        return [(yt_setup_wizard.process, [self, context])]

    def is_logged_in(self):
        return self._is_logged_in

    @staticmethod
    def get_dev_config(context, addon_id, dev_configs):
        _dev_config = context.get_ui().get_property('configs')
        context.get_ui().clear_property('configs')

        dev_config = {}
        if _dev_config:
            context.log_debug('Using window property for developer keys is deprecated, instead use the youtube_registration module.')
            try:
                dev_config = json.loads(_dev_config)
            except ValueError:
                context.log_error('Error loading developer key: |invalid json|')
        if not dev_config and addon_id and dev_configs:
            dev_config = dev_configs.get(addon_id)

        if dev_config and not context.get_settings().allow_dev_keys():
            context.log_debug('Developer config ignored')
            return None

        if dev_config:
            if not dev_config.get('main') or not dev_config['main'].get('key') \
                    or not dev_config['main'].get('system') or not dev_config.get('origin') \
                    or not dev_config['main'].get('id') or not dev_config['main'].get('secret'):
                context.log_error('Error loading developer config: |invalid structure| '
                                  'expected: |{"origin": ADDON_ID, "main": {"system": SYSTEM_NAME, "key": API_KEY, "id": CLIENT_ID, "secret": CLIENT_SECRET}}|')
                return {}
            dev_origin = dev_config['origin']
            dev_main = dev_config['main']
            dev_system = dev_main['system']
            if dev_system == 'JSONStore':
                dev_key = b64decode(dev_main['key'])
                dev_id = b64decode(dev_main['id'])
                dev_secret = b64decode(dev_main['secret'])
            else:
                dev_key = dev_main['key']
                dev_id = dev_main['id']
                dev_secret = dev_main['secret']
            context.log_debug('Using developer config: origin: |{0}| system |{1}|'.format(dev_origin, dev_system))
            return {'origin': dev_origin, 'main': {'id': dev_id, 'secret': dev_secret, 'key': dev_key, 'system': dev_system}}

        return {}

    def reset_client(self):
        self._client = None

    def get_client(self, context):
        if self._client is not None:
            return self._client
        # set the items per page (later)
        settings = context.get_settings()
        access_manager = context.get_access_manager()

        items_per_page = settings.get_items_per_page()

        language = settings.get_string('youtube.language', 'en-US')
        region = settings.get_string('youtube.region', 'US')

        api_last_origin = access_manager.get_last_origin()

        youtube_config = YouTube.CONFIGS.get('main')

        dev_id = context.get_param('addon_id')
        dev_configs = YouTube.CONFIGS.get('developer')
        dev_config = self.get_dev_config(context, dev_id, dev_configs)
        dev_keys = dev_config.get('main') if dev_config else None

        refresh_tokens = []

        if dev_id:
            dev_origin = dev_config.get('origin') if dev_config.get('origin') else dev_id
            if api_last_origin != dev_origin:
                context.log_debug('API key origin changed, clearing cache. |%s|' % dev_origin)
                access_manager.set_last_origin(dev_origin)
                self.get_resource_manager(context).clear()
        elif api_last_origin != 'plugin.video.youtube':
            context.log_debug('API key origin changed, clearing cache. |plugin.video.youtube|')
            access_manager.set_last_origin('plugin.video.youtube')
            self.get_resource_manager(context).clear()

        if dev_id:
            access_tokens = access_manager.get_dev_access_token(dev_id).split('|')
            if len(access_tokens) != 2 or access_manager.is_dev_access_token_expired(dev_id):
                # reset access_token
                access_manager.update_dev_access_token(dev_id, '')
                access_tokens = []
        else:
            access_tokens = access_manager.get_access_token().split('|')
            if len(access_tokens) != 2 or access_manager.is_access_token_expired():
                # reset access_token
                access_manager.update_access_token('')
                access_tokens = []

        if dev_id:
            if dev_keys:
                context.log_debug('Selecting YouTube developer config "%s"' % dev_id)
            else:
                context.log_debug('Selecting YouTube config "%s" w/ developer access tokens' % youtube_config['system'])

            if access_manager.developer_has_refresh_token(dev_id):
                if dev_keys:
                    keys_changed = access_manager.dev_keys_changed(dev_id, dev_keys['key'], dev_keys['id'], dev_keys['secret'])
                else:
                    keys_changed = access_manager.dev_keys_changed(dev_id, youtube_config['key'], youtube_config['id'], youtube_config['secret'])

                if keys_changed:
                    context.log_warning('API key set changed: Resetting client and updating access token')
                    self.reset_client()
                    access_manager.update_dev_access_token(dev_id, access_token='', refresh_token='')

                access_tokens = access_manager.get_dev_access_token(dev_id)
                if access_tokens:
                    access_tokens = access_tokens.split('|')

                refresh_tokens = access_manager.get_dev_refresh_token(dev_id)
                if refresh_tokens:
                    refresh_tokens = refresh_tokens.split('|')
                context.log_debug('Access token count: |%d| Refresh token count: |%d|' % (len(access_tokens), len(refresh_tokens)))
        else:
            context.log_debug('Selecting YouTube config "%s"' % youtube_config['system'])

            if access_manager.has_refresh_token():
                if YouTube.api_keys_changed:
                    context.log_warning('API key set changed: Resetting client and updating access token')
                    self.reset_client()
                    access_manager.update_access_token(access_token='', refresh_token='')

                access_tokens = access_manager.get_access_token()
                if access_tokens:
                    access_tokens = access_tokens.split('|')

                refresh_tokens = access_manager.get_refresh_token()
                if refresh_tokens:
                    refresh_tokens = refresh_tokens.split('|')
                context.log_debug('Access token count: |%d| Refresh token count: |%d|' % (len(access_tokens), len(refresh_tokens)))

        client = YouTube(language=language,
                         region=region,
                         items_per_page=items_per_page,
                         config=dev_keys if dev_keys else youtube_config)

        with client:
            if not refresh_tokens or not refresh_tokens[0]:
                client.set_log_error(context.log_error)
                self._client = client

            # create new access tokens
            elif len(access_tokens) != 2 and len(refresh_tokens) == 2:
                try:
                    access_token_kodi, expires_in_kodi = client.refresh_token(refresh_tokens[1])
                    access_token_tv, expires_in_tv = client.refresh_token_tv(refresh_tokens[0])
                    access_tokens = [access_token_tv, access_token_kodi]
                    access_token = '%s|%s' % (access_token_tv, access_token_kodi)
                    expires_in = min(expires_in_tv, expires_in_kodi)
                    if dev_id:
                        access_manager.update_dev_access_token(dev_id, access_token, expires_in)
                    else:
                        access_manager.update_access_token(access_token, expires_in)
                except (InvalidGrant, LoginException) as ex:
                    self.handle_exception(context, ex)
                    access_tokens = ['', '']
                    # reset access_token
                    if isinstance(ex, InvalidGrant):
                        if dev_id:
                            access_manager.update_dev_access_token(dev_id, access_token='', refresh_token='')
                        else:
                            access_manager.update_access_token(access_token='', refresh_token='')
                    elif dev_id:
                        access_manager.update_dev_access_token(dev_id, '')
                    else:
                        access_manager.update_access_token('')
                    # we clear the cache, so none cached data of an old account will be displayed.
                    self.get_resource_manager(context).clear()

            # in debug log the login status
            self._is_logged_in = len(access_tokens) == 2
            context.log_debug('User is logged in' if self._is_logged_in else
                              'User is not logged in')

            if not access_tokens:
                access_tokens = ['', '']
            client.set_access_token(access_token=access_tokens[1])
            client.set_access_token_tv(access_token_tv=access_tokens[0])

        client.set_log_error(context.log_error)
        self._client = client
        return self._client

    def get_resource_manager(self, context):
        if not self._resource_manager:
            # self._resource_manager = ResourceManager(weakref.proxy(context), weakref.proxy(self.get_client(context)))
            self._resource_manager = ResourceManager(context, self.get_client(context))
        return self._resource_manager

    def get_alternative_fanart(self, context):
        return self.get_fanart(context)

    @staticmethod
    def get_fanart(context):
        return context.create_resource_path('media', 'fanart.jpg')

    # noinspection PyUnusedLocal
    @RegisterProviderPath('^/uri2addon/$')
    def on_uri2addon(self, context, re_match):
        uri = context.get_param('uri')
        if not uri:
            return False

        resolver = UrlResolver(context)
        res_url = resolver.resolve(uri)
        url_converter = UrlToItemConverter(flatten=True)
        url_converter.add_url(res_url, self, context)
        items = url_converter.get_items(self, context, skip_title=True)
        if items:
            return items[0]

        return False

    """
    Lists the videos of a playlist.
    path       : '/channel/(?P<channel_id>[^/]+)/playlist/(?P<playlist_id>[^/]+)/'
        or
    path       : '/playlist/(?P<playlist_id>[^/]+)/'
    channel_id : ['mine'|<CHANNEL_ID>]
    playlist_id: <PLAYLIST_ID>
    """

    @RegisterProviderPath('^(?:/channel/(?P<channel_id>[^/]+))?/playlist/(?P<playlist_id>[^/]+)/$')
    def _on_playlist(self, context, re_match):
        self.set_content_type(context, constants.content_type.VIDEOS)
        client = self.get_client(context)
        resource_manager = self.get_resource_manager(context)

        batch_id = (re_match.group('playlist_id'),
                    context.get_param('page_token') or 0)

        json_data = resource_manager.get_playlist_items(batch_id=batch_id)
        if not json_data:
            return False
        result = v3.response_to_items(self, context, json_data[batch_id])
        return result

    """
    Lists all playlists of a channel.
    path      : '/channel/(?P<channel_id>[^/]+)/playlists/'
    channel_id: <CHANNEL_ID>
    """

    @RegisterProviderPath('^/channel/(?P<channel_id>[^/]+)/playlists/$')
    def _on_channel_playlists(self, context, re_match):
        self.set_content_type(context, constants.content_type.FILES)
        result = []

        channel_id = re_match.group('channel_id')
        page_token = context.get_param('page_token', '')

        resource_manager = self.get_resource_manager(context)

        item_params = {}
        incognito = context.get_param('incognito')
        addon_id = context.get_param('addon_id')
        if incognito:
            item_params.update({'incognito': incognito})
        if addon_id:
            item_params.update({'addon_id': addon_id})

        playlists = resource_manager.get_related_playlists(channel_id)
        uploads_playlist = playlists.get('uploads', '')
        if uploads_playlist:
            uploads_item = DirectoryItem(context.get_ui().bold(context.localize('uploads')),
                                         context.create_uri(['channel', channel_id, 'playlist', uploads_playlist],
                                                            item_params),
                                         image=context.create_resource_path('media', 'playlist.png'))
            result.append(uploads_item)

        # no caching
        json_data = self.get_client(context).get_playlists_of_channel(channel_id, page_token)
        if not json_data:
            return False
        result.extend(v3.response_to_items(self, context, json_data))

        return result

    """
    List live streams for channel.
    path      : '/channel/(?P<channel_id>[^/]+)/live/'
    channel_id: <CHANNEL_ID>
    """

    @RegisterProviderPath('^/channel/(?P<channel_id>[^/]+)/live/$')
    def _on_channel_live(self, context, re_match):
        self.set_content_type(context, constants.content_type.VIDEOS)
        result = []

        channel_id = re_match.group('channel_id')
        page_token = context.get_param('page_token', '')
        safe_search = context.get_settings().safe_search()

        # no caching
        json_data = self.get_client(context).search(q='', search_type='video', event_type='live', channel_id=channel_id, page_token=page_token, safe_search=safe_search)
        if not json_data:
            return False
        result.extend(v3.response_to_items(self, context, json_data))

        return result

    """
    Lists a playlist folder and all uploaded videos of a channel.
    path      :'/channel|user/(?P<channel_id|username>)[^/]+/'
    channel_id: <CHANNEL_ID>
    """

    @RegisterProviderPath('^/(?P<method>(channel|user))/(?P<channel_id>[^/]+)/$')
    def _on_channel(self, context, re_match):
        client = self.get_client(context)
        localize = context.localize
        create_path = context.create_resource_path
        create_uri = context.create_uri
        function_cache = context.get_function_cache()
        params = context.get_params()
        ui = context.get_ui()

        listitem_channel_id = ui.get_info_label('Container.ListItem(0).Property(channel_id)')

        method = re_match.group('method')
        channel_id = re_match.group('channel_id')

        if (method == 'channel' and channel_id and channel_id.lower() == 'property'
                and listitem_channel_id and listitem_channel_id.lower().startswith(('mine', 'uc'))):
            context.execute('Container.Update(%s)' % create_uri(['channel', listitem_channel_id]))  # redirect if keymap, without redirect results in 'invalid handle -1'

        if method == 'channel' and not channel_id:
            return False

        self.set_content_type(context, constants.content_type.VIDEOS)

        resource_manager = self.get_resource_manager(context)

        mine_id = ''
        result = []

        """
        This is a helper routine if we only have the username of a channel.
        This will retrieve the correct channel id based on the username.
        """
        if method == 'user' or channel_id == 'mine':
            context.log_debug('Trying to get channel id for user "%s"' % channel_id)

            json_data = function_cache.get(client.get_channel_by_username,
                                           function_cache.ONE_DAY,
                                           channel_id)
            if not json_data:
                return False

            # we correct the channel id based on the username
            items = json_data.get('items', [])
            if items:
                if method == 'user':
                    channel_id = items[0]['id']
                else:
                    mine_id = items[0]['id']
            else:
                context.log_warning('Could not find channel ID for user "%s"' % channel_id)
                if method == 'user':
                    return False

        channel_fanarts = resource_manager.get_fanarts([channel_id])
        page = params.get('page', 1)
        page_token = params.get('page_token', '')
        incognito = params.get('incognito')
        addon_id = params.get('addon_id')
        item_params = {}
        if incognito:
            item_params.update({'incognito': incognito})
        if addon_id:
            item_params.update({'addon_id': addon_id})

        hide_folders = params.get('hide_folders')

        if page == 1 and not hide_folders:
            hide_playlists = params.get('hide_playlists')
            hide_search = params.get('hide_search')
            hide_live = params.get('hide_live')

            if not hide_playlists:
                playlists_item = DirectoryItem(ui.bold(localize('playlists')),
                                               create_uri(['channel', channel_id, 'playlists'], item_params),
                                               image=create_path('media', 'playlist.png'))
                playlists_item.set_fanart(channel_fanarts.get(channel_id, self.get_fanart(context)))
                result.append(playlists_item)

            search_live_id = mine_id if mine_id else channel_id
            if not hide_search:
                search_item = NewSearchItem(context, alt_name=ui.bold(localize('search')),
                                            image=create_path('media', 'search.png'),
                                            fanart=self.get_fanart(context), channel_id=search_live_id, incognito=incognito, addon_id=addon_id)
                search_item.set_fanart(self.get_fanart(context))
                result.append(search_item)

            if not hide_live:
                live_item = DirectoryItem(ui.bold(localize('live')),
                                          create_uri(['channel', search_live_id, 'live'], item_params),
                                          image=create_path('media', 'live.png'))
                live_item.set_fanart(self.get_fanart(context))
                result.append(live_item)

        playlists = resource_manager.get_related_playlists(channel_id)
        upload_playlist = playlists.get('uploads', '')
        if upload_playlist:
            json_data = function_cache.get(client.get_playlist_items,
                                           function_cache.ONE_MINUTE * 5,
                                           upload_playlist,
                                           page_token=page_token)
            if not json_data:
                return False

            result.extend(v3.response_to_items(self, context, json_data))

        return result

    # noinspection PyUnusedLocal
    @RegisterProviderPath('^/location/mine/$')
    def _on_my_location(self, context, re_match):
        self.set_content_type(context, constants.content_type.FILES)

        create_path = context.create_resource_path
        create_uri = context.create_uri
        localize = context.localize
        settings = context.get_settings()
        result = []

        # search
        search_item = SearchItem(
            context,
            image=create_path('media', 'search.png'),
            fanart=self.get_fanart(context),
            location=True
        )
        result.append(search_item)

        # completed live events
        if settings.get_bool('youtube.folder.completed.live.show', True):
            live_events_item = DirectoryItem(
                localize('live.completed'),
                create_uri(['special', 'completed_live'], params={'location': True}),
                image=create_path('media', 'live.png')
            )
            live_events_item.set_fanart(self.get_fanart(context))
            result.append(live_events_item)

        # upcoming live events
        if settings.get_bool('youtube.folder.upcoming.live.show', True):
            live_events_item = DirectoryItem(
                localize('live.upcoming'),
                create_uri(['special', 'upcoming_live'], params={'location': True}),
                image=create_path('media', 'live.png')
            )
            live_events_item.set_fanart(self.get_fanart(context))
            result.append(live_events_item)

        # live events
        live_events_item = DirectoryItem(
            localize('live'),
            create_uri(['special', 'live'], params={'location': True}),
            image=create_path('media', 'live.png')
        )
        live_events_item.set_fanart(self.get_fanart(context))
        result.append(live_events_item)

        return result

    """
    Plays a video.
    path for video: '/play/?video_id=XXXXXXX'

    path for playlist: '/play/?playlist_id=XXXXXXX&mode=[OPTION]'
    OPTION: [normal(default)|reverse|shuffle]

    path for channel live streams: '/play/?channel_id=UCXXXXXXX&live=X
    OPTION:
        live parameter required, live=1 for first live stream
        live = index of live stream if channel has multiple live streams
    """

    # noinspection PyUnusedLocal
    @RegisterProviderPath('^/play/$')
    def on_play(self, context, re_match):
        ui = context.get_ui()

        redirect = False
        params = context.get_params()

        if ({'channel_id', 'live', 'playlist_id', 'playlist_ids', 'video_id'}
                .isdisjoint(params.keys())):
            path = ui.get_info_label('Container.ListItem(0).FileNameAndPath')
            if context.is_plugin_path(path, 'play/'):
                video_id = find_video_id(path)
                if video_id:
                    context.set_param('video_id', video_id)
                    params = context.get_params()
                else:
                    return False
            else:
                return False

        video_id = params.get('video_id')
        playlist_id = params.get('playlist_id')

        if ui.get_property('prompt_for_subtitles') != video_id:
            ui.clear_property('prompt_for_subtitles')

        if ui.get_property('audio_only') != video_id:
            ui.clear_property('audio_only')

        if ui.get_property('ask_for_quality') != video_id:
            ui.clear_property('ask_for_quality')

        if video_id and not playlist_id:
            if params.pop('prompt_for_subtitles', None):
                # redirect to builtin after setting home window property,
                # so playback url matches playable listitems
                ui.set_property('prompt_for_subtitles', video_id)
                context.log_debug('Redirecting playback with subtitles')
                redirect = True

            if params.pop('audio_only', None):
                # redirect to builtin after setting home window property,
                # so playback url matches playable listitems
                ui.set_property('audio_only', video_id)
                context.log_debug('Redirecting audio only playback')
                redirect = True

            if params.pop('ask_for_quality', None):
                # redirect to builtin after setting home window property,
                # so playback url matches playable listitems
                ui.set_property('ask_for_quality', video_id)
                context.log_debug('Redirecting ask quality playback')
                redirect = True

            builtin = None
            if context.get_handle() == -1:
                builtin = 'PlayMedia({0})'
                context.log_debug('Redirecting playback, handle is -1')
            elif redirect:
                builtin = 'RunPlugin({0})'

            if builtin:
                context.execute(builtin.format(
                    context.create_uri(['play'], params)
                ))
                return False
            return yt_play.play_video(self, context)

        if playlist_id or 'playlist_ids' in params:
            return yt_play.play_playlist(self, context)

        if 'channel_id' in params and params.get('live', 0) > 0:
            return yt_play.play_channel_live(self, context)
        return False

    @RegisterProviderPath('^/video/(?P<method>[^/]+)/$')
    def _on_video_x(self, context, re_match):
        method = re_match.group('method')
        return yt_video.process(method, self, context, re_match)

    @RegisterProviderPath('^/playlist/(?P<method>[^/]+)/(?P<category>[^/]+)/$')
    def _on_playlist_x(self, context, re_match):
        method = re_match.group('method')
        category = re_match.group('category')
        return yt_playlist.process(method, category, self, context)

    @RegisterProviderPath('^/subscriptions/(?P<method>[^/]+)/$')
    def _on_subscriptions(self, context, re_match):
        method = re_match.group('method')
        resource_manager = self.get_resource_manager(context)
        subscriptions = yt_subscriptions.process(method, self, context)

        if method == 'list':
            self.set_content_type(context, constants.content_type.FILES)
            channel_ids = []
            for subscription in subscriptions:
                channel_ids.append(subscription.get_channel_id())
            channel_fanarts = resource_manager.get_fanarts(channel_ids)
            for subscription in subscriptions:
                if channel_fanarts.get(subscription.get_channel_id()):
                    subscription.set_fanart(channel_fanarts.get(subscription.get_channel_id()))

        return subscriptions

    @RegisterProviderPath('^/special/(?P<category>[^/]+)/$')
    def _on_yt_specials(self, context, re_match):
        category = re_match.group('category')
        return yt_specials.process(category, self, context)

    # noinspection PyUnusedLocal
    @RegisterProviderPath('^/history/clear/$')
    def _on_yt_clear_history(self, context, re_match):
        if context.get_ui().on_yes_no_input(context.get_name(), context.localize('clear_history_confirmation')):
            json_data = self.get_client(context).clear_watch_history()
            if 'error' not in json_data:
                context.get_ui().show_notification(context.localize('succeeded'))

    @RegisterProviderPath('^/users/(?P<action>[^/]+)/$')
    def _on_users(self, context, re_match):
        action = re_match.group('action')
        refresh = context.get_param('refresh')

        localize = context.localize
        access_manager = context.get_access_manager()
        ui = context.get_ui()

        def select_user(reason, new_user=False):
            current_users = access_manager.get_users()
            current_user = access_manager.get_current_user()
            usernames = []
            for user, details in sorted(current_users.items()):
                username = details.get('name') or localize('user.unnamed')
                if user == current_user:
                    username = '> ' + ui.bold(username)
                if details.get('access_token') or details.get('refresh_token'):
                    username = ui.color('limegreen', username)
                usernames.append(username)
            if new_user:
                usernames.append(ui.italic(localize('user.new')))
            return ui.on_select(reason, usernames), sorted(current_users.keys())

        def add_user():
            results = ui.on_keyboard_input(localize('user.enter_name'))
            if results[0] is False:
                return None, None
            new_username = results[1].strip()
            if not new_username:
                new_username = localize('user.unnamed')
            return access_manager.add_user(new_username)

        def switch_to_user(user):
            access_manager.set_user(user, switch_to=True)
            ui.show_notification(
                localize('user.changed') % access_manager.get_username(user),
                localize('user.switch')
            )
            self.get_resource_manager(context).clear()
            if refresh:
                ui.refresh_container()

        if action == 'switch':
            result, user_index_map = select_user(localize('user.switch'),
                                                 new_user=True)
            if result == -1:
                return True
            if result == len(user_index_map):
                user, _ = add_user()
            else:
                user = user_index_map[result]

            if user is not None and user != access_manager.get_current_user():
                switch_to_user(user)

        elif action == 'add':
            user, details = add_user()
            if user is not None:
                result = ui.on_yes_no_input(
                    localize('user.switch'),
                    localize('user.switch.now') % details.get('name')
                )
                if result:
                    switch_to_user(user)

        elif action == 'remove':
            result, user_index_map = select_user(localize('user.remove'))
            if result == -1:
                return True

            user = user_index_map[result]
            username = access_manager.get_username(user)
            if ui.on_remove_content(username):
                access_manager.remove_user(user)
                if user == 0:
                    access_manager.add_user(username=localize('user.default'),
                                            user=0)
                if user == access_manager.get_current_user():
                    access_manager.set_user(0, switch_to=True)
                ui.show_notification(localize('removed') % username,
                                     localize('remove'))

        elif action == 'rename':
            result, user_index_map = select_user(localize('user.rename'))
            if result == -1:
                return True

            user = user_index_map[result]
            old_username = access_manager.get_username(user)
            results = ui.on_keyboard_input(localize('user.enter_name'),
                                           default=old_username)
            if results[0] is False:
                return True
            new_username = results[1].strip()
            if not new_username:
                new_username = localize('user.unnamed')
            if old_username == new_username:
                return True

            if access_manager.set_username(user, new_username):
                ui.show_notification(localize('renamed') % (old_username,
                                                            new_username),
                                     localize('rename'))

        return True

    @RegisterProviderPath('^/sign/(?P<mode>[^/]+)/$')
    def _on_sign(self, context, re_match):
        sign_out_confirmed = context.get_param('confirmed')
        mode = re_match.group('mode')
        if (mode == 'in') and context.get_access_manager().has_refresh_token():
            yt_login.process('out', self, context, sign_out_refresh=False)

        if (not sign_out_confirmed and mode == 'out'
                and context.get_ui().on_yes_no_input(
                    context.localize('sign.out'),
                    context.localize('are_you_sure'))):
            sign_out_confirmed = True

        if mode == 'in' or (mode == 'out' and sign_out_confirmed):
            yt_login.process(mode, self, context)
        return False

    @RegisterProviderPath('^/search/$')
    def endpoint_search(self, context, re_match):
        query = context.get_param('q')
        if not query:
            return []

        return self.on_search(query, context, re_match)

    def _search_channel_or_playlist(self, context, id_string):
        json_data = {}
        result = []

        if re.match(r'U[CU][0-9a-zA-Z_\-]{20,24}', id_string):
            json_data = self.get_client(context).get_channels(id_string)

        elif re.match(r'[OP]L[0-9a-zA-Z_\-]{30,40}', id_string):
            json_data = self.get_client(context).get_playlists(id_string)

        if not json_data:
            return []

        result.extend(v3.response_to_items(self, context, json_data))
        return result

    def on_search(self, search_text, context, re_match):
        result = self._search_channel_or_playlist(context, search_text)
        if result:  # found a channel or playlist matching search_text
            return result

        context.set_param('q', search_text)

        params = context.get_params()
        channel_id = params.get('channel_id')
        event_type = params.get('event_type')
        hide_folders = params.get('hide_folders')
        location = params.get('location')
        page = params.get('page', 1)
        page_token = params.get('page_token', '')
        search_type = params.get('search_type', 'video')

        safe_search = context.get_settings().safe_search()

        if search_type == 'video':
            self.set_content_type(context, constants.content_type.VIDEOS)
        else:
            self.set_content_type(context, constants.content_type.FILES)

        if page == 1 and search_type == 'video' and not event_type and not hide_folders:
            if not channel_id and not location:
                channel_params = {}
                channel_params.update(params)
                channel_params['search_type'] = 'channel'
                channel_item = DirectoryItem(context.get_ui().bold(context.localize('channels')),
                                             context.create_uri([context.get_path()], channel_params),
                                             image=context.create_resource_path('media', 'channels.png'))
                channel_item.set_fanart(self.get_fanart(context))
                result.append(channel_item)

            if not location:
                playlist_params = {}
                playlist_params.update(params)
                playlist_params['search_type'] = 'playlist'
                playlist_item = DirectoryItem(context.get_ui().bold(context.localize('playlists')),
                                              context.create_uri([context.get_path()], playlist_params),
                                              image=context.create_resource_path('media', 'playlist.png'))
                playlist_item.set_fanart(self.get_fanart(context))
                result.append(playlist_item)

            if not channel_id:
                # live
                live_params = {}
                live_params.update(params)
                live_params['search_type'] = 'video'
                live_params['event_type'] = 'live'
                live_item = DirectoryItem(context.get_ui().bold(context.localize('live')),
                                          context.create_uri([context.get_path().replace('input', 'query')], live_params),
                                          image=context.create_resource_path('media', 'live.png'))
                live_item.set_fanart(self.get_fanart(context))
                result.append(live_item)

        function_cache = context.get_function_cache()
        json_data = function_cache.get(self.get_client(context).search,
                                       function_cache.ONE_MINUTE * 10,
                                       q=search_text,
                                       search_type=search_type,
                                       event_type=event_type,
                                       safe_search=safe_search,
                                       page_token=page_token,
                                       channel_id=channel_id,
                                       location=location)
        if not json_data:
            return False
        result.extend(v3.response_to_items(self, context, json_data))
        return result

    @RegisterProviderPath('^/config/(?P<switch>[^/]+)/$')
    def configure_addon(self, context, re_match):
        switch = re_match.group('switch')
        localize = context.localize
        settings = context.get_settings()
        ui = context.get_ui()

        if switch == 'youtube':
            context.addon().openSettings()
            ui.refresh_container()
        elif switch == 'isa':
            if context.use_inputstream_adaptive():
                xbmcaddon.Addon(id='inputstream.adaptive').openSettings()
            else:
                settings.set_bool('kodion.video.quality.isa', False)
        elif switch == 'subtitles':
            yt_language = settings.get_string('youtube.language', 'en-US')
            sub_setting = settings.subtitle_languages()

            if yt_language.startswith('en'):
                sub_opts = [localize('none'),
                            localize('prompt'),
                            localize('subtitles.with_fallback') % ('en', 'en-US/en-GB'),
                            yt_language,
                            '%s (%s)' % (yt_language, localize('subtitles.no_auto_generated'))]

            else:
                sub_opts = [localize('none'),
                            localize('prompt'),
                            localize('subtitles.with_fallback') % (yt_language, 'en'),
                            yt_language,
                            '%s (%s)' % (yt_language, localize('subtitles.no_auto_generated'))]

            sub_opts[sub_setting] = ui.bold(sub_opts[sub_setting])

            result = ui.on_select(localize('subtitles.language'), sub_opts)
            if result > -1:
                settings.set_subtitle_languages(result)

            result = ui.on_yes_no_input(
                localize('subtitles.download'),
                localize('subtitles.download.pre')
            )
            if result > -1:
                settings.set_subtitle_download(result == 1)
        elif switch == 'listen_ip':
            local_ranges = ('10.', '172.16.', '192.168.')
            addresses = [iface[4][0]
                         for iface in socket.getaddrinfo(socket.gethostname(), None)
                         if iface[4][0].startswith(local_ranges)]
            addresses += ['127.0.0.1', '0.0.0.0']
            selected_address = ui.on_select(localize('select.listen.ip'), addresses)
            if selected_address != -1:
                settings.set_httpd_listen(addresses[selected_address])
        return False

    # noinspection PyUnusedLocal
    @RegisterProviderPath('^/my_subscriptions/filter/$')
    def manage_my_subscription_filter(self, context, re_match):
        params = context.get_params()
        settings = context.get_settings()
        ui = context.get_ui()

        action = params.get('action')
        channel = params.get('channel_name')
        if (not channel) or (not action):
            return

        filter_enabled = settings.get_bool('youtube.folder.my_subscriptions_filtered.show', False)
        if not filter_enabled:
            return

        channel_name = channel.lower()
        channel_name = channel_name.replace(',', '')

        filter_string = settings.get_string('youtube.filter.my_subscriptions_filtered.list', '')
        filter_string = filter_string.replace(', ', ',')
        filter_list = filter_string.split(',')
        filter_list = [x.lower() for x in filter_list]

        if action == 'add':
            if channel_name not in filter_list:
                filter_list.append(channel_name)
        elif action == 'remove' and channel_name in filter_list:
            filter_list = [chan_name for chan_name in filter_list if chan_name != channel_name]

        modified_string = ','.join(filter_list).lstrip(',')
        if filter_string != modified_string:
            settings.set_string('youtube.filter.my_subscriptions_filtered.list', modified_string)
            message = ''
            if action == 'add':
                message = context.localize('my_subscriptions.filter.added')
            elif action == 'remove':
                message = context.localize('my_subscriptions.filter.removed')
            if message:
                ui.show_notification(message=message)
        ui.refresh_container()

    @RegisterProviderPath('^/maintain/(?P<maint_type>[^/]+)/(?P<action>[^/]+)/$')
    def maintenance_actions(self, context, re_match):
        maint_type = re_match.group('maint_type')
        action = re_match.group('action')

        ui = context.get_ui()
        localize = context.localize

        if action == 'clear':
            if maint_type == 'function_cache':
                if ui.on_remove_content(localize('cache.function')):
                    context.get_function_cache().clear()
                    ui.show_notification(localize('succeeded'))
            elif maint_type == 'data_cache':
                if ui.on_remove_content(localize('cache.data')):
                    context.get_data_cache().clear()
                    ui.show_notification(localize('succeeded'))
            elif maint_type == 'search_cache':
                if ui.on_remove_content(localize('search.history')):
                    context.get_search_history().clear()
                    ui.show_notification(localize('succeeded'))
            elif maint_type == 'playback_history' and ui.on_remove_content(localize('playback.history')):
                context.get_playback_history().clear()
                ui.show_notification(localize('succeeded'))
        elif action == 'reset':
            if maint_type == 'access_manager' and ui.on_yes_no_input(context.get_name(), localize('reset.access_manager.confirm')):
                try:
                    context.get_function_cache().clear()
                    access_manager = context.get_access_manager()
                    client = self.get_client(context)
                    if access_manager.has_refresh_token():
                        refresh_tokens = access_manager.get_refresh_token().split('|')
                        for refresh_token in set(refresh_tokens):
                            try:
                                client.revoke(refresh_token)
                            except:
                                pass
                    self.reset_client()
                    access_manager.update_access_token(access_token='', refresh_token='')
                    ui.refresh_container()
                    ui.show_notification(localize('succeeded'))
                except:
                    ui.show_notification(localize('failed'))
        elif action == 'delete':
            _maint_files = {'function_cache': 'cache.sqlite',
                            'search_cache': 'search.sqlite',
                            'data_cache': 'data_cache.sqlite',
                            'playback_history': 'playback_history',
                            'settings_xml': 'settings.xml',
                            'api_keys': 'api_keys.json',
                            'access_manager': 'access_manager.json',
                            'temp_files': 'special://temp/plugin.video.youtube/'}
            _file = _maint_files.get(maint_type, '')
            success = False
            if _file:
                if 'sqlite' in _file:
                    _file_w_path = os.path.join(context.get_cache_path(), _file)
                elif maint_type == 'temp_files':
                    _file_w_path = _file
                elif _file == 'playback_history':
                    _file = ''.join([str(context.get_access_manager().get_current_user_id()), '.sqlite'])
                    _file_w_path = os.path.join(os.path.join(context.get_data_path(), 'playback'), _file)
                else:
                    _file_w_path = os.path.join(context.get_data_path(), _file)
                if ui.on_delete_content(_file):
                    if maint_type == 'temp_files':
                        _trans_path = xbmcvfs.translatePath(_file_w_path)
                        try:
                            xbmcvfs.rmdir(_trans_path, force=True)
                        except:
                            pass
                        if xbmcvfs.exists(_trans_path):
                            try:
                                shutil.rmtree(_trans_path)
                            except:
                                pass
                        success = not xbmcvfs.exists(_trans_path)
                    elif _file_w_path:
                        success = xbmcvfs.delete(_file_w_path)
                    if success:
                        ui.show_notification(localize('succeeded'))
                    else:
                        ui.show_notification(localize('failed'))
        elif action == 'install' and maint_type == 'inputstreamhelper':
            if context.get_system_version().get_version()[0] >= 17:
                try:
                    xbmcaddon.Addon('script.module.inputstreamhelper')
                    ui.show_notification(localize('inputstreamhelper.is_installed'))
                except RuntimeError:
                    context.execute('InstallAddon(script.module.inputstreamhelper)')
            else:
                ui.show_notification(localize('requires.krypton'))

    # noinspection PyUnusedLocal
    @RegisterProviderPath('^/api/update/$')
    def api_key_update(self, context, re_match):
        localize = context.localize
        params = context.get_params()
        settings = context.get_settings()
        ui = context.get_ui()

        api_key = params.get('api_key')
        client_id = params.get('client_id')
        client_secret = params.get('client_secret')
        enable = params.get('enable')

        updated_list = []
        log_list = []

        if api_key:
            settings.set_string('youtube.api.key', api_key)
            updated_list.append(localize('api.key'))
            log_list.append('Key')
        if client_id:
            settings.set_string('youtube.api.id', client_id)
            updated_list.append(localize('api.id'))
            log_list.append('Id')
        if client_secret:
            settings.set_string('youtube.api.secret', client_secret)
            updated_list.append(localize('api.secret'))
            log_list.append('Secret')
        if updated_list:
            ui.show_notification(localize('updated_') % ', '.join(updated_list))
        context.log_debug('Updated API keys: %s' % ', '.join(log_list))

        client_id = settings.get_string('youtube.api.id', '')
        client_secret = settings.get_string('youtube.api.secret', '')
        api_key = settings.get_string('youtube.api.key', '')
        missing_list = []
        log_list = []

        if enable and client_id and client_secret and api_key:
            ui.show_notification(localize('api.personal.enabled'))
            context.log_debug('Personal API keys enabled')
        elif enable:
            if not api_key:
                missing_list.append(localize('api.key'))
                log_list.append('Key')
            if not client_id:
                missing_list.append(localize('api.id'))
                log_list.append('Id')
            if not client_secret:
                missing_list.append(localize('api.secret'))
                log_list.append('Secret')
            ui.show_notification(localize('api.personal.failed') % ', '.join(missing_list))
            context.log_debug('Failed to enable personal API keys. Missing: %s' % ', '.join(log_list))

    # noinspection PyUnusedLocal
    @RegisterProviderPath('^/show_client_ip/$')
    def show_client_ip(self, context, re_match):
        port = context.get_settings().httpd_port()

        if is_httpd_live(port=port):
            client_ip = get_client_ip_address(port=port)
            if client_ip:
                context.get_ui().on_ok(context.get_name(), context.localize('client.ip') % client_ip)
            else:
                context.get_ui().show_notification(context.localize('client.ip.failed'))
        else:
            context.get_ui().show_notification(context.localize('httpd.not.running'))

    # noinspection PyUnusedLocal
    @RegisterProviderPath('^/playback_history/$')
    def on_playback_history(self, context, re_match):
        params = context.get_params()
        video_id = params.get('video_id')
        action = params.get('action')
        if not video_id or not action:
            return True
        playback_history = context.get_playback_history()
        play_data = playback_history.get_items([video_id]).get(video_id)
        if not play_data:
            play_data = {
                'play_count': 0,
                'total_time': 0,
                'played_time': 0,
                'played_percent': 0
            }

        if action == 'mark_unwatched':
            if play_data.get('play_count', 0) > 0:
                play_data['play_count'] = 0
                play_data['played_time'] = 0
                play_data['played_percent'] = 0

        elif action == 'mark_watched':
            if not play_data.get('play_count', 0):
                play_data['play_count'] = 1

        elif action == 'reset_resume':
            play_data['played_time'] = 0
            play_data['played_percent'] = 0

        playback_history.update(video_id,
                                play_data.get('play_count', 0),
                                play_data.get('total_time', 0),
                                play_data.get('played_time', 0),
                                play_data.get('played_percent', 0))
        context.get_ui().refresh_container()
        return True

    def on_root(self, context, re_match):
        """
        Support old YouTube url calls, but also log a deprecation warnings.
        """
        old_action = context.get_param('action')
        if old_action:
            return yt_old_actions.process_old_action(self, context, re_match)

        create_path = context.create_resource_path
        create_uri = context.create_uri
        localize = context.localize
        settings = context.get_settings()
        ui = context.get_ui()

        _ = self.get_client(context)  # required for self.is_logged_in()

        self.set_content_type(context, constants.content_type.FILES)

        result = []

        # sign in
        if not self.is_logged_in() and settings.get_bool('youtube.folder.sign.in.show', True):
            sign_in_item = DirectoryItem(ui.bold(localize('sign.in')),
                                         create_uri(['sign', 'in']),
                                         image=create_path('media', 'sign_in.png'))
            sign_in_item.set_action(True)
            sign_in_item.set_fanart(self.get_fanart(context))
            result.append(sign_in_item)

        if self.is_logged_in() and settings.get_bool('youtube.folder.my_subscriptions.show', True):
            # my subscription

            # clear cache
            cache = context.get_data_cache()
            cache.set_item('my-subscriptions-items', '[]')

            my_subscriptions_item = DirectoryItem(
                ui.bold(localize('my_subscriptions')),
                create_uri(['special', 'new_uploaded_videos_tv']),
                create_path('media', 'new_uploads.png'))
            my_subscriptions_item.set_fanart(self.get_fanart(context))
            result.append(my_subscriptions_item)

        if self.is_logged_in() and settings.get_bool('youtube.folder.my_subscriptions_filtered.show', True):
            # my subscriptions filtered
            my_subscriptions_filtered_item = DirectoryItem(
                localize('my_subscriptions.filtered'),
                create_uri(['special', 'new_uploaded_videos_tv_filtered']),
                create_path('media', 'new_uploads.png'))
            my_subscriptions_filtered_item.set_fanart(self.get_fanart(context))
            result.append(my_subscriptions_filtered_item)

        access_manager = context.get_access_manager()

        # Recommendations
        if self.is_logged_in() and settings.get_bool('youtube.folder.recommendations.show', True):
            watch_history_playlist_id = access_manager.get_watch_history_id()
            if watch_history_playlist_id != 'HL':
                recommendations_item = DirectoryItem(
                    localize('recommendations'),
                    create_uri(['special', 'recommendations']),
                    create_path('media', 'popular.png'))
                recommendations_item.set_fanart(self.get_fanart(context))
                result.append(recommendations_item)

        # what to watch
        if settings.get_bool('youtube.folder.popular_right_now.show', True):
            what_to_watch_item = DirectoryItem(
                localize('popular_right_now'),
                create_uri(['special', 'popular_right_now']),
                create_path('media', 'popular.png'))
            what_to_watch_item.set_fanart(self.get_fanart(context))
            result.append(what_to_watch_item)

        # search
        if settings.get_bool('youtube.folder.search.show', True):
            search_item = SearchItem(context, image=create_path('media', 'search.png'),
                                     fanart=self.get_fanart(context))
            result.append(search_item)

        if settings.get_bool('youtube.folder.quick_search.show', True):
            quick_search_item = NewSearchItem(context,
                                              alt_name=localize('search.quick'),
                                              fanart=self.get_fanart(context))
            result.append(quick_search_item)

        if settings.get_bool('youtube.folder.quick_search_incognito.show', True):
            quick_search_incognito_item = NewSearchItem(context,
                                                        alt_name=localize('search.quick.incognito'),
                                                        image=create_path('media', 'search.png'),
                                                        fanart=self.get_fanart(context),
                                                        incognito=True)
            result.append(quick_search_incognito_item)

        # my location
        if settings.get_bool('youtube.folder.my_location.show', True) and settings.get_location():
            my_location_item = DirectoryItem(localize('my_location'),
                                             create_uri(['location', 'mine']),
                                             image=create_path('media', 'channel.png'))
            my_location_item.set_fanart(self.get_fanart(context))
            result.append(my_location_item)

        # subscriptions
        if self.is_logged_in():
            # my channel
            if settings.get_bool('youtube.folder.my_channel.show', True):
                my_channel_item = DirectoryItem(localize('my_channel'),
                                                create_uri(['channel', 'mine']),
                                                image=create_path('media', 'channel.png'))
                my_channel_item.set_fanart(self.get_fanart(context))
                result.append(my_channel_item)

            # watch later
            watch_later_playlist_id = access_manager.get_watch_later_id()
            if settings.get_bool('youtube.folder.watch_later.show', True) and watch_later_playlist_id:
                watch_later_item = DirectoryItem(localize('watch_later'),
                                                 create_uri(['channel', 'mine', 'playlist', watch_later_playlist_id]),
                                                 create_path('media', 'watch_later.png'))
                watch_later_item.set_fanart(self.get_fanart(context))
                context_menu = []
                yt_context_menu.append_play_all_from_playlist(context_menu, context, watch_later_playlist_id)
                watch_later_item.set_context_menu(context_menu)
                result.append(watch_later_item)

            # liked videos
            if settings.get_bool('youtube.folder.liked_videos.show', True):
                resource_manager = self.get_resource_manager(context)
                playlists = resource_manager.get_related_playlists(channel_id='mine')
                if 'likes' in playlists:
                    liked_videos_item = DirectoryItem(localize('video.liked'),
                                                      create_uri(['channel', 'mine', 'playlist', playlists['likes']]),
                                                      create_path('media', 'likes.png'))
                    liked_videos_item.set_fanart(self.get_fanart(context))
                    context_menu = []
                    yt_context_menu.append_play_all_from_playlist(context_menu, context, playlists['likes'])
                    liked_videos_item.set_context_menu(context_menu)
                    result.append(liked_videos_item)

            # disliked videos
            if settings.get_bool('youtube.folder.disliked_videos.show', True):
                disliked_videos_item = DirectoryItem(localize('video.disliked'),
                                                     create_uri(['special', 'disliked_videos']),
                                                     create_path('media', 'dislikes.png'))
                disliked_videos_item.set_fanart(self.get_fanart(context))
                result.append(disliked_videos_item)

            # history
            if settings.get_bool('youtube.folder.history.show', False):
                watch_history_playlist_id = access_manager.get_watch_history_id()
                if watch_history_playlist_id != 'HL':
                    watch_history_item = DirectoryItem(localize('history'),
                                                       create_uri(['channel', 'mine', 'playlist', watch_history_playlist_id]),
                                                       create_path('media', 'history.png'))
                    watch_history_item.set_fanart(self.get_fanart(context))
                    context_menu = []
                    yt_context_menu.append_play_all_from_playlist(context_menu, context, watch_history_playlist_id)
                    watch_history_item.set_context_menu(context_menu)

                    result.append(watch_history_item)

            # (my) playlists
            if settings.get_bool('youtube.folder.playlists.show', True):
                playlists_item = DirectoryItem(localize('playlists'),
                                               create_uri(['channel', 'mine', 'playlists']),
                                               create_path('media', 'playlist.png'))
                playlists_item.set_fanart(self.get_fanart(context))
                result.append(playlists_item)

            # saved playlists
            if settings.get_bool('youtube.folder.saved.playlists.show', True):
                playlists_item = DirectoryItem(localize('saved.playlists'),
                                               create_uri(['special', 'saved_playlists']),
                                               create_path('media', 'playlist.png'))
                playlists_item.set_fanart(self.get_fanart(context))
                result.append(playlists_item)

            # subscriptions
            if settings.get_bool('youtube.folder.subscriptions.show', True):
                subscriptions_item = DirectoryItem(localize('subscriptions'),
                                                   create_uri(['subscriptions', 'list']),
                                                   image=create_path('media', 'channels.png'))
                subscriptions_item.set_fanart(self.get_fanart(context))
                result.append(subscriptions_item)

            # browse channels
            if settings.get_bool('youtube.folder.browse_channels.show', True):
                browse_channels_item = DirectoryItem(localize('browse_channels'),
                                                     create_uri(['special', 'browse_channels']),
                                                     image=create_path('media', 'browse_channels.png'))
                browse_channels_item.set_fanart(self.get_fanart(context))
                result.append(browse_channels_item)

        # completed live events
        if settings.get_bool('youtube.folder.completed.live.show', True):
            live_events_item = DirectoryItem(localize('live.completed'),
                                             create_uri(['special', 'completed_live']),
                                             image=create_path('media', 'live.png'))
            live_events_item.set_fanart(self.get_fanart(context))
            result.append(live_events_item)

        # upcoming live events
        if settings.get_bool('youtube.folder.upcoming.live.show', True):
            live_events_item = DirectoryItem(localize('live.upcoming'),
                                             create_uri(['special', 'upcoming_live']),
                                             image=create_path('media', 'live.png'))
            live_events_item.set_fanart(self.get_fanart(context))
            result.append(live_events_item)

        # live events
        if settings.get_bool('youtube.folder.live.show', True):
            live_events_item = DirectoryItem(localize('live'),
                                             create_uri(['special', 'live']),
                                             image=create_path('media', 'live.png'))
            live_events_item.set_fanart(self.get_fanart(context))
            result.append(live_events_item)

        # switch user
        if settings.get_bool('youtube.folder.switch.user.show', True):
            switch_user_item = DirectoryItem(localize('user.switch'),
                                             create_uri(['users', 'switch']),
                                             image=create_path('media', 'channel.png'))
            switch_user_item.set_action(True)
            switch_user_item.set_fanart(self.get_fanart(context))
            result.append(switch_user_item)

        # sign out
        if self.is_logged_in() and settings.get_bool('youtube.folder.sign.out.show', True):
            sign_out_item = DirectoryItem(localize('sign.out'),
                                          create_uri(['sign', 'out']),
                                          image=create_path('media', 'sign_out.png'))
            sign_out_item.set_action(True)
            sign_out_item.set_fanart(self.get_fanart(context))
            result.append(sign_out_item)

        if settings.get_bool('youtube.folder.settings.show', True):
            settings_menu_item = DirectoryItem(localize('settings'),
                                               create_uri(['config', 'youtube']),
                                               image=create_path('media', 'settings.png'))
            settings_menu_item.set_action(True)
            settings_menu_item.set_fanart(self.get_fanart(context))
            result.append(settings_menu_item)

        return result

    @staticmethod
    def set_content_type(context, content_type):
        context.set_content_type(content_type)
        context.add_sort_method(
            (constants.sort_method.UNSORTED,         '%T \u2022 %P',           '%D | %J'),
            (constants.sort_method.LABEL_IGNORE_THE, '%T \u2022 %P',           '%D | %J'),
        )
        if content_type != constants.content_type.VIDEOS:
            return
        context.add_sort_method(
            (constants.sort_method.PROGRAM_COUNT,    '%T \u2022 %P | %D | %J', '%C'),
            (constants.sort_method.VIDEO_RATING,     '%T \u2022 %P | %D | %J', '%R'),
            (constants.sort_method.DATE,             '%T \u2022 %P | %D',      '%J'),
            (constants.sort_method.DATEADDED,        '%T \u2022 %P | %D',      '%a'),
            (constants.sort_method.VIDEO_RUNTIME,    '%T \u2022 %P | %J',      '%D'),
            (constants.sort_method.TRACKNUM,         '[%N. ]%T \u2022 %P',     '%D | %J'),
        )

    def handle_exception(self, context, exception_to_handle):
        if isinstance(exception_to_handle, (InvalidGrant, LoginException)):
            ok_dialog = False
            message_timeout = 5000

            message = exception_to_handle.get_message()
            msg = exception_to_handle.get_message()
            log_message = exception_to_handle.get_message()

            error = ''
            code = ''
            if isinstance(msg, dict):
                if 'error_description' in msg:
                    message = strip_html_from_text(msg['error_description'])
                    log_message = strip_html_from_text(msg['error_description'])
                elif 'message' in msg:
                    message = strip_html_from_text(msg['message'])
                    log_message = strip_html_from_text(msg['message'])
                else:
                    message = 'No error message'
                    log_message = 'No error message'

                if 'error' in msg:
                    error = msg['error']

                if 'code' in msg:
                    code = msg['code']

            if error and code:
                title = '%s: [%s] %s' % ('LoginException', code, error)
            elif error:
                title = '%s: %s' % ('LoginException', error)
            else:
                title = 'LoginException'

            context.log_error('%s: %s' % (title, log_message))

            if error == 'deleted_client':
                message = context.localize('key.requirement.notification')
                context.get_access_manager().update_access_token(access_token='', refresh_token='')
                ok_dialog = True

            if error == 'invalid_client':
                if message == 'The OAuth client was not found.':
                    message = context.localize('client.id.incorrect')
                    message_timeout = 7000
                elif message == 'Unauthorized':
                    message = context.localize('client.secret.incorrect')
                    message_timeout = 7000

            if ok_dialog:
                context.get_ui().on_ok(title, message)
            else:
                context.get_ui().show_notification(message, title, time_ms=message_timeout)

            return False

        return True
