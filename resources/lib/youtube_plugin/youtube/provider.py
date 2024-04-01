# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2018 plugin.video.youtube

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only for more information.
"""

from __future__ import absolute_import, division, unicode_literals

import json
import re
from base64 import b64decode

from .client import YouTube
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
from ..kodion import AbstractProvider, RegisterProviderPath
from ..kodion.constants import (
    ADDON_ID,
    content,
    paths,
)
from ..kodion.items import (
    DirectoryItem,
    NewSearchItem,
    SearchItem,
    UriItem,
    menu_items,
)
from ..kodion.utils import find_video_id, strip_html_from_text


class Provider(AbstractProvider):
    def __init__(self):
        super(Provider, self).__init__()
        self._resource_manager = None

        self._client = None
        self._logged_in = False

        self.yt_video = yt_video

    def get_wizard_steps(self, context):
        steps = [
            yt_setup_wizard.process_default_settings,
            yt_setup_wizard.process_performance_settings,
            yt_setup_wizard.process_language,
            yt_setup_wizard.process_subtitles,
            yt_setup_wizard.process_geo_location,
            yt_setup_wizard.process_old_search_db,
            yt_setup_wizard.process_old_history_db,
            yt_setup_wizard.process_list_detail_settings,
        ]
        return steps

    def is_logged_in(self):
        return self._logged_in

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

        items_per_page = settings.items_per_page()

        language = settings.get_language()
        region = settings.get_region()

        api_last_origin = access_manager.get_last_origin()

        youtube_config = YouTube.CONFIGS.get('main')

        dev_id = context.get_param('addon_id')
        dev_configs = YouTube.CONFIGS.get('developer')
        dev_config = self.get_dev_config(context, dev_id, dev_configs)
        dev_keys = dev_config.get('main') if dev_config else None

        refresh_tokens = []

        if dev_id:
            origin = dev_config.get('origin') if dev_config.get('origin') else dev_id
        else:
            origin = ADDON_ID

        if api_last_origin != origin:
            context.log_debug('API key origin changed: |{old}| to |{new}|'
                              .format(old=api_last_origin, new=origin))
            access_manager.set_last_origin(origin)

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
                else:
                    access_tokens = []

                refresh_tokens = access_manager.get_dev_refresh_token(dev_id)
                if refresh_tokens:
                    refresh_tokens = refresh_tokens.split('|')
                else:
                    refresh_tokens = []

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
                else:
                    access_tokens = []

                refresh_tokens = access_manager.get_refresh_token()
                if refresh_tokens:
                    refresh_tokens = refresh_tokens.split('|')
                else:
                    refresh_tokens = []

                context.log_debug('Access token count: |%d| Refresh token count: |%d|' % (len(access_tokens), len(refresh_tokens)))

        client = YouTube(context=context,
                         language=language,
                         region=region,
                         items_per_page=items_per_page,
                         config=dev_keys if dev_keys else youtube_config)

        with client:
            if not refresh_tokens or not refresh_tokens[0]:
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
                except (InvalidGrant, LoginException) as exc:
                    self.handle_exception(context, exc)
                    # reset access_token
                    if isinstance(exc, InvalidGrant):
                        if dev_id:
                            access_manager.update_dev_access_token(dev_id, access_token='', refresh_token='')
                        else:
                            access_manager.update_access_token(access_token='', refresh_token='')
                    elif dev_id:
                        access_manager.update_dev_access_token(dev_id, '')
                    else:
                        access_manager.update_access_token('')

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
        if not self._resource_manager:
            # self._resource_manager = ResourceManager(weakref.proxy(context), weakref.proxy(self.get_client(context)))
            self._resource_manager = ResourceManager(context, self.get_client(context))
        return self._resource_manager

    # noinspection PyUnusedLocal
    @RegisterProviderPath('^/uri2addon/?$')
    def on_uri2addon(self, context, re_match, uri=None):
        if uri is None:
            uri = context.get_param('uri')
            skip_title = True
            listing = False
        else:
            skip_title = False
            listing = True

        if not uri:
            return False

        resolver = UrlResolver(context)
        res_url = resolver.resolve(uri)
        url_converter = UrlToItemConverter(flatten=True)
        url_converter.add_url(res_url, context)
        items = url_converter.get_items(self, context, skip_title=skip_title)
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

    @RegisterProviderPath('^(?:/channel/(?P<channel_id>[^/]+))?/playlist/(?P<playlist_id>[^/]+)/?$')
    def _on_playlist(self, context, re_match):
        context.set_content(content.VIDEO_CONTENT)
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

    @RegisterProviderPath('^/channel/(?P<channel_id>[^/]+)/playlists/?$')
    def _on_channel_playlists(self, context, re_match):
        context.set_content(content.LIST_CONTENT)
        result = []

        channel_id = re_match.group('channel_id')

        resource_manager = self.get_resource_manager(context)

        params = context.get_params()
        page_token = params.get('page_token', '')
        incognito = params.get('incognito')
        addon_id = params.get('addon_id')

        new_params = {}
        if incognito:
            new_params['incognito'] = incognito
        if addon_id:
            new_params['addon_id'] = addon_id

        playlists = resource_manager.get_related_playlists(channel_id)
        uploads_playlist = playlists.get('uploads', '')
        if uploads_playlist:
            item_label = context.localize('uploads')
            uploads_item = DirectoryItem(
                context.get_ui().bold(item_label),
                context.create_uri(
                    ('channel', channel_id, 'playlist', uploads_playlist),
                    new_params,
                ),
                image='{media}/playlist.png',
                category_label=item_label,
            )
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

    @RegisterProviderPath('^/channel/(?P<channel_id>[^/]+)/live/?$')
    def _on_channel_live(self, context, re_match):
        context.set_content(content.VIDEO_CONTENT)
        result = []

        channel_id = re_match.group('channel_id')
        page_token = context.get_param('page_token', '')
        safe_search = context.get_settings().safe_search()

        # no caching
        json_data = self.get_client(context).search(q='',
                                                    search_type='video',
                                                    event_type='live',
                                                    channel_id=channel_id,
                                                    page_token=page_token,
                                                    safe_search=safe_search)
        if not json_data:
            return False
        result.extend(v3.response_to_items(self, context, json_data))

        return result

    """
    Lists a playlist folder and all uploaded videos of a channel.
    path      :'/channel|user/(?P<channel_id|username>)[^/]+/'
    channel_id: <CHANNEL_ID>
    """

    @RegisterProviderPath('^/(?P<method>(channel|user))/(?P<channel_id>[^/]+)/?$')
    def _on_channel(self, context, re_match):
        listitem_channel_id = context.get_listitem_detail('channel_id')

        client = self.get_client(context)
        localize = context.localize
        create_uri = context.create_uri
        function_cache = context.get_function_cache()
        params = context.get_params()
        ui = context.get_ui()

        method = re_match.group('method')
        channel_id = re_match.group('channel_id')

        if (method == 'channel' and channel_id
                and channel_id.lower() == 'property'
                and listitem_channel_id
                and listitem_channel_id.lower().startswith(('mine', 'uc'))):
            context.execute('ActivateWindow(Videos, {channel}, return)'.format(
                channel=create_uri(('channel', listitem_channel_id))
            ))

        if method == 'channel' and not channel_id:
            return False

        context.set_content(content.VIDEO_CONTENT)

        resource_manager = self.get_resource_manager(context)

        mine_id = ''
        result = []

        """
        This is a helper routine if we only have the username of a channel.
        This will retrieve the correct channel id based on the username.
        """
        if method == 'user' or channel_id == 'mine':
            context.log_debug('Trying to get channel id for user "%s"' % channel_id)

            json_data = function_cache.run(client.get_channel_by_username,
                                           function_cache.ONE_DAY,
                                           _refresh=params.get('refresh'),
                                           username=channel_id)
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

        channel_fanarts = resource_manager.get_fanarts((channel_id,))

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
                    fanart=channel_fanarts.get(channel_id),
                    category_label=item_label,
                )
                result.append(playlists_item)

            search_live_id = mine_id if mine_id else channel_id
            if not hide_search:
                search_item = NewSearchItem(
                    context, name=ui.bold(localize('search')),
                    image='{media}/search.png',
                    channel_id=search_live_id,
                    incognito=incognito,
                    addon_id=addon_id,
                )
                result.append(search_item)

            if not hide_live:
                item_label = localize('live')
                live_item = DirectoryItem(
                    ui.bold(item_label),
                    create_uri(('channel', search_live_id, 'live'), new_params),
                    image='{media}/live.png',
                    category_label=item_label,
                )
                result.append(live_item)

        playlists = resource_manager.get_related_playlists(channel_id)
        upload_playlist = playlists.get('uploads', '')
        if upload_playlist:
            json_data = function_cache.run(client.get_playlist_items,
                                           function_cache.ONE_MINUTE * 5,
                                           _refresh=params.get('refresh'),
                                           playlist_id=upload_playlist,
                                           page_token=page_token)
            if not json_data:
                return result

            result.extend(v3.response_to_items(self, context, json_data))

        return result

    # noinspection PyUnusedLocal
    @RegisterProviderPath('^/location/mine/?$')
    def _on_my_location(self, context, re_match):
        context.set_content(content.LIST_CONTENT)

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
    @RegisterProviderPath('^/play/?$')
    def on_play(self, context, re_match):
        ui = context.get_ui()

        redirect = False
        params = context.get_params()

        if ({'channel_id', 'live', 'playlist_id', 'playlist_ids', 'video_id'}
                .isdisjoint(params.keys())):
            path = context.get_listitem_detail('FileNameAndPath', attr=True)
            if context.is_plugin_path(path, 'play/'):
                video_id = find_video_id(path)
                if video_id:
                    context.set_param('video_id', video_id)
                    params['video_id'] = video_id
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
                    context.create_uri(('play',), params)
                ))
                return False
            return yt_play.play_video(self, context)

        if playlist_id or 'playlist_ids' in params:
            return yt_play.play_playlist(self, context)

        if 'channel_id' in params and params.get('live', 0) > 0:
            return yt_play.play_channel_live(self, context)
        return False

    @RegisterProviderPath('^/video/(?P<method>[^/]+)/?$')
    def _on_video_x(self, context, re_match):
        method = re_match.group('method')
        return yt_video.process(method, self, context, re_match)

    @RegisterProviderPath('^/playlist/(?P<method>[^/]+)/(?P<category>[^/]+)/?$')
    def _on_playlist_x(self, context, re_match):
        method = re_match.group('method')
        category = re_match.group('category')
        return yt_playlist.process(method, category, self, context)

    @RegisterProviderPath('^/subscriptions/(?P<method>[^/]+)/?$')
    def _on_subscriptions(self, context, re_match):
        method = re_match.group('method')
        resource_manager = self.get_resource_manager(context)
        subscriptions = yt_subscriptions.process(method, self, context)

        if method == 'list':
            context.set_content(content.LIST_CONTENT)
            channel_ids = {subscription.get_channel_id(): subscription
                           for subscription in subscriptions}
            channel_fanarts = resource_manager.get_fanarts(channel_ids)
            for channel_id, fanart in channel_fanarts.items():
                channel_ids[channel_id].set_fanart(fanart)

        return subscriptions

    @RegisterProviderPath('^/special/(?P<category>[^/]+)/?$')
    def _on_yt_specials(self, context, re_match):
        category = re_match.group('category')
        return yt_specials.process(category, self, context)

    @RegisterProviderPath('^/users/(?P<action>[^/]+)/?$')
    def _on_users(self, _context, re_match):
        action = re_match.group('action')
        return UriItem('{addon},users/{action}'.format(
            addon=ADDON_ID, action=action
        ))

    @RegisterProviderPath('^/sign/(?P<mode>[^/]+)/?$')
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
        # Search by url to access unlisted videos
        if search_text.startswith(('https://', 'http://')):
            return self.on_uri2addon(context, None, search_text)

        result = self._search_channel_or_playlist(context, search_text)
        if result:  # found a channel or playlist matching search_text
            return result

        context.set_param('q', search_text)
        context.set_param('category_label', search_text)

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
            context.set_content(content.VIDEO_CONTENT)
        else:
            context.set_content(content.LIST_CONTENT)

        if page == 1 and search_type == 'video' and not event_type and not hide_folders:
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
                                       location=location)
        if not json_data:
            return False
        result.extend(v3.response_to_items(self, context, json_data))
        return result

    @RegisterProviderPath('^/config/(?P<action>[^/]+)/?$')
    def configure_addon(self, context, re_match):
        action = re_match.group('action')
        if action == 'setup_wizard':
            self.run_wizard(context)
            return False
        return UriItem('{addon},config/{action}'.format(
            addon=ADDON_ID, action=action
        ))

    # noinspection PyUnusedLocal
    @RegisterProviderPath('^/my_subscriptions/filter/?$')
    def manage_my_subscription_filter(self, context, re_match):
        settings = context.get_settings()
        ui = context.get_ui()

        params = context.get_params()
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

    @RegisterProviderPath('^/maintenance/(?P<action>[^/]+)/(?P<target>[^/]+)/?$')
    def maintenance_actions(self, context, re_match):
        target = re_match.group('target')
        action = re_match.group('action')

        if action != 'reset':
            return UriItem(
                '{addon},maintenance/{action}/?target={target}'.format(
                    addon=ADDON_ID, action=action, target=target,
                )
            )

        ui = context.get_ui()
        localize = context.localize

        if (target == 'access_manager' and ui.on_yes_no_input(
            context.get_name(), localize('reset.access_manager.confirm')
        )):
            try:
                access_manager = context.get_access_manager()
                client = self.get_client(context)
                if access_manager.has_refresh_token():
                    refresh_tokens = access_manager.get_refresh_token()
                    for refresh_token in set(refresh_tokens.split('|')):
                        try:
                            client.revoke(refresh_token)
                        except:
                            pass
                self.reset_client()
                access_manager.update_access_token(access_token='',
                                                   refresh_token='')
                ui.refresh_container()
                ui.show_notification(localize('succeeded'))
            except:
                ui.show_notification(localize('failed'))

    # noinspection PyUnusedLocal
    @RegisterProviderPath('^/api/update/?$')
    def api_key_update(self, context, re_match):
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
    def on_playback_history(self, context, re_match):
        params = context.get_params()
        action = params.get('action')
        if not action:
            return False

        playback_history = context.get_playback_history()

        if action == 'list':
            context.set_content(content.VIDEO_CONTENT, sub_type='history')
            items = playback_history.get_items()
            if not items:
                return True

            v3_response = {
                'kind': 'youtube#videoListResponse',
                'items': [
                    {
                        'kind': 'youtube#video',
                        'id': video_id,
                        'partial': True,
                    }
                    for video_id in items.keys()
                ]
            }
            video_items = v3.response_to_items(self, context, v3_response)

            for video_item in video_items:
                context_menu = [
                    menu_items.history_remove(
                        context, video_item.video_id
                    ),
                    menu_items.history_clear(
                        context
                    ),
                    ('--------', 'noop'),
                ]
                video_item.add_context_menu(context_menu)

            return video_items

        if (action == 'clear' and context.get_ui().on_yes_no_input(
                    context.get_name(),
                    context.localize('history.clear.confirm')
                )):
            playback_history.clear()
            context.get_ui().refresh_container()
            return True

        video_id = params.get('video_id')
        if not video_id:
            return False

        if action == 'remove':
            playback_history.remove(video_id)
            context.get_ui().refresh_container()
            return True

        play_data = playback_history.get_item(video_id)
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

        playback_history.update(video_id, play_data)
        context.get_ui().refresh_container()
        return True

    def on_root(self, context, re_match):
        create_uri = context.create_uri
        localize = context.localize
        settings = context.get_settings()
        ui = context.get_ui()

        _ = self.get_client(context)  # required for self.is_logged_in()
        logged_in = self.is_logged_in()
        # _.get_my_playlists()

        # context.set_content(content.LIST_CONTENT)

        result = []

        # sign in
        if not logged_in and settings.get_bool('youtube.folder.sign.in.show', True):
            item_label = localize('sign.in')
            sign_in_item = DirectoryItem(
                ui.bold(item_label),
                create_uri(('sign', 'in')),
                image='{media}/sign_in.png',
                action=True,
                category_label=item_label,
            )
            result.append(sign_in_item)

        if logged_in and settings.get_bool('youtube.folder.my_subscriptions.show', True):
            # my subscription
            item_label = localize('my_subscriptions')
            my_subscriptions_item = DirectoryItem(
                ui.bold(item_label),
                create_uri(('special', 'new_uploaded_videos_tv')),
                image='{media}/new_uploads.png',
                category_label=item_label,
            )
            result.append(my_subscriptions_item)

        if logged_in and settings.get_bool('youtube.folder.my_subscriptions_filtered.show', True):
            # my subscriptions filtered
            my_subscriptions_filtered_item = DirectoryItem(
                localize('my_subscriptions.filtered'),
                create_uri(('special', 'new_uploaded_videos_tv_filtered')),
                image='{media}/new_uploads.png',
            )
            result.append(my_subscriptions_filtered_item)

        access_manager = context.get_access_manager()
        watch_later_id = logged_in and access_manager.get_watch_later_id()
        history_id = logged_in and access_manager.get_watch_history_id()
        local_history = settings.use_local_history()

        # Home / Recommendations
        if settings.get_bool('youtube.folder.recommendations.show', True):
            recommendations_item = DirectoryItem(
                localize('recommendations'),
                create_uri(('special', 'recommendations')),
                image='{media}/home.png',
            )
            result.append(recommendations_item)

        # Related
        if settings.get_bool('youtube.folder.related.show', True):
            if history_id or local_history:
                related_item = DirectoryItem(
                    localize('related_videos'),
                    create_uri(('special', 'related_videos')),
                    image='{media}/related_videos.png',
                )
                result.append(related_item)

        # Trending
        if settings.get_bool('youtube.folder.popular_right_now.show', True):
            trending_item = DirectoryItem(
                localize('trending'),
                create_uri(('special', 'popular_right_now')),
                image='{media}/trending.png',
            )
            result.append(trending_item)

        # search
        if settings.get_bool('youtube.folder.search.show', True):
            search_item = SearchItem(
                context,
            )
            result.append(search_item)

        if settings.get_bool('youtube.folder.quick_search.show', True):
            quick_search_item = NewSearchItem(
                context,
                name=localize('search.quick'),
                image='{media}/quick_search.png',
            )
            result.append(quick_search_item)

        if settings.get_bool('youtube.folder.quick_search_incognito.show', True):
            quick_search_incognito_item = NewSearchItem(
                context,
                name=localize('search.quick.incognito'),
                image='{media}/incognito_search.png',
                incognito=True,
            )
            result.append(quick_search_incognito_item)

        # my location
        if settings.get_bool('youtube.folder.my_location.show', True) and settings.get_location():
            my_location_item = DirectoryItem(
                localize('my_location'),
                create_uri(('location', 'mine')),
                image='{media}/location.png',
            )
            result.append(my_location_item)

        # my channel
        if logged_in and settings.get_bool('youtube.folder.my_channel.show', True):
            my_channel_item = DirectoryItem(
                localize('my_channel'),
                create_uri(('channel', 'mine')),
                image='{media}/channel.png',
            )
            result.append(my_channel_item)

        # watch later
        if settings.get_bool('youtube.folder.watch_later.show', True):
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
                watch_later_item.set_context_menu(context_menu)
                result.append(watch_later_item)
            else:
                watch_history_item = DirectoryItem(
                    localize('watch_later'),
                    create_uri((paths.WATCH_LATER, 'list')),
                    image='{media}/watch_later.png',
                )
                result.append(watch_history_item)

        # liked videos
        if logged_in and settings.get_bool('youtube.folder.liked_videos.show', True):
            resource_manager = self.get_resource_manager(context)
            playlists = resource_manager.get_related_playlists(channel_id='mine')
            if 'likes' in playlists:
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
                liked_videos_item.set_context_menu(context_menu)
                result.append(liked_videos_item)

        # disliked videos
        if logged_in and settings.get_bool('youtube.folder.disliked_videos.show', True):
            disliked_videos_item = DirectoryItem(
                localize('video.disliked'),
                create_uri(('special', 'disliked_videos')),
                image='{media}/dislikes.png',
            )
            result.append(disliked_videos_item)

        # history
        if settings.get_bool('youtube.folder.history.show', False):
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
                watch_history_item.set_context_menu(context_menu)
                result.append(watch_history_item)
            elif local_history:
                watch_history_item = DirectoryItem(
                    localize('history'),
                    create_uri((paths.HISTORY,), params={'action': 'list'}),
                    image='{media}/history.png',
                )
                result.append(watch_history_item)

        # (my) playlists
        if logged_in and settings.get_bool('youtube.folder.playlists.show', True):
            playlists_item = DirectoryItem(
                localize('playlists'),
                create_uri(('channel', 'mine', 'playlists')),
                image='{media}/playlist.png',
            )
            result.append(playlists_item)

        # saved playlists
        # TODO: re-enable once functionality is restored
        # if logged_in and settings.get_bool('youtube.folder.saved.playlists.show', True):
        #     playlists_item = DirectoryItem(
        #         localize('saved.playlists'),
        #         create_uri(('special', 'saved_playlists')),
        #         image='{media}/playlist.png',
        #     )
        #     result.append(playlists_item)

        # subscriptions
        if logged_in and settings.get_bool('youtube.folder.subscriptions.show', True):
            subscriptions_item = DirectoryItem(
                localize('subscriptions'),
                create_uri(('subscriptions', 'list')),
                image='{media}/channels.png',
            )
            result.append(subscriptions_item)

        # browse channels
        if logged_in and settings.get_bool('youtube.folder.browse_channels.show', True):
            browse_channels_item = DirectoryItem(
                localize('browse_channels'),
                create_uri(('special', 'browse_channels')),
                image='{media}/browse_channels.png',
            )
            result.append(browse_channels_item)

        # completed live events
        if settings.get_bool('youtube.folder.completed.live.show', True):
            live_events_item = DirectoryItem(
                localize('live.completed'),
                create_uri(('special', 'completed_live')),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # upcoming live events
        if settings.get_bool('youtube.folder.upcoming.live.show', True):
            live_events_item = DirectoryItem(
                localize('live.upcoming'),
                create_uri(('special', 'upcoming_live')),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # live events
        if settings.get_bool('youtube.folder.live.show', True):
            live_events_item = DirectoryItem(
                localize('live'),
                create_uri(('special', 'live')),
                image='{media}/live.png',
            )
            result.append(live_events_item)

        # switch user
        if settings.get_bool('youtube.folder.switch.user.show', True):
            switch_user_item = DirectoryItem(
                localize('user.switch'),
                create_uri(('users', 'switch')),
                image='{media}/channel.png',
                action=True,
            )
            result.append(switch_user_item)

        # sign out
        if logged_in and settings.get_bool('youtube.folder.sign.out.show', True):
            sign_out_item = DirectoryItem(
                localize('sign.out'),
                create_uri(('sign', 'out')),
                image='{media}/sign_out.png',
                action=True,
            )
            result.append(sign_out_item)

        if settings.get_bool('youtube.folder.settings.show', True):
            settings_menu_item = DirectoryItem(
                localize('setup_wizard'),
                create_uri(('config', 'setup_wizard')),
                image='{media}/settings.png',
                action=True,
            )
            result.append(settings_menu_item)

        if settings.get_bool('youtube.folder.settings.advanced.show', True):
            settings_menu_item = DirectoryItem(
                localize('settings'),
                create_uri(('config', 'youtube')),
                image='{media}/settings.png',
                action=True,
            )
            result.append(settings_menu_item)

        return result

    def on_watch_later(self, context, re_match):
        params = context.get_params()
        command = re_match.group('command')
        if not command:
            return False

        if command == 'list':
            context.set_content(content.VIDEO_CONTENT, sub_type='watch_later')
            items = context.get_watch_later_list().get_items()
            if not items:
                return True

            v3_response = {
                'kind': 'youtube#videoListResponse',
                'items': [
                    {
                        'kind': 'youtube#video',
                        'id': video_id,
                        'partial': True,
                    }
                    for video_id in items.keys()
                ]
            }
            video_items = v3.response_to_items(self, context, v3_response)

            for video_item in video_items:
                context_menu = [
                    menu_items.watch_later_local_remove(
                        context, video_item.video_id
                    ),
                    menu_items.watch_later_local_clear(
                        context
                    ),
                    ('--------', 'noop'),
                ]
                video_item.add_context_menu(context_menu)

            return video_items

        if (command == 'clear' and context.get_ui().on_yes_no_input(
                    context.get_name(),
                    context.localize('watch_later.clear.confirm')
                )):
            context.get_watch_later_list().clear()
            context.get_ui().refresh_container()
            return True

        video_id = params.get('video_id')
        if not video_id:
            return False

        if command == 'add':
            item = params.get('item')
            if item:
                context.get_watch_later_list().add(video_id, item)
            return True

        if command == 'remove':
            context.get_watch_later_list().remove(video_id)
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
                    access_token='', refresh_token=''
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

    def tear_down(self, context):
        context.tear_down()
