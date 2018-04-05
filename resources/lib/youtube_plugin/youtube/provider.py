__author__ = 'bromix'

import os
import re
import json
import shutil
import socket
from base64 import b64decode

from ..youtube.helper import yt_subscriptions
from .. import kodion
from ..kodion.utils import FunctionCache
from ..kodion.items import *
from ..youtube.client import YouTube
from .helper import v3, ResourceManager, yt_specials, yt_playlist, yt_login, yt_setup_wizard, yt_video, \
    yt_context_menu, yt_play, yt_old_actions, UrlResolver, UrlToItemConverter
from .youtube_exceptions import LoginException

import xbmc
import xbmcaddon
import xbmcvfs


class Provider(kodion.AbstractProvider):
    LOCAL_MAP = {'youtube.search': 30102,
                 'youtube.watch_later': 30107,
                 'youtube.video.rate.none': 30108,
                 'youtube.remove': 30108,
                 'youtube.sign.in': 30111,
                 'youtube.sign.out': 30112,
                 'youtube.rename': 30113,
                 'youtube.delete': 30118,
                 'youtube.api.key': 30201,
                 'youtube.api.id': 30202,
                 'youtube.api.secret': 30203,
                 'youtube.channels': 30500,
                 'youtube.playlists': 30501,
                 'youtube.go_to_channel': 30502,
                 'youtube.subscriptions': 30504,
                 'youtube.unsubscribe': 30505,
                 'youtube.subscribe': 30506,
                 'youtube.my_channel': 30507,
                 'youtube.video.liked': 30508,
                 'youtube.history': 30509,
                 'youtube.my_subscriptions': 30510,
                 'youtube.video.queue': 30511,
                 'youtube.browse_channels': 30512,
                 'youtube.popular_right_now': 30513,
                 'youtube.related_videos': 30514,
                 'youtube.setting.auto_remove_watch_later': 30515,
                 'youtube.subscribe_to': 30517,
                 'youtube.sign.go_to': 30518,
                 'youtube.sign.enter_code': 30519,
                 'youtube.video.add_to_playlist': 30520,
                 'youtube.playlist.select': 30521,
                 'youtube.playlist.create': 30522,
                 'youtube.setup_wizard.select_language': 30524,
                 'youtube.setup_wizard.select_region': 30525,
                 'youtube.setup_wizard.adjust': 30526,
                 'youtube.setup_wizard.adjust.language_and_region': 30527,
                 'youtube.video.rate': 30528,
                 'youtube.video.rate.like': 30529,
                 'youtube.video.rate.dislike': 30530,
                 'youtube.playlist.play.all': 30531,
                 'youtube.playlist.play.default': 30532,
                 'youtube.playlist.play.reverse': 30533,
                 'youtube.playlist.play.shuffle': 30534,
                 'youtube.playlist.play.select': 30535,
                 'youtube.playlist.progress.updating': 30536,
                 'youtube.playlist.play.from_here': 30537,
                 'youtube.video.disliked': 30538,
                 'youtube.live': 30539,
                 'youtube.video.play_with': 30540,
                 'youtube.error.rtmpe_not_supported': 30542,
                 'youtube.refresh': 30543,
                 'youtube.video.description.links': 30544,
                 'youtube.video.description.links.not_found': 30545,
                 'youtube.sign.twice.title': 30546,
                 'youtube.sign.twice.text': 30547,
                 'youtube.video.more': 30548,
                 'youtube.error.no_video_streams_found': 30549,
                 'youtube.recommendations': 30551,
                 'youtube.function.cache': 30557,
                 'youtube.search.history': 30558,
                 'youtube.subtitle.language': 30560,
                 'youtube.none': 30561,
                 'youtube.prompt': 30566,
                 'youtube.set.as.watchlater': 30567,
                 'youtube.remove.as.watchlater': 30568,
                 'youtube.set.as.history': 30571,
                 'youtube.remove.as.history': 30572,
                 'youtube.succeeded': 30575,
                 'youtube.failed': 30576,
                 'youtube.settings': 30577,
                 'youtube.dash.enable.confirm': 30579,
                 'youtube.reset.access.manager.confirm': 30581,
                 'youtube.my_subscriptions_filtered': 30584,
                 'youtube.add.my_subscriptions.filter': 30587,
                 'youtube.remove.my_subscriptions.filter': 30588,
                 'youtube.added.my_subscriptions.filter': 30589,
                 'youtube.removed.my_subscriptions.filter': 30590,
                 'youtube.updated_': 30597,
                 'youtube.api.personal.enabled': 30598,
                 'youtube.api.personal.failed': 30599,
                 'youtube.subtitle._with_fallback': 30601,
                 'youtube.subtitle.no.auto.generated': 30602,
                 'youtube.quick.search': 30605,
                 'youtube.quick.search.incognito': 30606,
                 'youtube.clear_history': 30609,
                 'youtube.clear_history_confirmation': 30610,
                 'youtube.saved.playlists': 30611,
                 'youtube.retry': 30612,
                 'youtube.failed.watch_later.retry': 30614,
                 'youtube.cancel': 30615,
                 'youtube.must.be.signed.in': 30616,
                 'youtube.select.listen.ip': 30644,
                 'youtube.purchases': 30622,
                 'youtube.requires.krypton': 30624,
                 'youtube.inputstreamhelper.is.installed': 30625
                 }

    def __init__(self):
        kodion.AbstractProvider.__init__(self)
        self._resource_manager = None

        self._client = None
        self._is_logged_in = False

    def get_wizard_supported_views(self):
        return ['default', 'episodes']

    def get_wizard_steps(self, context):
        return [(yt_setup_wizard.process, [self, context])]

    def is_logged_in(self):
        return self._is_logged_in

    @staticmethod
    def get_dev_config(context, addon_id, dev_configs):
        _dev_config = context.get_ui().get_home_window_property('configs')
        context.get_ui().clear_home_window_property('configs')

        dev_config = None
        if _dev_config is not None:
            context.log_debug('Using window property for developer keys is deprecated, instead use the youtube_registration module.')
            try:
                dev_config = json.loads(_dev_config)
            except ValueError:
                context.log_error('Error loading developer key: |invalid json|')
        if not dev_config and addon_id and dev_configs:
            dev_config = dev_configs.get(addon_id)

        if dev_config is not None and not context.get_settings().allow_dev_keys():
            context.log_debug('Developer config ignored')
            return None
        elif dev_config:
            if not dev_config.get('main') or not dev_config['main'].get('key') \
                    or not dev_config['main'].get('system') or not dev_config.get('origin') \
                    or not dev_config['main'].get('id') or not dev_config['main'].get('secret'):
                context.log_error('Error loading developer config: |invalid structure| '
                                  'expected: |{"origin": ADDON_ID, "main": {"system": SYSTEM_NAME, "key": API_KEY, "id": CLIENT_ID, "secret": CLIENT_SECRET}}|')
                return None
            else:
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
        else:
            return None

    def reset_client(self):
        self._client = None

    def get_client(self, context):
        # set the items per page (later)
        settings = context.get_settings()
        access_manager = context.get_access_manager()

        items_per_page = settings.get_items_per_page()

        language = settings.get_string('youtube.language', 'en-US')
        region = settings.get_string('youtube.region', 'US')

        api_last_origin = access_manager.get_last_origin()

        youtube_config = YouTube.CONFIGS.get('main')

        dev_id = context.get_param('addon_id', None)
        dev_configs = YouTube.CONFIGS.get('developer')
        dev_config = self.get_dev_config(context, dev_id, dev_configs)
        if dev_config:
            dev_keys = dev_config.get('main')
            if api_last_origin != dev_config.get('origin'):
                context.log_debug('API key origin changed, clearing cache. |%s|' % dev_config.get('origin'))
                context.get_function_cache().clear()
                access_manager.set_last_origin(dev_config.get('origin'))
            self._client = YouTube(items_per_page=items_per_page, language=language, region=region, config=dev_keys)
            self._client.set_log_error(context.log_error)
        else:
            if api_last_origin != 'plugin.video.youtube':
                context.log_debug('API key origin changed, clearing cache. |plugin.video.youtube|')
                context.get_function_cache().clear()
                access_manager.set_last_origin('plugin.video.youtube')

            access_tokens = access_manager.get_access_token().split('|')
            if len(access_tokens) != 2 or access_manager.is_access_token_expired():
                # reset access_token
                access_manager.update_access_token('')
                # we clear the cache, so none cached data of an old account will be displayed.
                # context.get_function_cache().clear()
                # reset the client
                self._client = None

            if not self._client:
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
                    # create a new access_token
                    client = YouTube(language=language, region=region, items_per_page=items_per_page, config=youtube_config)
                    if len(access_tokens) != 2 and len(refresh_tokens) == 2:
                        try:

                            access_token_kodi, expires_in_kodi = client.refresh_token(refresh_tokens[1])

                            access_token_tv, expires_in_tv = client.refresh_token_tv(refresh_tokens[0])

                            access_tokens = [access_token_tv, access_token_kodi]

                            access_token = '%s|%s' % (access_token_tv, access_token_kodi)
                            expires_in = min(expires_in_tv, expires_in_kodi)

                            access_manager.update_access_token(access_token, expires_in)
                        except LoginException as ex:
                            self.handle_exception(context, ex)
                            access_tokens = ['', '']
                            # reset access_token
                            access_manager.update_access_token('')
                            # we clear the cache, so none cached data of an old account will be displayed.
                            context.get_function_cache().clear()

                    # in debug log the login status
                    self._is_logged_in = len(access_tokens) == 2
                    if self._is_logged_in:
                        context.log_debug('User is logged in')
                    else:
                        context.log_debug('User is not logged in')

                    if len(access_tokens) == 0:
                        access_tokens = ['', '']
                    client.set_access_token(access_token=access_tokens[1])
                    client.set_access_token_tv(access_token_tv=access_tokens[0])
                    self._client = client
                    self._client.set_log_error(context.log_error)
                else:
                    self._client = YouTube(items_per_page=items_per_page, language=language, region=region, config=youtube_config)
                    self._client.set_log_error(context.log_error)

                    # in debug log the login status
                    context.log_debug('User is not logged in')

        return self._client

    def get_resource_manager(self, context):
        if not self._resource_manager:
            # self._resource_manager = ResourceManager(weakref.proxy(context), weakref.proxy(self.get_client(context)))
            self._resource_manager = ResourceManager(context, self.get_client(context))
        return self._resource_manager

    def get_alternative_fanart(self, context):
        return self.get_fanart(context)

    def get_fanart(self, context):
        return context.create_resource_path('media', 'fanart.jpg')

    @kodion.RegisterProviderPath('^/uri2addon/$')
    def on_uri2addon(self, context, re_match):
        uri = context.get_param('uri', '')
        if not uri:
            return False

        resolver = UrlResolver(context)
        res_url = resolver.resolve(uri)
        url_converter = UrlToItemConverter(flatten=True)
        url_converter.add_urls([res_url], self, context)
        items = url_converter.get_items(self, context)
        if len(items) > 0:
            return items[0]

        return False

    @kodion.RegisterProviderPath('^/playlist/(?P<playlist_id>[^/]+)/$')
    def _on_playlist(self, context, re_match):
        self.set_content_type(context, kodion.constants.content_type.VIDEOS)

        result = []

        playlist_id = re_match.group('playlist_id')
        page_token = context.get_param('page_token', '')

        # no caching
        json_data = self.get_client(context).get_playlist_items(playlist_id=playlist_id, page_token=page_token)
        if not v3.handle_error(self, context, json_data):
            return False
        result.extend(v3.response_to_items(self, context, json_data))

        return result

    """
    Lists the videos of a playlist.
    path       : '/channel/(?P<channel_id>[^/]+)/playlist/(?P<playlist_id>[^/]+)/'
    channel_id : ['mine'|<CHANNEL_ID>]
    playlist_id: <PLAYLIST_ID>
    """

    @kodion.RegisterProviderPath('^/channel/(?P<channel_id>[^/]+)/playlist/(?P<playlist_id>[^/]+)/$')
    def _on_channel_playlist(self, context, re_match):
        self.set_content_type(context, kodion.constants.content_type.VIDEOS)
        client = self.get_client(context)
        settings = context.get_settings()
        result = []

        playlist_id = re_match.group('playlist_id')
        page_token = context.get_param('page_token', '')

        if re.match('^\s*WL$', playlist_id):
            watch_later_id = settings.get_string('youtube.folder.watch_later.playlist', '').strip()
            if watch_later_id:
                playlist_id = watch_later_id

        # no caching
        json_data = client.get_playlist_items(playlist_id=playlist_id, page_token=page_token)
        if not v3.handle_error(self, context, json_data):
            return False
        result.extend(v3.response_to_items(self, context, json_data))

        return result

    """
    Lists all playlists of a channel.
    path      : '/channel/(?P<channel_id>[^/]+)/playlists/'
    channel_id: <CHANNEL_ID>
    """

    @kodion.RegisterProviderPath('^/channel/(?P<channel_id>[^/]+)/playlists/$')
    def _on_channel_playlists(self, context, re_match):
        self.set_content_type(context, kodion.constants.content_type.FILES)
        result = []

        channel_id = re_match.group('channel_id')
        page_token = context.get_param('page_token', '')

        # no caching
        json_data = self.get_client(context).get_playlists_of_channel(channel_id, page_token)
        if not v3.handle_error(self, context, json_data):
            return False
        result.extend(v3.response_to_items(self, context, json_data))

        return result

    """
    List live streams for channel.
    path      : '/channel/(?P<channel_id>[^/]+)/live/'
    channel_id: <CHANNEL_ID>
    """

    @kodion.RegisterProviderPath('^/channel/(?P<channel_id>[^/]+)/live/$')
    def _on_channel_live(self, context, re_match):
        self.set_content_type(context, kodion.constants.content_type.VIDEOS)
        result = []

        channel_id = re_match.group('channel_id')
        page_token = context.get_param('page_token', '')
        safe_search = context.get_settings().safe_search()

        # no caching
        json_data = self.get_client(context).search(q='', search_type='video', event_type='live', channel_id=channel_id, page_token=page_token, safe_search=safe_search)
        if not v3.handle_error(self, context, json_data):
            return False
        result.extend(v3.response_to_items(self, context, json_data))

        return result

    """
    Lists a playlist folder and all uploaded videos of a channel.
    path      :'/channel|user/(?P<channel_id|username>)[^/]+/'
    channel_id: <CHANNEL_ID>
    """

    @kodion.RegisterProviderPath('^/(?P<method>(channel|user))/(?P<channel_id>[^/]+)/$')
    def _on_channel(self, context, re_match):
        self.set_content_type(context, kodion.constants.content_type.VIDEOS)

        resource_manager = self.get_resource_manager(context)

        result = []

        method = re_match.group('method')
        channel_id = re_match.group('channel_id')
        mine_id = ''

        """
        This is a helper routine if we only have the username of a channel. This will retrieve the correct channel id
        based on the username.
        """
        if method == 'user' or channel_id == 'mine':
            context.log_debug('Trying to get channel id for user "%s"' % channel_id)

            json_data = context.get_function_cache().get(FunctionCache.ONE_DAY,
                                                         self.get_client(context).get_channel_by_username, channel_id)
            if not v3.handle_error(self, context, json_data):
                return False

            # we correct the channel id based on the username
            items = json_data.get('items', [])
            if len(items) > 0:
                if method == 'user':
                    channel_id = items[0]['id']
                else:
                    mine_id = items[0]['id']
            else:
                context.log_warning('Could not find channel ID for user "%s"' % channel_id)
                if method == 'user':
                    return False

        channel_fanarts = resource_manager.get_fanarts([channel_id])
        page = int(context.get_param('page', 1))
        page_token = context.get_param('page_token', '')
        incognito = str(context.get_param('incognito', False)).lower() == 'true'
        addon_id = context.get_param('addon_id', '')
        item_params = {}
        if incognito:
            item_params.update({'incognito': incognito})
        if addon_id:
            item_params.update({'addon_id': addon_id})

        if page == 1:
            playlists_item = DirectoryItem('[B]' + context.localize(self.LOCAL_MAP['youtube.playlists']) + '[/B]',
                                           context.create_uri(['channel', channel_id, 'playlists'], item_params),
                                           image=context.create_resource_path('media', 'playlist.png'))
            playlists_item.set_fanart(channel_fanarts.get(channel_id, self.get_fanart(context)))
            result.append(playlists_item)
            search_live_id = mine_id if mine_id else channel_id
            search_item = kodion.items.NewSearchItem(context, alt_name='[B]' + context.localize(self.LOCAL_MAP['youtube.search']) + '[/B]',
                                                     image=context.create_resource_path('media', 'search.png'),
                                                     fanart=self.get_fanart(context), channel_id=search_live_id, incognito=incognito, addon_id=addon_id)
            result.append(search_item)
            live_item = DirectoryItem('[B]%s[/B]' % context.localize(self.LOCAL_MAP['youtube.live']),
                                      context.create_uri(['channel', search_live_id, 'live'], item_params),
                                      image=context.create_resource_path('media', 'live.png'))
            result.append(live_item)

        playlists = resource_manager.get_related_playlists(channel_id)
        upload_playlist = playlists.get('uploads', '')
        if upload_playlist:
            json_data = context.get_function_cache().get(FunctionCache.ONE_MINUTE * 5,
                                                         self.get_client(context).get_playlist_items, upload_playlist,
                                                         page_token=page_token)
            if not v3.handle_error(self, context, json_data):
                return False

            result.extend(
                v3.response_to_items(self, context, json_data, sort=lambda x: x.get_aired(), reverse_sort=True))

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

    @kodion.RegisterProviderPath('^/play/$')
    def on_play(self, context, re_match):
        params = context.get_params()
        if 'video_id' in params and not 'playlist_id' in params:
            return yt_play.play_video(self, context, re_match)
        elif 'playlist_id' in params:
            return yt_play.play_playlist(self, context, re_match)
        elif 'channel_id' in params and 'live' in params:
            if int(params['live']) > 0:
                return yt_play.play_channel_live(self, context, re_match)
        return False

    @kodion.RegisterProviderPath('^/video/(?P<method>[^/]+)/$')
    def _on_video_x(self, context, re_match):
        method = re_match.group('method')
        return yt_video.process(method, self, context, re_match)

    @kodion.RegisterProviderPath('^/playlist/(?P<method>[^/]+)/(?P<category>[^/]+)/$')
    def _on_playlist_x(self, context, re_match):
        method = re_match.group('method')
        category = re_match.group('category')
        return yt_playlist.process(method, category, self, context, re_match)

    @kodion.RegisterProviderPath('^/subscriptions/(?P<method>[^/]+)/$')
    def _on_subscriptions(self, context, re_match):
        method = re_match.group('method')
        if method == 'list':
            self.set_content_type(context, kodion.constants.content_type.FILES)
        return yt_subscriptions.process(method, self, context, re_match)

    @kodion.RegisterProviderPath('^/special/(?P<category>[^/]+)/$')
    def _on_yt_specials(self, context, re_match):
        category = re_match.group('category')
        if category == 'browse_channels':
            self.set_content_type(context, kodion.constants.content_type.FILES)
        return yt_specials.process(category, self, context, re_match)

    @kodion.RegisterProviderPath('^/history/clear/$')
    def _on_yt_clear_history(self, context, re_match):
        if context.get_ui().on_yes_no_input(context.get_name(), context.localize(self.LOCAL_MAP['youtube.clear_history_confirmation'])):
            json_data = self.get_client(context).clear_watch_history()
            if 'error' not in json_data:
                context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.succeeded']))

    @kodion.RegisterProviderPath('^/watch_later/playlist_id/$')
    def _on_yt_get_watch_later_id(self, context, re_match):
        client = self.get_client(context)
        settings = context.get_settings()
        if self.is_logged_in():
            watch_later_id = None
            while not watch_later_id:
                watch_later_id = client.get_watch_later_id()

                if watch_later_id:
                    settings.set_string('youtube.folder.watch_later.playlist', watch_later_id)
                    context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.succeeded']))
                    break
                else:
                    if not context.get_ui().on_yes_no_input(context.get_name(), context.localize(self.LOCAL_MAP['youtube.failed.watch_later.retry']),
                                                            nolabel=context.localize(self.LOCAL_MAP['youtube.cancel']),
                                                            yeslabel=context.localize(self.LOCAL_MAP['youtube.retry'])):
                        break
        else:
            context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.must.be.signed.in']))

    @kodion.RegisterProviderPath('^/events/post_play/$')
    def _on_post_play(self, context, re_match):
        video_id = context.get_param('video_id', '')
        if video_id:
            client = self.get_client(context)
            settings = context.get_settings()

            if self.is_logged_in():
                # first: update history
                client.update_watch_history(video_id)

                # second: remove video from 'Watch Later' playlist
                if context.get_settings().get_bool('youtube.playlist.watchlater.autoremove', True):
                    watch_later_id = settings.get_string('youtube.folder.watch_later.playlist', '').strip()

                    if watch_later_id:
                        playlist_item_id = client.get_playlist_item_id_of_video_id(playlist_id=watch_later_id, video_id=video_id)
                        if playlist_item_id:
                            json_data = client.remove_video_from_playlist(watch_later_id, playlist_item_id)
                            if not v3.handle_error(self, context, json_data):
                                return False

                history_playlist_id = settings.get_string('youtube.folder.history.playlist', '').strip()
                if history_playlist_id:
                    json_data = client.add_video_to_playlist(history_playlist_id, video_id)
                    if not v3.handle_error(self, context, json_data):
                        return False

                # rate video
                if context.get_settings().get_bool('youtube.post.play.rate', False):
                    json_data = client.get_video_rating(video_id)
                    if not v3.handle_error(self, context, json_data):
                        return False
                    items = json_data.get('items', [{'rating': 'none'}])
                    rating = items[0].get('rating', 'none')
                    if rating == 'none':
                        rating_match = re.search('/(?P<video_id>[^/]+)/(?P<rating>[^/]+)', '/%s/%s/' % (video_id, rating))
                        yt_video.process('rate', self, context, rating_match)
        else:
            context.log_warning('Missing video ID for post play event')
        return True

    @kodion.RegisterProviderPath('^/sign/(?P<mode>[^/]+)/$')
    def _on_sign(self, context, re_match):
        sign_out_confirmed = context.get_param('confirmed', '').lower() == 'true'
        mode = re_match.group('mode')
        if (mode == 'in') and context.get_access_manager().has_refresh_token():
            yt_login.process('out', self, context, re_match, sign_out_refresh=False)

        if not sign_out_confirmed:
            if (mode == 'out') and context.get_ui().on_yes_no_input(context.get_name(), context.localize(self.LOCAL_MAP['youtube.sign.out']) + '?'):
                sign_out_confirmed = True

        if (mode == 'in') or ((mode == 'out') and sign_out_confirmed):
            yt_login.process(mode, self, context, re_match)
        return True

    @kodion.RegisterProviderPath('^/search/$')
    def endpoint_search(self, context, re_match):
        query = context.get_param('q', '')
        if not query:
            return []

        return self.on_search(query, context, re_match)

    def on_search(self, search_text, context, re_match):
        result = []

        channel_id = context.get_param('channel_id', '')
        page_token = context.get_param('page_token', '')
        search_type = context.get_param('search_type', 'video')
        event_type = context.get_param('event_type', '')
        safe_search = context.get_settings().safe_search()
        page = int(context.get_param('page', 1))

        context.set_param('q', search_text)
        if context.get_path() == '/kodion/search/input/':
            context.set_path('/kodion/search/query/')

        if search_type == 'video':
            self.set_content_type(context, kodion.constants.content_type.VIDEOS)
        else:
            self.set_content_type(context, kodion.constants.content_type.FILES)

        if page == 1 and search_type == 'video' and not event_type:
            if not channel_id:
                channel_params = {}
                channel_params.update(context.get_params())
                channel_params['search_type'] = 'channel'
                channel_item = DirectoryItem('[B]' + context.localize(self.LOCAL_MAP['youtube.channels']) + '[/B]',
                                             context.create_uri([context.get_path().replace('input', 'query')], channel_params),
                                             image=context.create_resource_path('media', 'channels.png'))
                channel_item.set_fanart(self.get_fanart(context))
                result.append(channel_item)

            playlist_params = {}
            playlist_params.update(context.get_params())
            playlist_params['search_type'] = 'playlist'
            playlist_item = DirectoryItem('[B]' + context.localize(self.LOCAL_MAP['youtube.playlists']) + '[/B]',
                                          context.create_uri([context.get_path().replace('input', 'query')], playlist_params),
                                          image=context.create_resource_path('media', 'playlist.png'))
            playlist_item.set_fanart(self.get_fanart(context))
            result.append(playlist_item)

            if not channel_id:
                # live
                live_params = {}
                live_params.update(context.get_params())
                live_params['search_type'] = 'video'
                live_params['event_type'] = 'live'
                live_item = DirectoryItem('[B]%s[/B]' % context.localize(self.LOCAL_MAP['youtube.live']),
                                          context.create_uri([context.get_path().replace('input', 'query')], live_params),
                                          image=context.create_resource_path('media', 'live.png'))
                result.append(live_item)

        json_data = context.get_function_cache().get(FunctionCache.ONE_MINUTE * 10, self.get_client(context).search,
                                                     q=search_text, search_type=search_type, event_type=event_type,
                                                     safe_search=safe_search, page_token=page_token, channel_id=channel_id)
        if not v3.handle_error(self, context, json_data):
            return False
        result.extend(v3.response_to_items(self, context, json_data))
        return result

    @kodion.RegisterProviderPath('^/config/(?P<switch>[^/]+)/$')
    def configure_addon(self, context, re_match):
        switch = re_match.group('switch')
        settings = context.get_settings()
        if switch == 'youtube':
            context._addon.openSettings()
        elif switch == 'mpd':
            use_dash = context.use_inputstream_adaptive()
            if use_dash:
                xbmcaddon.Addon(id='inputstream.adaptive').openSettings()
            else:
                settings.set_bool('kodion.video.quality.mpd', False)
        elif switch == 'subtitles':
            yt_language = context.get_settings().get_string('youtube.language', 'en-US')
            sub_setting = context.get_settings().subtitle_languages()

            if yt_language.startswith('en'):
                sub_opts = [context.localize(self.LOCAL_MAP['youtube.none']), context.localize(self.LOCAL_MAP['youtube.prompt']),
                            context.localize(self.LOCAL_MAP['youtube.subtitle._with_fallback']) % ('en', 'en-US/en-GB'), yt_language,
                            '%s (%s)' % (yt_language, context.localize(self.LOCAL_MAP['youtube.subtitle.no.auto.generated']))]

            else:
                sub_opts = [context.localize(self.LOCAL_MAP['youtube.none']), context.localize(self.LOCAL_MAP['youtube.prompt']),
                            context.localize(self.LOCAL_MAP['youtube.subtitle._with_fallback']) % (yt_language, 'en'), yt_language,
                            '%s (%s)' % (yt_language, context.localize(self.LOCAL_MAP['youtube.subtitle.no.auto.generated']))]

            sub_opts[sub_setting] = '[B]%s[/B]' % sub_opts[sub_setting]

            result = context.get_ui().on_select(context.localize(self.LOCAL_MAP['youtube.subtitle.language']), sub_opts)
            if result == -1:
                return False
            context.get_settings().set_subtitle_languages(result)
        elif switch == 'listen_ip':
            local_ranges = ('10.', '172.16.', '192.168.')
            addresses = [iface[4][0] for iface in socket.getaddrinfo(socket.gethostname(), None) if iface[4][0].startswith(local_ranges)] + ['127.0.0.1', '0.0.0.0']
            selected_address = context.get_ui().on_select(context.localize(self.LOCAL_MAP['youtube.select.listen.ip']), addresses)
            if selected_address == -1:
                return False
            else:
                context.get_settings().set_httpd_listen(addresses[selected_address])
        else:
            return False

    @kodion.RegisterProviderPath('^/my_subscriptions/filter/$')
    def manage_my_subscription_filter(self, context, re_match):
        params = context.get_params()
        action = params.get('action')
        channel = params.get('channel_name')
        if (not channel) or (not action):
            return

        filter_enabled = context.get_settings().get_bool('youtube.folder.my_subscriptions_filtered.show', False)
        if not filter_enabled:
            return

        channel_name = channel.lower()
        channel_name = channel_name.replace(',', '')

        filter_string = context.get_settings().get_string('youtube.filter.my_subscriptions_filtered.list', '')
        filter_string = filter_string.replace(', ', ',')
        filter_list = filter_string.split(',')
        filter_list = [x.lower() for x in filter_list]

        if action == 'add':
            if channel_name not in filter_list:
                filter_list.append(channel_name)
        elif action == 'remove':
            if channel_name in filter_list:
                filter_list = [chan_name for chan_name in filter_list if chan_name != channel_name]

        modified_string = ','.join(filter_list).lstrip(',')
        if filter_string != modified_string:
            context.get_settings().set_string('youtube.filter.my_subscriptions_filtered.list', modified_string)
            message = ''
            if action == 'add':
                message = context.localize(self.LOCAL_MAP['youtube.added.my_subscriptions.filter'])
            elif action == 'remove':
                message = context.localize(self.LOCAL_MAP['youtube.removed.my_subscriptions.filter'])
            if message:
                context.get_ui().show_notification(message=message)
        context.get_ui().refresh_container()

    @kodion.RegisterProviderPath('^/maintain/(?P<maint_type>[^/]+)/(?P<action>[^/]+)/$')
    def maintenance_actions(self, context, re_match):
        maint_type = re_match.group('maint_type')
        action = re_match.group('action')
        if action == 'clear':
            if maint_type == 'function_cache':
                if context.get_ui().on_remove_content(context.localize(self.LOCAL_MAP['youtube.function.cache'])):
                    context.get_function_cache().clear()
                    context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.succeeded']))
            elif maint_type == 'search_cache':
                if context.get_ui().on_remove_content(context.localize(self.LOCAL_MAP['youtube.search.history'])):
                    context.get_search_history().clear()
                    context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.succeeded']))
        elif action == 'reset':
            if maint_type == 'access_manager':
                if context.get_ui().on_yes_no_input(context.get_name(), context.localize(self.LOCAL_MAP['youtube.reset.access.manager.confirm'])):
                    try:
                        context.get_function_cache().clear()
                        access_manager = context.get_access_manager()
                        client = self.get_client(context)
                        if access_manager.has_refresh_token():
                            refresh_tokens = access_manager.get_refresh_token().split('|')
                            refresh_tokens = list(set(refresh_tokens))
                            for refresh_token in refresh_tokens:
                                try:
                                    client.revoke(refresh_token)
                                except:
                                    pass
                        self.reset_client()
                        access_manager.update_access_token(access_token='', refresh_token='')
                        context.get_ui().refresh_container()
                        context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.succeeded']))
                    except:
                        context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.failed']))
        elif action == 'delete':
            _maint_files = {'function_cache': 'cache.sqlite',
                            'search_cache': 'search.sqlite',
                            'settings_xml': 'settings.xml',
                            'api_keys': 'api_keys.json',
                            'access_manager': 'access_manager.json',
                            'temp_files': 'special://temp/plugin.video.youtube/'}
            _file = _maint_files.get(maint_type, '')
            success = False
            if _file:
                if 'sqlite' in _file:
                    _file_w_path = os.path.join(context._get_cache_path(), _file)
                elif maint_type == 'temp_files':
                    _file_w_path = _file
                else:
                    _file_w_path = os.path.join(context._data_path, _file)
                if context.get_ui().on_delete_content(_file):
                    if maint_type == 'temp_files':
                        _trans_path = xbmc.translatePath(_file_w_path)
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
                        context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.succeeded']))
                    else:
                        context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.failed']))
        elif action == 'install':
            if maint_type == 'inputstreamhelper':
                if context.get_system_version().get_version()[0] >= 17:
                    try:
                        xbmcaddon.Addon('script.module.inputstreamhelper')
                        context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.inputstreamhelper.is.installed']))
                    except RuntimeError:
                        context.execute('InstallAddon(script.module.inputstreamhelper)')
                else:
                    context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.requires.krypton']))

    @kodion.RegisterProviderPath('^/api/update/$')
    def api_key_update(self, context, re_match):
        settings = context.get_settings()
        params = context.get_params()
        client_id = params.get('client_id')
        client_secret = params.get('client_secret')
        api_key = params.get('api_key')
        enable = params.get('enable', '').lower() == 'true'
        updated_list = []
        log_list = []

        if api_key:
            settings.set_string('youtube.api.key', api_key)
            updated_list.append(context.localize(self.LOCAL_MAP['youtube.api.key']))
            log_list.append('Key')
        if client_id:
            settings.set_string('youtube.api.id', client_id)
            updated_list.append(context.localize(self.LOCAL_MAP['youtube.api.id']))
            log_list.append('Id')
        if client_secret:
            settings.set_string('youtube.api.secret', client_secret)
            updated_list.append(context.localize(self.LOCAL_MAP['youtube.api.secret']))
            log_list.append('Secret')
        if updated_list:
            context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.updated_']) % ', '.join(updated_list))
        context.log_debug('Updated API keys: %s' % ', '.join(log_list))

        client_id = settings.get_string('youtube.api.id', '')
        client_secret = settings.get_string('youtube.api.secret', '')
        api_key = settings.get_string('youtube.api.key', '')
        missing_list = []
        log_list = []

        if enable and client_id and client_secret and api_key:
            settings.set_bool('youtube.api.enable', True)
            context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.api.personal.enabled']))
            context.log_debug('Personal API keys enabled')
        elif enable:
            if not api_key:
                missing_list.append(context.localize(self.LOCAL_MAP['youtube.api.key']))
                log_list.append('Key')
            if not client_id:
                missing_list.append(context.localize(self.LOCAL_MAP['youtube.api.id']))
                log_list.append('Id')
            if not client_secret:
                missing_list.append(context.localize(self.LOCAL_MAP['youtube.api.secret']))
                log_list.append('Secret')
            settings.set_bool('youtube.api.enable', False)
            context.get_ui().show_notification(context.localize(self.LOCAL_MAP['youtube.api.personal.failed']) % ', '.join(missing_list))
            context.log_debug('Failed to enable personal API keys. Missing: %s' % ', '.join(log_list))

    def on_root(self, context, re_match):
        """
        Support old YouTube url calls, but also log a deprecation warnings.
        """
        old_action = context.get_param('action', '')
        if old_action:
            return yt_old_actions.process_old_action(self, context, re_match)

        settings = context.get_settings()

        self.get_client(context)
        resource_manager = self.get_resource_manager(context)

        self.set_content_type(context, kodion.constants.content_type.FILES)

        result = []

        # sign in
        if not self.is_logged_in() and settings.get_bool('youtube.folder.sign.in.show', True):
            sign_in_item = DirectoryItem('[B]%s[/B]' % context.localize(self.LOCAL_MAP['youtube.sign.in']),
                                         context.create_uri(['sign', 'in']),
                                         image=context.create_resource_path('media', 'sign_in.png'))
            sign_in_item.set_fanart(self.get_fanart(context))
            result.append(sign_in_item)

        if self.is_logged_in() and settings.get_bool('youtube.folder.my_subscriptions.show', True):
            # my subscription
            my_subscriptions_item = DirectoryItem(
                '[B]' + context.localize(self.LOCAL_MAP['youtube.my_subscriptions']) + '[/B]',
                context.create_uri(['special', 'new_uploaded_videos_tv']),
                context.create_resource_path('media', 'new_uploads.png'))
            my_subscriptions_item.set_fanart(self.get_fanart(context))
            result.append(my_subscriptions_item)

        if self.is_logged_in() and settings.get_bool('youtube.folder.my_subscriptions_filtered.show', True):
            # my subscriptions filtered
            my_subscriptions_filtered_item = DirectoryItem(
                context.localize(self.LOCAL_MAP['youtube.my_subscriptions_filtered']),
                context.create_uri(['special', 'new_uploaded_videos_tv_filtered']),
                context.create_resource_path('media', 'new_uploads.png'))
            my_subscriptions_filtered_item.set_fanart(self.get_fanart(context))
            result.append(my_subscriptions_filtered_item)

        # Recommendations
        if self.is_logged_in() and settings.get_bool('youtube.folder.recommendations.show', True):
            recommendations_item = DirectoryItem(
                context.localize(self.LOCAL_MAP['youtube.recommendations']),
                context.create_uri(['special', 'recommendations']),
                context.create_resource_path('media', 'popular.png'))
            recommendations_item.set_fanart(self.get_fanart(context))
            result.append(recommendations_item)

        # what to watch
        if settings.get_bool('youtube.folder.popular_right_now.show', True):
            what_to_watch_item = DirectoryItem(
                context.localize(self.LOCAL_MAP['youtube.popular_right_now']),
                context.create_uri(['special', 'popular_right_now']),
                context.create_resource_path('media', 'popular.png'))
            what_to_watch_item.set_fanart(self.get_fanart(context))
            result.append(what_to_watch_item)

        # search
        if settings.get_bool('youtube.folder.search.show', True):
            search_item = kodion.items.SearchItem(context, image=context.create_resource_path('media', 'search.png'),
                                                  fanart=self.get_fanart(context))
            result.append(search_item)

        if settings.get_bool('youtube.folder.quick_search.show', True):
            quick_search_item = kodion.items.NewSearchItem(context,
                                                           alt_name=context.localize(self.LOCAL_MAP['youtube.quick.search']),
                                                           fanart=self.get_fanart(context))
            result.append(quick_search_item)

        if settings.get_bool('youtube.folder.quick_search_incognito.show', True):
            quick_search_incognito_item = kodion.items.NewSearchItem(context,
                                                                     alt_name=context.localize(self.LOCAL_MAP['youtube.quick.search.incognito']),
                                                                     image=context.create_resource_path('media', 'search.png'),
                                                                     fanart=self.get_fanart(context),
                                                                     incognito=True)
            result.append(quick_search_incognito_item)

        # subscriptions
        if self.is_logged_in():
            playlists = resource_manager.get_related_playlists(channel_id='mine')
            if 'watchLater' in playlists:
                cplid = settings.get_string('youtube.folder.watch_later.playlist', '').strip()
                playlists['watchLater'] = cplid if cplid else ' WL'
            if 'watchHistory' in playlists:
                cplid = settings.get_string('youtube.folder.history.playlist', '').strip()
                playlists['watchHistory'] = cplid if cplid else 'HL'

            # my channel
            if settings.get_bool('youtube.folder.my_channel.show', True):
                my_channel_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.my_channel']),
                                                context.create_uri(['channel', 'mine']),
                                                image=context.create_resource_path('media', 'channel.png'))
                my_channel_item.set_fanart(self.get_fanart(context))
                result.append(my_channel_item)

            # purchases
            if settings.get_bool('youtube.folder.purchases.show', False) and \
                    settings.use_dash() and \
                    settings.use_dash_proxy() and \
                    'drm' in context.inputstream_adaptive_capabilities():
                purchases_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.purchases']),
                                               context.create_uri(['special', 'purchases']),
                                               image=context.create_resource_path('media', 'popular.png'))
                purchases_item.set_fanart(self.get_fanart(context))
                result.append(purchases_item)

            # watch later
            if 'watchLater' in playlists and settings.get_bool('youtube.folder.watch_later.show', True):
                watch_later_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.watch_later']),
                                                 context.create_uri(
                                                     ['channel', 'mine', 'playlist', playlists['watchLater']]),
                                                 context.create_resource_path('media', 'watch_later.png'))
                watch_later_item.set_fanart(self.get_fanart(context))
                context_menu = []
                yt_context_menu.append_play_all_from_playlist(context_menu, self, context, playlists['watchLater'])
                watch_later_item.set_context_menu(context_menu)
                result.append(watch_later_item)

            # liked videos
            if 'likes' in playlists and settings.get_bool('youtube.folder.liked_videos.show', True):
                liked_videos_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.video.liked']),
                                                  context.create_uri(
                                                      ['channel', 'mine', 'playlist', playlists['likes']]),
                                                  context.create_resource_path('media', 'likes.png'))
                liked_videos_item.set_fanart(self.get_fanart(context))
                context_menu = []
                yt_context_menu.append_play_all_from_playlist(context_menu, self, context, playlists['likes'])
                liked_videos_item.set_context_menu(context_menu)
                result.append(liked_videos_item)

            # disliked videos
            if settings.get_bool('youtube.folder.disliked_videos.show', True):
                disliked_videos_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.video.disliked']),
                                                     context.create_uri(['special', 'disliked_videos']),
                                                     context.create_resource_path('media', 'dislikes.png'))
                disliked_videos_item.set_fanart(self.get_fanart(context))
                result.append(disliked_videos_item)

            # history
            if 'watchHistory' in playlists and settings.get_bool('youtube.folder.history.show', False):
                if playlists['watchHistory'] == 'HL':
                    watch_history_item = DirectoryItem(
                        context.localize(self.LOCAL_MAP['youtube.history']),
                        context.create_uri(['special', 'watch_history_tv']),
                        context.create_resource_path('media', 'history.png'))
                    watch_history_item.set_fanart(self.get_fanart(context))
                else:
                    watch_history_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.history']),
                                                       context.create_uri(
                                                           ['channel', 'mine', 'playlist', playlists['watchHistory']]),
                                                       context.create_resource_path('media', 'history.png'))
                    watch_history_item.set_fanart(self.get_fanart(context))
                result.append(watch_history_item)

            # (my) playlists
            if settings.get_bool('youtube.folder.playlists.show', True):
                playlists_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.playlists']),
                                               context.create_uri(['channel', 'mine', 'playlists']),
                                               context.create_resource_path('media', 'playlist.png'))
                playlists_item.set_fanart(self.get_fanart(context))
                result.append(playlists_item)

            # saved playlists
            if settings.get_bool('youtube.folder.saved.playlists.show', True):
                playlists_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.saved.playlists']),
                                               context.create_uri(['special', 'saved_playlists']),
                                               context.create_resource_path('media', 'playlist.png'))
                playlists_item.set_fanart(self.get_fanart(context))
                result.append(playlists_item)

            # subscriptions
            if settings.get_bool('youtube.folder.subscriptions.show', True):
                subscriptions_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.subscriptions']),
                                                   context.create_uri(['subscriptions', 'list']),
                                                   image=context.create_resource_path('media', 'channels.png'))
                subscriptions_item.set_fanart(self.get_fanart(context))
                result.append(subscriptions_item)

            # browse channels
            if settings.get_bool('youtube.folder.browse_channels.show', True):
                browse_channels_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.browse_channels']),
                                                     context.create_uri(['special', 'browse_channels']),
                                                     image=context.create_resource_path('media', 'browse_channels.png'))
                browse_channels_item.set_fanart(self.get_fanart(context))
                result.append(browse_channels_item)

        # live events
        if settings.get_bool('youtube.folder.live.show', True):
            live_events_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.live']),
                                             context.create_uri(['special', 'live']),
                                             image=context.create_resource_path('media', 'live.png'))
            live_events_item.set_fanart(self.get_fanart(context))
            result.append(live_events_item)

        # sign out
        if self.is_logged_in() and settings.get_bool('youtube.folder.sign.out.show', True):
            sign_out_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.sign.out']),
                                          context.create_uri(['sign', 'out']),
                                          image=context.create_resource_path('media', 'sign_out.png'))
            sign_out_item.set_fanart(self.get_fanart(context))
            result.append(sign_out_item)

        if settings.get_bool('youtube.folder.settings.show', True):
            settings_menu_item = DirectoryItem(context.localize(self.LOCAL_MAP['youtube.settings']),
                                               context.create_uri(['config', 'youtube']),
                                               image=context.create_resource_path('media', 'settings.png'))
            settings_menu_item.set_fanart(self.get_fanart(context))
            result.append(settings_menu_item)

        return result

    def set_content_type(self, context, content_type):
        context.set_content_type(content_type)
        if content_type == kodion.constants.content_type.VIDEOS:
            context.add_sort_method(kodion.constants.sort_method.UNSORTED,
                                    kodion.constants.sort_method.VIDEO_RUNTIME,
                                    kodion.constants.sort_method.DATE_ADDED,
                                    kodion.constants.sort_method.TRACK_NUMBER,
                                    kodion.constants.sort_method.VIDEO_TITLE,
                                    kodion.constants.sort_method.DATE)

    def handle_exception(self, context, exception_to_handle):
        if isinstance(exception_to_handle, LoginException):
            failed_refresh = False
            context.get_access_manager().update_access_token('')

            msg = message = exception_to_handle.get_message()
            error = ''
            code = ''

            if isinstance(msg, dict):
                if 'error_description' in msg:
                    message = msg['error_description']
                elif 'message' in msg:
                    message = msg['message']

                if 'error' in msg:
                    error = msg['error']

                if 'code' in msg:
                    code = msg['code']

                if message == u'Unauthorized' and error == u'unauthorized_client':
                    failed_refresh = True

            if error and code:
                title = '%s: [%s] %s' % ('LoginException', code, error)
            elif error:
                title = '%s: %s' % ('LoginException', error)
            else:
                title = 'LoginException'

            context.get_ui().show_notification(message, title)
            context.log_error('%s: %s' % (title, message))
            if not failed_refresh:
                context.get_ui().open_settings()
            return False

        return True
