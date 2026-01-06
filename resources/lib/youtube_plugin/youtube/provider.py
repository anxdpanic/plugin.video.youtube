# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2025 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

from atexit import register as atexit_register
from functools import partial
from re import compile as re_compile
from weakref import proxy

from .client import YouTubePlayerClient
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
from .helper.utils import update_duplicate_items
from .youtube_exceptions import InvalidGrant, LoginException
from ..kodion import AbstractProvider, logging
from ..kodion.constants import (
    ADDON_ID,
    CHANNEL_ID,
    CONTENT,
    HIDE_CHANNELS,
    HIDE_FOLDERS,
    HIDE_LIVE,
    HIDE_MEMBERS,
    HIDE_PLAYLISTS,
    HIDE_SEARCH,
    HIDE_SHORTS,
    HIDE_VIDEOS,
    INCOGNITO,
    PAGE,
    PATHS,
    PLAYLIST_ID,
    PLAY_COUNT,
    VIDEO_ID,
)
from ..kodion.items import (
    BaseItem,
    BookmarkItem,
    DirectoryItem,
    NewSearchItem,
    SearchItem,
    UriItem,
    VideoItem,
    menu_items,
)
from ..kodion.utils.convert_format import (
    channel_filter_split,
    strip_html_from_text,
    to_unicode,
)
from ..kodion.utils.datetime import now, since_epoch


class Provider(AbstractProvider):
    log = logging.getLogger(__name__)

    def __init__(self):
        super(Provider, self).__init__()
        self._resource_manager = None
        self._client = None

        self.on_video_x = self.register_path(r''.join((
            '^',
            PATHS.VIDEO,
            '/(?P<command>[^/]+)/?$',
        )), yt_video.process)

        self.on_playlist_x = self.register_path(r''.join((
            '^',
            PATHS.PLAYLIST,
            '/(?P<command>[^/]+)/(?P<category>[^/]+)/?$',
        )), yt_playlist.process)

        self.register_path(r''.join((
            '^',
            PATHS.PLAY,
            '/?$',
        )), yt_play.process)

        self.on_specials_x = self.register_path(r''.join((
            '^',
            PATHS.SPECIAL,
            '/(?P<category>[^/]+)(?:/(?P<sub_category>[^/]+))?/?$',
        )), yt_specials.process)

        self.register_path(r''.join((
            '^',
            PATHS.SUBSCRIPTIONS,
            '/(?P<command>[^/]+)/?$',
        )), yt_subscriptions.process)

        atexit_register(self.tear_down)

    @staticmethod
    def get_wizard_steps():
        return yt_setup_wizard.STEPS

    @staticmethod
    def pre_run_wizard_step(provider, context):
        yt_setup_wizard.process_pre_run(context)

    def reset_client(self, **kwargs):
        if self._client:
            kwargs.setdefault(
                'configs',
                {
                    'dev': {},
                    'user': {},
                    'tv': {},
                    'vr': {},
                }
            )
            kwargs.setdefault(
                'access_tokens',
                {
                    'dev': None,
                    'user': None,
                    'tv': None,
                    'vr': None,
                }
            )
            self._client.reinit(**kwargs)

    def get_client(self, context, refresh=False):
        access_manager = context.get_access_manager()
        api_store = context.get_api_store()
        settings = context.get_settings()

        user = access_manager.get_current_user()
        api_last_origin = access_manager.get_last_origin()

        client = self._client
        if not client or not client.initialised:
            synced = api_store.sync()
        else:
            synced = False
        configs = api_store.get_configs()

        dev_id = context.get_param('addon_id')
        if not dev_id or dev_id == ADDON_ID:
            origin = ADDON_ID
            dev_id = None
            if synced:
                switch = api_store.get_current_switch()
                key_details = api_store.get_key_set(switch)
                self.log.debug(('Using personal API details',
                                'Config:  {config!r}',
                                'User #:  {user!r}',
                                'Key set: {switch!r}'),
                               config=configs['user']['system'],
                               user=user,
                               switch=switch)
            else:
                switch = None
                key_details = None
        else:
            dev_config = api_store.get_developer_config(dev_id)
            origin = dev_config.get('origin')
            key_details = dev_config.get(origin)
            if key_details:
                configs[origin] = key_details
                switch = 'developer'
                self.log.debug(('Using developer provided API details',
                                'Config:  {config!r}',
                                'User #:  {user!r}',
                                'Key set: {switch!r}'),
                               config=key_details['system'],
                               user=user,
                               switch=switch)
            else:
                key_details = configs['dev']
                switch = api_store.get_current_switch()
                self.log.debug(('Using developer provided access tokens',
                                'Config:  {config!r}',
                                'User #:  {user!r}',
                                'Key set: {switch!r}'),
                               config=key_details['system'],
                               user=user,
                               switch=switch)

        if not client:
            client = YouTubePlayerClient(
                context=context,
                language=settings.get_language(),
                region=settings.get_region(),
                configs=configs,
            )
            self._client = client

        if key_details:
            keys_changed = access_manager.keys_changed(
                addon_id=dev_id,
                api_key=key_details['key'],
                client_id=key_details['id'],
                client_secret=key_details['secret'],
            )
            if keys_changed and switch == 'user':
                key_details = api_store.get_key_set('user_old')
                keys_changed = access_manager.keys_changed(
                    addon_id=dev_id,
                    api_key=key_details['key'],
                    client_id=key_details['id'],
                    client_secret=key_details['secret'],
                    update_hash=False,
                )
            if keys_changed:
                self.log.info('API key set changed - Signing out')
                yt_login.process(yt_login.SIGN_OUT, self, context)

        if api_last_origin != origin:
            self.log.info(('API key origin changed - Resetting client',
                           'Previous: {old!r}',
                           'Current:  {new!r}'),
                          old=api_last_origin,
                          new=origin)
            access_manager.set_last_origin(origin)
            client.initialised = False

        if not client.initialised:
            self.reset_client(
                context=context,
                language=settings.get_language(),
                region=settings.get_region(),
                items_per_page=settings.items_per_page(),
                configs=configs,
            )

        (
            access_tokens,
            num_access_tokens,
            _,
        ) = access_manager.get_access_tokens(dev_id)
        (
            refresh_tokens,
            num_refresh_tokens,
        ) = access_manager.get_refresh_tokens(dev_id)

        if num_access_tokens and client.logged_in:
            self.log.debug('User is %s logged in', client.logged_in)
            return client
        if num_access_tokens or num_refresh_tokens:
            self.log.debug(('# Access tokens:  %d',
                            '# Refresh tokens: %d'),
                           num_access_tokens,
                           num_refresh_tokens)
        else:
            self.log.debug('User is not logged in')
            access_manager.update_access_token(dev_id, access_token='')
            return client

        # create new access tokens
        with client:
            function_cache = context.get_function_cache()
            if not function_cache.run(
                    client.internet_available,
                    function_cache.ONE_MINUTE * 5,
                    _refresh=refresh or context.refresh_requested(),
            ):
                num_refresh_tokens = 0
            if num_refresh_tokens and num_access_tokens != num_refresh_tokens:
                access_tokens = [None, None, None, None]
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
                        access_token='',
                        refresh_token=refresh_token,
                    )
            client.set_access_token(access_tokens)
        return client

    def get_resource_manager(self, context, progress_dialog=None):
        resource_manager = self._resource_manager
        client = self.get_client(context)
        if not resource_manager or resource_manager.context_changed(
                context, client
        ):
            new_resource_manager = ResourceManager(proxy(self),
                                                   context,
                                                   client,
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

        url_to_item_converter = UrlToItemConverter(flatten=True)
        url_to_item_converter.process_url(resolved_url, context)
        items = url_to_item_converter.get_items(provider=provider,
                                                context=context,
                                                skip_title=skip_title)
        if items:
            if listing:
                return items, None
            return items[0], {provider.FORCE_RESOLVE: True}
        return [], None

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
        channel_id = re_match.group(CHANNEL_ID)
        new_params = {
            CHANNEL_ID: channel_id,
        }
        context.parse_params(new_params)
        params = context.get_params()

        resource_manager = provider.get_resource_manager(context)
        playlists = resource_manager.get_related_playlists(channel_id)
        uploads = playlists.get('uploads') if playlists else None
        if (params.get(PAGE, 1) == 1 and not params.get(HIDE_FOLDERS)
                and uploads and uploads.startswith('UU')):
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
                    '_params': {
                        'special_sort': 'top',
                    },
                },
                {
                    'kind': 'youtube#playlistShortsFolder',
                    'id': uploads.replace('UU', 'UUSH', 1),
                    'snippet': {
                        'channelId': channel_id,
                        'title': context.localize('shorts'),
                        'thumbnails': {'default': {
                            'url': '{media}/shorts.png',
                        }},
                    },
                    '_partial': True,
                    '_params': {
                        'special_sort': 'top',
                    },
                } if not params.get(HIDE_SHORTS) else None,
                {
                    'kind': 'youtube#playlistLiveFolder',
                    'id': uploads.replace('UU', 'UULV', 1),
                    'snippet': {
                        'channelId': channel_id,
                        'title': context.localize('live'),
                        'thumbnails': {'default': {
                            'url': '{media}/live.png',
                        }},
                    },
                    '_partial': True,
                    '_params': {
                        'special_sort': 'top',
                    },
                } if not params.get(HIDE_LIVE) else None,
            ]
        else:
            result = False

        json_data = resource_manager.get_my_playlists(
            channel_id, params.get('page_token', '')
        )
        if not json_data:
            return False, None

        if result and 'items' in json_data:
            result.extend(json_data['items'])
            json_data['items'] = result
        result = v3.response_to_items(provider, context, json_data)
        options = {
            provider.CONTENT_TYPE: {
                'content_type': CONTENT.LIST_CONTENT,
                'sub_type': None,
                'category_label': None,
            },
        }
        return result, options

    @AbstractProvider.register_path(r''.join((
            '^',
            PATHS.CHANNEL,
            '/(?P<', CHANNEL_ID, '>[^/]+)',
            '(?:/live|',
            PATHS.PLAYLIST,
            '/(?P<', PLAYLIST_ID, '>UULV[^/]+))/?$',
    )))
    @staticmethod
    def on_channel_live(provider,
                        context,
                        re_match=None,
                        channel_id=None,
                        playlist_id=None):
        """
        List live streams for a given channel.

        plugin://plugin.video.youtube/channel/<CHANNEL_ID>/live

        or

        plugin://plugin.video.youtube/channel/<CHANNEL_ID>/playlist/<PLAYLIST_ID>

        * CHANNEL_ID: YouTube channel ID
        * PLAYLIST_ID: YouTube live stream playlist ID beginning with UULV
        """
        resource_manager = provider.get_resource_manager(context)

        if re_match:
            channel_id = re_match.group(CHANNEL_ID)
            playlist_id = re_match.group(PLAYLIST_ID)
            if not playlist_id:
                playlists = resource_manager.get_related_playlists(channel_id)
                playlist_id = playlists.get('uploads') if playlists else None
                if playlist_id and playlist_id.startswith('UU'):
                    playlist_id = playlist_id.replace('UU', 'UULV', 1)
        if not channel_id or not playlist_id:
            return False, None

        new_params = {
            CHANNEL_ID: channel_id,
            PLAYLIST_ID: playlist_id,
        }
        context.parse_params(new_params)

        batch_id = (playlist_id, context.get_param('page_token') or 0)
        json_data = resource_manager.get_playlist_items(batch_id=batch_id)
        if not json_data:
            return False, None

        live_streams = provider.get_client(context).get_browse_items(
            channel_id=channel_id,
            route='streams',
            json_path={
                'items': (
                    'contents',
                    'twoColumnBrowseResultsRenderer',
                    'tabs',
                    slice(None),
                    'tabRenderer',
                    lambda x: (
                        x['content']
                        if x['title'] == 'Live' else
                        None
                    ),
                    'richGridRenderer',
                    'contents',
                    slice(None),
                    'richItemRenderer',
                    'content',
                    'videoRenderer',
                    lambda x: (
                        x
                        if (x[
                            'thumbnailOverlays'
                        ][
                            0
                        ][
                            'thumbnailOverlayTimeStatusRenderer'
                        ][
                            'style'
                        ]) == 'LIVE' else
                        None
                    ),
                ),
                'continuation': None,
            },
        )
        if live_streams and 'items' in live_streams and 'items' in json_data:
            live_streams['items'].extend(json_data['items'])
            json_data['items'] = live_streams['items']

        result = v3.response_to_items(
            provider, context, json_data,
            allow_duplicates=False,
            item_filter={
                'live_folder': True,
            },
        )
        options = {
            provider.CONTENT_TYPE: {
                'content_type': CONTENT.VIDEO_CONTENT,
                'sub_type': None,
                'category_label': None,
            },
        }
        return result, options

    @AbstractProvider.register_path(r''.join((
            '^',
            PATHS.CHANNEL,
            '/(?P<', CHANNEL_ID, '>[^/]+)',
            '(?:/shorts|',
            PATHS.PLAYLIST,
            '/(?P<', PLAYLIST_ID, '>UUSH[^/]+))/?$',
    )))
    @staticmethod
    def on_channel_shorts(provider,
                          context,
                          re_match=None,
                          channel_id=None,
                          playlist_id=None):
        """
        List shorts for channel.

        plugin://plugin.video.youtube/channel/<CHANNEL_ID>/shorts

        or

        plugin://plugin.video.youtube/channel/<CHANNEL_ID>/playlist/<PLAYLIST_ID>

        * CHANNEL_ID: YouTube channel ID
        * PLAYLIST_ID: YouTube live stream playlist ID beginning with UUSH
        """
        resource_manager = provider.get_resource_manager(context)

        if re_match:
            channel_id = re_match.group(CHANNEL_ID)
            playlist_id = re_match.group(PLAYLIST_ID)
            if not playlist_id:
                playlists = resource_manager.get_related_playlists(channel_id)
                playlist_id = playlists.get('uploads') if playlists else None
                if playlist_id and playlist_id.startswith('UU'):
                    playlist_id = playlist_id.replace('UU', 'UUSH', 1)
        if not channel_id or not playlist_id:
            return False, None

        new_params = {
            CHANNEL_ID: channel_id,
            PLAYLIST_ID: playlist_id,
        }
        context.parse_params(new_params)

        batch_id = (playlist_id, context.get_param('page_token') or 0)
        json_data = resource_manager.get_playlist_items(batch_id=batch_id)
        if not json_data:
            return False, None

        result = v3.response_to_items(
            provider, context, json_data,
            item_filter={
                'shorts': True,
            },
        )
        options = {
            provider.CONTENT_TYPE: {
                'content_type': CONTENT.VIDEO_CONTENT,
                'sub_type': None,
                'category_label': None,
            },
        }
        return result, options

    @AbstractProvider.register_path(r''.join((
            '^(?:',
            PATHS.CHANNEL,
            '/(?P<', CHANNEL_ID, '>[^/]+))?',
            PATHS.PLAYLIST,
            '/(?P<', PLAYLIST_ID, '>[^/]+)/?$',
    )))
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
        playlist_id = re_match.group(PLAYLIST_ID)
        new_params = {
            PLAYLIST_ID: playlist_id,
        }
        channel_id = re_match.group(CHANNEL_ID)
        if channel_id:
            new_params[CHANNEL_ID] = channel_id
        context.parse_params(new_params)

        resource_manager = provider.get_resource_manager(context)

        batch_id = (playlist_id, context.get_param('page_token') or 0)
        json_data = resource_manager.get_playlist_items(batch_id=batch_id)
        if not json_data:
            return False, None

        result = v3.response_to_items(provider, context, json_data)
        options = {
            provider.CONTENT_TYPE: {
                'content_type': CONTENT.VIDEO_CONTENT,
                'sub_type': CONTENT.PLAYLIST,
                'category_label': None,
            },
        }
        return result, options

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
        li_channel_id = context.get_ui().get_listitem_property(CHANNEL_ID)

        client = provider.get_client(context)
        create_uri = context.create_uri
        params = context.get_params()

        command = re_match.group('command')
        identifier = re_match.group('identifier')

        if (command == 'channel'
                and identifier
                and identifier.lower() == 'property'
                and li_channel_id
                and li_channel_id.lower().startswith(('mine', 'uc'))):
            context.execute('ActivateWindow(Videos, {channel}, return)'.format(
                channel=create_uri(
                    (PATHS.CHANNEL, li_channel_id,),
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

        if not channel_id:
            function_cache = context.get_function_cache()
            channel_id = function_cache.run(
                client.get_channel_by_identifier,
                function_cache.ONE_MONTH,
                _refresh=context.refresh_requested(),
                **{
                    command: True,
                    'identifier': identifier,
                }
            )
            if not channel_id:
                return False

        context.parse_params({
            CHANNEL_ID: channel_id,
        })

        resource_manager = provider.get_resource_manager(context)
        result = []
        options = {
            provider.CONTENT_TYPE: {
                'content_type': CONTENT.VIDEO_CONTENT,
                'sub_type': None,
                'category_label': None,
            },
        }

        playlists = resource_manager.get_related_playlists(channel_id)
        uploads = playlists.get('uploads') if playlists else None
        if uploads and not uploads.startswith('UU'):
            uploads = None

        if params.get(PAGE, 1) == 1 and not params.get(HIDE_FOLDERS):
            v3_response = {
                'kind': 'plugin#pluginListResponse',
                'items': [
                    {
                        'kind': 'plugin#playlistsFolder',
                        '_params': {
                            'title': context.localize('playlists'),
                            'image': '{media}/playlist.png',
                            CHANNEL_ID: channel_id,
                            'special_sort': 'top',
                        },
                    } if not params.get(HIDE_PLAYLISTS) else None,
                    {
                        'kind': 'plugin#searchFolder',
                        '_params': {
                            'title': context.localize('search'),
                            'image': '{media}/search.png',
                            CHANNEL_ID: channel_id,
                            'special_sort': 'top',
                        },
                    } if not params.get(HIDE_SEARCH) else None,
                    {
                        'kind': 'youtube#playlistShortsFolder',
                        'id': uploads.replace('UU', 'UUSH', 1),
                        'snippet': {
                            'channelId': channel_id,
                            'title': context.localize('shorts'),
                            'thumbnails': {'default': {
                                'url': '{media}/shorts.png',
                            }},
                        },
                        '_partial': True,
                        '_params': {
                            'special_sort': 'top',
                        },
                    } if uploads and not params.get(HIDE_SHORTS) else None,
                    {
                        'kind': 'youtube#playlistLiveFolder',
                        'id': uploads.replace('UU', 'UULV', 1),
                        'snippet': {
                            'channelId': channel_id,
                            'title': context.localize('live'),
                            'thumbnails': {'default': {
                                'url': '{media}/live.png',
                            }},
                        },
                        '_partial': True,
                        '_params': {
                            'special_sort': 'top',
                        },
                    } if uploads and not params.get(HIDE_LIVE) else None,
                    {
                        'kind': 'youtube#playlistMembersFolder',
                        'id': uploads.replace('UU', 'UUMO', 1),
                        'snippet': {
                            'channelId': channel_id,
                            'title': context.localize('members_only'),
                            'thumbnails': {'default': {
                                'url': '{media}/sign_in.png',
                            }},
                        },
                        '_partial': True,
                        '_params': {
                            'special_sort': 'top',
                        },
                    } if uploads and not params.get(HIDE_MEMBERS) else None,
                ],
            }
            result.extend(v3.response_to_items(provider, context, v3_response))

        if uploads:
            # The "UULF" videos playlist can only be used if videos in a channel
            # are made public. Use "UU" all uploads playlist and filter instead
            # if viewing personal channel.
            if command != 'mine':
                filtered_uploads = uploads.replace('UU', 'UULF', 1)
            else:
                filtered_uploads = None
            while 1:
                page_token = params.get('page_token')
                if filtered_uploads:
                    batch_id = (filtered_uploads, page_token or 0)
                else:
                    batch_id = (uploads, page_token or 0)

                json_data = resource_manager.get_playlist_items(
                    batch_id=batch_id,
                    defer_cache=False,
                )
                if json_data:
                    break
                if filtered_uploads:
                    filtered_uploads = None
                    continue
                return result, options

            context.parse_params({
                PLAYLIST_ID: filtered_uploads or uploads,
            })

            if not filtered_uploads:
                filler = partial(
                    resource_manager.get_playlist_items,
                    ids=(uploads,),
                    defer_cache=False,
                )
                json_data['_post_filler'] = filler

            result.extend(v3.response_to_items(
                provider, context, json_data,
                item_filter={
                    'live_folder': True,
                    'shorts': True,
                    'vod': True,
                } if filtered_uploads else {
                    'shorts': True,
                    'live': False,
                    'upcoming_live': False,
                },
            ))
        return result, options

    @AbstractProvider.register_path('^/location/mine/?$')
    @staticmethod
    def on_my_location(provider, context, **_kwargs):
        create_uri = context.create_uri
        localize = context.localize
        settings = context.get_settings()
        result = []
        options = {
            provider.CONTENT_TYPE: {
                'content_type': CONTENT.LIST_CONTENT,
                'sub_type': None,
                'category_label': None,
            },
        }

        # search
        search_item = SearchItem(
            context,
            image='{media}/search.png',
            location=True
        )
        result.append(search_item)

        # completed live events
        if settings.get_bool(settings.SHOW_COMPlETED_LIVE, True):
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
        if settings.get_bool(settings.SHOW_UPCOMING_LIVE, True):
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

        return result, options

    @AbstractProvider.register_path('^/users/(?P<action>[^/]+)/?$')
    @staticmethod
    def on_users(re_match, **_kwargs):
        action = re_match.group('action')
        return UriItem('script://{addon},users/{action}'.format(
            addon=ADDON_ID, action=action
        ))

    @AbstractProvider.register_path('^/sign/(?P<mode>[^/]+)/?$')
    @staticmethod
    def on_sign_x(provider, context, re_match):
        return yt_login.process(
            re_match.group('mode'),
            provider,
            context,
            client=provider.get_client(context, refresh=True),
        )

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
            return False, {
                self.CACHE_TO_DISC: False,
                self.FALLBACK: query,
            }

        result = self._search_channel_or_playlist(context, query)
        if result:  # found a channel or playlist matching search query
            return result, {
                self.CACHE_TO_DISC: False,
                self.FALLBACK: False,
                self.CONTENT_TYPE: {
                    'content_type': CONTENT.LIST_CONTENT,
                    'sub_type': None,
                    'category_label': query,
                },
            }
        result = []

        channel_id = params.get(CHANNEL_ID) or params.get('channelId')
        event_type = params.get('event_type') or params.get('eventType')
        location = params.get('location')
        page_token = params.get('page_token') or params.get('pageToken') or ''
        search_type = params.get('search_type', 'video') or params.get('type')

        options = {
            self.CACHE_TO_DISC: False,
            self.CONTENT_TYPE: {
                'content_type': (
                    CONTENT.VIDEO_CONTENT
                    if search_type == 'video' else
                    CONTENT.LIST_CONTENT
                ),
                'sub_type': None,
                'category_label': query,
            },
        }

        if params.get(PAGE, 1) == 1 and not params.get(HIDE_FOLDERS):
            if ((event_type or search_type != 'video')
                    and not params.get(HIDE_VIDEOS)):
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

            if (not channel_id
                    and not location
                    and search_type != 'channel'
                    and not params.get(HIDE_CHANNELS)):
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

            if (not location
                    and search_type != 'playlist'
                    and not params.get(HIDE_PLAYLISTS)):
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

            if (not channel_id
                    and event_type != 'live'
                    and not params.get(HIDE_LIVE)):
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

            if (event_type
                    and event_type != 'upcoming'
                    and not params.get(HIDE_LIVE)):
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

            if (event_type
                    and event_type != 'completed'
                    and not params.get(HIDE_LIVE)):
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
            _refresh=context.refresh_requested(),
            params=search_params,
        )
        if not json_data:
            return False, None

        # Store current search query
        if not params.get(INCOGNITO) and not params.get(CHANNEL_ID):
            context.get_search_history().add_item(search_params)

        result.extend(v3.response_to_items(
            self, context, json_data,
            item_filter={
                'live_folder': True,
            } if event_type else {
                'live': False,
            },
        ))
        return result, options

    @AbstractProvider.register_path('^/config/(?P<action>[^/]+)/?$')
    @staticmethod
    def on_configure_addon(provider, context, re_match):
        action = re_match.group('action')
        if action == 'setup_wizard':
            provider.run_wizard(context)
            return False, {provider.FALLBACK: False}
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

        channel_name = context.get_param('item_name')
        command = re_match.group('command')
        if not channel_name or not command:
            return False, None

        if not settings.subscriptions_filter_enabled():
            return False, None

        filter_string, filters_set, custom_filters = channel_filter_split(
            settings.subscriptions_filter()
        )

        if command == 'add':
            num_filters = len(filters_set)
            filters_set.add(channel_name)
            if len(filters_set) == num_filters:
                return False, None
        elif command == 'remove':
            try:
                filters_set.remove(channel_name)
            except KeyError:
                return False, None
        else:
            return False, None

        filter_list = list(filters_set)
        if custom_filters:
            filter_list.extend([
                ''.join([
                    '{' + part + '}'
                    for part in condition
                ])
                for custom_filter in custom_filters
                for condition in custom_filter
            ])
        settings.subscriptions_filter(filter_list)

        ui.show_notification(context.localize(('added.to.x'
                                               if command == 'add' else
                                               'removed.from.x',
                                               'my_subscriptions.filtered')))
        return True, None

    @AbstractProvider.register_path(r''.join((
            '^',
            PATHS.MAINTENANCE,
            '/(?P<action>[^/]+)',
            '/(?P<target>[^/]+)/?$',
    )))
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
            access_manager = context.get_access_manager()
            success, _ = yt_login.process(yt_login.SIGN_OUT, provider, context)
            if success:
                success = access_manager.set_defaults(reset=True)
            ui.show_notification(localize('succeeded' if success else 'failed'))
        else:
            success = False
        return success, None

    @AbstractProvider.register_path('^/api/update/?$')
    @staticmethod
    def on_api_key_update(context, **_kwargs):
        context.get_api_store().update()

    @staticmethod
    def on_playback_history(provider, context, re_match):
        params = context.get_params()
        command = re_match.group('command') or 'list'

        localize = context.localize
        playback_history = context.get_playback_history()
        ui = context.get_ui()

        if command in {'list', 'play'}:
            items = playback_history.get_items()
            if not items:
                return True, None

            context_menu = (
                menu_items.history_local_remove(context),
                menu_items.history_local_clear(context),
            )
            v3_response = {
                'kind': 'youtube#videoListResponse',
                'items': [
                    {
                        'kind': 'youtube#video',
                        'id': video_id,
                        '_partial': True,
                        '_context_menu': {
                            'context_menu': context_menu,
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
            options = {
                provider.CONTENT_TYPE: {
                    'content_type': CONTENT.VIDEO_CONTENT,
                    'sub_type': CONTENT.HISTORY,
                    'category_label': None,
                },
            }
            return video_items, options

        if command == 'clear':
            if not ui.on_yes_no_input(
                    localize('history.clear'),
                    localize('history.clear.check')
            ):
                return False, {provider.FALLBACK: False}

            playback_history.clear()
            ui.show_notification(
                localize('completed'),
                time_ms=2500,
                audible=False,
            )
            return True, {provider.FORCE_REFRESH: True}

        video_id = params.get(VIDEO_ID)
        if not video_id:
            return False, None

        if command == 'remove':
            video_name = params.get('item_name') or video_id
            video_name = to_unicode(video_name)
            if not ui.on_yes_no_input(
                    localize('content.remove'),
                    localize('content.remove.check.x', video_name),
            ):
                return False, {provider.FALLBACK: False}

            playback_history.del_item(video_id)
            ui.show_notification(
                localize('removed.name.x', video_name),
                time_ms=2500,
                audible=False,
            )
            return True, {provider.FORCE_REFRESH: True}

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

        if command == 'mark_as':
            if ui.get_listitem_info(PLAY_COUNT):
                play_data['play_count'] = 0
                play_data['played_time'] = 0
                play_data['played_percent'] = 0
            else:
                play_data['play_count'] = 1

        elif command == 'mark_unwatched':
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
        return True, {provider.FORCE_REFRESH: True}

    @staticmethod
    def on_root(provider, context, re_match):
        create_uri = context.create_uri
        localize = context.localize
        settings = context.get_settings()
        settings_bool = settings.get_bool
        bold = context.get_ui().bold

        logged_in = provider.get_client(context).logged_in
        # _.get_my_playlists()

        result = []
        options = {
            provider.CONTENT_TYPE: {
                'category_label': localize('youtube'),
            },
        }

        # sign in
        if ((not logged_in or logged_in == 'partially')
                and settings_bool(settings.SHOW_SIGN_IN, True)):
            item_label = localize('sign.in')
            sign_in_item = DirectoryItem(
                bold(item_label),
                create_uri(('sign', 'in')),
                image='{media}/sign_in.png',
                action=True,
                category_label=item_label,
            )
            result.append(sign_in_item)

        if settings_bool(settings.SHOW_MY_SUBSCRIPTIONS, True):
            # my subscription
            item_label = localize('my_subscriptions')
            my_subscriptions_item = DirectoryItem(
                bold(item_label),
                create_uri(PATHS.MY_SUBSCRIPTIONS),
                image='{media}/new_uploads.png',
                category_label=item_label,
            )
            result.append(my_subscriptions_item)

        if settings_bool(settings.SHOW_MY_SUBSCRIPTIONS_FILTERED):
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
        if logged_in and settings_bool(settings.SHOW_RECOMMENDATIONS, True):
            recommendations_item = DirectoryItem(
                localize('recommendations'),
                create_uri(PATHS.RECOMMENDATIONS),
                image='{media}/home.png',
            )
            result.append(recommendations_item)

        # Related
        if settings_bool(settings.SHOW_RELATED, True):
            if history_id or local_history:
                related_item = DirectoryItem(
                    localize('video.related'),
                    create_uri(PATHS.RELATED_VIDEOS),
                    image='{media}/related_videos.png',
                )
                result.append(related_item)

        # Trending
        if settings_bool(settings.SHOW_TRENDING, True):
            trending_item = DirectoryItem(
                localize('trending'),
                create_uri(PATHS.TRENDING),
                image='{media}/trending.png',
            )
            result.append(trending_item)

        # search
        if settings_bool(settings.SHOW_SEARCH, True):
            search_item = SearchItem(
                context,
            )
            result.append(search_item)

        if settings_bool(settings.SHOW_QUICK_SEARCH):
            quick_search_item = NewSearchItem(
                context,
                name=localize('search.quick'),
                image='{media}/quick_search.png',
            )
            result.append(quick_search_item)

        if settings_bool(settings.SHOW_INCOGNITO_SEARCH):
            quick_search_incognito_item = NewSearchItem(
                context,
                name=localize('search.quick.incognito'),
                image='{media}/incognito_search.png',
                incognito=True,
            )
            result.append(quick_search_incognito_item)

        # my location
        if (settings_bool(settings.SHOW_MY_LOCATION, True)
                and settings.get_location()):
            my_location_item = DirectoryItem(
                localize('my_location'),
                create_uri(('location', 'mine')),
                image='{media}/location.png',
            )
            result.append(my_location_item)

        # my channel
        if logged_in and settings_bool(settings.SHOW_MY_CHANNEL, True):
            my_channel_item = DirectoryItem(
                localize('my_channel'),
                create_uri(PATHS.MY_CHANNEL),
                image='{media}/user.png',
            )
            result.append(my_channel_item)

        # watch later
        if settings_bool(settings.SHOW_WATCH_LATER, True):
            if watch_later_id:
                path = (
                    (PATHS.VIRTUAL_PLAYLIST, watch_later_id)
                    if watch_later_id.lower() == 'wl' else
                    (PATHS.MY_PLAYLIST, watch_later_id)
                )
                watch_later_item = DirectoryItem(
                    localize('watch_later'),
                    create_uri(path),
                    image='{media}/watch_later.png',
                )
                context_menu = [
                    menu_items.playlist_play(
                        context, watch_later_id
                    ),
                    menu_items.playlist_play_recently_added(
                        context, watch_later_id
                    ),
                    menu_items.playlist_view(
                        context, watch_later_id
                    ),
                    menu_items.playlist_shuffle(
                        context, watch_later_id
                    ),
                    menu_items.refresh_listing(
                        context, path, {}
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
                    menu_items.folder_play(
                        context,
                        path=PATHS.WATCH_LATER,
                    ),
                    menu_items.folder_play(
                        context,
                        path=PATHS.WATCH_LATER,
                        order='shuffle',
                    ),
                ]
                watch_later_item.add_context_menu(context_menu)
                result.append(watch_later_item)

        # liked videos
        if logged_in and settings_bool(settings.SHOW_LIKED, True):
            resource_manager = provider.get_resource_manager(context)
            playlists = resource_manager.get_related_playlists('mine')
            if playlists and 'likes' in playlists:
                liked_list_id = playlists['likes'] or 'LL'
                path = (PATHS.VIRTUAL_PLAYLIST, liked_list_id)
                liked_videos_item = DirectoryItem(
                    localize('video.liked'),
                    create_uri(path),
                    image='{media}/likes.png',
                )
                context_menu = [
                    menu_items.playlist_play(
                        context, liked_list_id
                    ),
                    menu_items.playlist_play_recently_added(
                        context, liked_list_id
                    ),
                    menu_items.playlist_view(
                        context, liked_list_id
                    ),
                    menu_items.playlist_shuffle(
                        context, liked_list_id
                    ),
                    menu_items.refresh_listing(
                        context, path, {}
                    ),
                ]
                liked_videos_item.add_context_menu(context_menu)
                result.append(liked_videos_item)

        # disliked videos
        if logged_in and settings_bool(settings.SHOW_DISLIKED, True):
            disliked_videos_item = DirectoryItem(
                localize('video.disliked'),
                create_uri(PATHS.DISLIKED_VIDEOS),
                image='{media}/dislikes.png',
            )
            result.append(disliked_videos_item)

        # history
        if settings_bool(settings.SHOW_HISTORY, True):
            if history_id:
                path = (
                    (PATHS.VIRTUAL_PLAYLIST, history_id)
                    if history_id.lower() == 'hl' else
                    (PATHS.MY_PLAYLIST, history_id)
                )
                watch_history_item = DirectoryItem(
                    localize('history'),
                    create_uri(path),
                    image='{media}/history.png',
                )
                context_menu = [
                    menu_items.playlist_play(
                        context, history_id
                    ),
                    menu_items.playlist_play_recently_added(
                        context, history_id
                    ),
                    menu_items.playlist_view(
                        context, history_id
                    ),
                    menu_items.playlist_shuffle(
                        context, history_id
                    ),
                    menu_items.refresh_listing(
                        context, path, {}
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
                    menu_items.history_local_clear(
                        context
                    ),
                    menu_items.separator(),
                    menu_items.folder_play(
                        context,
                        path=PATHS.HISTORY,
                    ),
                    menu_items.folder_play(
                        context,
                        path=PATHS.HISTORY,
                        order='shuffle',
                    ),
                ]
                watch_history_item.add_context_menu(context_menu)
                result.append(watch_history_item)

        # (my) playlists
        if logged_in and settings_bool(settings.SHOW_PLAYLISTS, True):
            playlists_item = DirectoryItem(
                localize('playlists'),
                create_uri(PATHS.MY_PLAYLISTS),
                image='{media}/playlist.png',
            )
            result.append(playlists_item)

        # saved playlists
        if logged_in and settings_bool(settings.SHOW_SAVED_PLAYLISTS, True):
            playlists_item = DirectoryItem(
                localize('saved.playlists'),
                create_uri(PATHS.SAVED_PLAYLISTS),
                image='{media}/playlist.png',
            )
            result.append(playlists_item)

        # subscriptions
        if logged_in and settings_bool(settings.SHOW_SUBSCRIPTIONS, True):
            subscriptions_item = DirectoryItem(
                localize('subscriptions'),
                create_uri((PATHS.SUBSCRIPTIONS, 'list')),
                image='{media}/channels.png',
            )
            result.append(subscriptions_item)

        # bookmarks
        if settings_bool(settings.SHOW_BOOKMARKS, True):
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
                menu_items.folder_play(
                    context,
                    path=PATHS.BOOKMARKS,
                ),
                menu_items.folder_play(
                    context,
                    path=PATHS.BOOKMARKS,
                    order='shuffle',
                ),
            ]
            bookmarks_item.add_context_menu(context_menu)
            result.append(bookmarks_item)

        # browse channels
        if logged_in and settings_bool(settings.SHOW_BROWSE_CHANNELS, True):
            browse_channels_item = DirectoryItem(
                localize('browse_channels'),
                create_uri((PATHS.SPECIAL, 'browse_channels')),
                image='{media}/browse_channels.png',
            )
            result.append(browse_channels_item)

        # completed live events
        if settings_bool(settings.SHOW_COMPlETED_LIVE, True):
            live_events_item = DirectoryItem(
                localize('live.completed'),
                create_uri(PATHS.LIVE_VIDEOS_COMPLETED),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # upcoming live events
        if settings_bool(settings.SHOW_UPCOMING_LIVE, True):
            live_events_item = DirectoryItem(
                localize('live.upcoming'),
                create_uri(PATHS.LIVE_VIDEOS_UPCOMING),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # live events
        if settings_bool(settings.SHOW_LIVE, True):
            live_events_item = DirectoryItem(
                localize('live'),
                create_uri(PATHS.LIVE_VIDEOS),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # switch user
        if settings_bool(settings.SHOW_SWITCH_USER, True):
            switch_user_item = DirectoryItem(
                localize('user.switch'),
                create_uri(('users', 'switch')),
                image='{media}/user.png',
                action=True,
            )
            result.append(switch_user_item)

        # sign out
        if logged_in and settings_bool(settings.SHOW_SIGN_OUT, True):
            sign_out_item = DirectoryItem(
                localize('sign.out'),
                create_uri(('sign', 'out')),
                image='{media}/sign_out.png',
                action=True,
            )
            result.append(sign_out_item)

        if settings_bool(settings.SHOW_SETUP_WIZARD, True):
            settings_menu_item = DirectoryItem(
                localize('setup_wizard'),
                create_uri(PATHS.SETUP_WIZARD),
                image='{media}/settings.png',
                action=True,
            )
            context_menu = [
                menu_items.open_settings(context)
            ]
            settings_menu_item.add_context_menu(context_menu)
            result.append(settings_menu_item)

        if settings_bool(settings.SHOW_SETTINGS):
            settings_menu_item = DirectoryItem(
                localize('settings'),
                create_uri(PATHS.SETTINGS),
                image='{media}/settings.png',
                action=True,
            )
            context_menu = [
                menu_items.open_setup_wizard(context)
            ]
            settings_menu_item.add_context_menu(context_menu)
            result.append(settings_menu_item)

        return result, options

    @staticmethod
    def on_bookmarks(provider, context, re_match):
        params = context.get_params()
        command = re_match.group('command') or 'list'

        ui = context.get_ui()
        localize = context.localize
        parse_item_ids = context.parse_item_ids

        if command in {'list', 'play'}:
            bookmarks_list = context.get_bookmarks_list()
            items = bookmarks_list.get_items()

            context_menu_custom = (
                menu_items.bookmark_edit(context),
                menu_items.bookmark_remove(context),
                menu_items.bookmarks_clear(context),
            )
            context_menu = (
                menu_items.bookmark_edit(context),
                menu_items.bookmark_remove(context),
                menu_items.bookmarks_clear(context),
            )

            v3_response = {
                'kind': 'plugin#pluginListResponse',
                'items': [
                    {
                        'kind': 'plugin#bookmarkItem',
                        '_params': {
                            'name': localize('bookmarks.add'),
                            'uri': context.create_uri(
                                (PATHS.BOOKMARKS, 'add_custom',),
                            ),
                            'action': True,
                            'playable': False,
                            'special_sort': 'top',
                        },
                    },
                ],
            }

            def _update_bookmark(context, _id, old_item):
                def _update(new_item):
                    if isinstance(old_item, float):
                        bookmark_timestamp = old_item
                    elif isinstance(old_item, BaseItem):
                        bookmark_timestamp = old_item.get_bookmark_timestamp()
                    else:
                        return True

                    new_item.callback = None
                    if new_item.available:
                        new_item.bookmark_id = _id
                        new_item.set_bookmark_timestamp(bookmark_timestamp)
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
                item_name = ''
                item_uri = None
                kind = None
                yt_id = None
                partial_result = False
                can_edit = False
                item_params = {}

                while not kind:
                    if isinstance(item, float):
                        kind = 'youtube#channel'
                        yt_id = item_id
                        partial_result = True
                        continue

                    if not isinstance(item, BaseItem):
                        break
                    item_name = item.get_name()
                    item_uri = item.get_uri()

                    if isinstance(item, BookmarkItem):
                        kind = 'plugin#bookmarkItem'
                        yt_id = False
                        can_edit = True
                        item_params = {
                            'name': item_name,
                            'uri': item_uri,
                            'bookmark_id': item_id,
                            'plot': item_uri,
                            'action': item.is_action(),
                            'special_sort': False,
                            'date_time': item.get_date(),
                            'category_label': '__inherit__',
                        }
                    else:
                        if isinstance(item, VideoItem):
                            kind = 'youtube#video'
                            yt_id = item.video_id
                            continue

                        yt_id = getattr(item, PLAYLIST_ID, None)
                        if yt_id:
                            kind = 'youtube#playlist'
                            continue

                        yt_id = getattr(item, CHANNEL_ID, None)
                        if yt_id:
                            kind = 'youtube#channel'
                            continue

                    item_ids = parse_item_ids(item_uri, from_listitem=False)
                    for _kind in ('video', 'playlist', 'channel'):
                        id_type = _kind + '_id'
                        _yt_id = item_ids.get(id_type)
                        if not _yt_id or _yt_id == 'None':
                            continue
                        item_params.setdefault(id_type, _yt_id)
                        if kind:
                            continue
                        yt_id = _yt_id
                        kind = 'youtube#' + _kind

                    if kind:
                        partial_result = True
                        continue
                    break
                else:
                    v3_response['items'].append({
                        'kind': kind,
                        'id': yt_id,
                        '_partial': partial_result,
                        '_context_menu': {
                            'context_menu': (
                                context_menu_custom
                                if can_edit else
                                context_menu
                            ),
                            'position': 0,
                        },
                        '_callback': _update_bookmark(context, item_id, item),
                        '_params': item_params,
                    })
                    continue

                provider.log.warning(('Deleting unknown bookmark type',
                                      'ID:   {item_id}',
                                      'Item: {item!r}'),
                                     item_id=item_id,
                                     item=item)
                bookmarks_list.del_item(item_id)

            bookmarks = v3.response_to_items(provider, context, v3_response)
            if command == 'play':
                return yt_play.process_items_for_playlist(
                    context,
                    bookmarks,
                    action='play',
                    play_from='start',
                )
            options = {
                provider.CONTENT_TYPE: {
                    'content_type': CONTENT.VIDEO_CONTENT,
                    'sub_type': None,
                    'category_label': None,
                },
            }
            return bookmarks, options

        if command == 'clear':
            if not ui.on_yes_no_input(localize('bookmarks.clear'),
                                      localize('bookmarks.clear.check')):
                return False, {provider.FALLBACK: False}

            context.get_bookmarks_list().clear()
            ui.show_notification(
                localize('completed'),
                time_ms=2500,
                audible=False,
            )
            return True, {provider.FORCE_REFRESH: True}

        item_id = params.get('item_id')

        if command in {'add_custom', 'edit'}:
            results = ui.on_keyboard_input(localize('bookmarks.edit.uri'),
                                           params.get('uri', ''))
            if not results[0]:
                return False, None
            item_uri = results[1]
            if not item_uri:
                return False, None

            if item_uri.startswith(('https://', 'http://')):
                item_uri = UrlToItemConverter().process_url(
                    UrlResolver(context).resolve(item_uri),
                    context,
                    as_uri=True,
                )
            if not item_uri or not context.is_plugin_path(item_uri):
                ui.show_notification(
                    localize('failed'),
                    time_ms=2500,
                    audible=False,
                )
                return False, None

            results = ui.on_keyboard_input(localize('bookmarks.edit.name'),
                                           params.get('item_name', item_uri))
            if not results[0]:
                return False, None
            item_name = results[1]

            item_date_time = now()
            item = BookmarkItem(name=item_name,
                                uri=item_uri,
                                plot=item_uri,
                                date_time=item_date_time,
                                category_label='__inherit__')
            if item_id:
                item.bookmark_id = item_id
                context.get_bookmarks_list().update_item(item_id, repr(item))
            else:
                item_id = item.generate_id(
                    item_name,
                    item_uri,
                    since_epoch(item_date_time),
                    prefix='custom',
                )
                item.bookmark_id = item_id
                context.get_bookmarks_list().add_item(item_id, repr(item))

            ui.show_notification(
                localize('updated.x', item_name)
                if item_id else
                localize('bookmark.created'),
                time_ms=2500,
                audible=False,
            )
            return True, {provider.FORCE_REFRESH: True}

        if not item_id:
            return False, None

        if command == 'add':
            item = params.get('item')
            if not item:
                return False, None

            context.get_bookmarks_list().add_item(item_id, item)
            ui.show_notification(
                localize('bookmark.created'),
                time_ms=2500,
                audible=False,
            )
            return (
                True,
                {
                    provider.FORCE_REFRESH: context.get_path().startswith(
                        PATHS.BOOKMARKS
                    ),
                },
            )

        if command == 'remove':
            bookmark_name = params.get('item_name') or localize('bookmark')
            bookmark_name = to_unicode(bookmark_name)
            if not ui.on_yes_no_input(
                    localize('content.remove'),
                    localize('content.remove.check.x', bookmark_name),
            ):
                return False, {provider.FALLBACK: False}

            context.get_bookmarks_list().del_item(item_id)
            ui.show_notification(
                localize('removed.name.x', bookmark_name),
                time_ms=2500,
                audible=False,
            )
            return True, {provider.FORCE_REFRESH: True}

        return False, None

    @staticmethod
    def on_watch_later(provider, context, re_match):
        params = context.get_params()
        command = re_match.group('command') or 'list'

        localize = context.localize
        ui = context.get_ui()

        if command in {'list', 'play'}:
            items = context.get_watch_later_list().get_items()
            if not items:
                return True, None

            context_menu = (
                menu_items.watch_later_local_remove(context),
                menu_items.watch_later_local_clear(context),
            )
            v3_response = {
                'kind': 'youtube#videoListResponse',
                'items': [
                    {
                        'kind': 'youtube#video',
                        'id': video_id,
                        '_partial': True,
                        '_context_menu': {
                            'context_menu': context_menu,
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
            options = {
                provider.CONTENT_TYPE: {
                    'content_type': CONTENT.VIDEO_CONTENT,
                    'sub_type': 'watch_later',
                    'category_label': None,
                },
            }
            return video_items, options

        if command == 'clear':
            if not ui.on_yes_no_input(
                    localize('watch_later.clear'),
                    localize('watch_later.clear.check')
            ):
                return False, {provider.FALLBACK: False}

            context.get_watch_later_list().clear()
            ui.show_notification(
                localize('completed'),
                time_ms=2500,
                audible=False,
            )
            return True, {provider.FORCE_REFRESH: True}

        video_id = params.get(VIDEO_ID)
        if not video_id:
            return False, None

        if command == 'add':
            item = params.get('item')
            if not item:
                return False, None

            context.get_watch_later_list().add_item(video_id, item)
            ui.show_notification(
                localize(('added.to.x', 'watch_later')),
                time_ms=2500,
                audible=False,
            )
            return True, None

        if command == 'remove':
            video_name = params.get('item_name') or localize('untitled')
            video_name = to_unicode(video_name)
            if not ui.on_yes_no_input(
                    localize('content.remove'),
                    localize('content.remove.check.x', video_name),
            ):
                return False, {provider.FALLBACK: False}

            context.get_watch_later_list().del_item(video_id)
            ui.show_notification(
                localize('removed.name.x', video_name),
                time_ms=2500,
                audible=False,
            )
            return True, {provider.FORCE_REFRESH: True}

        return False, None

    def handle_exception(self, context, exception_to_handle):
        if not isinstance(exception_to_handle, (InvalidGrant, LoginException)):
            return False

        ok_dialog = False
        message = exception_to_handle.get_message()
        if isinstance(message, dict):
            log_msg = message.get('error_description') or message.get('message')
            if log_msg:
                log_msg = strip_html_from_text(log_msg)
            else:
                log_msg = 'No error message provided'

            error_type = message.get('error', 'Unknown error')
            error_code = message.get('code', 'N/A')
            if error_type == 'deleted_client':
                notification = context.localize('key.requirement')
                context.get_access_manager().update_access_token(
                    context.get_param('addon_id', None),
                    access_token='',
                    expiry=-1,
                    refresh_token='',
                )
                ok_dialog = True
            elif error_type == 'invalid_client':
                if log_msg == 'The OAuth client was not found.':
                    notification = context.localize('client.id.incorrect')
                elif log_msg == 'Unauthorized':
                    notification = context.localize('client.secret.incorrect')
                else:
                    notification = log_msg
            else:
                notification = log_msg
        else:
            notification = log_msg = message
            error_type = 'Unknown error'
            error_code = 'N/A'

        self.log.error(('Error - {error_type} (code: {error_code})',
                        'Message:   {message}',
                        'Exception: {exc!r}'),
                       error_type=error_type,
                       error_code=error_code,
                       message=log_msg,
                       exc=exception_to_handle)

        title = '{name}: {message} - {error_type} (code: {error_code})'.format(
            name=context.get_name(),
            message=exception_to_handle.get_message(),
            error_type=error_type,
            error_code=error_code,
        )
        if ok_dialog:
            context.get_ui().on_ok(title, notification)
        else:
            context.get_ui().show_notification(notification, title)
        return True

    def tear_down(self):
        attrs = (
            '_resource_manager',
            '_client',
        )
        for attr in attrs:
            try:
                delattr(self, attr)
                setattr(self, attr, None)
            except (AttributeError, TypeError):
                pass
