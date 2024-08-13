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
import re
from base64 import b64decode
from weakref import proxy

from .client import APICheck, YouTube
from .helper import (
    ResourceManager,
    UrlResolver,
    UrlToItemConverter,
    v3,
    yt_login,
    yt_play,
    yt_playlist,
    yt_setup_wizard,
    yt_specials,
    yt_subscriptions,
    yt_video,
)
from .youtube_exceptions import InvalidGrant, LoginException
from ..kodion import AbstractProvider
from ..kodion.constants import (
    ADDON_ID,
    CHANNEL_ID,
    CONTENT,
    DEVELOPER_CONFIGS,
    PATHS,
)
from ..kodion.items import (
    DirectoryItem,
    NewSearchItem,
    SearchItem,
    UriItem,
    VideoItem,
    menu_items,
)
from ..kodion.utils import strip_html_from_text


class Provider(AbstractProvider):
    def __init__(self):
        super(Provider, self).__init__()
        self._resource_manager = None
        self._client = None
        self._api_check = None
        self._logged_in = False

        self.on_video_x = self.register_path(
            '^/video/(?P<method>[^/]+)/?$',
            yt_video.process,
        )

        self.on_playlist_x = self.register_path(
            '^/playlist/(?P<method>[^/]+)/(?P<category>[^/]+)/?$',
            yt_playlist.process,
        )

        self.register_path(
            '^/play/?$',
            yt_play.process,
        )

        self.register_path(
            '^/special/(?P<category>[^/]+)/?$',
            yt_specials.process,
        )

        self.register_path(
            '^/subscriptions/(?P<method>[^/]+)/?$',
            yt_subscriptions.process,
        )

        atexit.register(self.tear_down)

    @staticmethod
    def get_wizard_steps():
        steps = [
            yt_setup_wizard.process_default_settings,
            yt_setup_wizard.process_performance_settings,
            yt_setup_wizard.process_language,
            yt_setup_wizard.process_subtitles,
            yt_setup_wizard.process_geo_location,
            yt_setup_wizard.process_old_search_db,
            yt_setup_wizard.process_old_history_db,
            yt_setup_wizard.process_list_detail_settings,
            yt_setup_wizard.process_refresh_settings,
        ]
        return steps

    def is_logged_in(self):
        return self._logged_in

    @staticmethod
    def get_dev_config(context, addon_id, dev_configs):
        _dev_config = context.get_ui().pop_property(DEVELOPER_CONFIGS)

        dev_config = {}
        if _dev_config:
            context.log_warning('Using window property for developer keys is'
                                ' deprecated. Please use the'
                                ' youtube_registration module instead')
            try:
                dev_config = json.loads(_dev_config)
            except ValueError:
                context.log_error('Error loading developer key: |invalid json|')
        if not dev_config and addon_id and dev_configs:
            dev_config = dev_configs.get(addon_id)

        if dev_config and not context.get_settings().allow_dev_keys():
            context.log_debug('Developer config ignored')
            return {}

        if dev_config:
            dev_main = dev_origin = None
            if {'main', 'origin'}.issubset(dev_config):
                dev_main = dev_config['main']
                dev_origin = dev_config['origin']

                if not {'system', 'key', 'id', 'secret'}.issubset(dev_main):
                    dev_main = None

            if not dev_main:
                context.log_error('Invalid developer config: |{dev_config}|\n'
                                  'expected: |{{'
                                  ' "origin": ADDON_ID,'
                                  ' "main": {{'
                                  ' "system": SYSTEM_NAME,'
                                  ' "key": API_KEY,'
                                  ' "id": CLIENT_ID,'
                                  ' "secret": CLIENT_SECRET'
                                  '}}}}|'.format(dev_config=dev_config))
                return {}

            dev_system = dev_main['system']
            if dev_system == 'JSONStore':
                dev_key = b64decode(dev_main['key'])
                dev_id = b64decode(dev_main['id'])
                dev_secret = b64decode(dev_main['secret'])
            else:
                dev_key = dev_main['key']
                dev_id = dev_main['id']
                dev_secret = dev_main['secret']
            context.log_debug('Using developer config: '
                              '|origin: {origin}, system: {system}|'
                              .format(origin=dev_origin, system=dev_system))
            return {
                'origin': dev_origin,
                'main': {
                    'system': dev_system,
                    'id': dev_id,
                    'secret': dev_secret,
                    'key': dev_key,
                }
            }

        return {}

    def reset_client(self):
        self._client = None
        self._api_check = None

    def get_client(self, context):
        access_manager = context.get_access_manager()

        if not self._api_check:
            self._api_check = APICheck(context)
        configs = self._api_check.get_configs()

        dev_id = context.get_param('addon_id')
        if not dev_id or dev_id == ADDON_ID:
            dev_id = dev_keys = None
            origin = ADDON_ID
        else:
            dev_config = self.get_dev_config(
                context, dev_id, configs['developer']
            )
            origin = dev_config.get('origin') or dev_id
            dev_keys = dev_config.get('main')

        api_last_origin = access_manager.get_last_origin()
        if api_last_origin != origin:
            context.log_debug('API key origin changed: |{old}| to |{new}|'
                              .format(old=api_last_origin, new=origin))
            access_manager.set_last_origin(origin)
            self.reset_client()

        if dev_id:
            access_tokens = access_manager.get_access_token(dev_id)
            if access_manager.is_access_token_expired(dev_id):
                # reset access_token
                access_tokens = []
                access_manager.update_access_token(dev_id, access_tokens)
            elif self._client:
                return self._client

            if dev_keys:
                context.log_debug('Selecting YouTube developer config "{0}"'
                                  .format(dev_id))
                configs['main'] = dev_keys
            else:
                dev_keys = configs['main']
                context.log_debug('Selecting YouTube config "{0}"'
                                  ' w/ developer access tokens'
                                  .format(dev_keys['system']))

            refresh_tokens = access_manager.get_refresh_token(dev_id)
            if refresh_tokens:
                keys_changed = access_manager.dev_keys_changed(
                    dev_id, dev_keys['key'], dev_keys['id'], dev_keys['secret']
                )
                if keys_changed:
                    context.log_warning('API key set changed: Resetting client'
                                        ' and updating access token')
                    self.reset_client()
                    access_tokens = []
                    refresh_tokens = []
                    access_manager.update_access_token(
                        dev_id, access_tokens, -1, refresh_tokens
                    )

                context.log_debug(
                    'Access token count: |{0}|, refresh token count: |{1}|'
                    .format(len(access_tokens), len(refresh_tokens))
                )
        else:
            access_tokens = access_manager.get_access_token(dev_id)
            if access_manager.is_access_token_expired(dev_id):
                # reset access_token
                access_tokens = []
                access_manager.update_access_token(dev_id, access_tokens)
            elif self._client:
                return self._client

            context.log_debug('Selecting YouTube config "{0}"'
                              .format(configs['main']['system']))

            refresh_tokens = access_manager.get_refresh_token(dev_id)
            if refresh_tokens:
                if self._api_check.changed:
                    context.log_warning('API key set changed: Resetting client'
                                        ' and updating access token')
                    self.reset_client()
                    access_tokens = []
                    refresh_tokens = []
                    access_manager.update_access_token(
                        dev_id, access_tokens, -1, refresh_tokens,
                    )

                context.log_debug(
                    'Access token count: |{0}|, refresh token count: |{1}|'
                    .format(len(access_tokens), len(refresh_tokens))
                )

        settings = context.get_settings()
        client = YouTube(context=context,
                         language=settings.get_language(),
                         region=settings.get_region(),
                         items_per_page=settings.items_per_page(),
                         configs=configs)

        with client:
            if not refresh_tokens:
                self._client = client

            # create new access tokens
            elif len(access_tokens) != 2 and len(refresh_tokens) == 2:
                try:
                    kodi_token = client.refresh_token(refresh_tokens[1])
                    tv_token = client.refresh_token_tv(refresh_tokens[0])
                    access_tokens = (tv_token[0], kodi_token[0])
                    expires_in = min(tv_token[1], kodi_token[1])
                    access_manager.update_access_token(
                        dev_id, access_tokens, expires_in,
                    )
                except (InvalidGrant, LoginException) as exc:
                    self.handle_exception(context, exc)
                    # reset access_token
                    if isinstance(exc, InvalidGrant):
                        access_manager.update_access_token(
                            dev_id, access_token='', refresh_token='',
                        )
                    else:
                        access_manager.update_access_token(dev_id)

            # in debug log the login status
            self._logged_in = len(access_tokens) == 2
            if self._logged_in:
                context.log_debug('User is logged in')
                client.set_access_token_tv(access_token_tv=access_tokens[0])
                client.set_access_token(access_token=access_tokens[1])
            else:
                context.log_debug('User is not logged in')
                client.set_access_token_tv(access_token_tv='')
                client.set_access_token(access_token='')

        self._client = client
        return self._client

    def get_resource_manager(self, context):
        resource_manager = self._resource_manager
        if not resource_manager or resource_manager.context_changed(context):
            new_resource_manager = ResourceManager(proxy(self), context)
            if not resource_manager:
                self._resource_manager = new_resource_manager
            return new_resource_manager
        return resource_manager

    @AbstractProvider.register_path('^/uri2addon/?$')
    @staticmethod
    def on_uri2addon(provider, context, uri=None, **_kwargs):
        if uri is None:
            uri = context.get_param('uri')
            skip_title = True
            listing = False
        else:
            skip_title = False
            listing = True

        if not uri:
            return False

        url_resolver = UrlResolver(context)
        resolved_url = url_resolver.resolve(uri)
        url_converter = UrlToItemConverter(flatten=True)
        url_converter.add_url(resolved_url, context)
        items = url_converter.get_items(provider=provider,
                                        context=context,
                                        skip_title=skip_title)
        if items:
            return items if listing else items[0]

        return False

    """
    Lists the videos of a playlist.
    path       : '/channel/(?P<channel_id>[^/]+)/playlist/(?P<playlist_id>[^/]+)/'
        or
    path       : '/playlist/(?P<playlist_id>[^/]+)/'
    channel_id : ['mine'|<CHANNEL_ID>]
    playlist_id: <PLAYLIST_ID>
    """

    @AbstractProvider.register_path(
        r'^(?:/channel/(?P<channel_id>[^/]+))?'
        r'/playlist/(?P<playlist_id>[^/]+)/?$'
    )
    @staticmethod
    def on_playlist(provider, context, re_match):
        context.set_content(CONTENT.VIDEO_CONTENT)
        resource_manager = provider.get_resource_manager(context)

        batch_id = (re_match.group('playlist_id'),
                    context.get_param('page_token') or 0)

        json_data = resource_manager.get_playlist_items(batch_id=batch_id)
        if not json_data:
            return False
        result = v3.response_to_items(provider, context, json_data[batch_id])
        return result

    """
    Lists all playlists of a channel.
    path      : '/channel/(?P<channel_id>[^/]+)/playlists/'
    channel_id: <CHANNEL_ID>
    """

    @AbstractProvider.register_path(
        r'^/channel/(?P<channel_id>[^/]+)'
        r'/playlists/?$')
    @staticmethod
    def on_channel_playlists(provider, context, re_match):
        context.set_content(CONTENT.LIST_CONTENT)

        channel_id = re_match.group('channel_id')

        params = context.get_params()
        page_token = params.get('page_token', '')
        incognito = params.get('incognito')
        addon_id = params.get('addon_id')

        new_params = {}
        if incognito:
            new_params['incognito'] = incognito
        if addon_id:
            new_params['addon_id'] = addon_id

        resource_manager = provider.get_resource_manager(context)
        fanart = resource_manager.get_fanarts(
            (channel_id,), force=True
        ).get(channel_id)
        playlists = resource_manager.get_related_playlists(channel_id)

        uploads = playlists.get('uploads')
        if uploads:
            item_label = context.localize('uploads')
            uploads = DirectoryItem(
                context.get_ui().bold(item_label),
                context.create_uri(
                    ('channel', channel_id, 'playlist', uploads),
                    new_params,
                ),
                image='{media}/playlist.png',
                fanart=fanart,
                category_label=item_label,
            )
            result = [uploads]
        else:
            result = False

        json_data = provider.get_client(context).get_playlists_of_channel(
            channel_id, page_token
        )
        if not json_data:
            return result

        if not result:
            result = []
        result.extend(v3.response_to_items(provider, context, json_data))
        return result

    """
    List live streams for channel.
    path      : '/channel/(?P<channel_id>[^/]+)/live/'
    channel_id: <CHANNEL_ID>
    """

    @AbstractProvider.register_path(
        r'^/channel/(?P<channel_id>[^/]+)'
        r'/live/?$')
    @staticmethod
    def on_channel_live(provider, context, re_match):
        context.set_content(CONTENT.VIDEO_CONTENT)
        result = []

        channel_id = re_match.group('channel_id')
        params = context.get_params()
        page_token = params.get('page_token', '')

        client = provider.get_client(context)
        function_cache = context.get_function_cache()
        resource_manager = provider.get_resource_manager(context)

        playlists = function_cache.run(resource_manager.get_related_playlists,
                                       function_cache.ONE_DAY,
                                       channel_id=channel_id)
        if playlists and 'uploads' in playlists:
            json_data = function_cache.run(client.get_playlist_items,
                                           function_cache.ONE_MINUTE * 5,
                                           _refresh=params.get('refresh'),
                                           playlist_id=playlists['uploads'],
                                           page_token=page_token)
            if not json_data:
                return result

            result.extend(v3.response_to_items(
                provider, context, json_data,
                item_filter={
                    'live_folder': True,
                },
            ))

        return result

    """
    Lists a playlist folder and all uploaded videos of a channel.
    path      :'/channel|handle|user/(?P<channel_id|username>)[^/]+/'
    channel_id: <CHANNEL_ID>
    """

    @AbstractProvider.register_path(
        r'^/(?P<method>(channel|handle|user))'
        r'/(?P<identifier>[^/]+)/?$')
    @staticmethod
    def on_channel(provider, context, re_match):
        listitem_channel_id = context.get_listitem_property(CHANNEL_ID)

        client = provider.get_client(context)
        localize = context.localize
        create_uri = context.create_uri
        function_cache = context.get_function_cache()
        params = context.get_params()
        ui = context.get_ui()

        method = re_match.group('method')
        identifier = re_match.group('identifier')

        if (method == 'channel'
                and identifier
                and identifier.lower() == 'property'
                and listitem_channel_id
                and listitem_channel_id.lower().startswith(('mine', 'uc'))):
            context.execute('ActivateWindow(Videos, {channel}, return)'.format(
                channel=create_uri(('channel', listitem_channel_id))
            ))

        if method == 'channel' and not identifier:
            return False

        context.set_content(CONTENT.VIDEO_CONTENT)

        resource_manager = provider.get_resource_manager(context)

        result = []

        """
        This is a helper routine that will retrieve the correct channel ID if we
        only have the handle or username of a channel.
        """
        if identifier == 'mine':
            method = 'mine'
        elif identifier.startswith('@'):
            method = 'handle'
        if method == 'channel':
            channel_id = identifier
        else:
            channel_id = None
            identifier = {method: True, 'identifier': identifier}

        if not channel_id:
            context.log_debug('Trying to get channel ID for |{0}|'.format(
                identifier['identifier']
            ))
            json_data = function_cache.run(client.get_channel_by_identifier,
                                           function_cache.ONE_DAY,
                                           _refresh=params.get('refresh'),
                                           **identifier)
            if not json_data:
                return False

            identifier = identifier['identifier']
            # we correct the channel id based on the username
            items = json_data.get('items', [])
            if items:
                channel_id = items[0]['id']
            else:
                context.log_debug('Channel ID not found for |{0}|'.format(
                    identifier
                ))

        if not channel_id:
            return False

        fanart = resource_manager.get_fanarts(
            (channel_id,), force=True
        ).get(channel_id)

        page = params.get('page', 1)
        page_token = params.get('page_token', '')
        incognito = params.get('incognito')
        addon_id = params.get('addon_id')

        new_params = {}
        if incognito:
            new_params['incognito'] = incognito
        if addon_id:
            new_params['addon_id'] = addon_id

        hide_folders = params.get('hide_folders')

        if page == 1 and not hide_folders:
            hide_playlists = params.get('hide_playlists')
            hide_search = params.get('hide_search')
            hide_live = params.get('hide_live')

            if not hide_playlists:
                item_label = localize('playlists')
                playlists_item = DirectoryItem(
                    ui.bold(item_label),
                    create_uri(
                        ('channel', channel_id, 'playlists'),
                        new_params,
                    ),
                    image='{media}/playlist.png',
                    fanart=fanart,
                    category_label=item_label,
                )
                result.append(playlists_item)

            if not hide_search:
                search_item = NewSearchItem(
                    context, name=ui.bold(localize('search')),
                    image='{media}/search.png',
                    fanart=fanart,
                    channel_id=channel_id,
                    incognito=incognito,
                    addon_id=addon_id,
                )
                result.append(search_item)

            if not hide_live:
                item_label = localize('live')
                live_item = DirectoryItem(
                    ui.bold(item_label),
                    create_uri(
                        ('channel', channel_id, 'live'),
                        new_params,
                    ),
                    image='{media}/live.png',
                    fanart=fanart,
                    category_label=item_label,
                )
                result.append(live_item)

        playlists = function_cache.run(resource_manager.get_related_playlists,
                                       function_cache.ONE_DAY,
                                       channel_id=identifier)
        if playlists and 'uploads' in playlists:
            json_data = function_cache.run(client.get_playlist_items,
                                           function_cache.ONE_MINUTE * 5,
                                           _refresh=params.get('refresh'),
                                           playlist_id=playlists['uploads'],
                                           page_token=page_token)
            if not json_data:
                return result

            result.extend(v3.response_to_items(
                provider, context, json_data,
                item_filter={
                    'live': False,
                    'upcoming_live': False,
                },
            ))

        return result

    @AbstractProvider.register_path('^/location/mine/?$')
    @staticmethod
    def on_my_location(context, **_kwargs):
        context.set_content(CONTENT.LIST_CONTENT)

        create_uri = context.create_uri
        localize = context.localize
        settings = context.get_settings()
        result = []

        # search
        search_item = SearchItem(
            context,
            image='{media}/search.png',
            location=True
        )
        result.append(search_item)

        # completed live events
        if settings.get_bool('youtube.folder.completed.live.show', True):
            live_events_item = DirectoryItem(
                localize('live.completed'),
                create_uri(
                    ('special', 'completed_live'),
                    params={'location': True},
                ),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # upcoming live events
        if settings.get_bool('youtube.folder.upcoming.live.show', True):
            live_events_item = DirectoryItem(
                localize('live.upcoming'),
                create_uri(
                    ('special', 'upcoming_live'),
                    params={'location': True},
                ),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # live events
        live_events_item = DirectoryItem(
            localize('live'),
            create_uri(
                ('special', 'live'),
                params={'location': True},
            ),
            image='{media}/live.png',
        )
        result.append(live_events_item)

        return result

    """
    Plays a video, playlist, or channel live stream.
    Video: '/play/?video_id=XXXXXX'

    Playlist: '/play/?playlist_id=XXXXXX[&order=ORDER][&action=ACTION]'
        ORDER: [normal(default)|reverse|shuffle] optional playlist ordering
        ACTION: [list|play|queue|None(default)] optional action to perform

    Channel live streams: '/play/?channel_id=UCXXXXXX[&live=X]
        X: optional index of live stream to play if channel has multiple live
           streams. 1 (default) for first live stream
    """

    @AbstractProvider.register_path('^/users/(?P<action>[^/]+)/?$')
    @staticmethod
    def on_users(re_match, **_kwargs):
        action = re_match.group('action')
        return UriItem('script://{addon},users/{action}'.format(
            addon=ADDON_ID, action=action
        ))

    @AbstractProvider.register_path('^/sign/(?P<mode>[^/]+)/?$')
    @staticmethod
    def on_sign(provider, context, re_match):
        sign_out_confirmed = context.get_param('confirmed')
        mode = re_match.group('mode')
        if (mode == 'in') and context.get_access_manager().get_refresh_token():
            yt_login.process('out', provider, context, sign_out_refresh=False)

        if (not sign_out_confirmed and mode == 'out'
                and context.get_ui().on_yes_no_input(
                    context.localize('sign.out'),
                    context.localize('are_you_sure')
                )):
            sign_out_confirmed = True

        if mode == 'in' or (mode == 'out' and sign_out_confirmed):
            yt_login.process(mode, provider, context)
        return False

    def _search_channel_or_playlist(self, context, identifier):
        if re.match(r'U[CU][0-9a-zA-Z_\-]{20,24}', identifier):
            json_data = self.get_client(context).get_channels(identifier)
        elif re.match(r'[OP]L[0-9a-zA-Z_\-]{30,40}', identifier):
            json_data = self.get_client(context).get_playlists(identifier)
        else:
            return False

        if json_data:
            return v3.response_to_items(self, context, json_data)
        return False

    def on_search_run(self, context, search_text):
        # Search by url to access unlisted videos
        if search_text.startswith(('https://', 'http://')):
            return self.on_uri2addon(provider=self,
                                     context=context,
                                     uri=search_text)
        if context.is_plugin_path(search_text):
            return self.reroute(context=context, uri=search_text)

        result = self._search_channel_or_playlist(context, search_text)
        if result:  # found a channel or playlist matching search_text
            return result
        result = []

        context.set_param('q', search_text)
        context.set_param('category_label', search_text)

        params = context.get_params()
        channel_id = params.get('channel_id')
        event_type = params.get('event_type')
        hide_folders = params.get('hide_folders')
        location = params.get('location')
        page = params.get('page', 1)
        page_token = params.get('page_token', '')
        order = params.get('order', 'relevance')
        search_type = params.get('search_type', 'video')
        safe_search = context.get_settings().safe_search()

        context.get_data_cache().set_item('search_query', search_text)
        if not params.get('incognito') and not params.get('channel_id'):
            context.get_search_history().add_item(search_text)

        if search_type == 'video':
            context.set_content(CONTENT.VIDEO_CONTENT)
        else:
            context.set_content(CONTENT.LIST_CONTENT)

        if (page == 1
                and search_type == 'video'
                and not event_type
                and not hide_folders):
            if not channel_id and not location:
                channel_params = dict(params, search_type='channel')
                item_label = context.localize('channels')
                channel_item = DirectoryItem(
                    context.get_ui().bold(item_label),
                    context.create_uri((context.get_path(),), channel_params),
                    image='{media}/channels.png',
                    category_label=item_label,
                )
                result.append(channel_item)

            if not location:
                playlist_params = dict(params, search_type='playlist')
                item_label = context.localize('playlists')
                playlist_item = DirectoryItem(
                    context.get_ui().bold(item_label),
                    context.create_uri((context.get_path(),), playlist_params),
                    image='{media}/playlist.png',
                    category_label=item_label,
                )
                result.append(playlist_item)

            if not channel_id:
                # live
                live_params = dict(params,
                                   search_type='video',
                                   event_type='live')
                item_label = context.localize('live')
                live_item = DirectoryItem(
                    context.get_ui().bold(item_label),
                    context.create_uri(
                        (context.get_path().replace('input', 'query'),),
                        live_params,
                    ),
                    image='{media}/live.png',
                    category_label=item_label,
                )
                result.append(live_item)

        function_cache = context.get_function_cache()
        json_data = function_cache.run(self.get_client(context).search,
                                       function_cache.ONE_MINUTE * 10,
                                       _refresh=params.get('refresh'),
                                       q=search_text,
                                       search_type=search_type,
                                       event_type=event_type,
                                       safe_search=safe_search,
                                       page_token=page_token,
                                       channel_id=channel_id,
                                       order=order,
                                       location=location)
        if not json_data:
            return False
        result.extend(v3.response_to_items(
            self, context, json_data,
            item_filter={
                'live_folder': True,
            } if event_type else {
                'live': False,
            },
        ))
        return result

    @AbstractProvider.register_path('^/config/(?P<action>[^/]+)/?$')
    @staticmethod
    def on_configure_addon(provider, context, re_match):
        action = re_match.group('action')
        if action == 'setup_wizard':
            provider.run_wizard(context)
            return False
        return UriItem('script://{addon},config/{action}'.format(
            addon=ADDON_ID, action=action
        ))

    @AbstractProvider.register_path('^/my_subscriptions/filter/?$')
    @staticmethod
    def on_manage_my_subscription_filter(context, **_kwargs):
        settings = context.get_settings()
        ui = context.get_ui()

        params = context.get_params()
        action = params.get('action')
        channel = params.get('channel_name')
        if not channel or not action:
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

    @AbstractProvider.register_path(
        r'^/maintenance'
        r'/(?P<action>[^/]+)'
        r'/(?P<target>[^/]+)/?$'
    )
    @staticmethod
    def on_maintenance_actions(provider, context, re_match):
        target = re_match.group('target')
        action = re_match.group('action')

        if action != 'reset':
            return UriItem(
                'script://{addon},maintenance/{action}/?target={target}'.format(
                    addon=ADDON_ID, action=action, target=target,
                )
            )

        ui = context.get_ui()
        localize = context.localize

        if target == 'access_manager' and ui.on_yes_no_input(
                context.get_name(), localize('reset.access_manager.confirm')
        ):
            addon_id = context.get_param('addon_id', None)
            access_manager = context.get_access_manager()
            client = provider.get_client(context)
            refresh_tokens = access_manager.get_refresh_token()
            success = True
            if refresh_tokens:
                for refresh_token in set(refresh_tokens):
                    try:
                        client.revoke(refresh_token)
                    except LoginException:
                        success = False
            provider.reset_client()
            access_manager.update_access_token(
                addon_id, access_token='', refresh_token='',
            )
            ui.refresh_container()
            ui.show_notification(localize('succeeded' if success else 'failed'))

    @AbstractProvider.register_path('^/api/update/?$')
    @staticmethod
    def on_api_key_update(context, **_kwargs):
        localize = context.localize
        settings = context.get_settings()
        ui = context.get_ui()

        params = context.get_params()
        api_key = params.get('api_key')
        client_id = params.get('client_id')
        client_secret = params.get('client_secret')
        enable = params.get('enable')

        updated_list = []
        log_list = []

        if api_key:
            settings.api_key(api_key)
            updated_list.append(localize('api.key'))
            log_list.append('Key')
        if client_id:
            settings.api_id(client_id)
            updated_list.append(localize('api.id'))
            log_list.append('Id')
        if client_secret:
            settings.api_secret(client_secret)
            updated_list.append(localize('api.secret'))
            log_list.append('Secret')
        if updated_list:
            ui.show_notification(localize('updated_') % ', '.join(updated_list))
        context.log_debug('Updated API keys: %s' % ', '.join(log_list))

        client_id = settings.api_id()
        client_secret = settings.api_secret()
        api_key = settings.api_key
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

    @staticmethod
    def on_playback_history(provider, context, re_match):
        params = context.get_params()
        action = params.get('action')
        if not action:
            return False

        playback_history = context.get_playback_history()

        if action == 'list':
            context.set_content(CONTENT.VIDEO_CONTENT, sub_type='history')
            items = playback_history.get_items()
            if not items:
                return True

            v3_response = {
                'kind': 'youtube#videoListResponse',
                'items': [
                    {
                        'kind': 'youtube#video',
                        'id': video_id,
                        '_partial': True,
                        '_context_menu': {
                            'context_menu': (
                                menu_items.history_remove(
                                    context, video_id
                                ),
                                menu_items.history_clear(
                                    context
                                ),
                                menu_items.separator(),
                            ),
                            'position': 0,
                        }
                    }
                    for video_id in items.keys()
                ]
            }
            video_items = v3.response_to_items(provider, context, v3_response)
            return video_items

        if action == 'clear' and context.get_ui().on_yes_no_input(
                context.get_name(),
                context.localize('history.clear.confirm')
        ):
            playback_history.clear()
            context.get_ui().refresh_container()
            return True

        video_id = params.get('video_id')
        if not video_id:
            return False

        if action == 'remove':
            playback_history.del_item(video_id)
            context.get_ui().refresh_container()
            return True

        play_data = playback_history.get_item(video_id)
        if play_data:
            playback_history_method = playback_history.update_item
        else:
            playback_history_method = playback_history.set_item
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

        playback_history_method(video_id, play_data)
        context.get_ui().refresh_container()
        return True

    @staticmethod
    def on_root(provider, context, re_match):
        create_uri = context.create_uri
        localize = context.localize
        settings = context.get_settings()
        settings_bool = settings.get_bool
        bold = context.get_ui().bold

        _ = provider.get_client(context)  # required for self.is_logged_in()
        logged_in = provider.is_logged_in()
        # _.get_my_playlists()

        # context.set_content(CONTENT.LIST_CONTENT)

        result = []

        # sign in
        if not logged_in and settings_bool('youtube.folder.sign.in.show', True):
            item_label = localize('sign.in')
            sign_in_item = DirectoryItem(
                bold(item_label),
                create_uri(('sign', 'in')),
                image='{media}/sign_in.png',
                action=True,
                category_label=item_label,
            )
            result.append(sign_in_item)

        if settings_bool('youtube.folder.my_subscriptions.show', True):
            # my subscription
            item_label = localize('my_subscriptions')
            my_subscriptions_item = DirectoryItem(
                bold(item_label),
                create_uri(('special', 'my_subscriptions')),
                image='{media}/new_uploads.png',
                category_label=item_label,
            )
            result.append(my_subscriptions_item)

        if settings_bool('youtube.folder.my_subscriptions_filtered.show'):
            # my subscriptions filtered
            my_subscriptions_filtered_item = DirectoryItem(
                localize('my_subscriptions.filtered'),
                create_uri(('special', 'my_subscriptions_filtered')),
                image='{media}/new_uploads.png',
            )
            result.append(my_subscriptions_filtered_item)

        access_manager = context.get_access_manager()
        watch_later_id = logged_in and access_manager.get_watch_later_id()
        history_id = logged_in and access_manager.get_watch_history_id()
        local_history = settings.use_local_history()

        # Home / Recommendations
        if logged_in and settings_bool('youtube.folder.recommendations.show', True):
            recommendations_item = DirectoryItem(
                localize('recommendations'),
                create_uri(('special', 'recommendations')),
                image='{media}/home.png',
            )
            result.append(recommendations_item)

        # Related
        if settings_bool('youtube.folder.related.show', True):
            if history_id or local_history:
                related_item = DirectoryItem(
                    localize('related_videos'),
                    create_uri(('special', 'related_videos')),
                    image='{media}/related_videos.png',
                )
                result.append(related_item)

        # Trending
        if settings_bool('youtube.folder.popular_right_now.show', True):
            trending_item = DirectoryItem(
                localize('trending'),
                create_uri(('special', 'popular_right_now')),
                image='{media}/trending.png',
            )
            result.append(trending_item)

        # search
        if settings_bool('youtube.folder.search.show', True):
            search_item = SearchItem(
                context,
            )
            result.append(search_item)

        if settings_bool('youtube.folder.quick_search.show'):
            quick_search_item = NewSearchItem(
                context,
                name=localize('search.quick'),
                image='{media}/quick_search.png',
            )
            result.append(quick_search_item)

        if settings_bool('youtube.folder.quick_search_incognito.show'):
            quick_search_incognito_item = NewSearchItem(
                context,
                name=localize('search.quick.incognito'),
                image='{media}/incognito_search.png',
                incognito=True,
            )
            result.append(quick_search_incognito_item)

        # my location
        if settings_bool('youtube.folder.my_location.show', True) and settings.get_location():
            my_location_item = DirectoryItem(
                localize('my_location'),
                create_uri(('location', 'mine')),
                image='{media}/location.png',
            )
            result.append(my_location_item)

        # my channel
        if logged_in and settings_bool('youtube.folder.my_channel.show', True):
            my_channel_item = DirectoryItem(
                localize('my_channel'),
                create_uri(('channel', 'mine')),
                image='{media}/user.png',
            )
            result.append(my_channel_item)

        # watch later
        if settings_bool('youtube.folder.watch_later.show', True):
            if watch_later_id:
                watch_later_item = DirectoryItem(
                    localize('watch_later'),
                    create_uri(('channel', 'mine', 'playlist', watch_later_id)),
                    image='{media}/watch_later.png',
                )
                context_menu = [
                    menu_items.play_all_from_playlist(
                        context, watch_later_id
                    )
                ]
                watch_later_item.add_context_menu(context_menu)
                result.append(watch_later_item)
            else:
                watch_history_item = DirectoryItem(
                    localize('watch_later'),
                    create_uri((PATHS.WATCH_LATER, 'list')),
                    image='{media}/watch_later.png',
                )
                result.append(watch_history_item)

        # liked videos
        if logged_in and settings_bool('youtube.folder.liked_videos.show', True):
            resource_manager = provider.get_resource_manager(context)
            playlists = resource_manager.get_related_playlists('mine')
            if playlists and 'likes' in playlists:
                liked_videos_item = DirectoryItem(
                    localize('video.liked'),
                    create_uri(('channel', 'mine', 'playlist', playlists['likes'])),
                    image='{media}/likes.png',
                )
                context_menu = [
                    menu_items.play_all_from_playlist(
                        context, playlists['likes']
                    )
                ]
                liked_videos_item.add_context_menu(context_menu)
                result.append(liked_videos_item)

        # disliked videos
        if logged_in and settings_bool('youtube.folder.disliked_videos.show', True):
            disliked_videos_item = DirectoryItem(
                localize('video.disliked'),
                create_uri(('special', 'disliked_videos')),
                image='{media}/dislikes.png',
            )
            result.append(disliked_videos_item)

        # history
        if settings_bool('youtube.folder.history.show', False):
            if history_id:
                watch_history_item = DirectoryItem(
                    localize('history'),
                    create_uri(('channel', 'mine', 'playlist', history_id)),
                    image='{media}/history.png',
                )
                context_menu = [
                    menu_items.play_all_from_playlist(
                        context, history_id
                    )
                ]
                watch_history_item.add_context_menu(context_menu)
                result.append(watch_history_item)
            elif local_history:
                watch_history_item = DirectoryItem(
                    localize('history'),
                    create_uri((PATHS.HISTORY,), params={'action': 'list'}),
                    image='{media}/history.png',
                )
                result.append(watch_history_item)

        # (my) playlists
        if logged_in and settings_bool('youtube.folder.playlists.show', True):
            playlists_item = DirectoryItem(
                localize('playlists'),
                create_uri(('channel', 'mine', 'playlists')),
                image='{media}/playlist.png',
            )
            result.append(playlists_item)

        # saved playlists
        # TODO: re-enable once functionality is restored
        # if logged_in and settings_bool('youtube.folder.saved.playlists.show', True):
        #     playlists_item = DirectoryItem(
        #         localize('saved.playlists'),
        #         create_uri(('special', 'saved_playlists')),
        #         image='{media}/playlist.png',
        #     )
        #     result.append(playlists_item)

        # subscriptions
        if logged_in and settings_bool('youtube.folder.subscriptions.show', True):
            subscriptions_item = DirectoryItem(
                localize('subscriptions'),
                create_uri(('subscriptions', 'list')),
                image='{media}/channels.png',
            )
            result.append(subscriptions_item)

        # bookmarks
        if settings_bool('youtube.folder.bookmarks.show', True):
            bookmarks_item = DirectoryItem(
                localize('bookmarks'),
                create_uri((PATHS.BOOKMARKS, 'list')),
                image='{media}/bookmarks.png',
            )
            result.append(bookmarks_item)

        # browse channels
        if logged_in and settings_bool('youtube.folder.browse_channels.show', True):
            browse_channels_item = DirectoryItem(
                localize('browse_channels'),
                create_uri(('special', 'browse_channels')),
                image='{media}/browse_channels.png',
            )
            result.append(browse_channels_item)

        # completed live events
        if settings_bool('youtube.folder.completed.live.show', True):
            live_events_item = DirectoryItem(
                localize('live.completed'),
                create_uri(('special', 'completed_live')),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # upcoming live events
        if settings_bool('youtube.folder.upcoming.live.show', True):
            live_events_item = DirectoryItem(
                localize('live.upcoming'),
                create_uri(('special', 'upcoming_live')),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # live events
        if settings_bool('youtube.folder.live.show', True):
            live_events_item = DirectoryItem(
                localize('live'),
                create_uri(('special', 'live')),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # switch user
        if settings_bool('youtube.folder.switch.user.show', True):
            switch_user_item = DirectoryItem(
                localize('user.switch'),
                create_uri(('users', 'switch')),
                image='{media}/user.png',
                action=True,
            )
            result.append(switch_user_item)

        # sign out
        if logged_in and settings_bool('youtube.folder.sign.out.show', True):
            sign_out_item = DirectoryItem(
                localize('sign.out'),
                create_uri(('sign', 'out')),
                image='{media}/sign_out.png',
                action=True,
            )
            result.append(sign_out_item)

        if settings_bool('youtube.folder.settings.show', True):
            settings_menu_item = DirectoryItem(
                localize('setup_wizard'),
                create_uri(('config', 'setup_wizard')),
                image='{media}/settings.png',
                action=True,
            )
            result.append(settings_menu_item)

        if settings_bool('youtube.folder.settings.advanced.show'):
            settings_menu_item = DirectoryItem(
                localize('settings'),
                create_uri(('config', 'youtube')),
                image='{media}/settings.png',
                action=True,
            )
            result.append(settings_menu_item)

        return result

    @staticmethod
    def on_bookmarks(provider, context, re_match):
        params = context.get_params()
        command = re_match.group('command')
        if not command:
            return False

        if command == 'list':
            context.set_content(CONTENT.VIDEO_CONTENT)
            bookmarks_list = context.get_bookmarks_list()
            items = bookmarks_list.get_items()
            if not items:
                return True

            v3_response = {
                'kind': 'youtube#pluginListResponse',
                'items': []
            }

            def _update_bookmark(_id, timestamp):
                def _update(new_item):
                    new_item.set_bookmark_timestamp(timestamp)
                    bookmarks_list.update_item(_id, repr(new_item), timestamp)

                return _update

            for item_id, item in items.items():
                if isinstance(item, float):
                    kind = 'youtube#channel'
                    yt_id = item_id
                    callback = _update_bookmark(item_id, item)
                    partial = True
                else:
                    callback = None
                    partial = False
                    if isinstance(item, VideoItem):
                        kind = 'youtube#video'
                        yt_id = item.video_id
                    else:
                        yt_id = item.playlist_id
                        if yt_id:
                            kind = 'youtube#playlist'
                        else:
                            kind = 'youtube#channel'
                            yt_id = item.channel_id

                if not yt_id:
                    continue

                item = {
                    'kind': kind,
                    'id': yt_id,
                    '_partial': partial,
                    '_context_menu': {
                        'context_menu': (
                            menu_items.bookmark_remove(
                                context, item_id
                            ),
                            menu_items.bookmarks_clear(
                                context
                            ),
                            menu_items.separator(),
                        ),
                        'position': 0,
                    },
                }
                if callback:
                    item['_callback'] = callback
                v3_response['items'].append(item)

            bookmarks = v3.response_to_items(provider, context, v3_response)
            return bookmarks

        ui = context.get_ui()
        localize = context.localize

        if command == 'clear' and ui.on_yes_no_input(
                context.get_name(),
                localize('bookmarks.clear.confirm')
        ):
            context.get_bookmarks_list().clear()
            ui.refresh_container()

            ui.show_notification(
                localize('succeeded'),
                time_ms=2500,
                audible=False
            )
            return True

        item_id = params.get('item_id')
        if not item_id:
            return False

        if command == 'add':
            item = params.get('item')
            context.get_bookmarks_list().add_item(item_id, item)

            ui.show_notification(
                localize('bookmark.created'),
                time_ms=2500,
                audible=False
            )
            return True

        if command == 'remove':
            context.get_bookmarks_list().del_item(item_id)
            context.get_ui().refresh_container()

            ui.show_notification(
                localize('removed') % localize('bookmark'),
                time_ms=2500,
                audible=False
            )
            return True

        return False

    @staticmethod
    def on_watch_later(provider, context, re_match):
        params = context.get_params()
        command = re_match.group('command')
        if not command:
            return False

        if command == 'list':
            context.set_content(CONTENT.VIDEO_CONTENT, sub_type='watch_later')
            items = context.get_watch_later_list().get_items()
            if not items:
                return True

            v3_response = {
                'kind': 'youtube#videoListResponse',
                'items': [
                    {
                        'kind': 'youtube#video',
                        'id': video_id,
                        '_partial': True,
                        '_context_menu': {
                            'context_menu': (
                                menu_items.watch_later_local_remove(
                                    context, video_id
                                ),
                                menu_items.watch_later_local_clear(
                                    context
                                ),
                                menu_items.separator(),
                            ),
                            'position': 0,
                        }
                    }
                    for video_id in items.keys()
                ]
            }
            video_items = v3.response_to_items(provider, context, v3_response)
            return video_items

        if command == 'clear' and context.get_ui().on_yes_no_input(
                context.get_name(),
                context.localize('watch_later.clear.confirm')
        ):
            context.get_watch_later_list().clear()
            context.get_ui().refresh_container()
            return True

        video_id = params.get('video_id')
        if not video_id:
            return False

        if command == 'add':
            item = params.get('item')
            if item:
                context.get_watch_later_list().add_item(video_id, item)
            return True

        if command == 'remove':
            context.get_watch_later_list().del_item(video_id)
            context.get_ui().refresh_container()
            return True

        return False

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
                message = context.localize('key.requirement')
                context.get_access_manager().update_access_token(
                    context.get_param('addon_id', None),
                    access_token='',
                    refresh_token='',
                )
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
                context.get_ui().show_notification(message,
                                                   title,
                                                   time_ms=message_timeout)

            return False

        return True

    def tear_down(self):
        attrs = (
            '_resource_manager',
            '_client',
            '_api_check',
        )
        for attr in attrs:
            try:
                delattr(self, attr)
                setattr(self, attr, None)
            except (AttributeError, TypeError):
                pass
