# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from atexit import register as atexit_register
from base64 import b64decode
from json import loads as json_loads
from re import compile as re_compile
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
from .helper.utils import filter_split, update_duplicate_items
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
    BaseItem,
    DirectoryItem,
    NewSearchItem,
    SearchItem,
    UriItem,
    VideoItem,
    menu_items,
)
from ..kodion.utils import strip_html_from_text, to_unicode


class Provider(AbstractProvider):
    def __init__(self):
        super(Provider, self).__init__()
        self._resource_manager = None
        self._client = None
        self._api_check = None
        self._logged_in = False

        self.on_video_x = self.register_path(
            '^/video/(?P<command>[^/]+)/?$',
            yt_video.process,
        )

        self.on_playlist_x = self.register_path(
            '^/playlist/(?P<command>[^/]+)/(?P<category>[^/]+)/?$',
            yt_playlist.process,
        )

        self.register_path(
            '^/play/?$',
            yt_play.process,
        )

        self.on_specials_x = self.register_path(
            '^/special/(?P<category>[^/]+)/?$',
            yt_specials.process,
        )

        self.register_path(
            '^/subscriptions/(?P<command>[^/]+)/?$',
            yt_subscriptions.process,
        )

        atexit_register(self.tear_down)

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
                dev_config = json_loads(_dev_config)
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
                context.log_error('Invalid developer config: |{dev_config}|'
                                  '\n\texpected: |{{'
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

        access_tokens = access_manager.get_access_token(dev_id)
        if access_manager.is_access_token_expired(dev_id):
            # reset access_token
            access_tokens = [None, None]
            access_manager.update_access_token(dev_id, access_token='')
        elif self._client:
            return self._client

        if not dev_id:
            context.log_debug('Selecting YouTube config "{0}"'
                              .format(configs['main']['system']))
        elif dev_keys:
            context.log_debug('Selecting YouTube developer config "{0}"'
                              .format(dev_id))
            configs['main'] = dev_keys
        else:
            dev_keys = configs['main']
            context.log_debug('Selecting YouTube config "{0}"'
                              ' w/ developer access tokens'
                              .format(dev_keys['system']))

        refresh_tokens = access_manager.get_refresh_token(dev_id)
        if any(refresh_tokens):
            keys_changed = access_manager.dev_keys_changed(
                dev_id, dev_keys['key'], dev_keys['id'], dev_keys['secret']
            ) if dev_id else self._api_check.changed
            if keys_changed:
                context.log_warning('API key set changed: Resetting client'
                                    ' and updating access token')
                access_tokens = [None, None]
                refresh_tokens = [None, None]
                access_manager.update_access_token(
                    dev_id, access_token='', expiry=-1, refresh_token=''
                )
                self.reset_client()

        num_access_tokens = sum(1 for token in access_tokens if token)
        num_refresh_tokens = sum(1 for token in refresh_tokens if token)
        context.log_debug(
            'Access token count: |{0}|, refresh token count: |{1}|'
            .format(num_access_tokens, num_refresh_tokens)
        )

        settings = context.get_settings()
        client = YouTube(context=context,
                         language=settings.get_language(),
                         region=settings.get_region(),
                         items_per_page=settings.items_per_page(),
                         configs=configs)

        with client:
            # create new access tokens
            if num_refresh_tokens and num_access_tokens != num_refresh_tokens:
                access_tokens = [None, None]
                token_expiry = 0
                try:
                    for token_type, value in enumerate(refresh_tokens):
                        if not value:
                            continue

                        json_data = client.refresh_token(token_type, value)
                        if not json_data:
                            continue

                        token = json_data.get('access_token')
                        expiry = int(json_data.get('expires_in', 3600))
                        if token and expiry > 0:
                            access_tokens[token_type] = token
                            if not token_expiry or expiry < token_expiry:
                                token_expiry = expiry

                    if any(access_tokens) and token_expiry:
                        access_manager.update_access_token(
                            dev_id,
                            access_token=access_tokens,
                            expiry=token_expiry,
                        )
                    else:
                        raise InvalidGrant('Failed to refresh access token(s)')

                except (InvalidGrant, LoginException) as exc:
                    self.handle_exception(context, exc)
                    # reset access token
                    # reset refresh token if InvalidGrant otherwise leave as-is
                    # to retry later
                    if isinstance(exc, InvalidGrant):
                        refresh_token = ''
                    else:
                        refresh_token = None
                    access_manager.update_access_token(
                        dev_id,
                        refresh_token=refresh_token,
                    )

                num_access_tokens = sum(1 for token in access_tokens if token)

            if num_access_tokens and access_tokens[1]:
                self._logged_in = True
                context.log_debug('User is logged in')
                client.set_access_token(
                    personal=access_tokens[1],
                    tv=access_tokens[0],
                )
            else:
                self._logged_in = False
                context.log_debug('User is not logged in')
                client.set_access_token(personal='', tv='')

        self._client = client
        return self._client

    def get_resource_manager(self, context, progress_dialog=None):
        resource_manager = self._resource_manager
        if not resource_manager or resource_manager.context_changed(context):
            new_resource_manager = ResourceManager(proxy(self),
                                                   context,
                                                   progress_dialog)
            if not resource_manager:
                self._resource_manager = new_resource_manager
            return new_resource_manager
        if progress_dialog:
            resource_manager.update_progress_dialog(progress_dialog)
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
            return False, None

        url_resolver = UrlResolver(context)
        resolved_url = url_resolver.resolve(uri)
        if not resolved_url:
            return False, None

        url_converter = UrlToItemConverter(flatten=True)
        url_converter.add_url(resolved_url, context)
        items = url_converter.get_items(provider=provider,
                                        context=context,
                                        skip_title=skip_title)
        if items:
            return (items if listing else items[0]), None

        return False, None

    @AbstractProvider.register_path(
        r'^(?:/channel/(?P<channel_id>[^/]+))?'
        r'/playlist/(?P<playlist_id>[^/]+)/?$'
    )
    @staticmethod
    def on_playlist(provider, context, re_match):
        """
        Lists the videos of a playlist.

        plugin://plugin.video.youtube/channel/<CHANNEL_ID>/playlist/<PLAYLIST_ID>

        or

        plugin://plugin.video.youtube/playlist/<PLAYLIST_ID>

        * CHANNEL_ID: ['mine'|YouTube Channel ID]
        * PLAYLIST_ID: YouTube Playlist ID
        """
        context.parse_params({
            'playlist_id': re_match.group('playlist_id'),
        })

        context.set_content(CONTENT.VIDEO_CONTENT)
        resource_manager = provider.get_resource_manager(context)

        batch_id = (re_match.group('playlist_id'),
                    context.get_param('page_token') or 0)

        json_data = resource_manager.get_playlist_items(batch_id=batch_id)
        if not json_data:
            return False
        result = v3.response_to_items(provider, context, json_data[batch_id])
        return result

    @AbstractProvider.register_path(
        r'^/channel/(?P<channel_id>[^/]+)'
        r'/playlists/?$')
    @staticmethod
    def on_channel_playlists(provider, context, re_match):
        """
        Lists all playlists of a channel.

        plugin://plugin.video.youtube/channel/<CHANNEL_ID>/playlists/

        * CHANNEL_ID: YouTube Channel ID
        """
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
        playlists = resource_manager.get_related_playlists(channel_id)
        uploads = playlists.get('uploads') if playlists else None
        if uploads and uploads.startswith('UU'):
            result = [
                {
                    'kind': 'youtube#playlist',
                    'id': uploads,
                    'snippet': {
                        'channelId': channel_id,
                        'title': context.localize('uploads'),
                        'thumbnails': {'default': {
                            'url': 'DefaultVideo.png',
                        }},
                    },
                    '_available': True,
                    '_partial': True,
                },
                {
                    'kind': 'youtube#playlist',
                    'id': uploads.replace('UU', 'UUSH', 1),
                    'snippet': {
                        'channelId': channel_id,
                        'title': context.localize('shorts'),
                        'thumbnails': {'default': {
                            'url': '{media}/shorts.png',
                        }},
                    },
                    '_partial': True,
                },
                {
                    'kind': 'youtube#playlist',
                    'id': uploads.replace('UU', 'UULV', 1),
                    'snippet': {
                        'channelId': channel_id,
                        'title': context.localize('live'),
                        'thumbnails': {'default': {
                            'url': '{media}/live.png',
                        }},
                    },
                    '_partial': True,
                },
            ]
        else:
            result = False

        json_data = resource_manager.get_my_playlists(channel_id, page_token)
        if not json_data:
            return False

        if result and 'items' in json_data:
            result.extend(json_data['items'])
            json_data['items'] = result
        result = v3.response_to_items(provider, context, json_data)
        return result

    @AbstractProvider.register_path(
        r'^/channel/(?P<channel_id>[^/]+)'
        r'/live/?$')
    @staticmethod
    def on_channel_live(provider, context, re_match):
        """
        List live streams for channel.

        plugin://plugin.video.youtube/channel/<CHANNEL_ID>/live

        * CHANNEL_ID: YouTube Channel ID
        """
        context.set_content(CONTENT.VIDEO_CONTENT)

        channel_id = re_match.group('channel_id')

        resource_manager = provider.get_resource_manager(context)
        playlists = resource_manager.get_related_playlists(channel_id)
        uploads = playlists.get('uploads') if playlists else None
        if uploads and uploads.startswith('UU'):
            uploads = uploads.replace('UU', 'UULV', 1)
            batch_id = (uploads, context.get_param('page_token') or 0)
        else:
            return False

        json_data = resource_manager.get_playlist_items(batch_id=batch_id)
        if not json_data:
            return False
        result = v3.response_to_items(
            provider, context, json_data[batch_id],
            item_filter={
                'live_folder': True,
            },
        )
        return result

    @AbstractProvider.register_path(
        r'^/channel/(?P<channel_id>[^/]+)'
        r'/shorts/?$')
    @staticmethod
    def on_channel_shorts(provider, context, re_match):
        """
        List shorts for channel.

        plugin://plugin.video.youtube/channel/<CHANNEL_ID>/shorts

        * CHANNEL_ID: YouTube Channel ID
        """
        context.set_content(CONTENT.VIDEO_CONTENT)

        channel_id = re_match.group('channel_id')

        resource_manager = provider.get_resource_manager(context)
        playlists = resource_manager.get_related_playlists(channel_id)
        uploads = playlists.get('uploads') if playlists else None
        if uploads and uploads.startswith('UU'):
            uploads = uploads.replace('UU', 'UUSH', 1)
            batch_id = (uploads, context.get_param('page_token') or 0)
        else:
            return False

        json_data = resource_manager.get_playlist_items(batch_id=batch_id)
        if not json_data:
            return False
        result = v3.response_to_items(
            provider, context, json_data[batch_id],
            item_filter={
                'shorts': True,
            },
        )
        return result

    @AbstractProvider.register_path(
        r'^/(?P<command>(channel|handle|user))'
        r'/(?P<identifier>[^/]+)/?$')
    @staticmethod
    def on_channel(provider, context, re_match):
        """
        Lists a playlist folder and all uploaded videos of a channel.

        plugin://plugin.video.youtube/<ID_TYPE>/<ID>

        * ID_TYPE: channel|handle|user
        * ID: YouTube ID
        """
        listitem_channel_id = context.get_listitem_property(CHANNEL_ID)

        client = provider.get_client(context)
        create_uri = context.create_uri
        function_cache = context.get_function_cache()
        params = context.get_params()

        command = re_match.group('command')
        identifier = re_match.group('identifier')

        if (command == 'channel'
                and identifier
                and identifier.lower() == 'property'
                and listitem_channel_id
                and listitem_channel_id.lower().startswith(('mine', 'uc'))):
            context.execute('ActivateWindow(Videos, {channel}, return)'.format(
                channel=create_uri(
                    (PATHS.CHANNEL, listitem_channel_id,),
                )
            ))

        if command == 'channel' and not identifier:
            return False

        """
        This is a helper routine that will retrieve the correct channel ID if we
        only have the handle or username of a channel.
        """
        if identifier == 'mine':
            command = 'mine'
        elif identifier.startswith('@'):
            command = 'handle'
        if command == 'channel':
            channel_id = identifier
        else:
            channel_id = None
            identifier = {command: True, 'identifier': identifier}

        if not channel_id:
            context.log_debug('Trying to get channel ID for |{0}|'.format(
                identifier['identifier']
            ))
            json_data = function_cache.run(
                client.get_channel_by_identifier,
                function_cache.ONE_DAY,
                _refresh=params.get('refresh', 0) > 0,
                **identifier
            )
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

        context.parse_params({
            'channel_id': channel_id,
        })

        context.set_content(CONTENT.VIDEO_CONTENT)
        resource_manager = provider.get_resource_manager(context)
        result = []

        page = params.get('page', 1)
        page_token = params.get('page_token', '')
        hide_folders = params.get('hide_folders')

        playlists = resource_manager.get_related_playlists(channel_id)
        uploads = playlists.get('uploads') if playlists else None
        if uploads and not uploads.startswith('UU'):
            uploads = None

        if page == 1 and not hide_folders:
            v3_response = {
                'kind': 'youtube#pluginListResponse',
                'items': [
                    {
                        'kind': 'youtube#playlistFolder',
                        'id': 'playlists',
                        'snippet': {
                            'channelId': channel_id,
                            'title': context.localize('playlists'),
                            'thumbnails': {'default': {
                                'url': '{media}/playlist.png',
                            }},
                        },
                        '_partial': True,
                    } if not params.get('hide_playlists') else None,
                    {
                        'kind': 'youtube#searchFolder',
                        'id': 'search',
                        'snippet': {
                            'channelId': channel_id,
                            'title': context.localize('search'),
                            'thumbnails': {'default': {
                                'url': '{media}/search.png',
                            }},
                        },
                        '_partial': True,
                    } if not params.get('hide_search') else None,
                    {
                        'kind': 'youtube#playlist',
                        'id': uploads.replace('UU', 'UUSH', 1),
                        'snippet': {
                            'channelId': channel_id,
                            'title': context.localize('shorts'),
                            'thumbnails': {'default': {
                                'url': '{media}/shorts.png',
                            }},
                        },
                        '_partial': True,
                    } if uploads and not params.get('hide_shorts') else None,
                    {
                        'kind': 'youtube#playlist',
                        'id': uploads.replace('UU', 'UULV', 1),
                        'snippet': {
                            'channelId': channel_id,
                            'title': context.localize('live'),
                            'thumbnails': {'default': {
                                'url': '{media}/live.png',
                            }},
                        },
                        '_partial': True,
                    } if uploads and not params.get('hide_live') else None,
                ],
            }
            result.extend(v3.response_to_items(provider, context, v3_response))

        if uploads:
            # The "UULF" videos playlist can only be used if videos in a channel
            # are made public. Use "UU" all uploads playlist and filter instead
            # uploads = uploads.replace('UU', 'UULF', 1)
            batch_id = (uploads, page_token or 0)

            json_data = resource_manager.get_playlist_items(batch_id=batch_id)
            if not json_data:
                return result

            context.parse_params({
                'playlist_id': uploads,
            })

            result.extend(v3.response_to_items(
                provider, context, json_data[batch_id],
                item_filter={
                    # 'shorts': False,
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
                    PATHS.LIVE_VIDEOS_COMPLETED,
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
                    PATHS.LIVE_VIDEOS_UPCOMING,
                    params={'location': True},
                ),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # live events
        live_events_item = DirectoryItem(
            localize('live'),
            create_uri(
                PATHS.LIVE_VIDEOS,
                params={'location': True},
            ),
            image='{media}/live.png',
        )
        result.append(live_events_item)

        return result

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
        if mode == 'in':
            refresh_tokens = context.get_access_manager().get_refresh_token()
            if any(refresh_tokens):
                yt_login.process('out',
                                 provider,
                                 context,
                                 sign_out_refresh=False)

        if (not sign_out_confirmed and mode == 'out'
                and context.get_ui().on_yes_no_input(
                    context.localize('sign.out'),
                    context.localize('are_you_sure')
                )):
            sign_out_confirmed = True

        if mode == 'in' or (mode == 'out' and sign_out_confirmed):
            yt_login.process(mode, provider, context)
        return True

    def _search_channel_or_playlist(self,
                                    context,
                                    identifier,
                                    channel_re=re_compile(
                                        r'U[CU][0-9a-zA-Z_\-]{20,24}'
                                    ),
                                    playlist_re=re_compile(
                                        r'[OP]L[0-9a-zA-Z_\-]{30,40}'
                                    )):
        if channel_re.match(identifier):
            json_data = self.get_client(context).get_channels(identifier)
        elif playlist_re.match(identifier):
            json_data = self.get_client(context).get_playlists(identifier)
        else:
            return None

        if json_data:
            return v3.response_to_items(self, context, json_data)
        return None

    def on_search_run(self, context, query=None):
        params = context.get_params()
        if query is None:
            query = to_unicode(params.get('q', ''))

        # Search by url to access unlisted videos
        if query.startswith(('https://', 'http://')):
            return self.on_uri2addon(provider=self, context=context, uri=query)
        if context.is_plugin_path(query):
            return UriItem(query), {
                self.RESULT_CACHE_TO_DISC: False,
                self.RESULT_FALLBACK: False,
            }

        result = self._search_channel_or_playlist(context, query)
        if result:  # found a channel or playlist matching search query
            return result, {
                self.RESULT_CACHE_TO_DISC: False,
                self.RESULT_FALLBACK: False,
            }
        result = []

        context.set_params(category_label=query)

        channel_id = params.get('channel_id') or params.get('channelId')
        event_type = params.get('event_type') or params.get('eventType')
        hide_folders = params.get('hide_folders')
        location = params.get('location')
        page = params.get('page', 1)
        page_token = params.get('page_token') or params.get('pageToken') or ''
        search_type = params.get('search_type', 'video') or params.get('type')

        if search_type == 'video':
            context.set_content(CONTENT.VIDEO_CONTENT)
        else:
            context.set_content(CONTENT.LIST_CONTENT)

        if not hide_folders and page == 1:
            if event_type or search_type != 'video':
                video_params = dict(params,
                                    search_type='video',
                                    event_type='')
                item_label = context.localize('videos')
                video_item = DirectoryItem(
                    context.get_ui().bold(item_label),
                    context.create_uri((context.get_path(),), video_params),
                    image='DefaultVideo.png',
                    category_label=item_label,
                )
                result.append(video_item)

            if not channel_id and not location and search_type != 'channel':
                channel_params = dict(params,
                                      search_type='channel',
                                      event_type='')
                item_label = context.localize('channels')
                channel_item = DirectoryItem(
                    context.get_ui().bold(item_label),
                    context.create_uri((context.get_path(),), channel_params),
                    image='{media}/channels.png',
                    category_label=item_label,
                )
                result.append(channel_item)

            if not location and search_type != 'playlist':
                playlist_params = dict(params,
                                       search_type='playlist',
                                       event_type='')
                item_label = context.localize('playlists')
                playlist_item = DirectoryItem(
                    context.get_ui().bold(item_label),
                    context.create_uri((context.get_path(),), playlist_params),
                    image='{media}/playlist.png',
                    category_label=item_label,
                )
                result.append(playlist_item)

            if not channel_id and event_type != 'live':
                live_params = dict(params,
                                   search_type='video',
                                   event_type='live')
                item_label = context.localize('live')
                live_item = DirectoryItem(
                    context.get_ui().bold(item_label),
                    context.create_uri((context.get_path(),), live_params),
                    image='{media}/live.png',
                    category_label=item_label,
                )
                result.append(live_item)

            if event_type and event_type != 'upcoming':
                upcoming_params = dict(params,
                                       search_type='video',
                                       event_type='upcoming')
                item_label = context.localize('live.upcoming')
                upcoming_item = DirectoryItem(
                    context.get_ui().bold(item_label),
                    context.create_uri((context.get_path(),), upcoming_params),
                    image='{media}/live.png',
                    category_label=item_label,
                )
                result.append(upcoming_item)

            if event_type and event_type != 'completed':
                completed_params = dict(params,
                                        search_type='video',
                                        event_type='completed')
                item_label = context.localize('live.completed')
                completed_item = DirectoryItem(
                    context.get_ui().bold(item_label),
                    context.create_uri((context.get_path(),), completed_params),
                    image='{media}/live.png',
                    category_label=item_label,
                )
                result.append(completed_item)

        search_params = {
            'q': query,
            'channelId': channel_id,
            'type': search_type,
            'eventType': event_type,
            'pageToken': page_token,
            'location': location,
        }
        for param in (context.SEARCH_PARAMS
                .intersection(params.keys())
                .difference(search_params.keys())):
            search_params[param] = params[param]

        function_cache = context.get_function_cache()
        search_params, json_data = function_cache.run(
            self.get_client(context).search_with_params,
            function_cache.ONE_MINUTE * 10,
            _refresh=params.get('refresh', 0) > 0,
            params=search_params,
        )
        if not json_data:
            return False, None

        # Store current search query
        if not params.get('incognito') and not params.get('channel_id'):
            context.get_search_history().add_item(search_params)

        result.extend(v3.response_to_items(
            self, context, json_data,
            item_filter={
                'live_folder': True,
            } if event_type else {
                'live': False,
            },
        ))
        return result, {self.RESULT_CACHE_TO_DISC: False}

    @AbstractProvider.register_path('^/config/(?P<action>[^/]+)/?$')
    @staticmethod
    def on_configure_addon(provider, context, re_match):
        action = re_match.group('action')
        if action == 'setup_wizard':
            provider.run_wizard(context)
            return False, {provider.RESULT_FALLBACK: False}
        return UriItem('script://{addon},config/{action}'.format(
            addon=ADDON_ID, action=action
        ))

    @AbstractProvider.register_path(
        '^/my_subscriptions/filter'
        '/(?P<command>add|remove)/?$'
    )
    @staticmethod
    def on_manage_my_subscription_filter(context, re_match, **_kwargs):
        settings = context.get_settings()
        ui = context.get_ui()

        channel = context.get_param('item_name')
        command = re_match.group('command')
        if not channel or not command:
            return

        filter_enabled = settings.get_bool(
            'youtube.folder.my_subscriptions_filtered.show', False
        )
        if not filter_enabled:
            return

        channel_name = channel.lower()
        channel_name = channel_name.replace(',', '')

        filter_string = settings.get_string(
            'youtube.filter.my_subscriptions_filtered.list', ''
        ).replace(', ', ',')
        custom_filters = []
        filter_list = [
            item.lower()
            for item in filter_string.split(',')
            if item and filter_split(item, custom_filters)
        ]

        if channel_name not in filter_list:
            if command == 'add':
                filter_list.append(channel_name)
            else:
                return False
        elif command == 'remove':
            filter_list = [item for item in filter_list if item != channel_name]
        else:
            return False

        if custom_filters:
            filter_list.extend([
                ''.join([
                    '{' + part + '}'
                    for part in condition
                ])
                for custom_filter in custom_filters
                for condition in custom_filter
            ])
        modified_string = ','.join(filter_list).lstrip(',')
        if filter_string != modified_string:
            settings.set_string('youtube.filter.my_subscriptions_filtered.list',
                                modified_string)

            ui.show_notification(context.localize(
                'my_subscriptions.filter.added'
                if command == 'add' else
                'my_subscriptions.filter.removed'
            ))

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
                context.get_name(), localize('reset.access_manager.check')
        ):
            addon_id = context.get_param('addon_id', None)
            access_manager = context.get_access_manager()
            client = provider.get_client(context)
            refresh_tokens = access_manager.get_refresh_token()
            success = True
            if any(refresh_tokens):
                for refresh_token in frozenset(refresh_tokens):
                    try:
                        if refresh_token:
                            client.revoke(refresh_token)
                    except LoginException:
                        success = False
            provider.reset_client()
            access_manager.update_access_token(
                addon_id, access_token='', expiry=-1, refresh_token='',
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
        command = re_match.group('command')
        if not command:
            return False

        localize = context.localize
        playback_history = context.get_playback_history()
        ui = context.get_ui()

        if command in {'list', 'play'}:
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
                            ),
                            'position': 0,
                        }
                    }
                    for video_id in items.keys()
                ]
            }
            video_items = v3.response_to_items(provider, context, v3_response)
            if command == 'play':
                return yt_play.process_items_for_playlist(
                    context,
                    video_items,
                    action='play',
                    play_from='start',
                )
            return video_items

        if command == 'clear':
            if not ui.on_yes_no_input(
                    localize('history.clear'),
                    localize('history.clear.check')
            ):
                return False, {provider.RESULT_FALLBACK: False}

            playback_history.clear()
            ui.refresh_container()

            ui.show_notification(
                localize('completed'),
                time_ms=2500,
                audible=False,
            )
            return True

        video_id = params.get('video_id')
        if not video_id:
            return False

        if command == 'remove':
            video_name = params.get('item_name') or video_id
            video_name = to_unicode(video_name)
            if not ui.on_yes_no_input(
                    localize('content.remove'),
                    localize('content.remove.check') % video_name,
            ):
                return False, {provider.RESULT_FALLBACK: False}

            playback_history.del_item(video_id)
            ui.refresh_container()

            ui.show_notification(
                localize('removed') % video_name,
                time_ms=2500,
                audible=False,
            )
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

        if command == 'mark_unwatched':
            if play_data.get('play_count', 0) > 0:
                play_data['play_count'] = 0
                play_data['played_time'] = 0
                play_data['played_percent'] = 0

        elif command == 'mark_watched':
            if not play_data.get('play_count', 0):
                play_data['play_count'] = 1

        elif command == 'reset_resume':
            play_data['played_time'] = 0
            play_data['played_percent'] = 0

        playback_history_method(video_id, play_data)
        ui.refresh_container()
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
        context.set_params(category_label=localize('youtube'))

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
                create_uri(PATHS.MY_SUBSCRIPTIONS),
                image='{media}/new_uploads.png',
                category_label=item_label,
            )
            result.append(my_subscriptions_item)

        if settings_bool('youtube.folder.my_subscriptions_filtered.show'):
            # my subscriptions filtered
            my_subscriptions_filtered_item = DirectoryItem(
                localize('my_subscriptions.filtered'),
                create_uri(PATHS.MY_SUBSCRIPTIONS_FILTERED),
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
                create_uri(PATHS.RECOMMENDATIONS),
                image='{media}/home.png',
            )
            result.append(recommendations_item)

        # Related
        if settings_bool('youtube.folder.related.show', True):
            if history_id or local_history:
                related_item = DirectoryItem(
                    localize('related_videos'),
                    create_uri(PATHS.RELATED_VIDEOS),
                    image='{media}/related_videos.png',
                )
                result.append(related_item)

        # Trending
        if settings_bool('youtube.folder.popular_right_now.show', True):
            trending_item = DirectoryItem(
                localize('trending'),
                create_uri(PATHS.TRENDING),
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
                create_uri((PATHS.CHANNEL, 'mine')),
                image='{media}/user.png',
            )
            result.append(my_channel_item)

        # watch later
        if settings_bool('youtube.folder.watch_later.show', True):
            if watch_later_id:
                watch_later_item = DirectoryItem(
                    localize('watch_later'),
                    create_uri(
                        (PATHS.CHANNEL, 'mine', 'playlist', watch_later_id,),
                    ),
                    image='{media}/watch_later.png',
                )
                context_menu = [
                    menu_items.play_playlist(
                        context, watch_later_id
                    ),
                    menu_items.play_playlist_recently_added(
                        context, watch_later_id
                    ),
                    menu_items.view_playlist(
                        context, watch_later_id
                    ),
                    menu_items.shuffle_playlist(
                        context, watch_later_id
                    ),
                ]
                watch_later_item.add_context_menu(context_menu)
                result.append(watch_later_item)
            else:
                watch_later_item = DirectoryItem(
                    localize('watch_later'),
                    create_uri((PATHS.WATCH_LATER, 'list')),
                    image='{media}/watch_later.png',
                )
                context_menu = [
                    menu_items.watch_later_local_clear(context),
                    menu_items.separator(),
                    menu_items.play_all_from(
                        context,
                        path=PATHS.WATCH_LATER,
                    ),
                    menu_items.play_all_from(
                        context,
                        path=PATHS.WATCH_LATER,
                        order='shuffle',
                    ),
                ]
                watch_later_item.add_context_menu(context_menu)
                result.append(watch_later_item)

        # liked videos
        if logged_in and settings_bool('youtube.folder.liked_videos.show', True):
            resource_manager = provider.get_resource_manager(context)
            playlists = resource_manager.get_related_playlists('mine')
            if playlists and 'likes' in playlists:
                liked_list_id = playlists['likes']
                liked_videos_item = DirectoryItem(
                    localize('video.liked'),
                    create_uri(
                        (PATHS.CHANNEL, 'mine', 'playlist', liked_list_id,),
                    ),
                    image='{media}/likes.png',
                )
                context_menu = [
                    menu_items.play_playlist(
                        context, liked_list_id
                    ),
                    menu_items.play_playlist_recently_added(
                        context, liked_list_id
                    ),
                    menu_items.view_playlist(
                        context, liked_list_id
                    ),
                    menu_items.shuffle_playlist(
                        context, liked_list_id
                    ),
                ]
                liked_videos_item.add_context_menu(context_menu)
                result.append(liked_videos_item)

        # disliked videos
        if logged_in and settings_bool('youtube.folder.disliked_videos.show', True):
            disliked_videos_item = DirectoryItem(
                localize('video.disliked'),
                create_uri(PATHS.DISLIKED_VIDEOS),
                image='{media}/dislikes.png',
            )
            result.append(disliked_videos_item)

        # history
        if settings_bool('youtube.folder.history.show', False):
            if history_id:
                watch_history_item = DirectoryItem(
                    localize('history'),
                    create_uri(
                        (PATHS.CHANNEL, 'mine', 'playlist', history_id,),
                    ),
                    image='{media}/history.png',
                )
                context_menu = [
                    menu_items.play_playlist(
                        context, history_id
                    ),
                    menu_items.play_playlist_recently_added(
                        context, history_id
                    ),
                    menu_items.view_playlist(
                        context, history_id
                    ),
                    menu_items.shuffle_playlist(
                        context, history_id
                    ),
                ]
                watch_history_item.add_context_menu(context_menu)
                result.append(watch_history_item)
            elif local_history:
                watch_history_item = DirectoryItem(
                    localize('history'),
                    create_uri((PATHS.HISTORY, 'list')),
                    image='{media}/history.png',
                )
                context_menu = [
                    menu_items.history_clear(
                        context
                    ),
                    menu_items.separator(),
                    menu_items.play_all_from(
                        context,
                        path=PATHS.HISTORY,
                    ),
                    menu_items.play_all_from(
                        context,
                        path=PATHS.HISTORY,
                        order='shuffle',
                    ),
                ]
                watch_history_item.add_context_menu(context_menu)
                result.append(watch_history_item)

        # (my) playlists
        if logged_in and settings_bool('youtube.folder.playlists.show', True):
            playlists_item = DirectoryItem(
                localize('playlists'),
                create_uri(
                    (PATHS.CHANNEL, 'mine', 'playlists',),
                ),
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
            context_menu = [
                menu_items.bookmarks_clear(
                    context
                ),
                menu_items.separator(),
                menu_items.play_all_from(
                    context,
                    path=PATHS.BOOKMARKS,
                ),
                menu_items.play_all_from(
                    context,
                    path=PATHS.BOOKMARKS,
                    order='shuffle',
                ),
            ]
            bookmarks_item.add_context_menu(context_menu)
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
                create_uri(PATHS.LIVE_VIDEOS_COMPLETED),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # upcoming live events
        if settings_bool('youtube.folder.upcoming.live.show', True):
            live_events_item = DirectoryItem(
                localize('live.upcoming'),
                create_uri(PATHS.LIVE_VIDEOS_UPCOMING),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # live events
        if settings_bool('youtube.folder.live.show', True):
            live_events_item = DirectoryItem(
                localize('live'),
                create_uri(PATHS.LIVE_VIDEOS),
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

        if command in {'list', 'play'}:
            context.set_content(CONTENT.VIDEO_CONTENT)
            bookmarks_list = context.get_bookmarks_list()
            items = bookmarks_list.get_items()
            if not items:
                return True

            v3_response = {
                'kind': 'youtube#pluginListResponse',
                'items': []
            }

            def _update_bookmark(context, _id, old_item):
                def _update(new_item):
                    if isinstance(old_item, float):
                        bookmark_timestamp = old_item
                    elif isinstance(old_item, BaseItem):
                        bookmark_timestamp = old_item.get_bookmark_timestamp()
                    else:
                        return True

                    if new_item.available:
                        new_item.bookmark_id = _id
                        new_item.set_bookmark_timestamp(bookmark_timestamp)
                        new_item.callback = None
                        bookmarks_list.update_item(
                            _id,
                            repr(new_item),
                            bookmark_timestamp,
                        )
                    else:
                        update_duplicate_items(old_item, [new_item])
                        new_item.bookmark_id = _id
                        new_item.set_bookmark_timestamp(bookmark_timestamp)
                        new_item.available = False
                        new_item.playable = False
                        new_item.set_name(context.get_ui().color(
                            'AA808080', new_item.get_name()
                        ))
                    return True

                return _update

            for item_id, item in items.items():
                callback = _update_bookmark(context, item_id, item)
                if isinstance(item, float):
                    kind = 'youtube#channel'
                    yt_id = item_id
                    item_name = ''
                    partial = True
                elif isinstance(item, BaseItem):
                    partial = False

                    if isinstance(item, VideoItem):
                        kind = 'youtube#video'
                        yt_id = item.video_id
                    else:
                        yt_id = getattr(item, 'playlist_id', None)
                        if yt_id:
                            kind = 'youtube#playlist'
                        else:
                            kind = 'youtube#channel'
                            yt_id = getattr(item, 'channel_id', None)
                    item_name = item.get_name()
                else:
                    kind = None
                    yt_id = None
                    item_name = ''
                    partial = False

                if not yt_id:
                    if isinstance(item, BaseItem):
                        item_ids = item.parse_item_ids_from_uri()
                        to_delete = False
                        for kind in ('video', 'playlist', 'channel'):
                            yt_id = item_ids.get(kind + '_id')
                            if not yt_id:
                                continue
                            if yt_id == 'None':
                                to_delete = True
                                continue
                            kind = 'youtube#' + kind
                            partial = True
                            break
                        else:
                            if to_delete:
                                bookmarks_list.del_item(item_id)
                            continue
                    else:
                        continue

                item = {
                    'kind': kind,
                    'id': yt_id,
                    '_partial': partial,
                    '_context_menu': {
                        'context_menu': (
                            menu_items.bookmark_remove(
                                context, item_id, item_name
                            ),
                            menu_items.bookmarks_clear(
                                context
                            ),
                        ),
                        'position': 0,
                    },
                }
                if callback:
                    item['_callback'] = callback
                v3_response['items'].append(item)

            bookmarks = v3.response_to_items(provider, context, v3_response)
            if command == 'play':
                return yt_play.process_items_for_playlist(
                    context,
                    bookmarks,
                    action='play',
                    play_from='start',
                )
            return bookmarks

        ui = context.get_ui()
        localize = context.localize

        if command == 'clear':
            if not ui.on_yes_no_input(
                    context.localize('bookmarks.clear'),
                    localize('bookmarks.clear.check')
            ):
                return False, {provider.RESULT_FALLBACK: False}

            context.get_bookmarks_list().clear()
            ui.refresh_container()

            ui.show_notification(
                localize('completed'),
                time_ms=2500,
                audible=False,
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
                audible=False,
            )
            return True

        if command == 'remove':
            bookmark_name = params.get('item_name') or localize('bookmark')
            bookmark_name = to_unicode(bookmark_name)
            if not ui.on_yes_no_input(
                    localize('content.remove'),
                    localize('content.remove.check') % bookmark_name,
            ):
                return False, {provider.RESULT_FALLBACK: False}

            context.get_bookmarks_list().del_item(item_id)
            context.get_ui().refresh_container()

            ui.show_notification(
                localize('removed') % bookmark_name,
                time_ms=2500,
                audible=False,
            )
            return True

        return False

    @staticmethod
    def on_watch_later(provider, context, re_match):
        params = context.get_params()
        command = re_match.group('command')
        if not command:
            return False

        localize = context.localize
        ui = context.get_ui()

        if command in {'list', 'play'}:
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
                                    context, video_id, item.get_name()
                                ),
                                menu_items.watch_later_local_clear(
                                    context
                                ),
                            ),
                            'position': 0,
                        }
                    }
                    for video_id, item in items.items()
                ]
            }
            video_items = v3.response_to_items(provider, context, v3_response)
            if command == 'play':
                return yt_play.process_items_for_playlist(
                    context,
                    video_items,
                    action='play',
                    play_from='start',
                )
            return video_items

        if command == 'clear':
            if not ui.on_yes_no_input(
                    localize('watch_later.clear'),
                    localize('watch_later.clear.check')
            ):
                return False, {provider.RESULT_FALLBACK: False}

            context.get_watch_later_list().clear()
            ui.refresh_container()

            ui.show_notification(
                localize('completed'),
                time_ms=2500,
                audible=False,
            )
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
            video_name = params.get('item_name') or localize('untitled')
            video_name = to_unicode(video_name)
            if not ui.on_yes_no_input(
                    localize('content.remove'),
                    localize('content.remove.check') % video_name,
            ):
                return False, {provider.RESULT_FALLBACK: False}

            context.get_watch_later_list().del_item(video_id)
            ui.refresh_container()

            ui.show_notification(
                localize('removed') % video_name,
                time_ms=2500,
                audible=False,
            )
            return True

        return False

    def handle_exception(self, context, exception_to_handle):
        if not isinstance(exception_to_handle, (InvalidGrant, LoginException)):
            return False

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
                expiry=-1,
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
